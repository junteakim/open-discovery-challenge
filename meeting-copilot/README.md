# Meeting Copilot — MacBook Air (무료·저지연)

**추가 비용 $0** — 회의 중 LLM API 호출 없음 (`lite` 모드).

## MacBook Air 한 줄 실행

```bash
pip install -e ".[overlay]"
cp config.example.yaml config.yaml

python -m meeting_copilot overlay --from-lang ko --to-lang en
```

기본값: `profile: macbook-air`, `live.mode: lite`

## lite vs full

| | lite (기본) | full (`--full`) |
| --- | --- | --- |
| 비용 | **$0** | CLI LLM 구독 한도 |
| 전사 | Whisper `tiny` CPU | 동일 |
| 번역 | Marian (로컬) | Marian 또는 LLM |
| Brief/제안 | 휴리스틱 + ontology | LLM |
| 회의 후 feedback | 생략 (수동 실행) | auto |

## 지연 최소화 설정 (이미 기본)

- `whisper_model: tiny`
- `chunk_seconds: 0.65`
- `cpu_threads: 4`
- VAD off in lite (CPU 절약)
- 전사 먼저 표시 → 번역 뒤따라

## LLM 쓰고 싶을 때만

```bash
python -m meeting_copilot overlay --full --from-lang ko --to-lang en
# config: llm.provider: claude
```

회의 후 영어 피드백 (lite):

```bash
python -m meeting_copilot feedback --session sessions/live-...
```

## License

MIT
