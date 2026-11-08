"""Streamlit front end for the multi-agent travel planner.

Run:  streamlit run app.py
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

import backend
from ui import canvas, styles
from ui import components as ui

st.set_page_config(page_title="Multi-Agent AI Travel Planner", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
styles.inject()

INTERESTS = ["Food", "Culture", "Nature", "Nightlife", "Shopping", "Adventure", "Relaxation", "History"]
CURRENCIES = ["USD", "EUR", "GBP", "PKR", "AED"]
AGENT_CHIPS = {
    "flight_agent": "✈️ Flights", "hotel_agent": "🏨 Hotels", "weather_agent": "🌤️ Weather", "budget_agent": "💰 Budget",
}
IDLE_STATUS = {n: "idle" for n in backend.ALL_NODES}


# ------------------------------------------------------------------------------ state
def init_state() -> None:
    ss = st.session_state
    ss.setdefault("demo", not backend.env_ready())
    ss.setdefault("run", None)
    ss.setdefault("job", None)
    ss.setdefault("demo_store", backend.seed_demo_store())
    ss.setdefault("history", None)
    ss.setdefault("history_error", "")
    ss.setdefault("structured", {})
    ss.setdefault("flash", None)
    ss.setdefault("speed", 1.0)
    ss.setdefault("ai_extract", True)


def _invalidate_history() -> None:
    st.session_state.history = None


def _open_trip(thread_id: str) -> None:
    st.session_state.load_tid = thread_id


def _decide(kind: str) -> None:
    """Callback for the approval buttons; the graph is resumed in the main script flow."""
    ss = st.session_state
    feedback = str(ss.get("fb_text", "")).strip()
    if kind == "approve":
        job = {"type": "resume", "approved": True, "feedback": feedback}
    elif kind == "changes":
        if not feedback:
            ss.flash = ("⚠️", "Add feedback first so the agents know what to change.")
            return
        job = {"type": "resume", "approved": False, "feedback": feedback}
    else:
        reason = f" Reason: {feedback}" if feedback else ""
        job = {"type": "resume", "approved": False, "feedback": f"[REJECTED] The user rejected this plan outright.{reason} Do not revise it. Briefly acknowledge and suggest two alternative directions."}
    ss.job = job


def refresh_history() -> None:
    ss = st.session_state
    if ss.history is not None:
        return
    try:
        ss.history, ss.history_error = backend.list_threads(ss.demo, ss.demo_store), ""
    except Exception as exc:  # noqa: BLE001
        ss.history, ss.history_error = [], backend._friendly(exc)


# ------------------------------------------------------------------------------ sidebar
def build_query(form: dict, preferred: list[str]) -> str:
    parts = [
        f"Plan a {form['days']}-day trip from {form['origin']} to {form['destination']}, {form['start']} to {form['end']}, "
        f"for {form['travelers']} traveler{'s' if form['travelers'] != 1 else ''}.",
        f"Total budget: {form['budget']:,.0f} {form['currency']}.",
        f"Travel style: {form['style']}.",
    ]
    if form["interests"]:
        parts.append("Interests: " + ", ".join(form["interests"]) + ".")
    if len(preferred) < len(AGENT_CHIPS):
        parts.append("Only consult these specialists: " + ", ".join(preferred or ["itinerary_agent"]) + ". Skip the others.")
    return " ".join(parts)


def sidebar() -> None:
    ss = st.session_state
    with st.sidebar:
        ui.brand()
        st.toggle("Demo mode", key="demo", on_change=_invalidate_history, help="Simulates the whole run with sample data. No API keys or database needed.")
        if ss.demo:
            st.caption("Sample data, no API calls.")
        with st.expander("Settings and environment"):
            st.slider("Demo speed", 0.5, 4.0, key="speed", step=0.5, help="Higher is faster.")
            st.toggle("AI card extraction", key="ai_extract", disabled=ss.demo, help="One extra LLM call turns agent text into cards. Off uses regex only.")
            ui.env_chips(backend.env_report())

        today = date.today()
        with st.form("trip_form", border=False):
            c1, c2 = st.columns(2)
            origin = c1.text_input("From", value="London")
            destination = c2.text_input("To", value="Tokyo")
            dates = st.date_input("Dates", value=(today + timedelta(days=30), today + timedelta(days=36)), min_value=today)
            c3, c4 = st.columns(2)
            travelers = c3.number_input("Travelers", 1, 12, 2)
            currency = c4.selectbox("Currency", CURRENCIES)
            budget = st.number_input("Total budget", min_value=100.0, value=3000.0, step=100.0)
            style = st.select_slider("Travel style", ["Budget", "Balanced", "Comfort", "Luxury"], value="Balanced")
            interests = st.pills("Interests", INTERESTS, selection_mode="multi", default=["Food", "Culture"])
            preferred = st.pills("Specialists to consult", list(AGENT_CHIPS), selection_mode="multi", default=list(AGENT_CHIPS), format_func=AGENT_CHIPS.get, help="Sent to the supervisor as a request. The itinerary agent always runs.")
            custom = st.text_area("Or describe it in your own words", placeholder="Optional. Replaces the fields above.", height=70)
            go = st.form_submit_button("Plan my trip", type="primary", width="stretch", icon=":material/travel_explore:")

        if go:
            dates = tuple(dates) if isinstance(dates, (list, tuple)) else (dates,)
            start, end = dates[0], dates[-1]
            if not custom.strip() and not (origin.strip() and destination.strip()):
                st.error("Add both a starting point and a destination.")
            else:
                form = {
                    "origin": origin.strip(), "destination": destination.strip(), "start": start.isoformat(), "end": end.isoformat(),
                    "days": max((end - start).days + 1, 1), "travelers": int(travelers), "budget": float(budget), "currency": currency,
                    "style": style, "interests": list(interests or []),
                }
                picked = list(preferred or [])
                query = custom.strip() or build_query(form, picked)
                ss.run = backend.new_run(query, demo=ss.demo, form=form)
                ss.job = {"type": "start", "preferred": [*picked, "itinerary_agent"]}
                ss.pop("fb_text", None)

        history_panel()


def history_panel() -> None:
    ss = st.session_state
    refresh_history()
    left, right = st.columns([3, 1], vertical_alignment="center")
    left.markdown('<div class="side-h">Trip history</div>', unsafe_allow_html=True)
    right.button("", icon=":material/refresh:", key="hist_refresh", on_click=_invalidate_history, help="Reload history")
    if ss.history_error:
        ui.banner("Could not load history", ss.history_error)
    elif not ss.history:
        st.caption("Trips you plan will show up here.")
    for item in ss.history[:12]:
        current = ss.run is not None and ss.run.thread_id == item["thread_id"]
        st.button(
            f'{ui.STATUS_ICON.get(item["status"], "•")} {item["title"][:30]}', key=f'open_{item["thread_id"]}', on_click=_open_trip,
            args=(item["thread_id"],), width="stretch", type="primary" if current else "secondary",
        )
        ui.history_caption(item)


# ------------------------------------------------------------------------------ results
def get_structured(run, live: bool = False) -> dict:
    ss = st.session_state
    use_llm = bool(ss.ai_extract) and not run.demo
    key = (run.thread_id, backend.results_signature(run), use_llm)
    if key in ss.structured:
        return ss.structured[key]
    if live:  # cheap and uncached while streaming
        return backend.structure_results(run, use_llm=False)
    with st.spinner("Designing your result cards…"):
        data = backend.structure_results(run, use_llm=use_llm)
    ss.structured[key] = data
    return data


def _section(run, node: str, icon: str, title: str, caption: str, live: bool, S: dict, body) -> None:
    text = run.state.get(backend.RESULT_KEY[node])
    status = run.status.get(node, "idle")
    if status == "skipped":
        return
    badge = f"{run.durations[node]:.1f}s" if node in run.durations else ""
    if text:
        ui.section_header(icon, title, caption, badge)
        body(S, str(text))
    elif live and run.phase == "running" and run.status.get("supervisor") == "done":
        ui.section_header(icon, title, "Working on it…")
        ui.skeleton(3 if node != "itinerary_agent" else 2)


def render_sections(run, S: dict, live: bool) -> None:
    def flights(S, text):
        ui.flight_cards(S["flights"]) if S["flights"] else ui.text_card(text)

    def hotels(S, text):
        ui.hotel_cards(S["hotels"]) if S["hotels"] else ui.text_card(text)

    def weather(S, text):
        ui.weather_strip(S["weather"]) if S["weather"] else ui.text_card(text)

    def budget(S, text):
        ui.budget_view(S["budget"]) if S["budget"]["items"] else ui.text_card(text)

    def itinerary(S, text):
        ui.itinerary_timeline(S["itinerary"]) if S["itinerary"] else ui.text_card(text)

    if live and run.status.get("supervisor") != "done" and run.phase == "running":
        ui.skeleton(3)
        return
    _section(run, "flight_agent", "✈️", "Flights", "Likely routes, airlines and fares", live, S, flights)
    _section(run, "hotel_agent", "🏨", "Where to stay", "Hotels and areas from a live web search", live, S, hotels)
    _section(run, "weather_agent", "🌤️", "Weather", "Day-by-day outlook for your dates", live, S, weather)
    _section(run, "budget_agent", "💰", "Budget", "Estimated cost against your limit", live, S, budget)
    _section(run, "itinerary_agent", "🗺️", "Itinerary", "Draft day-by-day plan", live, S, itinerary)


def render_plan(run) -> None:
    if run is None:
        ui.empty_state()
        return
    if run.demo:
        ui.banner("Demo mode", "Everything below is generated sample data. Switch Demo mode off in the sidebar to use your live graph.", kind="info", icon="🧪")
    if run.phase == "blocked":
        ui.banner("This doesn't look like a travel request", run.error or "The input guardrail blocked it.")
        st.caption("Describe where you want to go, when, and what you enjoy, then plan again.")
        return
    if run.phase == "error":
        ui.banner("The run stopped", run.error or "Unknown error")
        st.caption("Details are in the Raw trace tab. Fix the problem, then plan again.")
    S = get_structured(run) if any(run.state.get(k) for k in backend.RESULT_KEY.values()) else None
    if run.phase == "awaiting_approval" and S:
        ui.approval_panel(run, S, _decide)
    if run.phase == "complete" and run.state.get("final_response"):
        ui.final_card(run)
    if S:
        render_sections(run, S, live=False)
    elif run.phase == "idle":
        ui.empty_state()


# ------------------------------------------------------------------------------ job runner
def run_job(canvas_slot, results_slot, status_slot) -> None:
    ss = st.session_state
    run, job = ss.run, ss.job
    ss.job = None
    backend.begin_job(run, job)
    if run.demo:
        ss.demo_store[run.thread_id] = run
    label = "Planning your trip…" if job["type"] == "start" else "Finishing your plan…"
    gen = backend.stream_run(run, job, speed=float(ss.speed))
    with status_slot.container():
        box = st.status(label, expanded=True)
    try:
        for ev in gen:
            backend.apply_event(run, ev)
            canvas.draw(canvas_slot, run.status, run.durations, run.log, run.phase)
            if ev["type"] == "node_end":
                box.write(f"{ev['node'].replace('_', ' ').title()} finished in {run.durations[ev['node']]:.1f}s")
                with results_slot.container():
                    render_sections(run, get_structured(run, live=True), live=True)
            if run.phase in ("blocked", "error"):
                gen.close()
                break
    except Exception as exc:  # noqa: BLE001
        backend.apply_event(run, {"type": "error", "message": backend._friendly(exc), "detail": repr(exc)})
        canvas.draw(canvas_slot, run.status, run.durations, run.log, run.phase)

    state = {"awaiting_approval": "complete", "complete": "complete"}.get(run.phase, "error")
    box.update(label={"awaiting_approval": "Draft ready for your review", "complete": "Plan complete", "blocked": "Request blocked"}.get(run.phase, "Run stopped"), state=state, expanded=False)
    ss.flash = {
        "awaiting_approval": ("✋", "Draft ready. Review it and choose Approve, Request changes or Reject."),
        "complete": ("🏁", "Your plan is ready."), "blocked": ("⛔", "That request was blocked by the guardrail."),
    }.get(run.phase, ("⚠️", run.error or "The run stopped."))
    ss.history = None
    st.rerun()


# ------------------------------------------------------------------------------ main
def main() -> None:
    ss = st.session_state
    init_state()

    if ss.flash:
        icon, msg = ss.flash
        ss.flash = None
        st.toast(msg, icon=icon)
    tid = ss.pop("load_tid", None)
    if tid:
        try:
            ss.run = backend.load_run(tid, ss.demo, ss.demo_store)
        except Exception as exc:  # noqa: BLE001
            ss.flash = ("⚠️", backend._friendly(exc))
            st.rerun()

    sidebar()
    run = ss.run

    if run is None:
        ui.hero("Plan the whole trip with a team of AI agents", "Flights, hotels, weather and budget are handled by specialist agents. You review the draft and decide what happens next.")
    else:
        dest = (run.state.get("trip_constraints") or {}).get("destination") or run.form.get("destination") or "Your trip"
        ui.hero(str(dest), run.query[:200], compact=True)

    canvas_slot = st.empty()
    canvas.draw(canvas_slot, run.status if run else IDLE_STATUS, run.durations if run else {}, run.log if run else "Fill in your trip and press Plan my trip.", run.phase if run else "idle")

    tab_plan, tab_trace = st.tabs(["Trip plan", "Raw trace"])
    with tab_plan:
        if ss.job and run:
            status_slot, results_slot = st.empty(), st.empty()
            run_job(canvas_slot, results_slot, status_slot)
        else:
            render_plan(run)
    with tab_trace:
        ui.trace_view(run)


main()
