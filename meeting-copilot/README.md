# Meeting Copilot — Smooth AI–style local alternative

[Smooth AI](https://www.trysmooth.ai)와 같은 **비원어민 영어 회의 copilot** — 로컬·무료·ontology 주입.

## 한 줄 시작 (Mac, 권장)

```bash
cd meeting-copilot
pip install -e ".[overlay]"
cp config.example.yaml config.yaml   # llm.provider: claude | codex | grok

python -m meeting_copilot overlay --from-lang ko --to-lang en
```

**always-on-top** 작은 창이 뜹니다 (Smooth와 같은 사용법).

## Smooth 기능 대응

| Smooth | 명령/구현 |
| --- | --- |
| 플로팅 overlay | `overlay` (pywebview) 또는 `desktop/` (Tauri) |
| Live 번역 | Whisper `tiny` + Marian/NLLB |
| Brief | Brief 탭 |
| 답변 제안 | 질문 감지 → LLM |
| Compose | Agree/Disagree/Question/Suggestion |
| 회의 후 피드백 | `feedback.md` |
| ontology 맥락 | `context/ontology.json` (JSON-LD 지원) |

## Zoom/Teams 오디오

```bash
chmod +x scripts/setup-mac-audio.sh
./scripts/setup-mac-audio.sh
python -m meeting_copilot overlay --list-devices
python -m meeting_copilot overlay --device <BlackHole index> --from-lang ko --to-lang en
```

## Tauri 네이티브 앱 (선택)

```bash
pip install -e ".[live,overlay]"
python -m meeting_copilot live --from-lang ko --to-lang en   # 터미널 1
cd desktop && npm install && npm run tauri dev               # 터미널 2
```

## 지연 최적화

- 기본 `whisper_model: tiny`, `chunk_seconds: 0.85`
- STT 먼저 표시 → 번역은 뒤따라 업데이트
- `config.yaml`의 `live.whisper_device: auto` (CUDA 있으면 사용)

## License

MIT
