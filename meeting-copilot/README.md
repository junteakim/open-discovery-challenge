# Flow — Meeting Copilot

Smooth AI와 같은 **비원어민 영어 회의 copilot**. 로컬·무료·ontology 맥락.

> Smooth AI는 기술적으로 특별한 게 아닙니다. 오픈소스([MeetU](https://github.com/jessecu2024/MeetU), [NexQ](https://github.com/johnbarraza/NexQ) 등)가 같은 기능을 이미 구현합니다. 비교 문서: [`docs/OPEN_SOURCE_PEERS.md`](docs/OPEN_SOURCE_PEERS.md)

## 한 줄 실행 (MacBook Air)

```bash
pip install -e ".[overlay]"
cp config.example.yaml config.yaml
# optional: live.my_names: ["YourName"]

python -m meeting_copilot overlay --from-lang ko --to-lang en
```

## 오픈소스에서 가져온 패턴

| 출처 | 패턴 | Flow |
| --- | --- | --- |
| MeetU | Whisper hallucination filter | ✅ |
| MeetU | @Mention / 질문 알림 | ✅ `my_names` |
| MeetU | 답변 3종 (diplomatic/assertive/conservative) | ✅ lite |
| MeetU | Custom glossary | ✅ ontology |
| NexQ | Always-on-top overlay | ✅ |
| live-translation | BlackHole Mac 오디오 | ✅ scripts |

## Smooth vs Flow vs MeetU

| | Smooth | MeetU | Flow |
| --- | --- | --- | --- |
| 비용 | $7~/월 | BYOK | **$0 lite** |
| 로컬 | 클라우드 | Local-first | Local-first |
| 제안 3종 | — | ✅ LLM | ✅ 템플릿 (lite) |
| ontology | — | glossary | ✅ |
| Mac 시스템 오디오 | 내장 | ScreenCaptureKit | BlackHole |

## License

MIT
