"""Briefing Deck Agent (Streamlit). Run: streamlit run app.py"""
import asyncio
import sys

# Windows: silence harmless "connection reset" noise when a browser disconnects.
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport

        _original_connection_lost = _ProactorBasePipeTransport._call_connection_lost

        def _quiet_connection_lost(self, exc):
            try:
                _original_connection_lost(self, exc)
            except ConnectionResetError:
                pass

        _ProactorBasePipeTransport._call_connection_lost = _quiet_connection_lost
    except Exception:
        pass

import io
import json
import zipfile
from pathlib import Path

import streamlit as st

from core import analyze as an, auth, build, data, decide as dc, plan as pl, research, scraper, understand

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text())
st.set_page_config(page_title="Briefing Deck Agent", page_icon="📊", layout="wide")
ss = st.session_state

# Global UI styling: light background, card-style login, professional buttons.
st.markdown("""
<style>
  .stApp { background: #f7f8fa; }

  [data-testid="stForm"] {
    max-width: 420px;
    width: 100%;
    margin: 1rem auto 2rem;
    padding: 2rem;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
  }

  .login-header { text-align: center; margin: 2rem 0 1rem; }

  button[data-testid="stBaseButton-primary"],
  button[data-testid="stBaseButton-secondaryFormSubmit"],
  button[kind="primary"] {
    background: #__PRIMARY__ !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15);
    transition: all .2s ease;
  }
  button[data-testid="stBaseButton-primary"]:hover,
  button[data-testid="stBaseButton-secondaryFormSubmit"]:hover,
  button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
  }

  button[data-testid="stBaseButton-secondary"],
  button[kind="secondary"] {
    border-radius: 10px !important;
  }

  button[data-testid="stBaseButton-secondaryFormSubmit"] {
    width: 100% !important;
    padding: 0.75rem 1rem !important;
  }

  /* Make the form's submit row stretch on small screens */
  [data-testid="stFormSubmitButton"],
  div:has(> [data-testid="stFormSubmitButton"]),
  [data-testid="stElementContainer"]:has(> div > [data-testid="stFormSubmitButton"]) {
    width: 100% !important;
  }

  .stTextInput input, .stPasswordInput input {
    border-radius: 10px;
    border: 1px solid #d1d5db;
  }

  @media (max-width: 600px) {
    [data-testid="stForm"] { margin: 0.5rem; padding: 1.25rem; }
    .login-header h1 { font-size: 1.5rem; }
    button[data-testid="stBaseButton-primary"],
    [data-testid="stButton"]:has(button[data-testid="stBaseButton-primary"]),
    [data-testid="stElementContainer"]:has(button[data-testid="stBaseButton-primary"]) {
      width: 100% !important;
    }
  }
</style>
""".replace("__PRIMARY__", CFG["theme"]["primary"]), unsafe_allow_html=True)

COOKIE_NAME = "bdauth"

# Preset selectors shown in the "What to extract" dropdown.
SCRAPE_PRESETS = {
    "Table rows — table tr": "table tr",
    "Section headings — h2": "h2",
    "Lists and cards — li": "li",
    "Paragraphs — p": "p",
}

TABS = ["1. Data", "2. Slide plan", "3. Download"]


def go_tab(name):
    st.query_params["tab"] = name
    st.rerun()


def set_auth_cookie(token):
    value = f"{COOKIE_NAME}={token}; path=/; max-age={auth.TOKEN_TTL}; SameSite=Lax"
    st.iframe(f"<script>document.cookie={json.dumps(value)};</script>", height=1)


def clear_auth_cookie():
    value = f"{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax"
    st.iframe(f"<script>document.cookie={json.dumps(value)};</script>", height=1)


def saved_user():
    """Username from a valid session cookie, or None."""
    try:
        token = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        token = None
    return auth.verify_token(token) if token else None


