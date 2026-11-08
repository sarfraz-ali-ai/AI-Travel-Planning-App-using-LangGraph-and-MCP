"""Thin adapter between the Streamlit UI and your LangGraph travel planner.

ASSUMPTIONS (everything about your graph that the UI relies on lives in this block):
  * graph.py exposes the compiled graph as `app`, built with a PostgresSaver checkpointer.
  * human_approval calls interrupt() and expects the resume value
    {"approved": bool, "feedback": str}  ->  build_resume().
  * Streaming uses stream_mode="updates": each chunk is {node_name: state_update},
    and a pause arrives as {"__interrupt__": (Interrupt(value=...),)}.
  * itinerary_agent always runs (your routing falls back to it), so it is never "skipped".
  * A guardrail rejection is detected as: supervisor returns selected_agents == [] together with
    a final_response. Your current routing still forwards that to itinerary_agent, so the UI
    stops reading the stream at that point.
  * TravelState keys used below.
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator

import mock_data
import parsers

# --- graph structure --------------------------------------------------------------------------
AGENT_ORDER = ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"]
ALL_NODES = ["supervisor", *AGENT_ORDER, "human_approval", "final_response"]
RESULT_KEY = {  # node -> TravelState key holding its output
    "flight_agent": "flight_results", "hotel_agent": "hotel_results", "weather_agent": "weather_results",
    "budget_agent": "budget_results", "itinerary_agent": "itinerary",
}
USER_ID = "streamlit-user"
RUNNING_MSG = {
    "supervisor": "Supervisor is checking the request and choosing specialists…",
    "flight_agent": "Flight agent is looking up airports and airlines…",
    "hotel_agent": "Hotel agent is searching the web for places to stay…",
    "weather_agent": "Weather agent is pulling the current weather and forecast…",
    "budget_agent": "Budget agent is checking costs against your limit…",
    "itinerary_agent": "Itinerary agent is drafting the day-by-day plan…",
    "human_approval": "Draft ready. Waiting for your decision…",
    "final_response": "Final agent is polishing the plan…",
}
DONE_MSG = {"supervisor": "Specialists selected.", "final_response": "Your plan is ready."}


def build_input(query: str) -> dict:
    return {"user_query": query, "user_id": USER_ID, "messages": [], "llm_calls": 0}


def build_resume(approved: bool, feedback: str) -> dict:
    return {"approved": bool(approved), "feedback": feedback or ""}


class BackendError(RuntimeError):
    """Raised with a message that is safe to show to the user."""


# --- run model --------------------------------------------------------------------------------
@dataclass
class Run:
    thread_id: str
    query: str
    demo: bool
    form: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)
    status: dict = field(default_factory=lambda: {n: "idle" for n in ALL_NODES})
    durations: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)
    phase: str = "idle"  # idle | running | awaiting_approval | complete | blocked | error
    log: str = "Ready when you are."
    error: str = ""
    error_detail: str = ""
    interrupt: dict | None = None
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    t0: dict = field(default_factory=dict)


def new_run(query: str, demo: bool, form: dict | None = None) -> Run:
    return Run(thread_id=f"trip-{uuid.uuid4().hex[:10]}", query=query, demo=demo, form=form or {})


def begin_job(run: Run, job: dict) -> None:
    run.phase, run.error, run.error_detail = "running", "", ""
    if job["type"] == "resume":
        run.interrupt = None


# --- environment ------------------------------------------------------------------------------
def load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def env_report() -> list[tuple[str, bool, str]]:
    load_env()
    spec = [
        ("DATABASE_URL", "Postgres checkpointer (required for live mode)"),
        ("GOOGLE_API_KEY", "Google Gemini LLM key"),
        ("TAVILY_API_KEY", "Hotel web search"),
        ("OPENWEATHER_API_KEY", "Weather"),
        ("AVIATION_STACK_API_KEY", "Airports and airlines"),
    ]
    return [(k, bool(os.getenv(k)), why) for k, why in spec]


def env_ready() -> bool:
    load_env()
    return bool(os.getenv("DATABASE_URL")) and bool(os.getenv("GOOGLE_API_KEY")) 


_GRAPH = None


def get_graph():
    """Import your compiled graph lazily so demo mode works with no keys or database."""
    global _GRAPH
    if _GRAPH is None:
        load_env()
        if not os.getenv("DATABASE_URL"):
            raise BackendError(
                "DATABASE_URL is not set. Live mode needs the Postgres checkpointer (it stores every trip and powers "
                "pause and resume). Add it to your .env file, or switch on Demo mode in the sidebar."
            )
        try:
            from graph import app  # your graph.py
        except Exception as exc:  # noqa: BLE001
            raise BackendError(f"Could not import your graph (graph.py): {type(exc).__name__}: {exc}") from exc
        _GRAPH = app
    return _GRAPH


def _friendly(exc: Exception) -> str:
    if isinstance(exc, BackendError):
        return str(exc)
    text = f"{type(exc).__name__}: {exc}"
    low = text.lower()
    if "checkpointer" in low or "thread_id" in low:
        return "The graph has no checkpointer. Set DATABASE_URL so trips can pause for approval and be reopened."
    if "operationalerror" in low or "connection refused" in low or "could not connect" in low:
        return "Could not reach Postgres. Check that DATABASE_URL is correct and the database is running."
    if "401" in low or "invalid api key" in low or "incorrect api key" in low or "authentication" in low:
        return "The LLM endpoint rejected the API key. Check FREELLMAPI_API_KEY and FREELLMAPI_BASE_URL."
    if "connecterror" in low or "apiconnectionerror" in low or "connection error" in low:
        return "Could not reach the LLM endpoint. Check that FREELLMAPI_BASE_URL is running and reachable."
    if isinstance(exc, ValueError) and "substring not found" in low:
        return "A model reply was not valid JSON (the supervisor or guardrail step). Try again, or switch the model."
    if "rate limit" in low or "429" in low:
        return "The LLM endpoint is rate limiting requests. Wait a moment and try again."
    return text


# --- routing mirror (predicts which node runs next, so the canvas can show it as "running") ----
def effective_chain(selected: list[str] | None) -> list[str]:
    sel = selected or []
    return ["supervisor", *[a for a in AGENT_ORDER if a in sel or a == "itinerary_agent"], "human_approval", "final_response"]


def predict_next(node: str, state: dict) -> str | None:
    sel = state.get("selected_agents") or []
    if node == "supervisor":
        chain = [a for a in AGENT_ORDER if a in sel]
        return chain[0] if chain else "itinerary_agent"
    if node in AGENT_ORDER and node != "itinerary_agent":
        for nxt in AGENT_ORDER[AGENT_ORDER.index(node) + 1:]:
            if nxt in sel:
                return nxt
        return "itinerary_agent"
    return {"itinerary_agent": "human_approval", "human_approval": "final_response"}.get(node)


# --- streaming --------------------------------------------------------------------------------
def stream_run(run: Run, job: dict, speed: float = 1.0) -> Iterator[dict]:
    """Yield normalized events for a start or resume job. The consumer must call apply_event() on each one."""
    if run.demo:
        if job["type"] == "start":
            yield from mock_data.mock_stream(run.form, run.query, job.get("preferred"), speed)
        else:
            yield from mock_data.mock_resume(run.form, run.state, job["approved"], job["feedback"], speed)
    else:
        yield from _stream_real(run, job)


def _stream_real(run: Run, job: dict) -> Iterator[dict]:
    try:
        graph = get_graph()
        from langgraph.types import Command
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": _friendly(exc), "detail": repr(exc)}
        return

    cfg = {"configurable": {"thread_id": run.thread_id}}
    if job["type"] == "start":
        payload, first = build_input(run.query), "supervisor"
    else:
        payload, first = Command(resume=build_resume(job["approved"], job["feedback"])), "human_approval"

    yield {"type": "node_start", "node": first}
    try:
        for chunk in graph.stream(payload, cfg, stream_mode="updates"):
            if "__interrupt__" in chunk:
                yield {"type": "interrupt", "payload": _to_plain(_interrupt_value(chunk["__interrupt__"]))}
                return
            for node, update in chunk.items():
                if node.startswith("__"):
                    continue
                yield {"type": "node_end", "node": node, "update": _to_plain(update or {})}
                nxt = predict_next(node, run.state)  # run.state already merged by the consumer
                if nxt:
                    yield {"type": "node_start", "node": nxt}
        snap = graph.get_state(cfg)
        if snap.next:
            yield {"type": "interrupt", "payload": _to_plain(_snapshot_interrupt(snap))}
        else:
            yield {"type": "complete"}
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": _friendly(exc), "detail": repr(exc)}


def _interrupt_value(raw: Any) -> Any:
    try:
        first = raw[0] if isinstance(raw, (list, tuple)) else raw
        return getattr(first, "value", first)
    except Exception:  # noqa: BLE001
        return {}


def _snapshot_interrupt(snap: Any) -> Any:
    for task in getattr(snap, "tasks", ()) or ():
        for intr in getattr(task, "interrupts", ()) or ():
            return getattr(intr, "value", intr)
    return {}


def _to_plain(obj: Any) -> Any:
    """Make LangChain messages and other objects JSON friendly."""
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_plain(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if hasattr(obj, "content") and hasattr(obj, "type"):
        return {"type": getattr(obj, "type", "message"), "content": _to_plain(obj.content)}
    return str(obj)


def apply_event(run: Run, ev: dict) -> None:
    """Reduce one stream event into the Run (status, timings, state, trace)."""
    kind, now = ev["type"], time.time()
    if kind == "node_start":
        node = ev["node"]
        run.status[node], run.t0[node], run.log = "running", now, ev.get("msg") or RUNNING_MSG.get(node, node)
    elif kind == "node_end":
        node, upd = ev["node"], ev.get("update") or {}
        run.status[node] = "done"
        run.durations[node] = now - run.t0.get(node, now)
        for key, value in upd.items():
            if key == "messages":
                run.state["messages"] = [*run.state.get("messages", []), *value]
            else:
                run.state[key] = value
        run.trace.append({"node": node, "seconds": round(run.durations[node], 2), "at": datetime.now(timezone.utc).isoformat(), "update": upd})
        run.log = DONE_MSG.get(node, f"{node.replace('_', ' ').title()} finished.")
        if node == "supervisor":
            _after_supervisor(run)
    elif kind == "interrupt":
        run.status["human_approval"], run.phase, run.interrupt = "waiting", "awaiting_approval", ev.get("payload") or {}
        run.log = "Draft ready. Waiting for your decision."
    elif kind == "complete":
        run.phase, run.log = "complete", DONE_MSG["final_response"]
    elif kind == "error":
        for node, st in run.status.items():
            if st == "running":
                run.status[node] = "error"
        run.phase, run.error, run.error_detail, run.log = "error", ev.get("message", "Unknown error"), ev.get("detail", ""), "Stopped because of an error."
        run.trace.append({"node": "error", "seconds": 0, "at": datetime.now(timezone.utc).isoformat(), "update": {"message": run.error, "detail": run.error_detail}})


def _after_supervisor(run: Run) -> None:
    selected = run.state.get("selected_agents")
    if selected is not None and not selected and run.state.get("final_response") and not run.state.get("trip_constraints"):
        run.phase, run.error, run.log = "blocked", str(run.state["final_response"]), "Request blocked by the input guardrail."
        for node in ALL_NODES[1:]:
            run.status[node] = "skipped"
        return
    for agent in AGENT_ORDER:
        if agent not in (selected or []) and agent != "itinerary_agent":
            run.status[agent] = "skipped"


# --- structured result cards ------------------------------------------------------------------
def results_signature(run: Run) -> str:
    raw = "|".join(str(run.state.get(k, "")) for k in (*RESULT_KEY.values(), "final_response"))
    return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:12]


def structure_results(run: Run, use_llm: bool = True) -> dict:
    if run.demo:
        return mock_data.structured_sample(run.form, run.state)
    base = parsers.heuristic_structure(run.state)
    if not use_llm or not any(run.state.get(k) for k in RESULT_KEY.values()):
        return base
    try:
        from config import get_llm  # your config.py

        system, prompt = parsers.build_structuring_prompt(run.state)
        raw = get_llm().invoke([("system", system), ("human", prompt)]).content
        return parsers.merge_structured(base, parsers.parse_llm_json(str(raw)))
    except Exception:  # noqa: BLE001 - fall back to heuristics, never break the page
        return base


# --- history ----------------------------------------------------------------------------------
def _summary(tid: str, vals: dict, ts: str) -> dict:
    cons = vals.get("trip_constraints") or {}
    sel = vals.get("selected_agents")
    if sel is not None and not sel and vals.get("final_response") and not vals.get("itinerary"):
        status = "blocked"
    elif vals.get("final_response"):
        status = "complete"
    elif vals.get("itinerary"):
        status = "awaiting_approval"
    else:
        status = "in_progress"
    query = str(vals.get("user_query", ""))
    return {
        "thread_id": tid, "status": status, "ts": ts,
        "title": str(cons.get("destination") or query[:40] or tid), "subtitle": str(cons.get("duration") or query[:60]),
    }


def summarize_run(run: Run) -> dict:
    status = {"complete": "complete", "awaiting_approval": "awaiting_approval", "blocked": "blocked", "error": "error"}.get(run.phase, "in_progress")
    cons = run.state.get("trip_constraints") or {}
    return {
        "thread_id": run.thread_id, "status": status, "ts": run.created,
        "title": str(cons.get("destination") or run.form.get("destination") or run.query[:40]),
        "subtitle": str(cons.get("duration") or run.query[:60]),
    }


def list_threads(demo: bool, store: dict, limit: int = 30) -> list[dict]:
    if demo:
        runs = sorted(store.values(), key=lambda r: r.created, reverse=True)
        return [summarize_run(r) for r in runs][:limit]
    cp = get_graph().checkpointer
    out, seen = [], set()
    for tup in cp.list(None, limit=600):  # newest first across all threads
        tid = tup.config["configurable"]["thread_id"]
        if tid in seen:
            continue
        seen.add(tid)
        ckpt = tup.checkpoint or {}
        vals = ckpt.get("channel_values") or {}
        if vals.get("user_query"):
            out.append(_summary(tid, vals, str(ckpt.get("ts", ""))))
        if len(out) >= limit:
            break
    return out


def load_run(thread_id: str, demo: bool, store: dict) -> Run:
    if demo:
        if thread_id not in store:
            raise BackendError("That demo trip is no longer in this session.")
        return store[thread_id]
    graph = get_graph()
    snap = graph.get_state({"configurable": {"thread_id": thread_id}})
    vals = _to_plain(dict(snap.values or {}))
    if not vals:
        raise BackendError("No saved state found for that trip.")
    run = Run(thread_id=thread_id, query=str(vals.get("user_query", "")), demo=False, state=vals)
    paused = bool(snap.next) and "human_approval" in snap.next
    _restore(run, paused, _to_plain(_snapshot_interrupt(snap)) if paused else None)
    run.trace = [{"node": "(restored state)", "seconds": 0, "at": "", "update": vals}]
    return run


def _restore(run: Run, paused: bool, interrupt_payload: Any) -> None:
    s = run.state
    sel = s.get("selected_agents")
    run.status["supervisor"] = "done" if sel is not None else "idle"
    for agent in AGENT_ORDER:
        if s.get(RESULT_KEY[agent]):
            run.status[agent] = "done"
        elif sel is not None and agent not in sel and agent != "itinerary_agent":
            run.status[agent] = "skipped"
    if paused:
        run.status["human_approval"], run.phase, run.interrupt = "waiting", "awaiting_approval", interrupt_payload or {}
        run.log = "Draft ready. Waiting for your decision."
    elif s.get("final_response") and "approved" in s:
        run.status["human_approval"] = run.status["final_response"] = "done"
        run.phase, run.log = "complete", "Your plan is ready."
    elif sel is not None and not sel and s.get("final_response"):
        run.phase, run.error, run.log = "blocked", str(s["final_response"]), "Request blocked by the input guardrail."
    else:
        run.phase, run.log = "idle", "Restored a partly finished trip."


def seed_demo_store() -> dict:
    """One finished sample trip so the history list is not empty in demo mode."""
    form = {"origin": "Berlin", "destination": "Lisbon", "days": 4, "travelers": 2, "budget": 2400, "currency": "EUR", "interests": ["Food", "History"], "style": "Balanced"}
    run = new_run("Plan a 4-day trip from Berlin to Lisbon for 2 travelers, 2400 EUR, food and history.", demo=True, form=form)
    run.created = "2026-10-01T09:00:00+00:00"
    for job in ({"type": "start", "preferred": None}, {"type": "resume", "approved": True, "feedback": ""}):
        begin_job(run, job)
        for ev in stream_run(run, job, speed=10_000):
            apply_event(run, ev)
    return {run.thread_id: run}
