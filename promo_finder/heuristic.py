"""Rule-based scoring. Cheap, offline, deterministic. Used to shortlist
candidates (and as a fallback judge when no LLM key is set)."""
import re

HOT = set("""cold cruel furious shouting screaming mocking venomous threatening scornful
spiteful taunting sinister menacing gloating outraged hysterical enraged ruthless deadly
vicious shrieking accusatory accusing condemning contemptuous chilling desperate defiant
sneering smug arrogant condescending malicious vindictive terrified panicked horrified
sobbing weeping begging pleading shocked stunned gasping broken devastated betrayed
thunderous booming commanding demanding harsh vengeful triumphant warning ominous
dangerous scathing biting icy brutal aggressive roaring incredulous fierce steely
unyielding dismissive derisive callous imperious haughty agonized anguished shattered
heartbroken crying""".split())
SOFT = set("""gentle soft calm warm tender reassuring loving peaceful relieved grateful
comforting playful fond amused curious reflective sincere earnest caring quiet low
measured steady humble pleased""".split())

STAKES = re.compile(r"\b(slap\w*|struck|strikes?|crop|blood\w*|bleed\w*|fire|flames?|blaze|"
                    r"inferno|explo\w+|smoke|swords?|blade|knife|dagger|chain\w*|shackle\w*|"
                    r"dungeon|execut\w+|gallows|hang\w*|noose|poison\w*|arsenic|witch\w*|"
                    r"arrest\w*|seiz\w+|shov\w+|hurl\w*|throws?|mud|kneel\w*|knee|propos\w+|"
                    r"kiss\w*|collaps\w+|scream\w*|burn\w*|red-hot|betray\w*|abandon\w*|"
                    r"disown\w*|duke|duchess|crown|heir|dead|alive|reveal\w*|unmask\w*|"
                    r"fram\w+|trial|guilty|sentenc\w+|thorns?|briars?|kill\w*|murder\w*|"
                    r"thief|theft|stole\w*|liar|traitor|treason|grab\w*|choke\w*|"
                    r"bursts?|storms?|slams?|weds?|wedding|altar|marry|married)\b", re.I)
CLIFF = re.compile(r"(cut to black|freez\w+|ominous|swell\w*|sting|cliffhanger|"
                   r"bursts? (in|open|through)|doorway|appears|arriv\w+|silhouette|"
                   r"hold(s|ing)? on|interrupt\w*|footsteps|creak\w*|gasp\w*|shock\w*|"
                   r"tension|suspense|dread|unresolved)", re.I)
RESOLVE = re.compile(r"\b(smil\w+|embrac\w+|peace\w*|relie\w+|warmth|laugh\w*|thank\w*|"
                     r"sleep\w*|safe|comfort\w*|hug\w*|content\w*|serene|happily|"
                     r"into the (sun)?light|sunlight|hand[- ]in[- ]hand|fad(es|ing) out|triumphant (swell|music)|tenderly|kiss(es)? her forehead)\b", re.I)
CONTEXT = re.compile(r"\b(remember|earlier|yesterday|last night|again|as I said|"
                     r"you promised|back then|after what)\b", re.I)
ARCHETYPE = re.compile(r"\b(husband|wife|sister|mother|father|son|daughter|fianc\w+|bride|"
                       r"groom|duke|duchess|maid|stepmother|family|wedding|marr\w+)\b", re.I)
WEAK_OPEN = re.compile(r"\b(establishing|wide shot|exterior|landscape|aerial|drone|slow pan|"
                       r"dawn|sunrise|morning light|exterior)\b", re.I)
REPLY_OPEN = re.compile(r"^(and|but|because|so|then|yes|well|also)\b", re.I)


def tone_heat(tone):
    ws = [w.strip().lower() for w in re.split(r"[,/;]| and ", tone) if w.strip()]
    if not ws:
        return 0.0
    hot = sum(any(h in w for h in HOT) for w in ws)
    soft = sum(any(s in w for s in SOFT) for w in ws)
    return max(0.0, min(1.0, (hot - 0.7 * soft) / len(ws)))


