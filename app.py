import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import ui
from run import run, resolve_input
from promo_finder.parse import load_show
from promo_finder.pipeline import transcript, as_row
from promo_finder.judge import PROVIDERS

st.set_page_config(page_title="Promo Finder", page_icon="🎬", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
ss = st.session_state


def secret(name):
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def html(s):
    st.markdown(s, unsafe_allow_html=True)


# ---------- sidebar: guide, saved runs, settings ----------
with st.sidebar:
    html(ui.brand())
    html(ui.howto())

    outs = sorted(Path("outputs").glob("promos_ranked_*.json"))
    shows = sorted(p for p in Path("data").glob("*") if p.is_dir()) if Path("data").exists() else []
    if outs and shows:
        html('<div class="side-h">Saved runs</div>')
        names = ["—"] + [p.stem.replace("promos_ranked_", "") for p in outs]
        pick = st.selectbox("Open a saved run", names, label_visibility="collapsed")
        if pick != "—" and ss.get("saved") != pick:
            p = Path("outputs") / f"promos_ranked_{pick}.json"
            mp = Path("outputs") / f"run_meta_{pick}.json"
            meta = json.loads(mp.read_text()) if mp.exists() else {"judge": pick}
            ss["res"] = (json.loads(p.read_text(encoding="utf-8")), meta, str(shows[0]))
            ss["saved"] = pick

    html('<div class="side-h">Settings</div>')
    with st.expander("Advanced: AI judge", expanded=False):
        judge = st.selectbox("Judge", ["heuristic"] + list(PROVIDERS),
                             help="heuristic = free offline rules (~20s). Others ask an LLM to re-score the shortlist.")
        model = st.text_input("Model", "", placeholder="default for this provider")
        key, mode = "", "Quick"
        if judge not in ("heuristic", "ollama"):
            env = PROVIDERS[judge][2]
            key = st.text_input(env, type="password", value=secret(env))
            mode = st.radio("AI run", ["Quick: top 60 clips (~2-3 min)", "Full: all clips (15-40 min on free tier)"])
            st.caption("Quick mode judges only the 60 clips the rules rate highest.")
    top = st.slider("Promos to return", 5, 40, 20)

# ---------- main ----------
html(ui.hero())

c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
up = c1.file_uploader("Upload a show (.zip of episode .txt scripts)", type=["zip"])
go = c2.button("Find promos", type="primary", disabled=not up, use_container_width=True)

if go and up:
    tmp = Path(tempfile.mkdtemp())
    z = tmp / up.name
    z.write_bytes(up.getvalue())
    if key:
        os.environ[PROVIDERS[judge][2]] = key
    with st.status("Reading the show...", expanded=True) as box:
        quick = 60 if mode.startswith("Quick") else None
        ranked, _, meta = run(z, judge, model or None, top, out=tmp / "out", log=box.write, llm_top=quick)
        box.update(label=f"Found {len(ranked)} promos in {meta['seconds']}s", state="complete", expanded=False)
    ss["res"] = (ranked, meta, str(z))
    ss["saved"] = None

if "res" not in ss:
    html(ui.empty())
    st.stop()

ranked, meta, src = ss["res"]
folder, _ = resolve_input(src)
by = {e["ep"]: e for e in load_show(folder)}

html('<div class="sec">Results</div>')
html(ui.tiles(meta, ranked))

with st.expander("Where in the show do the promos come from?"):
    html('<div class="sec-sub">One bar per episode. Taller = more promos from it, bright = a top-5 pick.</div>')
    html(ui.series_map(ranked, max(by)))

best = ranked[0]
html('<div class="sec">Top pick</div>')
html(ui.card(best, as_row(best), by, spot=True))
with st.expander("Details and full script"):
    html(ui.details(best, as_row(best), by))
    st.code(transcript(by, best, 6000), language=None)

html('<div class="sec">All promos</div>')
f1, f2 = st.columns([3, 1])
types = f1.multiselect("Filter", list(ui.TYPE.values()), default=list(ui.TYPE.values()),
                       label_visibility="collapsed", key="types")
view = f2.radio("View", ["Cards", "Table"], horizontal=True, label_visibility="collapsed", key="view")
rows = [x for x in ranked[1:] if ui.TYPE[x["type"]] in types]

if view == "Table":
    st.dataframe(pd.DataFrame([as_row(x) for x in [best] + rows]), width="stretch", hide_index=True)
else:
    for x in rows:
        html(ui.card(x, as_row(x), by))
        with st.expander("Details and full script"):
            html(ui.details(x, as_row(x), by))
            st.code(transcript(by, x, 6000), language=None)

html('<div class="sec">Take it to the editor</div>')
d1, d2, _ = st.columns([1, 1, 3])
df = pd.DataFrame([as_row(x) for x in ranked])
d1.download_button("Download CSV", df.to_csv(index=False), "promos.csv", use_container_width=True)
d2.download_button("Download JSON", json.dumps(ranked, indent=2), "promos.json", use_container_width=True)
