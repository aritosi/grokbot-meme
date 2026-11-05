#!/bin/sh
# Remove the installed copy and the PATH link. Imported stickers are deleted too.
set -eu
TARGET=${GROKBOT_MEME_HOME:-$HOME/.grokbot-meme}
[ -L "$HOME/.local/bin/gb-meme" ] && rm -f "$HOME/.local/bin/gb-meme"
if [ -d "$TARGET" ]; then
    rm -rf "$TARGET"
    echo "removed $TARGET"
else
    echo "nothing at $TARGET"
fi
