"""Reusable UI components. HTML snippets are built without blank lines or indentation so the
Markdown renderer keeps them as raw HTML blocks."""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Callable

import plotly.graph_objects as go
import streamlit as st

E = html.escape
PALETTE = ["#2dd4bf", "#a78bfa", "#38bdf8", "#f5b544", "#fb7185", "#34d399"]
STATUS_ICON = {"complete": "✅", "awaiting_approval": "✋", "blocked": "⛔", "error": "⚠️", "in_progress": "⏳"}
STATUS_TEXT = {"complete": "Finished", "awaiting_approval": "Needs approval", "blocked": "Blocked", "error": "Failed", "in_progress": "In progress"}
WEATHER_ICONS = [
    ("thunder", "⛈️"), ("storm", "⛈️"), ("snow", "❄️"), ("drizzle", "🌦️"), ("shower", "🌦️"), ("rain", "🌧️"),
    ("fog", "🌫️"), ("mist", "🌫️"), ("haze", "🌫️"), ("overcast", "☁️"), ("scattered", "⛅"), ("few clouds", "🌤️"),
    ("cloud", "⛅"), ("wind", "💨"), ("clear", "☀️"), ("sun", "☀️"),
]


def render(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def md_inline(text: str) -> str:
    out = E(str(text))
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", out)


def _next_key() -> int:
    n = st.session_state.get("_ck", 0) + 1
    st.session_state["_ck"] = n
    return n


# --------------------------------------------------------------------------- chrome
def brand() -> None:
    render(
        '<div class="brand"><div class="brand-mark">🧭</div><div><div class="brand-name">AI Travel Planner</div>'
        '<div class="brand-sub">Multi-agent system</div></div></div>'
    )


def hero(title: str, subtitle: str, compact: bool = False) -> None:
    cls = "vy-hero vy-compact" if compact else "vy-hero"
    render(f'<div class="{cls}"><h1 class="vy-title">{E(title)}</h1><p class="vy-sub">{E(subtitle)}</p></div>')


def section_header(icon: str, title: str, caption: str = "", badge: str = "") -> None:
    cap = f'<div class="cap">{E(caption)}</div>' if caption else ""
    chip = f'<span class="chip mute">{E(badge)}</span>' if badge else ""
    render(f'<div class="vy-sh"><div class="ico">{icon}</div><div><h3>{E(title)}</h3>{cap}</div><div class="sp"></div>{chip}</div>')


def chips(items: list[tuple[str, str]]) -> None:
    """items: (text, kind) where kind is ok | warn | err | mute | ''."""
    render(" ".join(f'<span class="chip {k}">{E(t)}</span>' for t, k in items))


def banner(title: str, detail: str = "", kind: str = "error", icon: str = "⚠️") -> None:
    cls = "vy-banner info" if kind == "info" else "vy-banner"
    d = f'<div class="d">{E(detail)}</div>' if detail else ""
    render(f'<div class="{cls}" role="alert"><div>{icon}</div><div><div class="t">{E(title)}</div>{d}</div></div>')


def empty_state() -> None:
    tiles = [
        ("📝", "Tell us the basics", "Add where you are going, when, who is coming and your budget in the sidebar."),
        ("🛰️", "Watch the agents work", "Flights, hotels, weather and budget specialists run live on the canvas above."),
        ("✋", "Approve or adjust", "Review the draft, approve it or ask for changes, and get a polished plan."),
    ]
    cards = "".join(f'<div class="vy-card hv vy-tile"><div style="font-size:1.5rem">{i}</div><h4>{E(t)}</h4><p>{E(d)}</p></div>' for i, t, d in tiles)
    render(f'<div class="vy-grid" style="margin-top:.4rem">{cards}</div>')


def skeleton(n: int = 3) -> None:
    render(f'<div class="vy-grid">{"".join(["<div class=sk></div>"] * n)}</div>')


def env_chips(report: list[tuple[str, bool, str]]) -> None:
    render(" ".join(f'<span class="chip {"ok" if ok else "err"}" title="{E(why)}">{"✓" if ok else "✗"} {E(k)}</span>' for k, ok, why in report))


def history_caption(item: dict) -> None:
    try:
        when = datetime.fromisoformat(item["ts"]).strftime("%b %d, %H:%M")
    except (ValueError, KeyError, TypeError):
        when = ""
    text = " · ".join(x for x in (STATUS_TEXT.get(item["status"], ""), item.get("subtitle", "")[:34], when) if x)
    render(f'<div class="hist-cap">{E(text)}</div>')


# --------------------------------------------------------------------------- result cards
def flight_cards(rows: list[dict]) -> None:
    cards = []
    for r in rows:
        cards.append(
            '<div class="vy-card hv">'
            f'<div class="fl-top"><span class="fl-air">{E(r["airline"])}</span><span class="fl-price">{E(r["price"] or "–")}</span></div>'
            f'<div class="fl-route"><div><div class="fl-time">{E(r["depart"] or "–")}</div><div class="fl-iata">{E(r["from"])}</div></div>'
            f'<div class="fl-line"><span>{E(r["duration"])}</span><i></i></div>'
            f'<div style="text-align:right"><div class="fl-time">{E(r["arrive"] or "–")}</div><div class="fl-iata">{E(r["to"])}</div></div></div>'
            f'<div class="fl-note">{md_inline(r["note"])}</div></div>'
        )
    render(f'<div class="vy-grid">{"".join(cards)}</div>')


def hotel_cards(rows: list[dict]) -> None:
    cards = []
    for r in rows:
        rating = f'<span class="ht-rate">★ {r["rating"]:.1f}</span>' if r.get("rating") else '<span class="chip mute">Not rated</span>'
        price = f'<span class="ht-price">{E(r["price"])} <small>per night</small></span>' if r.get("price") else '<span class="chip mute">Price not listed</span>'
        link = (
            f'<a class="ht-link" href="{E(r["url"], quote=True)}" target="_blank" rel="noopener noreferrer">View listing</a>'
            if str(r.get("url", "")).startswith(("http://", "https://")) else ""
        )
        cards.append(
            '<div class="vy-card hv">'
            f'<div class="ht-name">{E(r["name"])}</div><div class="ht-area">{E(r["area"])}</div>'
            f'<div class="ht-row">{rating}{price}</div><div class="ht-note">{md_inline(r["note"])}</div>{link}</div>'
        )
    render(f'<div class="vy-grid">{"".join(cards)}</div>')


def weather_icon(condition: str) -> str:
    low = (condition or "").lower()
    return next((icon for word, icon in WEATHER_ICONS if word in low), "🌡️")


def weather_strip(rows: list[dict]) -> None:
    def temp(v):
        return "–" if v is None else f"{v:.0f}°"

    days = "".join(
        f'<div class="vy-card hv wx-day"><div class="wx-ico">{weather_icon(r["condition"])}</div><div class="wx-lbl">{E(r["label"])}</div>'
        f'<div class="wx-cond">{E(r["condition"])}</div><div class="wx-t">{temp(r["high"])} <span>{temp(r["low"])}</span></div></div>'
        for r in rows
    )
    render(f'<div class="wx-strip">{days}</div>')


def itinerary_timeline(days: list[dict]) -> None:
    blocks = []
    for d in days:
        items = "".join(
            f'<div class="tl-item"><div class="tl-time">{E(i["time"])}</div><div>{md_inline(i["text"])}</div></div>' for i in d["items"]
        )
        title = E(d["title"]) if d["title"] else f"Day {d['day']}"
        blocks.append(f'<div class="tl-day"><div class="tl-dot">{d["day"]}</div><div class="vy-card"><div class="tl-title">{title}</div>{items}</div></div>')
    render(f'<div class="tl">{"".join(blocks)}</div>')


def stat_tiles(items: list[tuple[str, str, str]]) -> None:
    """items: (label, value, kind) where kind is '' | good | bad."""
    render('<div class="stat-row">' + "".join(f'<div class="stat {k}"><b>{E(v)}</b><span>{E(l)}</span></div>' for l, v, k in items) + "</div>")


def text_card(text: str, title: str = "") -> None:
    """Fallback when an agent's text could not be turned into cards."""
    with st.container(key=f"glass_{_next_key()}"):
        if title:
            st.markdown(f"**{title}**")
        st.markdown(text)


def _fmt(cur: str, value: float) -> str:
    return f"{cur}{value:,.0f}"


def budget_view(b: dict) -> None:
    items, cur = b["items"], b.get("currency") or "$"
    total, limit = sum(i["amount"] for i in items), b.get("limit")
    tiles = [("Estimated total", _fmt(cur, total), "")]
    if limit:
        diff = limit - total
        tiles += [("Your limit", _fmt(cur, limit), ""), ("Left over" if diff >= 0 else "Over budget by", _fmt(cur, abs(diff)), "good" if diff >= 0 else "bad")]
    stat_tiles(tiles)

    font = {"color": "#e8ecff", "family": "Plus Jakarta Sans, sans-serif"}
    base = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=font, margin=dict(l=10, r=10, t=10, b=10), height=300)
    left, right = st.columns([3, 2])
    donut = go.Figure(go.Pie(
        labels=[i["label"] for i in items], values=[i["amount"] for i in items], hole=0.64, sort=False,
        marker=dict(colors=PALETTE, line=dict(color="#0a0f24", width=3)), textinfo="percent", hovertemplate="%{label}: %{value:,.0f}<extra></extra>",
    ))
    donut.update_layout(**base, legend=dict(font=dict(size=12)), annotations=[dict(text=f"<b>{_fmt(cur, total)}</b><br>estimated", showarrow=False, font=dict(size=15))])
    left.plotly_chart(donut, theme=None, width="stretch", config={"displayModeBar": False}, key=f"plot_{_next_key()}")

    if limit:
        over = total > limit
        bars = go.Figure(go.Bar(
            x=[total, limit], y=["Estimated", "Limit"], orientation="h", text=[_fmt(cur, total), _fmt(cur, limit)], textposition="auto",
            marker=dict(color=["#fb7185" if over else "#2dd4bf", "#a78bfa"], cornerradius=8),
        ))
        bars.update_layout(**base, showlegend=False, xaxis=dict(visible=False), yaxis=dict(autorange="reversed"))
        right.plotly_chart(bars, theme=None, width="stretch", config={"displayModeBar": False}, key=f"plot_{_next_key()}")
    else:
        right.caption("No budget limit was found in the request, so only the cost split is shown.")
    if b.get("verdict"):
        banner("Budget check", b["verdict"], kind="info", icon="💡")


