"""Standard-library-only sticker library and CLI."""
import argparse
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import copy
import hashlib
import re
import sqlite3
import time
import zipfile
from collections import Counter

ROOT = Path(os.environ.get('GB_MEME_ROOT', Path(__file__).resolve().parents[1])).resolve()
PACKS = ['demo', 'user']
VERSION = '2.1.0'
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
MOODS = 'happy angry sad shy confused surprised sleep work daily like fool sigh see cpu morning meow givemoney baka color think celebrate thanks sorry cool hug'.split()
KEYWORDS = {
    'happy': ['开心', '哈哈', '笑死', 'happy', 'haha', '🙂', '😂'],
    'angry': ['生气', 'angry', '😡'], 'sad': ['哭', '难过', 'sad', '😭'],
    'shy': ['害羞', 'shy', '😳'], 'confused': ['困惑', '疑惑', 'confused', '❓'],
    'surprised': ['震惊', '惊讶', 'surprised', '😮'],
    'sleep': ['睡觉', '晚安', 'sleep', 'good night', '😴'],
    'work': ['加班', '工作', 'work'], 'daily': ['摸鱼', 'daily'],
    'like': ['喜欢', '爱你', 'like', '❤️'], 'sigh': ['无语', 'sigh'],
    'morning': ['早安', 'morning'], 'think': ['思考', 'think', '🤔'],
    'celebrate': ['庆祝', '加油', 'celebrate', '✨', '🎉'],
    'thanks': ['谢谢', '感谢', 'thanks', 'thank you'],
    'sorry': ['抱歉', '对不起', 'sorry'], 'cool': ['酷', 'cool', '😎'],
    'hug': ['抱抱', 'hug'],
}
TRIGGERS = ['发表情', '发个表情', '斗图', '贴图', 'sticker', 'meme', '表情']


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


KEYWORDS.update({
    'sad': KEYWORDS['sad'] + ['哭哭', '呜呜', '泪目', '伤心', '委屈', '难受'],
    'happy': KEYWORDS['happy'] + ['哈哈哈', '乐死', '好笑', '高兴', '绷不住'],
    'sigh': ['无语', '冷漠', '叹气', '心累', 'sigh'],
    'angry': KEYWORDS['angry'] + ['愤怒', '气死', '别吵'],
    'confused': KEYWORDS['confused'] + ['不懂', '你确定', '问号'],
    'shy': KEYWORDS['shy'] + ['脸红', '不好意思'],
    'sleep': KEYWORDS['sleep'] + ['困了', '被窝', '休息'],
    'work': KEYWORDS['work'] + ['开工', '上班', '忙碌'],
    'celebrate': KEYWORDS['celebrate'] + ['成功', '搞定', '好耶'],
    'meow': ['喵', 'meow'], 'cpu': ['烧脑', '宕机', 'cpu'],
})
DEFAULT = {
    'mode': 'active', 'packs': PACKS,
    'features': dict.fromkeys(['semantic', 'gif_prefer', 'task_events', 'emotion_fsm', 'rate_limit', 'dedupe', 'poke'], True),
    'cooldown_seconds': 8, 'min_interval_seconds': 3, 'max_per_hour': 40,
    'dedupe_window': 12, 'prefer_animated': True, 'fsm_stickiness': 2,
    'semantic_threshold': 0.12,
}
ACTIONS = {'start': ['work', 'cpu'], 'working': ['work', 'cpu'],
           'success': ['celebrate', 'happy', 'like'], 'done': ['celebrate', 'happy', 'like'],
           'fail': ['sad', 'angry', 'confused'], 'error': ['sad', 'angry', 'confused'],
           'wait': ['daily', 'sleep'], 'idle': ['daily', 'sleep'],
           'poke': ['shy', 'meow', 'surprised', 'happy'], 'poke_back': ['shy', 'meow', 'surprised', 'happy'],
           'morning': ['morning'], 'night': ['sleep']}


