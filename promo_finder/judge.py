"""Judges. The LLM only scores and explains candidates that code already cut.
It never invents timestamps: it answers per candidate id, and any quote it
returns is checked against the transcript."""
import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

PROVIDERS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash", "GEMINI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free", "OPENROUTER_API_KEY"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY"),
    "ollama": ("http://localhost:11434/v1", "llama3.1", ""),
}

SYSTEM = """You are a senior performance-marketing editor for vertical microdrama apps
(ReelShort, DramaBox style). You judge promo clips that will run as paid ads on
TikTok / Reels / Shorts for viewers who have NEVER seen the show.

For each candidate you get the exact transcript a viewer would see. Score 0-10:
- hook: would a scrolling viewer stop in the first 3 seconds? (slap, reveal,
  shocking line, humiliation, threat). Establishing shots or mid-conversation
  replies score low.
- cliff: does it cut on an unresolved moment (threat, question, interruption,
  arrival, reveal about to land)? Ending on comfort, a hug or a resolved beat scores low.
- standalone: can a stranger follow who is who and what is at stake without
  backstory?
verdict: "keep" or "reject".
hook_line and cliff_line MUST be copied word for word from the transcript.
why: one plain sentence on why it would or would not convert.
If you are unsure, say so in why. Do not invent events that are not in the transcript.

Reply with JSON only: {"results":[{"id":..., "hook":int, "cliff":int,
"standalone":int, "verdict":"keep|reject", "hook_line":"...", "cliff_line":"...",
"why":"..."}]}"""


class HeuristicJudge:
    name = "heuristic"

    def judge(self, cands, transcripts, context):
        for c in cands:
            why = []
            why.append("strong opening beat" if c["hook"] >= 0.7 else "soft opening")
            if c["cliff"] >= 0.8:
                why.append("cuts on the episode's own cliffhanger" if "ominous" in c["cliff_text"].lower()
                           or c["cliff"] >= 0.9 else "ends on an unresolved beat")
            elif c["cliff"] < 0.4:
                why.append("ending may feel resolved")
            if c["standalone"] < 0.4:
                why.append("needs backstory")
            c["why"] = "; ".join(why).capitalize() + "."
            c["judge"] = self.name
        return cands


class LLMJudge:
    def __init__(self, provider="gemini", model=None, base_url=None, api_key=None,
                 cache_dir=".cache", rpm=None):
        url, default_model, env = PROVIDERS.get(provider, (None, None, ""))
        self.base = (base_url or os.getenv("LLM_BASE_URL") or url).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL") or default_model
        self.key = api_key or os.getenv("LLM_API_KEY") or (os.getenv(env) if env else "") or ""
        self.name = f"{provider}:{self.model}"
        self.cache = Path(cache_dir)
        self.cache.mkdir(exist_ok=True)
        self.gap = 60.0 / float(rpm or os.getenv("LLM_RPM", 8))
        self._last = 0.0

    def _call(self, messages):
        body = {"model": self.model, "messages": messages, "temperature": 0.2,
                "response_format": {"type": "json_object"}}
        h = hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
        f = self.cache / f"{h}.json"
        if f.exists():
            return json.loads(f.read_text())
        err = ""
        for attempt in range(7):
            wait = self.gap - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(
                f"{self.base}/chat/completions", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
            try:
                self._last = time.time()
                with urllib.request.urlopen(req, timeout=300) as r:
                    out = json.loads(r.read())
                text = out["choices"][0]["message"]["content"]
                f.write_text(json.dumps({"text": text, "usage": out.get("usage", {})}))
                return {"text": text, "usage": out.get("usage", {})}
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="ignore")
                if e.code == 400 and "response_format" in body:  # some providers lack JSON mode
                    body.pop("response_format")
                    continue
                if e.code == 429:
                    if re.search(r"per ?day|PerDay|daily", msg, re.I):
                        raise RuntimeError(f"429 daily quota used up: {msg[:300]}")
                    m = re.search(r'retry(?:Delay| in)\D{0,6}(\d+(?:\.\d+)?)', msg, re.I)
                    time.sleep(float(m.group(1)) + 2 if m else 20 * (attempt + 1))
                    err = f"429: {msg[:200]}"
                    continue
                if e.code in (500, 502, 503, 504):
                    time.sleep(15 * (attempt + 1))
                    err = f"{e.code}"
                    continue
                raise RuntimeError(f"{e.code}: {msg[:300]}")
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                err = f"network: {e}"
                time.sleep(10 * (attempt + 1))
                continue
        raise RuntimeError(f"LLM call kept failing: {err}")

    def judge(self, cands, transcripts, context):
        blocks = [f"### id={c['cid']} type={c['type']} duration={c['duration']}s\n{transcripts[c['cid']]}"
                  for c in cands]
        user = (f"Show premise (what a stranger might know from the ad's title): {context}\n\n"
                + "\n\n".join(blocks))
        res = self._call([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
        data = parse_json(res["text"])
        got = {str(r.get("id")): r for r in data.get("results", [])}
        for c in cands:
            r = got.get(c["cid"])
            c["judge"] = self.name
            c["usage"] = res.get("usage", {})
            if not r:
                c.setdefault("qc", []).append("llm_missing")
                continue
            llm = (0.38 * num(r.get("hook")) + 0.38 * num(r.get("cliff")) + 0.24 * num(r.get("standalone"))) / 10
            c["llm"] = {k: r.get(k) for k in ("hook", "cliff", "standalone", "verdict")}
            c["judge_score"] = round(0.7 * llm + 0.3 * c["score"], 4)
            c["verdict"] = str(r.get("verdict", "keep")).lower()
            c["why"] = r.get("why", "")
            tr = norm(transcripts[c["cid"]])
            for k, fb in (("hook_line", "hook_text"), ("cliff_line", "cliff_text")):
                q = (r.get(k) or "").strip()
                if q and norm(q) in tr:
                    c[k] = q
                else:  # quote not in transcript -> do not trust it
                    c.setdefault("qc", []).append(f"unverified_{k}")
                    c[k] = c[fb]
        return cands


def num(x):
    try:
        return max(0.0, min(10.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()


def parse_json(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0) if m else text)
    except json.JSONDecodeError:
        return {}


def make_judge(name="heuristic", **kw):
    if name == "heuristic":
        return HeuristicJudge()
    return LLMJudge(provider=name, **kw)