# --------------------------------------------------------------------------- approval + final
def approval_panel(run, S: dict, on_decide: Callable[[str], None]) -> None:
    cons = run.state.get("trip_constraints") or {}
    b = S["budget"]
    total = sum(i["amount"] for i in b["items"])
    tiles = [
        ("Destination", str(cons.get("destination") or run.form.get("destination") or "–"), ""),
        ("Length", str(cons.get("duration") or "–"), ""),
        ("Days planned", str(len(S["itinerary"])) if S["itinerary"] else "–", ""),
    ]
    if total and b.get("limit"):
        tiles.append(("Estimate vs limit", f'{_fmt(b["currency"], total)} / {_fmt(b["currency"], b["limit"])}', "good" if total <= b["limit"] else "bad"))
    with st.container(key="approval_panel"):
        render(
            '<div class="vy-sh" style="margin-top:0"><div class="ico">✋</div><div><h3>Approve this draft?</h3>'
            '<div class="cap">Read the itinerary below, then tell the final agent what to do.</div></div>'
            '<div class="sp"></div><span class="chip warn">Needs your review</span></div>'
        )
        stat_tiles(tiles)
        st.text_area("Feedback for the agents (required to request changes)", key="fb_text", height=90, placeholder="Example: swap day 3 for a day trip and keep hotels under 150 per night.")
        c1, c2, c3 = st.columns(3)
        c1.button("Approve plan", type="primary", icon=":material/check_circle:", width="stretch", key="btn_approve", on_click=on_decide, args=("approve",))
        c2.button("Request changes", icon=":material/edit_note:", width="stretch", key="btn_changes", on_click=on_decide, args=("changes",))
        c3.button("Reject", icon=":material/block:", width="stretch", key="btn_reject", on_click=on_decide, args=("reject",))


