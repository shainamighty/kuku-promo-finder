"""Automatic checks on every promo (code, no AI)."""
from .heuristic import RESOLVE, WEAK_OPEN


def check(c, eps_by_num):
    flags = list(c.get("qc", []))
    if not 20 <= c["duration"] <= 60:
        flags.append("bad_duration")
    for s in c["segments"]:
        ep = eps_by_num.get(s["ep"])
        if not ep or s["start"] < 0 or s["end"] > ep["duration"] + 0.05 or s["end"] <= s["start"]:
            flags.append("out_of_bounds")
            continue
        for b in ep["beats"]:
            if b["kind"] != "line":
                continue
            for t in (s["start"], s["end"]):
                if b["start"] + 0.05 < t < b["end"] - 0.05:
                    flags.append("cuts_mid_line")
    first = c["segments"][0]
    ep = eps_by_num[first["ep"]]
    opening = [b for b in ep["beats"] if first["start"] <= b["start"] < first["start"] + 3]
    if not any(b["kind"] in ("line", "action") for b in opening):
        flags.append("no_line_or_action_in_first_3s")
    if any(b["kind"] == "camera" and WEAK_OPEN.search(b["text"]) for b in opening):
        flags.append("opens_on_establishing_shot")
    last = c["segments"][-1]
    ep = eps_by_num[last["ep"]]
    tail = [b for b in ep["beats"] if last["end"] - 4 <= b["end"] <= last["end"] + 0.01]
    if any(RESOLVE.search(b["text"]) for b in tail):
        flags.append("ending_may_resolve")
    if c["segments"][0]["ep"] >= 30:
        flags.append("late_episode_needs_backstory")
    if c["segments"][0]["start"] < 8 and c["segments"][0]["ep"] > 1:
        flags.append("starts_in_recap_of_prev_ep")
    c["qc"] = sorted(set(flags))
    return c
