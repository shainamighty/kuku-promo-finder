"""HTML pieces for the Streamlit app."""
import re
from html import escape as e

from promo_finder.parse import fmt

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea {font-family:'Inter',sans-serif !important}
.block-container{padding-top:3.2rem;max-width:1180px}
[data-testid="stSidebar"]{background:#101116;border-right:1px solid #22242e}
[data-testid="stSidebar"] .block-container{padding-top:2rem}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#FF6B4A,#FF3D7F);display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:16px}
.brand .nm{font-size:1.15rem;font-weight:800;color:#F2F2F5}
.side-h{font-size:.72rem;font-weight:700;color:#8b8d9c;text-transform:uppercase;letter-spacing:.08em;margin:18px 0 8px}
.step{display:flex;gap:10px;margin:8px 0;font-size:.86rem;color:#c9cad4;line-height:1.35}
.step .n{flex:none;width:22px;height:22px;border-radius:50%;background:#22242e;color:#FF8A6E;font-weight:700;font-size:.75rem;display:flex;align-items:center;justify-content:center}
.gl{font-size:.83rem;color:#b9bac6;margin:6px 0;line-height:1.35}
.gl b{color:#F2F2F5}
.hero{padding:26px 28px;border-radius:20px;background:radial-gradient(1200px 300px at 0% 0%,rgba(255,107,74,.18),transparent 60%),radial-gradient(800px 300px at 100% 0%,rgba(143,184,255,.12),transparent 60%),#121319;border:1px solid #23252f;margin-bottom:18px}
.hero .ttl{font-size:2.3rem;font-weight:800;letter-spacing:-.03em;color:#F4F4F7;line-height:1.1}
.hero .ttl span{background:linear-gradient(90deg,#FF6B4A,#FF3D7F);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero .sub{color:#a3a5b4;margin:8px 0 16px;font-size:1rem;max-width:720px}
.flow{display:flex;gap:10px;flex-wrap:wrap}
.flow .f{display:flex;align-items:center;gap:8px;background:#1a1c24;border:1px solid #2a2d39;border-radius:999px;padding:7px 14px;font-size:.85rem;color:#d8d9e0}
.flow .f i{font-style:normal;color:#FF8A6E;font-weight:700}
.flow .ar{color:#4a4d5c;align-self:center}
.sec{font-size:1.25rem;font-weight:800;color:#F2F2F5;margin:22px 0 4px;letter-spacing:-.01em}
.sec-sub{color:#8b8d9c;font-size:.88rem;margin-bottom:12px}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:6px 0 16px}
.tile{background:#14151B;border:1px solid #23252f;border-radius:14px;padding:14px 16px}
.tile .k{color:#8b8d9c;font-size:.74rem;text-transform:uppercase;letter-spacing:.06em}
.tile .v{font-size:1.55rem;font-weight:800;margin-top:4px;color:#F2F2F5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile .h{color:#6d6f7e;font-size:.75rem;margin-top:2px}
.map{background:#14151B;border:1px solid #23252f;border-radius:14px;padding:14px 16px;margin-bottom:6px}
.cells{display:flex;gap:3px;align-items:flex-end;height:46px}
.cell{flex:1;border-radius:3px;background:#262833;min-height:6px}
.cell.on{background:#FF6B4A}.cell.on2{background:#FFB199}
.axis{display:flex;justify-content:space-between;color:#6d6f7e;font-size:.72rem;margin-top:6px}
.card{display:grid;grid-template-columns:170px 1fr;gap:22px;background:#14151B;border:1px solid #23252f;border-radius:18px;padding:18px;margin:0 0 6px}
.card.spot{grid-template-columns:230px 1fr;border-color:#5a3328;background:linear-gradient(180deg,rgba(255,107,74,.07),transparent 40%),#14151B}
.phone{position:relative;aspect-ratio:9/16;border-radius:18px;overflow:hidden;border:2px solid #2c2f3b;background:linear-gradient(160deg,#2a1b2e,#121521 55%,#2a1a17);display:flex;flex-direction:column;justify-content:space-between;padding:12px 10px}
.phone:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 50% 40%,rgba(255,255,255,.06),transparent 60%)}
.phone .tag{position:relative;align-self:flex-start;font-size:.62rem;font-weight:700;background:rgba(0,0,0,.45);color:#fff;padding:3px 7px;border-radius:999px}
.phone .cap{position:relative;color:#fff;font-weight:800;font-size:.82rem;line-height:1.25;text-shadow:0 2px 8px rgba(0,0,0,.8);text-align:center}
.phone .cap.top{margin-top:8px}
.phone .cap.bot{font-weight:700;font-size:.74rem;color:#ffe2d9}
.phone .cta{position:relative;margin-top:8px;background:#FF6B4A;color:#fff;font-size:.66rem;font-weight:800;text-align:center;border-radius:8px;padding:6px}
.spot .phone .cap{font-size:1rem}.spot .phone .cap.bot{font-size:.86rem}.spot .phone .cta{font-size:.74rem}
.top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.rank{font-size:1.6rem;font-weight:800;color:#FF6B4A;margin-right:4px}
.spotlbl{font-size:.72rem;font-weight:800;color:#FF8A6E;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.badge{font-size:.7rem;font-weight:700;padding:3px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em}
.b-single{background:#1f2f4a;color:#8fb8ff}.b-cold_open{background:#40261f;color:#ffab8f}.b-arc_montage{background:#2e2447;color:#c3a8ff}
.chip{font-family:ui-monospace,Menlo,monospace;font-size:.76rem;background:#1d2029;color:#c9cad4;padding:3px 8px;border-radius:7px}
.score{margin-left:auto;text-align:right}
.score .n{font-size:1.5rem;font-weight:800;color:#F2F2F5}
.score .l{font-size:.66rem;color:#8b8d9c;text-transform:uppercase;letter-spacing:.06em}
.lbl{font-size:.68rem;color:#8b8d9c;text-transform:uppercase;letter-spacing:.07em;margin:14px 0 6px}
.tlrow{display:flex;align-items:center;gap:10px;margin:4px 0}
.tlrow .ep{font-size:.74rem;color:#8b8d9c;width:42px}
.bar{flex:1;height:9px;background:#232631;border-radius:6px;position:relative;overflow:hidden}
.seg{position:absolute;top:0;bottom:0;background:#FF6B4A;border-radius:6px}
.seg.t{background:#FFB199}
.tlrow .len{font-size:.7rem;color:#6d6f7e;width:44px;text-align:right}
.quotes{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0 8px}
.q{background:#1a1c24;border-left:3px solid #FF6B4A;border-radius:8px;padding:10px 12px}
.q.c{border-left-color:#8fb8ff}
.q .k{font-size:.66rem;color:#8b8d9c;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.q .t{font-size:.95rem;font-weight:600;line-height:1.35;color:#ECECF1}
.why{color:#b9bac6;font-size:.9rem;margin:6px 0 10px}
.why b{color:#ECECF1}
.arr{color:#5b5e6e;margin:0 2px}
.q .who{font-size:.72rem;font-weight:700;color:#FF8A6E;margin-bottom:2px}
.det{padding:4px 2px 10px}
.meters{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.m .k{display:flex;justify-content:space-between;font-size:.7rem;color:#8b8d9c;margin-bottom:4px}
.m .bar{height:6px}
.m .fill{position:absolute;top:0;bottom:0;left:0;background:linear-gradient(90deg,#FF6B4A,#FFB199);border-radius:6px}
.flags{margin-top:10px;display:flex;gap:6px;flex-wrap:wrap}
.flag{font-size:.68rem;background:#3a2a12;color:#f5c26b;padding:2px 8px;border-radius:999px}
.empty{border:1px dashed #2f3240;border-radius:18px;padding:34px;text-align:center;color:#8b8d9c}
.empty b{color:#F2F2F5;font-size:1.05rem}
@media(max-width:760px){.tiles{grid-template-columns:repeat(2,1fr)}.card,.card.spot{grid-template-columns:1fr}.phone{max-width:200px}.quotes,.meters{grid-template-columns:1fr}}
</style>
"""

TYPE = {"single": "Single cut", "cold_open": "Cold open", "arc_montage": "Montage"}


def brand():
    return '<div class="brand"><div class="logo">P</div><div class="nm">Promo Finder</div></div>'


def howto():
    steps = ["Upload the show as a <b>.zip</b> of episode .txt scripts.",
             "Click <b>Find promos</b>. Rules take ~20s; an AI judge is slower.",
             "Read the cards. Each one is a ready-to-cut ad clip.",
             "Download the CSV and hand it to the editor."]
    s = "".join(f'<div class="step"><div class="n">{i}</div><div>{t}</div></div>' for i, t in enumerate(steps, 1))
    g = ('<div class="gl"><b>Hook</b> · what plays in the first 3 seconds</div>'
         '<div class="gl"><b>Cliffhanger</b> · the moment the clip cuts</div>'
         '<div class="gl"><b>Single cut</b> · one continuous clip</div>'
         '<div class="gl"><b>Cold open</b> · flash the big moment, then the build-up</div>'
         '<div class="gl"><b>Montage</b> · moments from 3 episodes</div>')
    return f'<div class="side-h">How to use</div>{s}<div class="side-h">What the words mean</div>{g}'


def hero():
    return ('<div class="hero"><div class="ttl">Find the ads hiding in <span>your episodes</span></div>'
            '<div class="sub">Promo Finder reads every episode script and picks the 20 to 60 second clips that '
            'will stop a scroll and make people need the next episode.</div>'
            '<div class="flow"><div class="f"><i>1</i> Upload scripts</div><div class="ar">→</div>'
            '<div class="f"><i>2</i> Code cuts every possible clip</div><div class="ar">→</div>'
            '<div class="f"><i>3</i> AI judges the shortlist</div><div class="ar">→</div>'
            '<div class="f"><i>4</i> You pick what to post</div></div></div>')


def empty():
    return ('<div class="empty"><b>No show loaded yet</b><br>Upload a .zip above, or open a saved run from the sidebar.</div>')


def tiles(meta, ranked):
    clean = sum(1 for x in ranked if not x.get("qc"))
    items = [("Episodes read", meta.get("episodes", "-"), "whole show"),
             ("Clips judged", meta.get("candidates", "-"), "after code filtering"),
             ("Judge", str(meta.get("judge", "-")).split(":")[-1], "swap anytime"),
             ("Passed all checks", f"{clean}/{len(ranked)}", "no QC warning")]
    return '<div class="tiles">' + "".join(
        f'<div class="tile"><div class="k">{k}</div><div class="v" title="{e(str(v))}">{e(str(v))}</div>'
        f'<div class="h">{h}</div></div>' for k, v, h in items) + "</div>"


def series_map(ranked, n_eps):
    hits = {}
    for x in ranked:
        for s in x["segments"]:
            hits.setdefault(s["ep"], []).append(x["rank"])
    cells = []
    for ep in range(1, n_eps + 1):
        r = sorted(set(hits.get(ep, [])))
        if r:
            h = 18 + min(28, 9 * len(r))
            cls = "on" if min(r) <= 5 else "on2"
            cells.append(f'<div class="cell {cls}" style="height:{h}px" title="Ep {ep}: rank {", ".join(map(str, r))}"></div>')
        else:
            cells.append(f'<div class="cell" title="Ep {ep}"></div>')
    return (f'<div class="map"><div class="cells">{"".join(cells)}</div>'
            f'<div class="axis"><span>Ep 1</span><span>Ep {n_eps // 2}</span><span>Ep {n_eps}</span></div></div>')


def caption(t, n=95):
    t = str(t).strip()
    m = re.match(r'^[A-Z][A-Z .\'-]+:\s*"?(.*?)"?$', t)
    if m:
        t = m.group(1)
    t = t.strip('"')
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def phone(x, r):
    s = x["segments"][0]
    last = x["segments"][-1]["ep"]
    return (f'<div class="phone"><div class="tag">Ep {s["ep"]} · {fmt(s["start"])[:5]}</div>'
            f'<div class="cap top">{e(caption(r["hook"]))}</div>'
            f'<div><div class="cap bot">{e(caption(r["cliffhanger"], 80))}</div>'
            f'<div class="cta">▶ Watch Ep {last}</div></div></div>')


def timeline(x, by):
    rows = []
    for i, s in enumerate(x["segments"]):
        dur = by[s["ep"]]["duration"] or 1
        l, w = 100 * s["start"] / dur, max(1.5, 100 * (s["end"] - s["start"]) / dur)
        tease = " t" if x["type"] == "cold_open" and i == 0 else ""
        rows.append(f'<div class="tlrow"><div class="ep">Ep {s["ep"]}</div><div class="bar">'
                    f'<div class="seg{tease}" style="left:{l:.2f}%;width:{w:.2f}%"></div></div>'
                    f'<div class="len">{fmt(dur)[:5]}</div></div>')
    return "".join(rows)


def meters(x):
    l = x.get("llm")
    if l:
        vals = [("Hook", l.get("hook")), ("Cliffhanger", l.get("cliff")), ("Makes sense alone", l.get("standalone"))]
    else:
        vals = [("Hook", x["hook"] * 10), ("Cliffhanger", x["cliff"] * 10), ("Makes sense alone", x["standalone"] * 10)]
    out = []
    for k, v in vals:
        try:
            v = max(0.0, min(10.0, float(v)))
        except (TypeError, ValueError):
            v = 0.0
        out.append(f'<div class="m"><div class="k"><span>{k}</span><span>{v:.0f}/10</span></div>'
                   f'<div class="bar"><div class="fill" style="width:{v * 10:.0f}%"></div></div></div>')
    return '<div class="meters">' + "".join(out) + "</div>"


def speaker(t):
    t = str(t).strip()
    m = re.match(r'^([A-Z][A-Z .\'-]+):\s*"?(.*?)"?$', t)
    return (m.group(1).title(), m.group(2)) if m else ("", t.strip('"'))


def quote(k, t, cls=""):
    who, txt = speaker(t)
    w = f'<div class="who">{e(who)}</div>' if who else ""
    return f'<div class="q {cls}"><div class="k">{k}</div>{w}<div class="t">{e(txt)}</div></div>'


def card(x, r, by, spot=False):
    cuts = ' <span class="arr">→</span> '.join(
        f'<span class="chip">Ep{s["ep"]} {fmt(s["start"])}–{fmt(s["end"])}</span>' for s in x["segments"])
    lbl = '<div class="spotlbl">★ Post this first</div>' if spot else ""
    why = f'<div class="why"><b>Why it works:</b> {e(r["why"])}</div>' if r["why"] else ""
    return (f'<div class="card{" spot" if spot else ""}">{phone(x, r)}<div>{lbl}'
            f'<div class="top"><div class="rank">#{r["rank"]}</div>'
            f'<span class="badge b-{x["type"]}">{TYPE[x["type"]]}</span>'
            f'<span class="chip">{r["duration_s"]}s</span></div>'
            f'<div class="lbl">Cut</div><div class="top">{cuts}</div>'
            f'<div class="quotes">{quote("Hook · first 3 seconds", r["hook"])}'
            f'{quote("Cliffhanger · where it cuts", r["cliffhanger"], "c")}</div>'
            f'{why}</div></div>')


def details(x, r, by):
    flags = "".join(f'<span class="flag">⚠ {e(f.replace("_", " "))}</span>' for f in x.get("qc", []))
    return (f'<div class="det"><div class="lbl">Score {float(r["score"]):.2f}</div>{meters(x)}'
            f'<div class="lbl">Position in the episode</div>{timeline(x, by)}'
            f'{"<div class=lbl>QC warnings</div><div class=flags>" + flags + "</div>" if flags else ""}</div>')
