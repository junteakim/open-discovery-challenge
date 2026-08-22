# Meeting Copilot (Local Mac, 무료 우선)

로컬 Mac **대면 실시간 번역** + 회의 copilot (맥락 LLM, 제안).

| 기능 | 구현 |
| --- | --- |
| **실시간 대면 번역** | 마이크 → faster-whisper → Marian/NLLB 즉시 번역 → 브라우저 UI |
| 전사 (회의 후처리) | 오디오 파일 STT, Teams 자막 파일 (비실시간) |
| 맥락 LLM | ontology.json + memory.md → CLI LLM |
| 실시간 제안 | 전사 델타 → questions/decisions/followups |

## 실시간 대면 번역 (핵심)

맥북 마이크로 말하면 **1~2초 내** 원문·번역이 브라우저에 표시됩니다. 양방향(한↔영 등) 자동 감지.

```bash
cd meeting-copilot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[live]"

# 마이크 권한: 시스템 설정 → 개인정보 → 마이크 → Terminal 허용
python -m meeting_copilot live --from-lang ko --to-lang en
# → http://127.0.0.1:8765 열기 (폰/태블릿도 같은 Wi‑Fi에서 접속 가능)
```

**지연 줄이기 (Mac CPU):**

```bash
python -m meeting_copilot live --from-lang ko --to-lang en \
  --whisper-model tiny --chunk-seconds 0.9
```

**마이크 선택:**

```bash
python -m meeting_copilot live --list-devices
python -m meeting_copilot live --device 1 --from-lang ko --to-lang en
```

| 언어 쌍 | 번역 엔진 | 비고 |
| --- | --- | --- |
| en↔ko, en↔ja 등 | MarianMT (빠름) | 대면 통역에 적합 |
| 기타 | NLLB-200 (느림) | 첫 로드 후 캐시 |

첫 실행 시 Whisper·번역 모델 다운로드 (~500MB–1.5GB). 이후 **완전 오프라인·$0**.

---

## 회의 copilot (맥락 + 제안)

ontology/memory를 채운 뒤 세션 생성:

```bash
pip install -e .
cp config.example.yaml config.yaml
cp context/ontology.example.json context/ontology.json
cp context/memory.example.md context/memory.md

python -m meeting_copilot create --title "Discovery" --type discovery
```

`config.yaml`에서 `llm.provider: claude | codex | grok`.

---

## Teams / 파일 기반 (비실시간 보조)

Teams 자막 파일 감시는 **온라인 회의 요약용**이며 대면 실시간 번역과 다릅니다.

```bash
python -m meeting_copilot watch --session <dir> --captions-file state/captions.log
```

---

## 비용

| 구성요소 | 비용 |
| --- | --- |
| `live` (마이크 STT + 번역) | $0 |
| CLI LLM (제안/요약) | 구독 한도 내 |

## License

MIT