def login_gate():
    st.markdown(
        """
        <div class="login-header">
            <div style="font-size: 3rem; line-height: 1;">📊</div>
            <h1 style="margin: .25rem 0;">Briefing Deck Agent</h1>
            <p style="color: #6b7280; margin: 0;">Sign in to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if ss.get("fails", 0) >= 5:
        st.error("Too many failed attempts. Restart the app.")
        st.stop()
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    if ok:
        success, role = auth.authenticate(u, p)
        if success:
            ss.user, ss.role, ss.fails = u.strip().lower(), role, 0
            ss.logged_out = False
            ss.set_cookie = auth.make_token(ss.user)
            st.rerun()
        ss.fails = ss.get("fails", 0) + 1
        st.error("Invalid username or password.")
    st.caption("Accounts are issued by an administrator.")
    st.stop()


def offline_kit():
    """Zip of the files needed to run the agent offline (no users, no UI)."""
    buf = io.BytesIO()
    wanted = ["cli.py", "config.json", "requirements.txt", "sample_data.csv", "README.md",
              ".env.example"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in wanted:
            path = ROOT / name
            if path.is_file():  # skip optional files that are missing
                z.write(path, f"briefing_kit/{name}")
        for f in sorted((ROOT / "core").glob("*.py")):
            if f.name not in ("auth.py",):
                z.write(f, f"briefing_kit/core/{f.name}")
    return buf.getvalue()


def build_script():
    """Standalone .py that rebuilds the deck from the current plan and data."""
    result = dict(ss.result)
    result["groups"] = {str(k): float(v) for k, v in ss.result["groups"].items()}
    csv_text = ss.df.to_csv(index=False)
    return f'''"""Rebuild briefing.pptx from the data used in Briefing Deck Agent.

Run from the project root:  python build_briefing.py
"""
import io
import json
from pathlib import Path

import pandas as pd

from core import build

df = pd.read_csv(io.StringIO({csv_text!r}))
plan = json.loads({json.dumps(ss.plan, ensure_ascii=False)!r})
result = json.loads({json.dumps(result, ensure_ascii=False)!r})
result["groups"] = pd.Series(result["groups"])
cfg = json.loads({json.dumps(CFG, ensure_ascii=False)!r})

out = Path("briefing.pptx")
out.write_bytes(build.build_pptx(plan, df, result, cfg))
print(f"Saved {{out}}")
'''


def move(i, d):
    j = i + d
    if 0 <= j < len(ss.plan):
        ss.plan[i], ss.plan[j] = ss.plan[j], ss.plan[i]


# Restore the session from the cookie; set or clear it when asked.
if ss.pop("clear_cookie", False):
    clear_auth_cookie()
if not ss.get("user") and not ss.get("logged_out"):
    user = saved_user()
    if user:
        ss.user = user
        ss.role = auth.role_for(user)
pending_token = ss.pop("set_cookie", None)
if pending_token and ss.get("user"):
    set_auth_cookie(pending_token)

if not ss.get("user"):
    login_gate()

with st.sidebar:
    st.write(f"Signed in as **{ss.user}** ({ss.get('role', 'admin')})")
    if st.button("Sign out"):
        ss.clear()
        ss.logged_out = True
        ss.clear_cookie = True
        st.rerun()
    if ss.get("role", "admin") == "admin":
        st.download_button("Download offline kit (.zip)", offline_kit(), "briefing_kit.zip", "application/zip")

st.title("Briefing Deck Agent")
_current = st.query_params.get("tab", TABS[0])
if _current not in TABS:
    _current = TABS[0]
_selected = st.pills("Section", TABS, selection_mode="single", default=_current,
                     key="active_tab", label_visibility="collapsed")
if _selected != _current:
    st.query_params["tab"] = _selected
    st.rerun()

# ---- 1. Data
if _current == TABS[0]:
        f = st.file_uploader("Upload raw data", type=["csv", "xlsx", "json"])
        if f and ss.get("loaded") != (f.name, f.size):
            try:
                ss.df, ss.loaded = data.load(f, f.name), (f.name, f.size)
                ss.scrape_note = None
            except Exception as e:
                st.error(e)
        with st.expander("Or scrape a web page"):
            url = st.text_input("Page URL", key="scrape_url")
            mode = st.selectbox("What to extract", [*SCRAPE_PRESETS, "Custom selector…"],
                                key="scrape_extract",
                                help="Pick a preset, or choose 'Custom selector…' to type your own.")
            if mode == "Custom selector…":
                sel = (st.text_input("CSS selector", key="scrape_custom",
                                     placeholder="e.g. table.wikitable tr") or "table tr").strip()
            else:
                sel = SCRAPE_PRESETS[mode]
            st.caption("If the selector matches nothing, the page text is extracted automatically.")
            if st.button("Scrape") and url:
                try:
                    df = scraper.scrape(url, sel)
                    ss.df, ss.loaded = df, ("scrape", url)
                    ss.scrape_note = df.attrs.get("fallback")
                    if not ss.scrape_note:
                        st.success("Loaded.")
                except Exception as e:
                    ss.scrape_note = None
                    st.error(e)
        if ss.get("scrape_note"):
            st.info(ss.scrape_note)
        if ss.get("df") is not None:
            st.caption(f"{len(ss.df)} rows, {len(ss.df.columns)} columns")
            st.dataframe(ss.df, width="stretch", height=420)
            st.download_button("Download loaded data (.csv)",
                               ss.df.to_csv(index=False).encode("utf-8-sig"),
                               "loaded_data.csv", "text/csv")
            st.button("Next: Slide plan →", type="primary", on_click=go_tab, args=(TABS[1],))

    # ---- 2. Plan
if _current == TABS[1]:
        if ss.get("df") is None:
            st.info("Load data first.")
        else:
            org = st.text_input("Organisation", placeholder="e.g. Your Organisation")
            org = org.strip() or CFG["organisation"]
            tpl = st.file_uploader("Optional base template (.pptx with your logo and fonts)", type=["pptx"])
            ss.template = tpl.getvalue() if tpl else None
            is_admin = ss.get("role", "admin") == "admin"
            use_ai = st.checkbox("Add AI-drafted options (draft only, verify)",
                                 disabled=(not research.available(CFG)) or not is_admin,
                                 help="Needs an AI key in .env and an admin account.")
            user_text = st.text_area("Describe the situation",
                                     placeholder="e.g. we pay too much overtime and HR needs a plan next month",
                                     height=90)
            if st.button("Understand"):
                try:
                    profile = understand.profile_data(ss.df)
                    data_summary = understand.interpret_data(ss.df, profile, CFG, use_ai)
                    user_intent = understand.understand_user(user_text, list(ss.df.columns), CFG, use_ai)
                    if not user_intent.get("metric"):
                        user_intent["metric"] = data_summary.get("suggested_metric")
                    if not user_intent.get("group"):
                        user_intent["group"] = data_summary.get("suggested_group")
                    if not user_intent.get("goal"):
                        user_intent["goal"] = "reduce"
                    if not user_intent.get("problem"):
                        user_intent["problem"] = user_text.strip() or "Decision"
                    ss.understood = {"data_summary": data_summary, "user_intent": user_intent}
                    st.rerun()
                except Exception as e:
                    st.error(e)

            if ss.get("understood"):
                st.subheader("Here is what I understood")
                ui = ss.understood["user_intent"]
                ds = ss.understood["data_summary"]
                ui["problem"] = st.text_input("Problem", ui.get("problem", ""), key="understood_problem")
                ui["goal"] = st.selectbox("Goal", ["reduce", "increase"],
                                          index=0 if ui.get("goal") == "reduce" else 1,
                                          key="understood_goal")
                ui["metric"] = st.text_input("Metric column", ui.get("metric") or "", key="understood_metric")
                ui["group"] = st.text_input("Group column", ui.get("group") or "", key="understood_group")
                ui["audience"] = st.text_input("Audience", ui.get("audience") or "leadership",
                                               key="understood_audience")
                constraints = ui.get("constraints") or {}
                budget = st.text_input("Budget constraint", constraints.get("budget") or "",
                                       key="understood_budget")
                time_limit = st.text_input("Time constraint", constraints.get("time") or "",
                                           key="understood_time")
                ui["constraints"] = {"budget": budget or None, "time": time_limit or None}
                st.caption(f"Data: {ds.get('about', '')}")
                if st.button("Confirm and draft plan", type="primary"):
                    try:
                        agent = dc.run_agent(ss.df, user_text, CFG, use_ai, overrides=ui)
                        p = pl.make_plan(agent["result"], ui["problem"], org, CFG, agent=agent)
                        ss.result, ss.plan, ss.ver, ss.pptx = agent["result"], p, ss.get("ver", 0) + 1, None
                        ss.agent = agent
                    except Exception as e:
                        st.error(e)

            if ss.get("plan"):
                agent = ss.get("agent") or {}
                conf = (agent.get("check") or {}).get("confidence")
                if conf:
                    st.caption(f"Confidence: {conf.get('label')} — winner in {conf.get('wins')} of {conf.get('total')} scenarios")
                st.caption("Edit titles and bullets (one per line), switch slides off, or reorder.")
                for i, s in enumerate(ss.plan):
                    k = f"{s['id']}_{ss.ver}"
                    with st.expander(f"{i + 1}. {s['title']}", expanded=False):
                        s["on"] = st.checkbox("Include", s["on"], key=f"on_{k}")
                        s["title"] = st.text_input("Title", s["title"], key=f"t_{k}")
                        if s["type"] in ("title", "bullets"):
                            s["bullets"] = st.text_area("Bullets", "\n".join(s["bullets"]), key=f"b_{k}", height=130).split("\n")
                        else:
                            st.caption("Built automatically from the data.")
                        c1, c2, _ = st.columns([1, 1, 6])
                        c1.button("Up", key=f"u_{k}", on_click=move, args=(i, -1))
                        c2.button("Down", key=f"d_{k}", on_click=move, args=(i, 1))

                st.button("Next: Download →", type="primary", on_click=go_tab, args=(TABS[2],))

    # ---- 3. Download
if _current == TABS[2]:
        if not ss.get("plan"):
            st.info("Draft a slide plan first.")
        else:
            if st.button("Build PowerPoint", type="primary"):
                try:
                    ss.pptx = build.build_pptx(ss.plan, ss.df, ss.result, CFG, ss.get("template"))
                except Exception as e:
                    st.error(f"Build failed: {e}")
            if ss.get("pptx"):
                st.download_button("Download briefing.pptx", ss.pptx, "briefing.pptx",
                                   "application/vnd.openxmlformats-officedocument.presentationml.presentation")
            st.download_button("Download build script (.py)",
                               build_script().encode("utf-8"),
                               "build_briefing.py", "text/x-python")