def beat_heat(b):
    """0..1 intensity of a single beat."""
    t = b["text"]
    s = min(1.0, 0.35 * len(STAKES.findall(t)))
    if b["kind"] == "line":
        s = 0.55 * tone_heat(b["tone"]) + 0.45 * s
        if t.endswith("!") or t.endswith("?"):
            s += 0.1
    elif b["kind"] == "action":
        s *= 0.9
    else:  # camera / sound carry less weight
        s *= 0.5
    return min(1.0, s)


def hook_score(beats, start):
    """What is on screen in the first 3 seconds?"""
    first = [b for b in beats if start <= b["start"] < start + 3.0]
    if not first:
        return 0.0, ""
    talk = [b for b in first if b["kind"] in ("line", "action")]
    h = max([beat_heat(b) for b in first] + [0])
    if not talk:
        h *= 0.5
    lines = [b for b in first if b["kind"] == "line"]
    if lines:
        h += 0.15
        if REPLY_OPEN.match(lines[0]["text"]):
            h -= 0.2
    if any(WEAK_OPEN.search(b["text"]) for b in first if b["kind"] == "camera"):
        h -= 0.2
    best = max(talk or first, key=beat_heat)
    desc = (f'{best["who"]}: "{best["text"]}"' if best["kind"] == "line" else best["text"])
    return max(0.0, min(1.0, h)), desc


def cliff_score(beats, end, ep_end):
    """How unresolved is the last ~4 seconds?"""
    last = [b for b in beats if end - 4.0 <= b["end"] <= end + 0.01]
    if not last:
        return 0.0, ""
    txt = " ".join(b["text"] for b in last)
    c = 0.25 * min(2, len(CLIFF.findall(txt)))
    c += 0.5 * max(beat_heat(b) for b in last)
    lines = [b for b in last if b["kind"] == "line"]
    if lines:
        lt = lines[-1]["text"]
        if lt.endswith("?") or lt.endswith("...") or lt.endswith("—") or lt.endswith("-"):
            c += 0.2
        if re.search(r"\b(or|unless|if you|will|until)\b", lt, re.I):
            c += 0.1
    resolved = bool(RESOLVE.search(txt))
    if resolved:
        c -= 0.35
    if ep_end - end < 1.5 and not resolved:  # writers usually end episodes on a cliffhanger
        c += 0.3
    key = lines[-1] if lines else last[-1]
    desc = (f'{key["who"]}: "{key["text"]}"' if key["kind"] == "line" else key["text"])
    return max(0.0, min(1.0, c)), desc


def standalone_score(beats, ep):
    who = {b["who"] for b in beats if b["kind"] == "line"}
    txt = " ".join(b["text"] for b in beats)
    s = 0.6
    s -= 0.08 * max(0, len(who) - 3)
    s -= 0.1 * min(3, len(CONTEXT.findall(txt)))
    s += 0.2 if ARCHETYPE.search(txt) else 0
    s += 0.2 if len([b for b in beats if b["kind"] == "line"]) >= 4 else 0
    s -= 0.004 * ep  # later episodes lean on more backstory (assumption)
    return max(0.0, min(1.0, s))


def dur_fit(d):
    if d < 20 or d > 60:
        return 0.0
    if 28 <= d <= 50:
        return 1.0
    return 0.75


def score_window(beats, start, end, ep, ep_end):
    inside = [b for b in beats if b["start"] >= start - 0.01 and b["end"] <= end + 0.01]
    h, hd = hook_score(inside, start)
    c, cd = cliff_score(inside, end, ep_end)
    heat = sum(beat_heat(b) for b in inside) / max(1, len(inside))
    st = standalone_score(inside, ep)
    total = (0.33 * h + 0.35 * c + 0.17 * min(1, heat * 2) + 0.15 * st) * (0.7 + 0.3 * dur_fit(end - start))
    return {"score": round(total, 4), "hook": round(h, 3), "cliff": round(c, 3),
            "heat": round(heat, 3), "standalone": round(st, 3),
            "hook_text": hd, "cliff_text": cd}