def valid_id(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[\w-]+', value))


def config():
    path = ROOT / 'data/config.json'
    value = copy.deepcopy(DEFAULT)
    try:
        supplied = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        value.update(supplied)
        value['features'] = {**DEFAULT['features'], **supplied.get('features', {})}
        if value['mode'] not in ('active', 'normal') or not isinstance(value['packs'], list):
            raise ValueError('invalid mode/packs')
        value['packs'] = [p for p in value['packs'] if p != 'grokbot']
        if any(not valid_id(p) for p in value['packs']):
            raise ValueError('invalid pack id')
        if any(type(v) is not bool for v in value['features'].values()):
            raise ValueError('invalid feature flag')
        for field in ('cooldown_seconds', 'min_interval_seconds', 'max_per_hour', 'dedupe_window', 'fsm_stickiness', 'semantic_threshold'):
            if type(value[field]) not in (float, int) or value[field] < 0:
                raise ValueError('invalid numeric setting')
        if not isinstance(value.get('keywords', KEYWORDS), dict):
            raise ValueError('invalid keywords')
        for words in [*value.get('keywords', KEYWORDS).values(), value.get('triggers', TRIGGERS)]:
            if not isinstance(words, list) or any(not isinstance(w, str) or not w for w in words):
                raise ValueError('invalid words')
    except (ValueError, TypeError, AttributeError):
        if path.exists():
            shutil.copy2(path, path.with_name(f'config.broken.{time.time_ns()}.json'))
        value = copy.deepcopy(DEFAULT)
    if not path.exists() or value != read_json(path, None):
        write_json(path, value)
    return value


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return copy.deepcopy(default)


def rebuild():
    rows = []
    for base in sorted((ROOT / 'stickers').glob('*')):
        if not base.is_dir() or not valid_id(base.name):
            continue
        manifest = read_json(base / 'manifest.json', {})
        metadata = {}
        db = base / 'index.db'
        if db.is_file():
            try:
                with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as connection:
                    for path, caption, words in connection.execute('SELECT path, caption, keywords FROM memes'):
                        metadata[path.replace('\\', '/')] = (caption, words)
            except sqlite3.Error:
                pass
        for path in sorted(base.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS or not path.resolve().is_relative_to(base.resolve()):
                continue
            relative = path.relative_to(base)
            parts = relative.parts[1:] if relative.parts[0] == 'memes' else relative.parts
            mood = parts[0] if len(parts) > 1 else 'inbox'
            caption, words = metadata.get(relative.as_posix(), (path.stem, KEYWORDS.get(mood, [mood])))
            if isinstance(words, str):
                try:
                    words = json.loads(words)
                except ValueError:
                    words = words.split()
            if not isinstance(words, list):
                words = [str(words)]
            rows.append({'id': path.stem, 'pack': base.name, 'pack_name': manifest.get('name', base.name),
                         'mood': mood, 'path': path.relative_to(ROOT).as_posix(), 'description': caption or path.stem,
                         'keywords': words, 'animated': path.suffix.lower() == '.gif',
                         'content_hash': hashlib.sha256(path.read_bytes()).hexdigest()})
    write_json(ROOT / 'data/index.json', rows)
    return rows


def index():
    rows = read_json(ROOT / 'data/index.json', None)
    if not isinstance(rows, list) or not rows:
        return rebuild()
    for row in rows:
        path = row.get('path') if isinstance(row, dict) else None
        if (not isinstance(path, str) or not path or 'content_hash' not in row or 'animated' not in row
                or (Path(path).is_absolute() and not Path(path).is_relative_to(ROOT))):
            return rebuild()
    return rows


def resolve(row):
    path = Path(row['path'])
    return path if path.is_absolute() else ROOT / path


def import_pack(source):
    source = Path(source).resolve()
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        if source.is_file() and zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as archive:
                for info in archive.infolist():
                    target = stage / info.filename
                    if '\\' in info.filename or not target.resolve().is_relative_to(stage) or (info.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('unsafe archive path')
                archive.extractall(stage)
        elif source.is_dir():
            if any(p.is_symlink() for p in source.rglob('*')):
                raise ValueError('symlinks are not supported')
            shutil.copytree(source, stage, dirs_exist_ok=True)
        else:
            raise ValueError(f'unsupported or missing pack: {source}')
        manifests = list(stage.rglob('manifest.json'))
        if len(manifests) > 1:
            raise ValueError('multiple manifests')
        base = manifests[0].parent if manifests else stage
        manifest = json.loads(manifests[0].read_text(encoding='utf-8-sig')) if manifests else {'id': source.stem, 'name': source.stem}
        pack = manifest.get('id')
        if not valid_id(pack):
            raise ValueError('invalid manifest.id')
        dest = ROOT / 'stickers' / pack
        if dest.is_symlink():
            raise ValueError('unsafe pack destination')
        # Preflight existing paths so an old symlink cannot redirect an overwrite.
        if dest.exists() and any(p.is_symlink() for p in dest.rglob('*')):
            raise ValueError('unsafe pack destination')
        shutil.copytree(base, dest, dirs_exist_ok=True)
        write_json(dest / 'manifest.json', manifest)
        return {'id': pack, 'name': manifest.get('name', pack)}


def normalize(text):
    return ''.join(c for c in text.casefold() if c.isalnum())


def dice(left, right):
    def grams(text):
        text = normalize(text)
        return set(text[i:i+2] for i in range(len(text)-1))
    a, b = grams(left), grams(right)
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0


def pick(args, cfg):
    features = cfg['features']
    event = args.event
    if event in ('poke', 'poke_back') and not features['poke']:
        return {'ok': True, 'send': False, 'reason': 'disabled'}
    runtime = read_json(ROOT / 'data/runtime.json', {})
    available = [r for r in index() if r['pack'] in cfg['packs'] and resolve(r).is_file()]
    text = args.text.casefold()
    mood, keyword = next(((m, k) for m, words in cfg.get('keywords', KEYWORDS).items() for k in words if k.casefold() in text), (None, None))
    trigger = next((k for k in cfg.get('triggers', TRIGGERS) if k.casefold() in text), None)
    reason = f'keyword:{keyword}' if keyword else (f'trigger:{trigger}' if trigger else '')
    semantic_row = None
    if not mood and features['semantic'] and text and available:
        best = max(available, key=lambda r: dice(text, r['description'] + ' ' + ' '.join(r['keywords'])))
        score = dice(text, best['description'] + ' ' + ' '.join(best['keywords']))
        if score > 0 and score >= cfg['semantic_threshold']:
            mood, semantic_row = best['mood'], best
            reason = f'semantic:{args.text}'
    actions = read_json(ROOT / 'data/actions.json', ACTIONS)
    mapped = actions.get(event) if features['task_events'] else None
    if mapped and isinstance(mapped, list):
        if event in ('poke', 'poke_back'):
            offset = runtime.get('poke_index', 0) % len(mapped)
            mapped = mapped[offset:] + mapped[:offset]
        mood = next((m for m in mapped if any(r['mood'] == m for r in available)), mapped[0])
        semantic_row = None
        reason = f'event:{event}'
    fsm = runtime.get('fsm', {})
    strong = bool(keyword or mapped or args.force)
    if features['emotion_fsm'] and not strong and fsm.get('mood') and fsm.get('streak', 0) < cfg['fsm_stickiness']:
        mood = fsm['mood']
        semantic_row = None
        reason = (reason + '|' if reason else '') + f'fsm:{mood}'
    if cfg['mode'] == 'normal' and not args.force and not mood and not trigger:
        return {'ok': True, 'send': False, 'reason': 'no_trigger'}
    mood = mood or 'daily'
    reason = reason or ('force' if args.force else 'active:daily')
    candidates = [r for r in available if r['mood'] == mood] or [r for r in available if r['mood'] == 'daily'] or available
    if not candidates:
        return {'ok': True, 'send': False, 'reason': 'no_candidate'}
    mood = candidates[0]['mood']
    now = time.time()
    bucket = runtime.get('hour_bucket', {})
    gates = {'cooldown': now - runtime.get('last_mood_at', {}).get(mood, 0) < cfg['cooldown_seconds'],
             'min_interval': now - runtime.get('last_sent_at', 0) < cfg['min_interval_seconds'],
             'max_per_hour': bucket.get('hour') == int(now // 3600) and bucket.get('count', 0) >= cfg['max_per_hour']}
    if features['rate_limit'] and any(gates.values()):
        return {'ok': True, 'send': False, 'reason': 'rate_limited', 'gates': gates}
    if features['dedupe'] and cfg['dedupe_window']:
        fresh = [r for r in candidates if r['path'] not in runtime.get('last_keys', []) and r['content_hash'] not in runtime.get('last_hashes', [])]
        candidates = fresh or candidates
    prefer = cfg['prefer_animated'] if args.prefer_gif is None else args.prefer_gif
    if features['gif_prefer'] and prefer:
        candidates = [r for r in candidates if r['animated']] or candidates
    row = semantic_row if semantic_row in candidates else random.choice(candidates)
    window = int(cfg['dedupe_window'])
    for field, value in [('last_ids', row['id']), ('last_keys', row['path']), ('last_hashes', row['content_hash'])]:
        runtime[field] = (runtime.get(field, []) + [value])[-window:] if window else []
    runtime.update(last_sent_at=now, hour_bucket={'hour': int(now // 3600), 'count': (bucket.get('count', 0) if bucket.get('hour') == int(now // 3600) else 0) + 1}, last_event=event)
    runtime.setdefault('last_mood_at', {})[row['mood']] = now
    if features['emotion_fsm']:
        runtime['fsm'] = {'mood': row['mood'], 'streak': fsm.get('streak', 0) + 1 if fsm.get('mood') == row['mood'] else 1}
    if event in ('poke', 'poke_back'):
        runtime['poke_index'] = runtime.get('poke_index', 0) + 1
    write_json(ROOT / 'data/runtime.json', runtime)
    result = {k: row[k] for k in ('mood', 'id', 'pack', 'animated')}
    result['path'] = str(resolve(row))
    return {'ok': True, 'send': True, **result, 'reason': reason, 'gates': gates if features['rate_limit'] else {}}


def run(args):
    cfg = config()
    if args.command == 'status':
        rows = index()
        return {'ok': True, 'version': VERSION, **cfg, 'count': len(rows), 'counts': dict(Counter(r['pack'] for r in rows)), 'runtime': read_json(ROOT / 'data/runtime.json', {})}
    if args.command in ('set-mode', 'feature'):
        if args.command == 'set-mode':
            cfg['mode'] = args.mode
        else:
            cfg['features'][args.name] = args.value == 'on'
        write_json(ROOT / 'data/config.json', cfg)
        return {'ok': True, 'mode': cfg['mode'], 'features': cfg['features']}
    if args.command == 'reset-runtime':
        write_json(ROOT / 'data/runtime.json', {})
        return {'ok': True}
    if args.command == 'rebuild-index':
        return {'ok': True, 'count': len(rebuild())}
    if args.command == 'list':
        return {'ok': True, 'stickers': [
            {**r, 'path': str(resolve(r))} for r in index()
            if (not args.pack or r['pack'] == args.pack)
            and (not args.mood or r['mood'] == args.mood)
            and (not args.animated or r['animated'])]}
    if args.command == 'import-pack':
        imported = []
        for source in args.files:
            pack = import_pack(source)
            if pack['id'] not in cfg['packs']:
                cfg['packs'].append(pack['id'])
            write_json(ROOT / 'data/config.json', cfg)
            imported.append(pack)
        rows = rebuild()
        for pack in imported:
            pack['count'] = sum(r['pack'] == pack['id'] for r in rows)
        return {'ok': True, 'imported': imported}
    if args.command == 'import':
        sources = [Path(p).resolve() for p in args.files]
        for source in sources:
            if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
                raise ValueError(f'unsupported or missing image: {source}')
        dest = ROOT / 'stickers/user' / (args.mood or 'inbox')
        dest.mkdir(parents=True, exist_ok=True)
        imported = []
        for source in sources:
            target = dest / source.name
            counter = 1
            while target.exists():
                target = dest / f'{source.stem}_{counter}{source.suffix}'
                counter += 1
            shutil.copy2(source, target)
            imported.append({'path': str(target), 'id': target.stem})
        rebuild()
        return {'ok': True, 'imported': imported}
    return pick(args, cfg)


def main():
    parser = argparse.ArgumentParser(description='Grok Bot sticker CLI')
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('status', 'rebuild-index', 'reset-runtime'):
        sub.add_parser(command)
    mode = sub.add_parser('set-mode')
    mode.add_argument('mode', choices=['active', 'normal'])
    feature = sub.add_parser('feature')
    feature.add_argument('name', choices=list(DEFAULT['features']))
    feature.add_argument('value', choices=['on', 'off'])
    for command in ('pick', 'poke'):
        select = sub.add_parser(command)
        select.add_argument('--text', default='')
        select.add_argument('--event', default='poke' if command == 'poke' else None)
        select.add_argument('--force', action='store_true', default=command == 'poke')
        group = select.add_mutually_exclusive_group()
        group.add_argument('--prefer-gif', dest='prefer_gif', action='store_true')
        group.add_argument('--no-gif', dest='prefer_gif', action='store_false')
        select.set_defaults(prefer_gif=None)
    for command in ('import', 'import-pack'):
        imp = sub.add_parser(command)
        imp.add_argument('files', nargs='+')
        if command == 'import':
            imp.add_argument('--mood', choices=MOODS + ['inbox'])
    listing = sub.add_parser('list')
    listing.add_argument('--pack')
    listing.add_argument('--mood')
    listing.add_argument('--animated', action='store_true')
    try:
        try:
            args = parser.parse_args()
        except SystemExit as exc:
            if exc.code == 0:
                return 0
            raise ValueError('invalid command arguments') from exc
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
