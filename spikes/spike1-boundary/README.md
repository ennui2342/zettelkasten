# Spike 1 — Episode Boundary Detection

Validates H2 from `docs/design/zettelkasten-memory.md`.

## Run (primary — researcher pipeline data)

```bash
docker compose run --rm dev python spikes/spike1-boundary/spike.py
```

Results are written to `spikes/spike1-boundary/results.md`. Fill in the
qualitative scoring table manually after reviewing episode listings.

## Tuning

```bash
# Adjust word-overlap threshold for Approach B pre-filter (default 0.6)
MODEL=anthropic:claude-sonnet-4-6 SIM_THRESHOLD=0.5 docker compose run --rm dev \
  python spikes/spike1-boundary/spike.py

# Use a different model
MODEL=anthropic:claude-sonnet-4-6 docker compose run --rm dev \
  python spikes/spike1-boundary/spike.py
```

## LoCoMo supplementary benchmark (optional)

LoCoMo provides annotated session boundaries for quantitative precision/recall scoring.

**Download:**

```python
# Inside the dev container:
pip install datasets
python -c "
from datasets import load_dataset
ds = load_dataset('maharana/locomo', split='test')
import json
with open('spikes/spike1-boundary/locomo_test.jsonl', 'w') as f:
    for row in ds:
        f.write(json.dumps(row) + '\n')
print(f'Saved {len(ds)} conversations')
"
```

Once `locomo_test.jsonl` exists in this directory, the spike will automatically
run a fourth section scoring each approach against LoCoMo's annotated boundaries.

**LoCoMo data format:**
- Each row is a long conversation split across multiple sessions
- `sessions` field: list of sessions (each is the ground-truth episode)
- Sessions are concatenated and run through each boundary approach
- Score: precision, recall, F1 on recovering the annotated session boundaries

## Go / No-Go

After scoring the results table manually:

| Criterion | Target |
|-----------|--------|
| ≥2 approaches score ≥3.5/5 overall | → **Go** |
| Only 1 approach meets bar | → Investigate data format issues before deciding |
| 0 approaches meet bar | → **No-go**: revisit boundary mechanism before building |