def final_card(run) -> None:
    text = str(run.state.get("final_response", ""))
    feedback = str(run.state.get("human_feedback", ""))
    rejected = run.state.get("approved") is False and feedback.startswith("[REJECTED]")
    revised = run.state.get("approved") is False and not rejected
    title = "Plan set aside" if rejected else "Revised plan" if revised else "Your trip plan"
    chip = ("Rejected", "err") if rejected else ("Revised from your feedback", "warn") if revised else ("Approved", "ok")
    dest = str((run.state.get("trip_constraints") or {}).get("destination") or run.form.get("destination") or "trip")
    slug = re.sub(r"[^a-z0-9]+", "-", dest.lower()).strip("-") or "trip"
    with st.container(key="final_card"):
        render(f'<div class="vy-sh" style="margin-top:0"><div class="ico">🏁</div><div><h3>{E(title)}</h3></div><div class="sp"></div><span class="chip {chip[1]}">{E(chip[0])}</span></div>')
        st.markdown(text or "_The final agent returned no text._")
        c1, c2, _ = st.columns([1, 1, 2])
        c1.download_button("Download Markdown", data=text, file_name=f"{slug}-plan.md", mime="text/markdown", icon=":material/download:", key="dl_md", width="stretch", on_click="ignore")
        pdf = to_pdf_bytes(title, text) if text else None
        if pdf:
            c2.download_button("Download PDF", data=pdf, file_name=f"{slug}-plan.pdf", mime="application/pdf", icon=":material/picture_as_pdf:", key="dl_pdf", width="stretch", on_click="ignore")


