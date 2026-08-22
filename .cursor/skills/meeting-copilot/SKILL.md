---
name: meeting-copilot
description: >-
  Use when preparing for, running, or closing a live meeting on a local Mac with
  Teams or real-time translation. Triggers on "meeting copilot", "live copilot",
  Teams meeting, real-time translation, ontology context, or requests to turn
  transcript chunks into briefing, questions, decisions, and follow-ups. Uses
  local CLI LLMs (Claude Code, Codex CLI, Grok CLI) with ontology + memory injection.
---

# Meeting Copilot (Local Mac)

로컬 Mac에서 회의 전·중·후를 돌리는 copilot. **전사는 Teams 내장 자막 또는 로컬 Whisper**, **번역은 NLLB(무료) 또는 LLM**, **맥락은 ontology + memory 파일 주입**, **제안은 UPDATE 루프**로 생성한다.

프로젝트 루트의 `meeting-copilot/` CLI를 사용한다.

## 사전 조건 (Mac)

1. Python 3.11+
2. (선택) Teams 웹 자막 파일 감시 — `meeting-copilot watch --captions-file`
3. (선택) 로컬 STT — `pip install faster-whisper` + BlackHole로 시스템 오디오
4. (선택) 무료 다국어 번역 — `pip install ctranslate2 transformers sentencepiece`
5. CLI LLM 중 하나: Claude Code (`claude`), Codex (`codex`), Grok (`grok`)

## 컨텍스트 주입 (ontology + memory)

회의 전에 다음 파일을 채운다:

- `meeting-copilot/context/ontology.json` — 엔티티, 관계, 용어 정의
- `meeting-copilot/context/memory.md` — 사전 브리핑, 과거 대화, 가설

CREATE/UPDATE/CLOSE 시 이 파일들이 LLM 프롬프트에 자동 포함된다.

## Modes

| Mode | When | Command |
| --- | --- | --- |
| CREATE | 회의 전 | `python -m meeting_copilot create --title "..." --type discovery` |
| UPDATE | 회의 중 (전사 델타) | `python -m meeting_copilot update --session <dir>` |
| CLOSE | 회의 후 | `python -m meeting_copilot close --session <dir>` |
| WATCH | 실시간 입력 | `python -m meeting_copilot watch --session <dir> --captions-file ...` |

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
