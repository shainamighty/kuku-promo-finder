import re
from pathlib import Path

TS = re.compile(r"\((\d+):(\d+(?:\.\d+)?)\)")
LABEL = re.compile(r"^\*\*(.+?):\*\*\s*$")


def secs(m, s):
    return int(m) * 60 + float(s)


def fmt(t):
    m = int(t // 60)
    return f"{m:02d}:{t - m * 60:05.2f}"


def parse_episode(text, name=""):
    head = {}
    for k in ("EPISODE NUMBER", "EPISODE LOGLINE", "CONTINUITY NOTES"):
        m = re.search(rf"^{k}:\s*(.*)$", text, re.M)
        head[k] = m.group(1).strip() if m else ""
    num = re.search(r"\d+", head["EPISODE NUMBER"] or name)
    ep = int(num.group()) if num else 0

    beats, scene, heading = [], 0, ""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("SCENE "):
            scene += 1
        elif ln.startswith("Scene heading:"):
            heading = ln.split(":", 1)[1].strip()
        m = LABEL.match(ln)
        if m and i + 1 < len(lines) and lines[i + 1].strip().startswith("Start:"):
            label = m.group(1).strip()
            t = TS.findall(lines[i + 1])
            if len(t) < 2:
                i += 1
                continue
            body = []
            j = i + 2
            while j < len(lines) and lines[j].strip() and not LABEL.match(lines[j].strip()):
                body.append(lines[j].strip())
                j += 1
            txt = " ".join(body).strip().strip('"')
            kind, who, tone = label.lower(), "", ""
            if label in ("CAMERA", "ACTION"):
                kind = label.lower()
            elif label.startswith("SOUND"):
                kind = "sound"
            else:
                kind = "line"
                mm = re.match(r"^(.*?)\s*\((.*)\)\s*$", label)
                who, tone = (mm.group(1), mm.group(2)) if mm else (label, "")
            beats.append({
                "ep": ep, "scene": scene, "heading": heading, "kind": kind,
                "who": who.strip(), "tone": tone.strip(), "text": txt,
                "start": secs(*t[0]), "end": secs(*t[1]),
            })
            i = j
            continue
        i += 1

    beats.sort(key=lambda b: (b["start"], b["end"]))
    for k, b in enumerate(beats):
        b["id"] = f"E{ep}-B{k}"
    dur = max((b["end"] for b in beats), default=0)
    return {"ep": ep, "logline": head["EPISODE LOGLINE"],
            "notes": head["CONTINUITY NOTES"], "duration": dur, "beats": beats}


def load_show(folder):
    eps = []
    for p in sorted(Path(folder).glob("*.txt")):
        eps.append(parse_episode(p.read_text(encoding="utf-8", errors="ignore"), p.name))
    return sorted(eps, key=lambda e: e["ep"])
