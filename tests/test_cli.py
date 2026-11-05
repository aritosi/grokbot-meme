import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'bin/gb-meme'
DEMO = ROOT / 'stickers/demo'
DEMO_COUNT = sum(1 for p in DEMO.rglob('*') if p.suffix in ('.png', '.gif'))


class CLITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(DEMO, self.root / 'stickers/demo')
        self.env = {**os.environ, 'GB_MEME_ROOT': str(self.root), 'PYTHONDONTWRITEBYTECODE': '1'}

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, code=0, env=None):
        result = subprocess.run([str(CLI), *args], env=env or self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, code, result.stderr + result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        return json.loads(result.stdout)

    def config(self, **values):
        cfg = self.cli('status')
        for key in ('version', 'count', 'counts', 'runtime'):
            cfg.pop(key)
        cfg.update(values)
        (self.root / 'data/config.json').write_text(json.dumps(cfg), encoding='utf-8')

    def make_pack(self, name='test-pack', moods=('happy', 'sad')):
        pack = self.root / name
        for mood in moods:
            directory = pack / 'memes' / mood
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f'{mood}.png').write_bytes(b'\x89PNG\r\n\x1a\n' + mood.encode())
        (pack / 'manifest.json').write_text(json.dumps({'id': name, 'name': name}), encoding='utf-8')
        return pack

    def test_status_and_modes(self):
        status = self.cli('status')
        self.assertEqual(status['version'], '2.1.0')
        self.assertEqual(status['mode'], 'active')
        self.assertEqual(status['count'], DEMO_COUNT)
        self.assertEqual(set(status['packs']), {'demo', 'user'})
        self.assertTrue(all(status['features'].values()))
        for mode in ('normal', 'active'):
            self.assertEqual(self.cli('set-mode', mode)['mode'], mode)
        self.assertEqual(self.cli('rebuild-index')['count'], DEMO_COUNT)

    def test_normal_and_force(self):
        self.cli('set-mode', 'normal')
        self.assertEqual(self.cli('pick', '--text', '请检查代码')['reason'], 'no_trigger')
        self.assertTrue(self.cli('pick', '--force')['send'])

    def test_keywords_and_events(self):
        cases = [(('--text', '哭哭'), ['sad']),
                 (('--text', '发个开心的表情'), ['happy']),
                 (('--event', 'fail'), ['sad', 'angry', 'confused']),
                 (('--event', 'success'), ['celebrate', 'happy', 'like'])]
        for args, moods in cases:
            self.cli('reset-runtime')
            row = self.cli('pick', *args)
            self.assertTrue(row['send'], row)
            self.assertIn(row['mood'], moods)
            self.assertTrue(Path(row['path']).is_file())

    def test_poke_and_limits(self):
        self.cli('reset-runtime')
        self.assertTrue(self.cli('poke')['send'])
        self.assertEqual(self.cli('poke')['reason'], 'rate_limited')
        self.cli('feature', 'rate_limit', 'off')
        self.assertTrue(self.cli('poke')['send'])
        self.cli('feature', 'poke', 'off')
        self.assertEqual(self.cli('poke')['reason'], 'disabled')

    def test_cooldown_hour_bucket(self):
        self.config(min_interval_seconds=0)
        self.assertTrue(self.cli('pick', '--text', '开心')['send'])
        self.assertTrue(self.cli('pick', '--text', '开心')['gates']['cooldown'])
        self.cli('reset-runtime')
        self.config(cooldown_seconds=0, max_per_hour=1)
        self.assertTrue(self.cli('pick')['send'])
        self.assertTrue(self.cli('pick')['gates']['max_per_hour'])

    def test_import_and_collision(self):
        source = next(p for p in (self.root / 'stickers/demo').rglob('*.png'))
        for suffix in ('', '_1'):
            row = self.cli('import', str(source))
            self.assertEqual(row['imported'][0]['id'], source.stem + suffix)
        self.assertEqual(len(self.cli('list', '--pack', 'user')['stickers']), 2)
        self.assertIn('/happy/', self.cli('import', str(source), '--mood', 'happy')['imported'][0]['path'])

    def test_pack_import_idempotence_and_gif(self):
        archive = self.root / 'pack.zip'
        with zipfile.ZipFile(archive, 'w') as zf:
            zf.writestr('manifest.json', json.dumps({'id': 'zip-pack', 'name': 'Zip Pack'}))
            zf.writestr('memes/happy/a.png', b'png-a')
            zf.writestr('memes/happy/b.gif', b'GIF89a')
            zf.writestr('memes/sad/c.png', b'png-c')
        for _ in range(2):
            row = self.cli('import-pack', str(archive))
            self.assertEqual(row['imported'][0]['count'], 3)
        self.assertIn('zip-pack', self.cli('status')['packs'])
        self.assertEqual(len(self.cli('list', '--pack', 'zip-pack', '--animated')['stickers']), 1)
        self.config(packs=['zip-pack'], keywords={})
        row = self.cli('pick', '--text', '难过呜呜')
        self.assertEqual(row['pack'], 'zip-pack')
        self.assertEqual(row['mood'], 'sad')

    def test_semantics_and_feature_fallback(self):
        self.cli('import-pack', str(self.make_pack()))
        self.config(mode='normal', packs=['test-pack'], keywords={})
        row = self.cli('pick', '--text', '哈哈哈笑死我了')
        self.assertTrue(row['send'])
        self.assertEqual(row['mood'], 'happy')
        self.assertTrue(row['reason'].startswith('semantic:'), row)
        self.cli('reset-runtime')
        self.cli('feature', 'semantic', 'off')
        self.assertEqual(self.cli('pick', '--text', '哈哈哈笑死我了')['reason'], 'no_trigger')

    def test_fsm_and_dedupe(self):
        self.cli('feature', 'rate_limit', 'off')
        first = self.cli('pick', '--text', '开心')
        second = self.cli('pick')
        self.assertEqual(second['mood'], 'happy')
        self.assertIn('fsm:happy', second['reason'])
        self.assertEqual(self.cli('pick')['mood'], 'daily')
        self.cli('feature', 'emotion_fsm', 'off')
        self.cli('reset-runtime')
        self.cli('feature', 'gif_prefer', 'off')
        rows = [r for r in self.cli('list', '--mood', 'happy')['stickers'] if not r['animated']]
        results = [self.cli('pick', '--text', '开心', '--no-gif')['path'] for _ in rows]
        self.assertEqual(len(set(results)), len(rows))
        self.assertTrue(self.cli('pick', '--text', '开心')['send'])

    def test_gif_preference(self):
        self.cli('reset-runtime')
        row = self.cli('pick', '--text', '开心', '--prefer-gif')
        self.assertTrue(row['animated'])
        self.assertEqual(row['path'].rsplit('.', 1)[1], 'gif')

    def test_pack_dir_no_manifest_and_traversal(self):
        pack = self.root / 'custom'
        (pack / 'memes/daily').mkdir(parents=True)
        (pack / 'memes/daily/a.gif').write_bytes(b'GIF89a')
        self.assertEqual(self.cli('import-pack', str(pack))['imported'][0]['id'], 'custom')
        plain = self.root / 'plain.zip'
        with zipfile.ZipFile(plain, 'w') as zf:
            zf.writestr('memes/daily/a.png', b'png')
        self.assertEqual(self.cli('import-pack', str(plain))['imported'][0]['id'], 'plain')
        unsafe = self.root / 'unsafe.zip'
        with zipfile.ZipFile(unsafe, 'w') as zf:
            zf.writestr('../escape.png', b'bad')
        self.assertFalse(self.cli('import-pack', str(unsafe), code=1)['ok'])
        self.assertFalse((self.root / 'escape.png').exists())

    def test_event_fsm_gif_switches(self):
        self.cli('feature', 'rate_limit', 'off')
        self.cli('feature', 'emotion_fsm', 'off')
        self.cli('feature', 'task_events', 'off')
        self.assertEqual(self.cli('pick', '--event', 'fail')['mood'], 'daily')
        self.cli('pick', '--text', '开心')
        self.assertEqual(self.cli('pick')['mood'], 'daily')
        self.cli('feature', 'gif_prefer', 'off')
        self.assertEqual(self.cli('pick', '--text', '开心', '--prefer-gif')['mood'], 'happy')

    def test_bad_config_and_missing_index(self):
        self.cli('status')
        (self.root / 'data/config.json').write_text('{bad', encoding='utf-8')
        self.assertEqual(self.cli('status')['mode'], 'active')
        self.assertTrue(list((self.root / 'data').glob('config.broken.*.json')))
        (self.root / 'data/index.json').unlink()
        self.assertEqual(self.cli('status')['count'], DEMO_COUNT)

    def test_errors_and_no_candidate(self):
        for args in [('import', 'missing.png'), ('set-mode', 'bad'), ('unknown',)]:
            self.assertFalse(self.cli(*args, code=1)['ok'])
        self.config(packs=[])
        self.assertEqual(self.cli('pick')['reason'], 'no_candidate')

    def test_index_is_portable(self):
        self.cli('status')
        index = json.loads((self.root / 'data/index.json').read_text(encoding='utf-8'))
        self.assertTrue(index)
        for row in index:
            self.assertFalse(Path(row['path']).is_absolute(), row['path'])
            self.assertTrue((self.root / row['path']).is_file())
        moved = self.root / 'moved'
        shutil.copytree(self.root / 'data', moved / 'data')
        shutil.copytree(self.root / 'stickers', moved / 'stickers')
        env = {**self.env, 'GB_MEME_ROOT': str(moved)}
        row = self.cli('pick', '--force', env=env)
        self.assertTrue(row['path'].startswith(str(moved)), row['path'])
        self.assertTrue(Path(row['path']).is_file())


if __name__ == '__main__':
    unittest.main()
