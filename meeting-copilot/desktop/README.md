# Meeting Copilot Desktop (Tauri)

Smooth AI–style **always-on-top** native window for Mac.

## Prerequisites (Mac)

```bash
# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Python backend
cd ..
pip install -e ".[live,overlay]"

# Node
brew install node
```

## Quick start (recommended)

Python overlay (no Rust build):

```bash
cd ..
python -m meeting_copilot overlay --from-lang ko --to-lang en
```

## Tauri native app

1. Start backend first (separate terminal):

```bash
python -m meeting_copilot live --from-lang ko --to-lang en
```

2. Build/run Tauri shell:

```bash
cd desktop
npm install
npm run tauri dev
```

Tauri window loads `http://127.0.0.1:8765` with `alwaysOnTop: true`.

## Production build

```bash
npm run tauri build
# → src-tauri/target/release/bundle/macos/
```

## Audio (Zoom/Teams)

```bash
../scripts/setup-mac-audio.sh
```
