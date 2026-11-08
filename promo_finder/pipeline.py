"""parse -> candidates (code) -> judge (heuristic or any LLM) -> rank (code)"""
import json
from .parse import fmt
from .candidates import episode_candidates, arc_montage


def all_candidates(eps, per_ep=4, arc_len=3):
    cands = []
    for ep in eps:
        cands += episode_candidates(ep, k=per_ep)
    for i in range(0, len(eps) - arc_len + 1, arc_len):
        m = arc_montage(eps[i:i + arc_len])
        if m:
            cands.append(m)
    for i, c in enumerate(cands):
        c["cid"] = f"C{i:03d}"
    return cands


def transcript(eps_by_num, c, max_chars=2200):
    """Plain-text view of exactly what a viewer would see, segment by segment."""
    out = []
    for n, s in enumerate(c["segments"], 1):
        ep = eps_by_num[s["ep"]]
        out.append(f"[Segment {n} | Ep {s['ep']} {fmt(s['start'])}-{fmt(s['end'])}]")
        for b in ep["beats"]:
            if b["start"] >= s["start"] - 0.01 and b["end"] <= s["end"] + 0.01:
                t = round(b["start"] - s["start"], 1)
                if b["kind"] == "line":
                    out.append(f"+{t}s {b['who']} ({b['tone']}): \"{b['text']}\"")
                elif b["kind"] in ("action", "sound"):
                    out.append(f"+{t}s [{b['kind'].upper()}] {b['text']}")
    txt = "\n".join(out)
    return txt[:max_chars]


def rank(cands, top=20, per_ep=2, early_bonus=0.06):
    """Final order = judge score + small bonus for early episodes (a new
    viewer lands on Ep 1, so a promo from Ep 3 pays off faster than Ep 45).
    Max `per_ep` promos per episode in the top list so the feed has variety."""
    n = max(c["segments"][-1]["ep"] for c in cands)
    for c in cands:
        first_ep = c["segments"][0]["ep"]
        base = c.get("judge_score", c["score"])
        c["final"] = round(base + early_bonus * (1 - (first_ep - 1) / max(1, n - 1)), 4)
    order = sorted(cands, key=lambda c: -c["final"])
    picked, seen = [], {}
    for c in order:
        key = c["segments"][-1]["ep"]
        if c["type"] == "cold_open":  # don't post both a cut and its cold-open twin
            base_seg = c["segments"][-1]
            if any(p["segments"][-1] == base_seg for p in picked):
                continue
        else:
            if any(p["type"] == "cold_open" and p["segments"][-1] == c["segments"][0] for p in picked):
                continue
        if seen.get(key, 0) >= per_ep:
            continue
        if c.get("verdict") == "reject":
            continue
        seen[key] = seen.get(key, 0) + 1
        picked.append(c)
        if len(picked) >= top:
            break
    for i, c in enumerate(picked, 1):
        c["rank"] = i
    return picked


def as_row(c):
    segs = "; ".join(f"Ep{s['ep']} {fmt(s['start'])}-{fmt(s['end'])}" for s in c["segments"])
    return {"rank": c.get("rank", ""), "id": c["cid"], "type": c["type"], "segments": segs,
            "duration_s": c["duration"], "score": c.get("final", c["score"]),
            "hook": c.get("hook_line", c["hook_text"]), "cliffhanger": c.get("cliff_line", c["cliff_text"]),
            "why": c.get("why", ""), "qc_flags": ", ".join(c.get("qc", []))}


def to_markdown(rows, title):
    md = [f"# {title}\n"]
    for r in rows:
        md.append(f"## #{r['rank']}  {r['segments']}  ({r['duration_s']}s, {r['type']}, score {r['score']})")
        md.append(f"- **Hook:** {r['hook']}")
        md.append(f"- **Cliffhanger:** {r['cliffhanger']}")
        if r["why"]:
            md.append(f"- **Why it works:** {r['why']}")
        if r["qc_flags"]:
            md.append(f"- **QC flags:** {r['qc_flags']}")
        md.append("")
    return "\n".join(md)


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
