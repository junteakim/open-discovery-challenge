# Meeting Copilot — Smooth AI–style local alternative

[Smooth AI](https://www.trysmooth.ai)처럼 **비원어민 영어 회의**를 돕는 로컬 copilot. 무료·로컬·ontology 주입.

## Smooth AI vs 이 프로젝트

| Smooth AI | Meeting Copilot (local) |
| --- | --- |
| 실시간 전사·번역 | ✅ `live` — Whisper + Marian/NLLB |
| 실시간 요약 (Brief) | ✅ Brief 탭 — LLM |
| 질문 시 답변 제안 | ✅ Suggested reply |
| Compose (Agree/Disagree/…) | ✅ 상단 칩 + Compose 탭 |
| 회의 후 영어 피드백 | ✅ `feedback.md` |
| 화면 플로팅 오버레이 | ⚠️ 브라우저 작은 창 고정 (네이티브 앱은 Tauri 단계) |
| Zoom/Teams 시스템 오디오 | ⚠️ BlackHole + 마이크 (설정 필요) |
| 클라우드 SaaS | ✅ 100% 로컬 + CLI LLM |

## 시작 (Smooth와 같은 사용법)

```bash
cd meeting-copilot
pip install -e ".[live]"
cp config.example.yaml config.yaml
# llm.provider: claude | codex | grok

python -m meeting_copilot live --from-lang ko --to-lang en
```

1. **http://127.0.0.1:8765** 를 작은 창으로 띄우고 회의 옆에 고정
2. **Live** — 실시간 전사·번역·질문 답변 제안
3. **Brief** — 실시간 요약
4. **Agree / Disagree / Question / Suggestion** — 즉시 말할 영어 문장
5. `Ctrl+C` → `sessions/live-*/feedback.md` (영어 교정·표현 학습)

## 맥락 주입 (차별점)

- `context/ontology.json` — 도메인 엔티티·용어
- `context/memory.md` — 사전 브리핑

Brief·답변·Compose에 자동 반영.

## Zoom/Teams 오디오

1. [BlackHole](https://existential.audio/blackhole/) 설치
2. Multi-Output으로 시스템 오디오 + 마이크 믹스
3. `python -m meeting_copilot live --list-devices`

## 다음 단계 (Smooth 완전 동등)

- Tauri always-on-top 오버레이
- 시스템 오디오 원클릭
- 지연 500ms 이하 (GPU + CTranslate2)

## License

MIT
