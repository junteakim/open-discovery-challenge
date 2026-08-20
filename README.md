# Open Discovery Challenge Harness / 탐색 하네스

**English** | Computational search harness for [FINAL-Bench Open Discovery Challenge](https://huggingface.co/spaces/FINAL-Bench/open-discovery-challenge) Season 1 (PfDHODH / malaria). This is **not a drug** — scores are model predictions, not wet-lab proof.

**한국어** | [FINAL-Bench Open Discovery Challenge](https://huggingface.co/spaces/FINAL-Bench/open-discovery-challenge) 시즌 1(PfDHODH / 말라리아)용 **코드 전용** 탐색 하네스입니다. **약물이 아닙니다** — 점수는 모델 예측이며 실험실 증명이 아닙니다.

## Rules enforced / 적용 규칙

0. **Local judgment layer** filters submits using official leaderboard conditionals (NOT MW-band median alone)
1. Gates before scoring: PAINS, covalent warheads, MW cap, mutagenicity alerts, insolubility, duplicates, invalid structures
2. Optimize 70-pt core first (activity → binding → selectivity)
3. Scaffold hop — reject close analogues of known antimalarials (e.g. DSM265)
4. Rank by uncertainty lower bound
5. ADMET / synthesis after core is competitive
6. Persist feedback to `data/feedback.jsonl`
7. Mutate worst-scoring axis only
8. Parallel populations per scaffold family (round-robin)
9. **NEW:** Warhead-constrained generation (pyrazole/benzene, NOT DSM triazolopyrimidine)
10. **NEW:** Failed-family fingerprint reject (Tanimoto vs known low-selectivity failures)

**Note:** Computational predictions ≠ wet-lab validation. 

**CRITICAL:** The local judgment layer uses **empirical conditionals** from official leaderboard (2026-08-20, n=2415):
- P(total≥60 | selectivity < 3) = 0/1169 = 0.0
- P(total≥60 | MW 500-550 AND sel < 3) = 0/64 = 0.0
- P(total≥60 | MW 500-550 AND sel ≥ 10) = 116/118 ≈ 0.983

**MW 500-550 alone is NEVER sufficient for submit.** The old median (67.6) mixed two populations. Low-selectivity molecules in that band have P(≥60) = 0. This is a **local filter**, not an official GPU score.

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

# NEW: Local judgment layer (NOT official GPU scores)
python -m discovery rank --smiles "CCO" "c1ccccc1"
python -m discovery rank --candidates-file candidates.txt --verbose
```

**⚠️ IMPORTANT:** The `rank` command produces **LOCAL judgments ONLY**, NOT official GPU scores. Do NOT auto-submit based on these rankings. Manual review is required.

## Local Judgment Layer

The judgment layer prevents blind hourly submits by filtering candidates through:

1. **Empirical prior** — Official leaderboard conditionals (documented data, not invented scores)
2. **Failed-family reject** — Tanimoto similarity vs known failed submissions (sel≈0, scores 6-41)
3. **DSM analogue reject** — Reject DSM265/antimalarial close analogues (novelty gate poison)
4. **Warhead-constrained generator** — Grow molecules from non-DSM warheads (pyrazole/benzene)
5. **should_submit()** — Refuse unless ALL conditions pass (gates + not-failed + not-DSM + warhead + prior≠0)

**Default is HOLD.** MW 500-550 alone will NOT pass. See `discovery/judgment/` for implementation.

All local judgments are labeled `LOCAL` / `empirical_prior_from_official_leaderboard`, never as official GPU scores.

## API / Auth

Endpoints are discovered at runtime from `/openapi.json` (falls back to `/gradio_api/openapi.json`).

- `GET /api/seasons`, `/api/leaderboard?season=1`
- `POST /api/submit` — requires `HF_TOKEN` or `CHALLENGE_TOKEN`

There is **no public `/api/score`** — official scoring happens after authenticated submit. The stub provider refuses to fake official scores. The local judgment layer does NOT produce official scores either.

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
