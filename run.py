"""Find promos in a microdrama screenplay pack.

python run.py --input path/to/show_folder_or.zip --judge heuristic
python run.py --input show.zip --judge gemini          (needs GEMINI_API_KEY)
python run.py --input show.zip --judge groq --model llama-3.1-8b-instant
"""
import argparse
import csv
import io
import tempfile
import time
import zipfile
from collections import defaultdict
from pathlib import Path

from promo_finder.parse import load_show
from promo_finder.pipeline import all_candidates, transcript, rank, as_row, to_markdown, dump
from promo_finder.judge import make_judge
from promo_finder.qc import check


def resolve_input(p):
    p = Path(p)
    if p.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp())
        zipfile.ZipFile(p).extractall(tmp)
        p = tmp
    txts = list(p.rglob("*.txt"))
    folder = txts[0].parent if txts else p
    return folder, folder.name


def run(input_path, judge="heuristic", model=None, top=20, out="outputs", per_ep=4, log=print, llm_top=None):
    t0 = time.time()
    folder, title = resolve_input(input_path)
    eps = load_show(folder)
    eps = [e for e in eps if e["beats"]]
    if not eps:
        raise SystemExit("No timed beats found. Expected blocks like **NAME (Tone):** then "
                         "'Start: (mm:ss.xx) | End: (mm:ss.xx)'. Check the input format.")
    by_num = {e["ep"]: e for e in eps}
    log(f"Parsed {len(eps)} episodes, {sum(len(e['beats']) for e in eps)} beats")

    cands = all_candidates(eps, per_ep=per_ep)
    log(f"{len(cands)} candidates after code filtering")
    trs = {c["cid"]: transcript(by_num, c) for c in cands}
    context = f'"{title}". Episode 1: {eps[0]["logline"]}' if eps else title

    j = make_judge(judge, model=model) if judge != "heuristic" else make_judge()
    if llm_top and judge != "heuristic":  # quick mode: only the best clips go to the LLM
        cands = sorted(cands, key=lambda c: -c["score"])[:llm_top]
        log(f"Quick mode: sending the top {len(cands)} clips to the LLM")
    groups = defaultdict(list)
    for c in cands:
        groups[("arc", 0) if c["type"] == "arc_montage" else ("ep", c["segments"][0]["ep"])].append(c)
    size = 10 if llm_top else 6
    batches = []
    if llm_top:  # fewer, bigger calls
        flat = [c for g in groups.values() for c in g]
        batches = [flat[i:i + size] for i in range(0, len(flat), size)]
    else:
        for g in groups.values():
            for i in range(0, len(g), size):
                batches.append(g[i:i + size])
    usage = defaultdict(int)
    for n, b in enumerate(batches, 1):
        try:
            j.judge(b, trs, context)
            for k, v in (b[0].get("usage") or {}).items():  # one call per batch, count it once
                if isinstance(v, int):
                    usage[k] += v
        except Exception as e:  # keep going, mark it, fall back to code score
            msg = str(e)
            if msg[:3] in ("400", "401", "403", "404") or "daily quota" in msg:
                raise SystemExit(f"LLM setup error, stopping: {msg[:400]}")
            for c in b:
                c.setdefault("qc", []).append("judge_error")
            log(f"judge error on batch {n}: {e}")
        if n % 10 == 0:
            log(f"judged {n}/{len(batches)} batches")

    for c in cands:
        check(c, by_num)
    ranked = rank(cands, top=top)

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [as_row(c) for c in ranked]
    tag = j.name.replace(":", "_").replace("/", "_")
    dump(out / f"promos_ranked_{tag}.json", ranked)
    dump(out / f"candidates_all_{tag}.json", cands)
    with open(out / f"promos_ranked_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["editor_ok (y/n)", "editor_note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    per = sorted(cands, key=lambda c: (c["segments"][0]["ep"], -c.get("judge_score", c["score"])))
    with open(out / f"all_promos_by_episode_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(as_row(per[0]).keys()))
        w.writeheader()
        for c in per:
            w.writerow(as_row(c))
    (out / f"promos_ranked_{tag}.md").write_text(
        to_markdown(rows, f"Top {len(rows)} promos: {title} (judge: {j.name})"), encoding="utf-8")
    meta = {"show": title, "episodes": len(eps), "candidates": len(cands), "judge": j.name,
            "llm_calls": len(batches) if judge != "heuristic" else 0, "tokens": dict(usage),
            "seconds": round(time.time() - t0, 1)}
    dump(out / f"run_meta_{tag}.json", meta)
    log(f"Done in {meta['seconds']}s -> {out}")
    return ranked, cands, meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--judge", default="heuristic",
                    help="heuristic | gemini | groq | openrouter | openai | ollama")
    ap.add_argument("--model", default=None)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--quick", type=int, default=None, help="only send the top N clips to the LLM (e.g. 60)")
    a = ap.parse_args()
    run(a.input, a.judge, a.model, a.top, a.out, llm_top=a.quick)
