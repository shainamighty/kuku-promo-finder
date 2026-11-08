"""Turn an episode into candidate promo windows (pure code, no AI)."""
from .heuristic import score_window, beat_heat, hook_score, cliff_score, standalone_score

MIN_D, MAX_D = 20.0, 60.0


def cut_points(beats):
    """Safe start/end times: never inside a line of dialogue."""
    lines = [(b["start"], b["end"]) for b in beats if b["kind"] == "line"]

    def inside_line(t):
        return any(s + 0.05 < t < e - 0.05 for s, e in lines)

    starts = sorted({round(b["start"], 2) for b in beats
                     if b["kind"] in ("line", "action") or b is beats[0]})
    starts = [t for t in starts if not inside_line(t)]
    ends = sorted({round(b["end"], 2) for b in beats})
    ends = [t for t in ends if not inside_line(t)]
    return starts, ends


def windows(ep):
    beats, dur = ep["beats"], ep["duration"]
    starts, ends = cut_points(beats)
    out = []
    for s in starts:
        for e in ends:
            d = e - s
            if d < MIN_D:
                continue
            if d > MAX_D:
                break
            sc = score_window(beats, s, e, ep["ep"], dur)
            out.append({"type": "single", "segments": [{"ep": ep["ep"], "start": s, "end": e}],
                        "duration": round(d, 2), **sc})
    return out


def iou(a, b):
    sa, ea = a["segments"][-1]["start"], a["segments"][-1]["end"]
    sb, eb = b["segments"][-1]["start"], b["segments"][-1]["end"]
    inter = max(0, min(ea, eb) - max(sa, sb))
    return inter / (max(ea, eb) - min(sa, sb))


def nms(cands, k=4, thr=0.25):
    keep = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if all(iou(c, x) < thr for x in keep):
            keep.append(c)
        if len(keep) >= k:
            break
    return keep


def moment(beats, b, min_len=2.5, max_len=7.0):
    """Expand one strong beat into a short clip, snapped so no line is cut."""
    s, e = b["start"], b["end"]
    if e - s < min_len:
        e = s + min_len
    lines = [x for x in beats if x["kind"] == "line"]
    for x in lines:
        if x["start"] < s < x["end"]:
            s = x["start"]
        if x["start"] < e < x["end"]:
            e = x["end"] if x["end"] - s <= max_len else x["start"]
    if e <= b["end"]:
        e = b["end"]
    return round(max(0.0, s), 2), round(e, 2)


def with_cold_open(c, ep):
    """ReelShort-style: flash the most explosive beat first, then play the
    stretch that builds to it and cuts at the cliffhanger."""
    seg = c["segments"][0]
    beats = ep["beats"]
    inside = [b for b in beats if b["start"] >= seg["start"] + 10 and b["end"] <= seg["end"] - 3
              and b["kind"] in ("line", "action")]
    if not inside:
        return None
    best = max(inside, key=beat_heat)
    if beat_heat(best) < 0.55 or beat_heat(best) <= c["hook"]:
        return None
    ms, me = moment(beats, best)
    total = (me - ms) + (seg["end"] - seg["start"])
    if total > MAX_D:
        return None
    teaser_hook = min(1.0, beat_heat(best) + 0.15)
    sc = dict(c)
    sc.update(type="cold_open", duration=round(total, 2),
              segments=[{"ep": ep["ep"], "start": ms, "end": me}, dict(seg)],
              hook=round(teaser_hook, 3),
              hook_text=(f'{best["who"]}: "{best["text"]}"' if best["kind"] == "line" else best["text"]))
    sc["score"] = round(c["score"] + 0.33 * (teaser_hook - c["hook"]) - 0.02, 4)
    return sc


def arc_montage(eps):
    """Cross-episode promo: setup beat from the first episode, escalation from
    the middle, then the last ~20-30s of the final episode (its cliffhanger)."""
    first, mid, last = eps[0], eps[len(eps) // 2], eps[-1]
    segs, used = [], 0.0
    for ep in (first, mid):
        talk = [b for b in ep["beats"] if b["kind"] == "line"]
        if not talk:
            return None
        b = max(talk, key=beat_heat)
        s, e = moment(ep["beats"], b, max_len=7.0)
        segs.append({"ep": ep["ep"], "start": s, "end": e, "_b": b})
        used += e - s
    starts, _ = cut_points(last["beats"])
    tail_start = None
    for s in starts:
        if 18 <= last["duration"] - s <= min(32, 58 - used):
            tail_start = s
            break
    if tail_start is None:
        return None
    segs.append({"ep": last["ep"], "start": tail_start, "end": round(last["duration"], 2)})
    h = min(1.0, beat_heat(segs[0]["_b"]) + 0.15)
    tail = [b for b in last["beats"] if b["start"] >= tail_start]
    c, cd = cliff_score(tail, last["duration"], last["duration"])
    allb = [segs[0]["_b"], segs[1]["_b"]] + tail
    st = standalone_score(allb, first["ep"])
    heat = sum(beat_heat(b) for b in allb) / len(allb)
    d = sum(x["end"] - x["start"] for x in segs)
    hb = segs[0]["_b"]
    for x in segs:
        x.pop("_b", None)
    return {"type": "arc_montage", "segments": segs, "duration": round(d, 2),
            "score": round((0.33 * h + 0.35 * c + 0.17 * min(1, heat * 2) + 0.15 * st) - 0.03, 4),
            "hook": round(h, 3), "cliff": round(c, 3), "heat": round(heat, 3),
            "standalone": round(st, 3),
            "hook_text": f'{hb["who"]}: "{hb["text"]}"', "cliff_text": cd}


def episode_candidates(ep, k=4):
    base = nms(windows(ep), k=k)
    extra = [x for x in (with_cold_open(c, ep) for c in base) if x]
    return base + extra
