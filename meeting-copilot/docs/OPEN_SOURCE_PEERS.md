# Open-source landscape (Smooth AI peers)

Smooth AI와 비슷한 **오픈소스** 프로젝트를 조사한 결과입니다.  
Flow 설계 시 참고할 패턴을 체크했습니다.

## Comparison matrix

| Project | Stack | STT | Translation | Suggestions | Overlay | Cost model | License | Mac |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **[MeetU](https://github.com/jessecu2024/MeetU)** | Electron + React | Deepgram / Whisper API / Local whisper.cpp | LLM + **custom glossary** | **3 strategies** when @mentioned | Desktop beside meeting | BYOK | BSL→MIT 2029 | ✅ ScreenCaptureKit |
| **[NexQ](https://github.com/johnbarraza/NexQ)** | Tauri 2 + React | 10 providers (Whisper, Deepgram, …) | 5 providers | Streaming LLM replies | Always-on-top | Local / BYOK | OSS | ✅ |
| **[Natively](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant)** | Desktop | Local Whisper / Moonshine | Multilingual | Stealth suggestions | Stealth overlay | Local / BYOK | OSS | ✅ |
| **[MeetingCopilot](https://github.com/JWM0203/MeetingCopilot)** | Desktop | FunASR / Whisper | — | Teleprompter answers | Capture-protected | BYOK | OSS | ✅ |
| **[MeetingBro](https://github.com/mzyas/MeetingBro)** | Electron + FastAPI | Local Whisper | EN/ZH/DE | Rolling summary | App UI | Local / Ollama / BYOK | OSS | ⚠️ loopback setup |
| **[live-translation](https://github.com/KazKozDev/live-translation)** | macOS native | MLX Whisper | **Ollama LLM** | — | Glass overlay | Fully offline | OSS | ✅ Apple Silicon |
| **[ghst](https://github.com/bnovik0v/ghst)** | Electron | Groq Whisper | — | Copilot on end-of-turn | Transparent overlay | Groq free tier | MIT | ❌ Linux |
| **Flow (ours)** | Python + pywebview/Tauri | faster-whisper | Marian (lite) | Pattern + ontology | Always-on-top | **$0 lite** / CLI LLM | MIT | ✅ |

## What Smooth AI actually is

Not novel tech. The product is a **bundle**:

1. Live STT + translation  
2. Live brief  
3. Suggested reply when questioned  
4. Compose chips (Agree / Disagree / Question / Suggestion)  
5. Post-meeting English coaching  
6. Floating UI only you see  

Open source already covers all of this — MeetU / NexQ / Natively are the closest.

## Patterns worth copying (ranked for Flow)

### 1. MeetU — highest relevance

| Pattern | Why | Flow status |
| --- | --- | --- |
| **Custom glossary** | Domain terms → better translation display | ✅ ontology highlight |
| **@Mention / name detection** | Alert when you're addressed | ✅ added |
| **3 reply strategies** | conservative / assertive / diplomatic | ✅ added (lite templates) |
| **Hallucination filter** | Drop Whisper junk ("Thank you for watching") | ✅ added |
| **Silence RMS gate** | Skip silent windows before STT | ✅ already (RMS threshold) |
| **ScreenCaptureKit loopback** | System audio without BlackHole | ⬜ roadmap (macOS 13+) |
| **SQLite meeting history** | Search past transcripts | ⬜ roadmap |
| **Local whisper.cpp** | Faster than Python on Mac | ⬜ optional later |

### 2. NexQ / Natively

| Pattern | Why | Flow status |
| --- | --- | --- |
| **You / Them dual channel** | Mic vs system audio | ⬜ needs BlackHole or ScreenCaptureKit |
| **Local RAG** | Past meetings as context | Partial via `memory.md` |
| **Tauri always-on-top** | Smooth-like UX | ✅ scaffold in `desktop/` |
| **Stealth / capture protection** | Hidden from screen share | ⬜ Tauri private API |

### 3. KazKozDev/live-translation (Mac-only gem)

| Pattern | Why | Flow status |
| --- | --- | --- |
| **MLX Whisper** | Apple Silicon speed | ⬜ optional if M1/M2/M3 |
| **Ollama sentence-level translation** | Better quality than Marian, still $0 | ⬜ optional (`translation.backend: ollama`) |
| **BlackHole + glass overlay** | Proven Mac audio path | ✅ documented in scripts |

## Recommended architecture for Flow (after study)

```text
                    ┌─────────────────────┐
  Mic / System ───► │ faster-whisper tiny │ ──► transcript (fast path)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ hallucination filter │
                    │ mention detector     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         Marian MT        Brief (lite)    Reply ×3 strategies
         ($0, fast)       heuristic       + ontology terms
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                     Flow overlay UI (Live/Brief/Compose)
```

**Do not** call cloud LLM on every transcript chunk (MeetU/NexQ also gate AI on events: @mention, interval, end-of-turn).

## License notes

- **MeetU**: Business Source License — free for personal/internal use; commercial competing product needs license until 2029.
- Prefer MIT/Apache patterns from NexQ, ghst, live-translation when copying code ideas.
- Flow stays MIT; we **reference designs**, not copy proprietary code.

## Next adoption priorities

1. ✅ Hallucination filter + mention detect + 3-way compose replies  
2. Dual-channel labels (You / Them) when system audio available  
3. Optional Ollama translation backend (Mac $0 quality bump)  
4. macOS ScreenCaptureKit path (eliminate BlackHole friction)  
5. SQLite session history + search  
