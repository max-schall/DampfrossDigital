#!/usr/bin/env bash
# Build a self-contained DampfrossDigital bundle for the current platform.
# Run once per target OS (Linux, macOS, Windows) on the respective machine.
# Output goes to dist/DampfrossDigital/.
set -e
cd "$(dirname "$0")"
pip install pyinstaller platformdirs pygame --quiet
pyinstaller dampfross.spec
echo ""
echo "Done! Bundle is at dist/DampfrossDigital/"
echo "Zip that folder and send it — no Python install needed on the recipient's machine."
