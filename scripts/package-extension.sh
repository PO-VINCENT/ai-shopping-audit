#!/bin/sh
# Package the browser extension for the Chrome Web Store.
set -e
cd "$(dirname "$0")/.."
VERSION=$(python3 -c "import json; print(json.load(open('browser-extension/manifest.json'))['version'])")
mkdir -p dist
rm -f "dist/catalogready-extension-v$VERSION.zip"
cd browser-extension
zip -r "../dist/catalogready-extension-v$VERSION.zip" . -x README.md
cd ..
echo "Wrote dist/catalogready-extension-v$VERSION.zip"
unzip -l "dist/catalogready-extension-v$VERSION.zip"
