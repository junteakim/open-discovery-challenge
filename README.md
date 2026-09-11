# Open Discovery Challenge Harness / 탐색 하네스

**English** | Computational search harness for [FINAL-Bench Open Discovery Challenge](https://huggingface.co/spaces/FINAL-Bench/open-discovery-challenge) Season 1 (PfDHODH / malaria). This is **not a drug** — scores are model predictions, not wet-lab proof.

**한국어** | [FINAL-Bench Open Discovery Challenge](https://huggingface.co/spaces/FINAL-Bench/open-discovery-challenge) 시즌 1(PfDHODH / 말라리아)용 **코드 전용** 탐색 하네스입니다. **약물이 아닙니다** — 점수는 모델 예측이며 실험실 증명이 아닙니다.

## Rules enforced / 적용 규칙

0. Effective score ≤ 60 → auto-excluded (uses lower bound when uncertainty exists); **submit blocked by MW-band prior: only 500-550 band (median 67.6) passes**
1. Gates before scoring: PAINS, covalent warheads, MW cap, mutagenicity alerts, insolubility, duplicates, invalid structures
2. Optimize 70-pt core first (activity → binding → selectivity)
3. Scaffold hop — reject close analogues of known antimalarials (e.g. DSM265)
4. Rank by uncertainty lower bound
5. ADMET / synthesis after core is competitive
6. Persist feedback to `data/feedback.jsonl`
7. Mutate worst-scoring axis only
8. Parallel populations per scaffold family (round-robin)

**Note:** Computational predictions ≠ wet-lab validation. MW-band prior uses **median** from live 2026-08-19 leaderboard (honest, conservative). 450-500 band median is 42.6 (rejected), 500-550 band median is 67.6 (accepted). This is a **local filter**, not an official GPU score.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI

```bash
python -m discovery init
python -m discovery search --generations 3 --mock-scores   # local demo only
python -m discovery score "CCO"
python -m discovery submit "SMILES" "Display Name" --dry-run
```

## API / Auth

Endpoints are discovered at runtime from `/openapi.json` (falls back to `/gradio_api/openapi.json`).

- `GET /api/seasons`, `/api/leaderboard?season=1`
- `POST /api/submit` — requires `HF_TOKEN` or `CHALLENGE_TOKEN`

There is **no public `/api/score`** — official scoring happens after authenticated submit. The stub provider refuses to fake official scores.

## Environment

| Variable | Purpose |
|----------|---------|
| `HF_TOKEN` / `HUGGINGFACE_TOKEN` | Hugging Face auth for submit |
| `CHALLENGE_TOKEN` | Alternative auth token |
| `FINALBENCH_BASE_URL` | Override API base URL |
| `FINALBENCH_SEASON` | Season number (default 1) |

## Tests

```bash
pytest -q
```

## License

MIT — Copyright (c) Juntae Kim

## PipeCAD Web

브라우저용 플랜트 배관 CAD는 [`web/`](./web) 에 있습니다.

```bash
cd web && npm install && npm run dev
```

샘플 로그인: `SYSTEM` / `XXXXXX`
