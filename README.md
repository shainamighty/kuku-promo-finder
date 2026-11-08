# Promo Finder

Reads a microdrama screenplay pack and returns ranked 20 to 60 second promo cuts:
episode, start and end timestamps of every segment, the hook, the cliffhanger and
one line on why it works.

## How it works

```
episode .txt files
  -> parse.py       code: every camera / action / dialogue / sound beat with timestamps
  -> candidates.py  code: every 20-60s window that starts and ends on a clean cut
                    (never mid-line), rule-scored, overlap removed, top 4 per episode,
                    plus cold-open and cross-episode montage variants
  -> judge.py       swappable: heuristic rules (free, offline) or any LLM
                    (Gemini, Groq, OpenRouter, OpenAI, local Ollama) re-scores the shortlist
  -> qc.py          code: duration, mid-line cuts, weak opening, resolved ending,
                    unverified LLM quotes, backstory risk
  -> pipeline.rank  code: final order, max 2 per episode, early-episode bonus
```

The LLM never writes timestamps. It only scores candidates by id, and any line it
quotes is checked word for word against the script. Quotes that don't match are
flagged and replaced.

## Run

```bash
pip install -r requirements.txt

# offline baseline, no key needed
python run.py --input path/to/show.zip --judge heuristic

# LLM judge (free key from aistudio.google.com)
export GEMINI_API_KEY=...
python run.py --input path/to/show.zip --judge gemini

# swap model or provider
python run.py --input show.zip --judge gemini --model gemini-3.5-flash-lite
export GROQ_API_KEY=... && python run.py --input show.zip --judge groq
LLM_BASE_URL=https://any-openai-compatible/v1 LLM_API_KEY=... LLM_MODEL=... python run.py --input show.zip --judge openai

# quick AI run: only the top 60 clips go to the LLM (6 calls instead of 54)
python run.py --input show.zip --judge gemini --quick 60

# quality report across runs
python evaluate.py outputs

# web app
streamlit run app.py
```

Free-tier note: `LLM_RPM` (default 8) throttles calls. LLM replies are cached in
`.cache/`, so a re-run costs nothing.

## Outputs (in `outputs/`)

- `promos_ranked_<judge>.md / .csv / .json`: the top list (CSV has editor_ok and note columns)
- `all_promos_by_episode_<judge>.csv`: every candidate, per episode
- `candidates_all_<judge>.json`: full scores, QC flags, LLM verdicts
- `run_meta_<judge>.json`: counts, tokens, time

The input screenplays are Kuku's confidential content and are not in this repo.
