---
name: meeting-copilot
description: >-
  Use when building a Smooth AI–like local meeting copilot on Mac: real-time
  translation, live brief, suggested replies, compose chips, post-meeting English
  feedback, with ontology + memory injection. Triggers on Smooth AI, meeting copilot,
  live translation, non-native English meetings, or ontology context.
---

# Meeting Copilot (Smooth AI–style, Local Mac)

[Smooth AI](https://www.trysmooth.ai)와 유사한 로컬 copilot. **live** 명령 하나로 Live/Brief/Compose UI.

## LIVE (Smooth 동등 기능)

```bash
pip install -e ".[live]"
python -m meeting_copilot live --from-lang ko --to-lang en
# http://127.0.0.1:8765 — 작은 창으로 고정
```

| Smooth | 구현 |
| --- | --- |
| Live translation | Whisper + Marian/NLLB |
| Live brief | Brief 탭 |
| Suggested reply | 질문 감지 → LLM |
| Compose chips | Agree/Disagree/Question/Suggestion |
| Post feedback | Ctrl+C → feedback.md |

ontology + memory → 모든 LLM 호출에 주입.

## 아직 없음 (로드맵)

- 네이티브 always-on-top 오버레이 (Tauri)
- Zoom/Teams 원클릭 시스템 오디오

## Modes

| Mode | When | Command |
| --- | --- | --- |
| **LIVE** | 대면 실시간 번역 | `python -m meeting_copilot live --from-lang ko --to-lang en` |
| CREATE | 회의 전 | `python -m meeting_copilot create --title "..."` |
| UPDATE | 회의 중 (델타) | `python -m meeting_copilot update --session <dir>` |
| CLOSE | 회의 후 | `python -m meeting_copilot close --session <dir>` |
| WATCH | Teams 자막 파일 (비실시간) | `python -m meeting_copilot watch ...` |

## CREATE

입력: 제목, 유형(discovery/sales/support 등), 날짜, 참가자(선택)

1. `sessions/YYYY-MM-DD-<slug>/` 생성
2. `app/` 대시보드 + `state/` 전사 상태
3. ontology + memory를 읽어 `briefing.js` 초기화
4. `python -m http.server 8080`으로 `app/` 서빙

## UPDATE (실시간 맥락 + 제안)

전사 입력은 **전체 청크**를 stdin 또는 파일로 받고, `diff.py`로 **델타만** LLM에 전달한다.

```bash
cat transcript-new.txt | python -m meeting_copilot update --session sessions/...
```

LLM은 델타 + ontology + memory를 받아:

- `questions.js` — 놓친 질문, 다음 질문
- `topics.js` — 토픽 진행
- `decisions.js` — 결정, 리스크, 블로커
- `followups.js` — 액션 아이템, 후속 메시지 초안
- `translation.js` — (옵션) 번역 라인

회의 중에는 **프로필/ontology 파일을 수정하지 않는다**. 속도 우선.

## WATCH (Teams / 실시간 번역)

**Teams (무료, 권장)**

1. Teams 웹에서 회의 입장 → **Live captions** 켜기
2. 자막을 클립보드/파일로 누적하거나, 브라우저 확장/스크립트로 `captions.log`에 append
3. `watch`가 파일 변경을 감지하고 UPDATE 루프 실행

**로컬 STT (무료)**

BlackHole + `faster-whisper`로 마이크/시스템 오디오 전사 → 같은 UPDATE 루프.

**실시간 번역 (무료, 전 언어)**

`config.yaml`에서 `translation.backend: nllb` — NLLB-200 distilled (CTranslate2).
대상 언어는 `translation.target_lang` (예: `kor`, `eng`, `jpn`).

## CLOSE

1. 최종 전사 처리
2. `summary.md` — 결과, 결정, 액션, 오픈 질문, 후속 초안
3. (요청 시) sanitized export — 이름·회사·링크 제거

## Privacy

공개 산출물에 넣지 않는다:

- raw transcript, 개인 식별 정보, 내부 URL, 토큰

## Quality bar

- 대시보드 로컬에서 열림
- UPDATE 후 탭 JS 문법 오류 없음
- ontology/memory가 briefing에 반영됨
- CLOSE에 결정과 액션 분리
