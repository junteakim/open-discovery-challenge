# Flow — Meeting Copilot

Smooth AI와 같은 **비원어민 영어 회의 copilot**. 로컬·무료·ontology 맥락.

> Smooth AI는 기술적으로 특별한 게 아닙니다. **전사 + 번역 + 제안 + Brief + Compose**를 한 플로팅 UI에 잘 묶은 제품입니다. Flow는 같은 UX를 **로컬 Mac**에서 $0로 재현합니다.

## 한 줄 실행 (MacBook Air)

```bash
pip install -e ".[overlay]"
cp config.example.yaml config.yaml

python -m meeting_copilot overlay --from-lang ko --to-lang en
```

**Flow** 창이 always-on-top으로 뜹니다.

## Smooth vs Flow

| Smooth AI | Flow (우리) |
| --- | --- |
| 클라우드 SaaS | 100% 로컬 |
| 월 $7~ | 회의 중 **$0** (lite) |
| Live / Brief / Compose | ✅ 동일 탭 구조 |
| Agree·Disagree·Question·Suggestion | ✅ |
| 질문 시 답변 제안 | ✅ (패턴 + ontology) |
| 용어 하이라이트 | ✅ ontology.json |
| 전사 검색 | ✅ |
| 복사 버튼 | ✅ |
| 회의 후 영어 피드백 | `feedback` 명령 |
| **ontology 주입** | ✅ Smooth에 없음 |

## UI 미리보기

- **Live** — 실시간 전사·번역, 질문 시 “바로 말할 답변” 카드
- **Brief** — 실시간 요약 + 핵심 용어 + 온톨로지 glossary
- **Compose** — Agree/Disagree/Question/Suggestion 칩

## 맥락 설정

```bash
cp context/ontology.example.json context/ontology.json
cp context/memory.example.md context/memory.md
```

ontology 용어는 전사·번역에서 **자동 하이라이트**됩니다.

## LLM 쓰고 싶을 때

```bash
python -m meeting_copilot overlay --full --from-lang ko --to-lang en
```

## License

MIT