@st.cache_data(show_spinner=False)
def to_pdf_bytes(title: str, markdown: str) -> bytes | None:
    """Plain PDF export (fpdf2, core fonts). Emoji and non-Latin text are dropped. Returns None if fpdf2 is missing."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    swaps = {"–": "-", "—": "-", "→": "->", "’": "'", "‘": "'", "“": '"', "”": '"', "•": "-", "…": "...", "€": "EUR ", "\u00a0": " "}

    def clean(s: str) -> str:
        s = re.sub(r"[*_`>]{1,3}", "", s)
        for k, v in swaps.items():
            s = s.replace(k, v)
        return re.sub(r"[^\x20-\x7e\xa0-\xff]", "", s)

    pdf = FPDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    def line(txt: str, size: int, style: str, h: float) -> None:
        pdf.set_font("Helvetica", style, size)
        try:
            pdf.multi_cell(0, h, txt, new_x="LMARGIN", new_y="NEXT")
        except Exception:  # an unbreakable token (e.g. a very long URL); skip the line
            pdf.ln(h)

    line(clean(title), 20, "B", 10)
    pdf.ln(2)
    for raw in markdown.splitlines():
        if not raw.strip():
            pdf.ln(3)
            continue
        head = re.match(r"^(#{1,4})\s+(.*)", raw)
        if head:
            size = {1: 16, 2: 14, 3: 12, 4: 11}[len(head.group(1))]
            line(clean(head.group(2)), size, "B", size * 0.6)
        else:
            line(clean(re.sub(r"^\s*[-*+]\s+", "- ", raw.rstrip())), 11, "", 6)
    return bytes(pdf.output())


# --------------------------------------------------------------------------- trace tab
def trace_view(run) -> None:
    if run is None:
        banner("No trace yet", "Run a trip (or open one from the history) to see per-node output and timings here.", kind="info", icon="🔎")
        return
    chips([(f"thread {run.thread_id}", "mute"), ("demo data" if run.demo else "live graph", "warn" if run.demo else "ok"), (f"phase: {run.phase}", "mute"), (f"LLM calls: {run.state.get('llm_calls', 0)}", "mute")])
    rows = [{"Node": t["node"], "Seconds": t["seconds"], "State keys written": ", ".join(k for k in t["update"] if k != "messages") or "-"} for t in run.trace]
    if rows:
        top = max([r["Seconds"] for r in rows] + [1])
        st.dataframe(
            rows, hide_index=True, width="stretch",
            column_config={"Seconds": st.column_config.ProgressColumn("Seconds", format="%.2f", min_value=0, max_value=float(top))},
        )
    for t in run.trace:
        with st.expander(f'{t["node"]} ({t["seconds"]}s)'):
            st.json(t["update"], expanded=1)
    if run.interrupt:
        with st.expander("Pending interrupt payload"):
            st.json(run.interrupt, expanded=1)
    if run.error_detail:
        with st.expander("Error detail", expanded=True):
            st.code(run.error_detail)
    with st.expander("Full accumulated state"):
        st.json(run.state, expanded=1)
