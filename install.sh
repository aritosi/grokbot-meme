#!/bin/sh
# Install gb-meme to a stable location so the Grok Bot skill always finds it.
# Usage: ./install.sh
#   GROKBOT_MEME_HOME=/path ./install.sh   # custom install location
set -eu

SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${GROKBOT_MEME_HOME:-$HOME/.grokbot-meme}

command -v python3 >/dev/null 2>&1 || { echo "python3 3.9+ is required" >&2; exit 1; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
    echo "python3 3.9+ is required (found $(python3 -V 2>&1))" >&2
    exit 1
}

mkdir -p "$TARGET/bin" "$TARGET/src" "$TARGET/data" "$TARGET/stickers" "$TARGET/skill"
cp "$SOURCE/bin/gb-meme" "$TARGET/bin/gb-meme"
cp "$SOURCE/src/gb_meme.py" "$TARGET/src/gb_meme.py"
cp "$SOURCE/skill/SKILL.md" "$TARGET/skill/SKILL.md"
[ -f "$TARGET/data/actions.json" ] || cp "$SOURCE/data/actions.json" "$TARGET/data/actions.json"
if [ ! -f "$TARGET/stickers/demo/manifest.json" ]; then
    cp -R "$SOURCE/stickers/demo" "$TARGET/stickers/demo"
fi
chmod +x "$TARGET/bin/gb-meme"

# Bake the absolute install path into the skill so the bot needs no shell variables.
python3 - "$TARGET/skill/SKILL.md" "$TARGET" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
path.write_text(path.read_text(encoding='utf-8').replace('$HOME/.grokbot-meme', sys.argv[2]), encoding='utf-8')
PY

mkdir -p "$HOME/.local/bin"
ln -sf "$TARGET/bin/gb-meme" "$HOME/.local/bin/gb-meme"

STATUS=$("$TARGET/bin/gb-meme" status)
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "note: add \$HOME/.local/bin to PATH to call 'gb-meme' directly." ;;
esac

echo "$STATUS"
echo
echo "Installed to: $TARGET"
echo "Skill file:   $TARGET/skill/SKILL.md"
echo
echo "Make Grok Bot use it (one step, inside Grok Bot):"
echo "  读取 $TARGET/skill/SKILL.md，用 UpdateSkill(action=\"write\", id=\"grokbot-meme\") 安装。"
echo "Then ask the bot anything; it will call gb-meme pick by itself."
