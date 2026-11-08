"""Quality report on a run: QC flag rates, coverage, and (if two judges ran)
how much they agree. python evaluate.py outputs"""
import json
import sys
from collections import Counter
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def report(d):
    d = Path(d)
    runs = sorted(d.glob("promos_ranked_*.json"))
    lines = []
    tops = {}
    for r in runs:
        tag = r.stem.replace("promos_ranked_", "")
        top = load(r)
        tops[tag] = top
        flags = Counter(f for c in top for f in c.get("qc", []))
        eps = sorted({s["ep"] for c in top for s in c["segments"]})
        durs = [c["duration"] for c in top]
        lines.append(f"## Judge: {tag}  (top {len(top)})")
        lines.append(f"- clean (no QC flag): {sum(1 for c in top if not c.get('qc'))}/{len(top)}")
        for f, n in flags.most_common():
            lines.append(f"- flag `{f}`: {n}")
        lines.append(f"- types: {dict(Counter(c['type'] for c in top))}")
        lines.append(f"- episodes covered: {len(eps)} -> {eps}")
        lines.append(f"- duration min/median/max: {min(durs)}/{sorted(durs)[len(durs)//2]}/{max(durs)}")
        allc = load(d / f"candidates_all_{tag}.json")
        rej = [c for c in allc if c.get("verdict") == "reject"]
        if rej:
            lines.append(f"- LLM rejected {len(rej)}/{len(allc)} candidates")
        lines.append("")
    if len(tops) >= 2:
        names = list(tops)
        key = lambda c: json.dumps(c["segments"])
        a, b = ({key(c) for c in tops[n]} for n in names[:2])
        lines.append(f"## Agreement {names[0]} vs {names[1]}: {len(a & b)}/{len(a)} of top picks shared")
    out = "\n".join(lines)
    (d / "quality_report.md").write_text(out)
    print(out)


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else "outputs")
