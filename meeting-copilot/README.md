# Meeting Copilot (Local Mac, 무료 우선)

로컬 Mac에서 Teams 온라인 미팅 또는 실시간 번역과 함께 쓰는 회의 copilot.

| 기능 | 무료 구현 |
| --- | --- |
| 전사 | Teams Live Captions → 파일 감시, 또는 BlackHole + faster-whisper |
| 실시간 번역 | NLLB-200 distilled (CTranslate2) — 다국어 |
| 맥락 LLM | ontology.json + memory.md 주입 → CLI LLM |
| 실시간 제안 | 전사 델타 → questions/topics/decisions/followups 갱신 |

**약물/의료 프로젝트와 무관** — `discovery` 하네스와 분리된 도구입니다.

## Quick start

```bash
cd meeting-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 설정 복사
cp config.example.yaml config.yaml
cp context/ontology.example.json context/ontology.json
cp context/memory.example.md context/memory.md

# 회의 세션 생성
python -m meeting_copilot create --title "Discovery with Company X" --type discovery

# 대시보드 (세션 경로는 create 출력 참고)
cd sessions/YYYY-MM-DD-*/app && python3 -m http.server 8080
```

## Teams 실시간 (권장, $0)

1. [Teams 웹](https://teams.microsoft.com)에서 회의 입장
2. **More → Language and speech → Turn on live captions**
3. 자막 텍스트를 세션 `state/captions.log`에 누적 (수동 paste 또는 브라우저 스니펫)
4. 감시 시작:

```bash
python -m meeting_copilot watch \
  --session sessions/YYYY-MM-DD-discovery-with-company-x \
  --captions-file state/captions.log \
  --translate --target-lang kor
```

`watch`는 파일이 바뀔 때마다 델타를 추출하고, (옵션) 번역 후 CLI LLM으로 탭을 갱신합니다.

### 자막 자동 누적 (선택)

Teams 웹 자막 DOM은 UI 업데이트가 잦아 **완전 자동은 brittle**합니다. 실용적 무료 경로:

- **수동**: 30~60초마다 자막 영역 복사 → `captions.log` append
- **반자동**: macOS Shortcuts로 클립보드 → 파일 append
- **오디오**: BlackHole + Whisper — UI에 의존하지 않음

## 로컬 STT (Teams 없을 때)

```bash
# BlackHole로 시스템 오디오 녹음 후 (Audacity 등)
python -m meeting_copilot stt --session <dir> --audio recording.wav
```

## CLI LLM 설정

`config.yaml`:

```yaml
llm:
  provider: claude   # claude | codex | grok
  claude:
    command: ["claude", "-p", "--output-format", "text"]
  codex:
    command: ["codex", "exec", "--full-auto"]
  grok:
    command: ["grok", "-p"]
```

구독 한도 내에서는 **클라우드 CLI가 품질 최고**. 한도 소진 시 `provider: echo`로 파이프라인만 검증.

## Ontology + Memory

- `context/ontology.json` — 도메인 엔티티, 관계, 용어 (회의 전 주입)
- `context/memory.md` — 브리핑, 가설, 과거 스레드

CREATE 시 briefing에 반영; UPDATE 시 매 델타와 함께 LLM에 전달.

## 번역 (전 언어, 무료)

NLLB-200 distilled:

```bash
pip install ctranslate2 transformers sentencepiece
```

`config.yaml`:

```yaml
translation:
  backend: nllb
  model: facebook/nllb-200-distilled-600M
  source_lang: eng_Latn
  target_lang: kor_Hang
```

언어 코드는 [NLLB FLORES-200](https://github.com/facebookresearch/flores/blob/main/flores200/README.md#languages-in-flores-200) 형식.

## 비용 요약

| 구성요소 | 비용 |
| --- | --- |
| Teams captions | $0 |
| NLLB 로컬 | $0 (디스크 ~1GB, CPU) |
| faster-whisper | $0 |
| Claude/Codex/Grok CLI | 구독/한도 내 (인프라 $0) |

## License

MIT
