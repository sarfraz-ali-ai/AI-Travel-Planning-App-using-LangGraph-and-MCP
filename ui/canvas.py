"""Live agent canvas: an animated SVG pipeline rendered inside an iframe.

`draw()` is called once per stream event with an st.empty() placeholder, so the
canvas is redrawn in place as nodes move idle -> running -> done.
"""
from __future__ import annotations

import html

import streamlit as st

# (node id, label, icon)
NODES = [
    ("supervisor", "Supervisor", "🧭"),
    ("flight_agent", "Flights", "✈️"),
    ("hotel_agent", "Hotels", "🏨"),
    ("weather_agent", "Weather", "🌤️"),
    ("budget_agent", "Budget", "💰"),
    ("itinerary_agent", "Itinerary", "🗺️"),
    ("human_approval", "Approval", "✋"),
    ("final_response", "Final plan", "🏁"),
]

PHASE_TEXT = {
    "idle": "Ready",
    "running": "Agents at work",
    "awaiting_approval": "Waiting for your approval",
    "complete": "Plan ready",
    "blocked": "Request blocked",
    "error": "Something went wrong",
}

X0, DX, Y, R = 84, 146, 112, 34
WIDTH, HEIGHT = X0 * 2 + DX * (len(NODES) - 1), 222
FRAME_HEIGHT = 352

SUB = {
    "idle": "queued",
    "running": "working",
    "waiting": "needs you",
    "skipped": "skipped",
    "error": "failed",
    "blocked": "blocked",
}

STYLE = """
*{box-sizing:border-box;}
body{margin:0; background:transparent; color:#e8ecff; font-family:'Plus Jakarta Sans',system-ui,sans-serif;}
.wrap{border:1px solid rgba(255,255,255,.10); border-radius:20px; padding:14px 16px 14px;
  background:linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.02)); box-shadow:0 16px 44px rgba(0,0,0,.32);}
.top{display:flex; justify-content:space-between; align-items:center; font-size:13px; font-weight:600; margin-bottom:4px;}
.phase{display:flex; align-items:center; gap:8px;}
.dot{width:9px; height:9px; border-radius:50%; background:%DOT%; box-shadow:0 0 0 0 %DOT%; animation:%DOTANIM%;}
.pct{color:#a3aed8; font-variant-numeric:tabular-nums;}
.scroll{overflow-x:auto;}
svg{display:block; min-width:760px; width:100%; height:auto;}
.rail{stroke:rgba(255,255,255,.13); stroke-width:2; stroke-dasharray:3 7; fill:none;}
.e-idle{stroke:rgba(255,255,255,.18); stroke-width:2; stroke-dasharray:5 7; fill:none;}
.e-done{stroke:url(#gDone); stroke-width:3.5; fill:none; stroke-linecap:round;}
.e-active{stroke:url(#gDone); stroke-width:3.5; fill:none; stroke-dasharray:9 9; animation:flow .7s linear infinite;}
.body{fill:#141c3d; stroke:#2c3868; stroke-width:2;}
.lbl{font-size:13.5px; font-weight:700; fill:#e8ecff; text-anchor:middle;}
.sub{font-size:11.5px; fill:#a3aed8; text-anchor:middle;}
.ico{font-size:25px; text-anchor:middle; dominant-baseline:central;}
.halo{fill:none; opacity:0;}
.n-running .body{fill:url(#gRun); stroke:#99f6e4;}
.n-running .halo{fill:rgba(45,212,191,.28); opacity:1; transform-box:fill-box; transform-origin:center; animation:pulse 1.5s ease-in-out infinite;}
.n-done .body{fill:#0d2a2d; stroke:#2dd4bf;}
.n-waiting .body{fill:#2b2109; stroke:#f5b544;}
.n-waiting .halo{fill:rgba(245,181,68,.30); opacity:1; transform-box:fill-box; transform-origin:center; animation:pulse 1.8s ease-in-out infinite;}
.n-skipped{opacity:.34;} .n-skipped .body{stroke-dasharray:4 5;}
.n-error .body, .n-blocked .body{fill:#2a1018; stroke:#fb7185;}
.n-running .sub{fill:#99f6e4;} .n-waiting .sub{fill:#f5b544;} .n-error .sub, .n-blocked .sub{fill:#fb7185;}
.badge{fill:#2dd4bf;} .tick{fill:none; stroke:#06101f; stroke-width:2.4; stroke-linecap:round; stroke-linejoin:round;}
.bar{height:5px; border-radius:5px; background:rgba(255,255,255,.08); overflow:hidden; margin:6px 0 12px;}
.bar i{display:block; height:100%; width:%PCT%%; border-radius:5px; background:linear-gradient(90deg,#2dd4bf,#a78bfa); transition:width .4s;}
.log{font:500 13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; color:#c7d0f5; white-space:nowrap; overflow:hidden;}
.log .pr{color:#2dd4bf; margin-right:6px;}
.type{display:inline-block; max-width:calc(100% - 40px); overflow:hidden; vertical-align:bottom; white-space:nowrap;
  width:%CH%ch; animation:typing %TYPEDUR%s steps(%CH%) 1 both;}
.cur{display:inline-block; width:8px; height:15px; margin-left:3px; vertical-align:-2px; background:#2dd4bf; animation:blink 1s steps(1) infinite;}
@keyframes flow{to{stroke-dashoffset:-18;}}
@keyframes pulse{0%,100%{transform:scale(.92); opacity:.55;} 50%{transform:scale(1.22); opacity:1;}}
@keyframes ring{0%{box-shadow:0 0 0 0 rgba(45,212,191,.55);} 100%{box-shadow:0 0 0 10px rgba(45,212,191,0);}}
@keyframes ringAmber{0%{box-shadow:0 0 0 0 rgba(245,181,68,.55);} 100%{box-shadow:0 0 0 10px rgba(245,181,68,0);}}
@keyframes typing{from{width:0;} to{width:%CH%ch;}}
@keyframes blink{50%{opacity:0;}}
@media (prefers-reduced-motion: reduce){*{animation:none !important;}}
"""

DOT_COLOR = {
    "idle": "#64708f", "running": "#2dd4bf", "awaiting_approval": "#f5b544",
    "complete": "#2dd4bf", "blocked": "#fb7185", "error": "#fb7185",
}


def _x(i: int) -> int:
    return X0 + DX * i


def _edge(i: int, j: int, state: str) -> str:
    x1, x2 = _x(i), _x(j)
    if j == i + 1:
        d = f"M {x1 + R} {Y} L {x2 - R} {Y}"
    else:  # bypass arc over skipped nodes
        top = Y - R
        d = f"M {x1} {top} C {x1} {top - 70}, {x2} {top - 70}, {x2} {top}"
    return f'<path class="e-{state}" d="{d}"/>'


def _node(i: int, node_id: str, label: str, icon: str, state: str, seconds: float | None) -> str:
    x = _x(i)
    sub = SUB.get(state, "")
    if state == "done":
        sub = f"{seconds:.1f}s" if seconds is not None else "done"
    badge = ""
    if state == "done":
        badge = (
            f'<g transform="translate(24,-24)"><circle class="badge" r="11"/>'
            f'<path class="tick" d="M-5 0.5 L-1.5 4 L5 -3.5"/></g>'
        )
    return (
        f'<g class="n-{state}" transform="translate({x},{Y})">'
        f'<circle class="halo" r="{R + 10}"/><circle class="body" r="{R}"/>'
        f'<text class="ico">{icon}</text>{badge}'
        f'<text class="lbl" y="{R + 26}">{html.escape(label)}</text>'
        f'<text class="sub" y="{R + 44}">{html.escape(sub)}</text></g>'
    )


def build_html(status: dict, durations: dict, message: str, phase: str) -> str:
    states = {n[0]: status.get(n[0], "idle") for n in NODES}
    active = [i for i, n in enumerate(NODES) if states[n[0]] != "skipped"]

    # rail through every node (faint), then the effective chain on top
    rail = f'<path class="rail" d="M {_x(0)} {Y} L {_x(len(NODES) - 1)} {Y}"/>'
    edges = []
    for a, b in zip(active, active[1:]):
        s_src, s_dst = states[NODES[a][0]], states[NODES[b][0]]
        if s_src == "done" and s_dst == "done":
            st_ = "done"
        elif s_src == "done" and s_dst in ("running", "waiting"):
            st_ = "active"
        else:
            st_ = "idle"
        edges.append(_edge(a, b, st_))

    nodes = "".join(
        _node(i, nid, lbl, ico, states[nid], durations.get(nid)) for i, (nid, lbl, ico) in enumerate(NODES)
    )
    chain_done = sum(1 for i in active if states[NODES[i][0]] == "done")
    pct = int(round(100 * chain_done / max(len(active), 1)))

    msg = (message or "Ready when you are.").strip()[:110]
    ch = max(len(msg), 1)
    dot = DOT_COLOR.get(phase, "#64708f")
    dot_anim = "none"
    if phase == "running":
        dot_anim = "ring 1.2s ease-out infinite"
    elif phase == "awaiting_approval":
        dot_anim = "ringAmber 1.4s ease-out infinite"

    style = (
        STYLE.replace("%DOTANIM%", dot_anim).replace("%DOT%", dot).replace("%PCT%", str(pct))
        .replace("%CH%", str(ch)).replace("%TYPEDUR%", f"{min(max(ch * 0.028, 0.4), 2.6):.2f}")
    )
    svg = (
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Agent pipeline progress">'
        f'<defs><linearGradient id="gDone" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{WIDTH}" y2="0">'
        f'<stop offset="0" stop-color="#2dd4bf"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>'
        f'<linearGradient id="gRun" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#0f766e"/><stop offset="1" stop-color="#5b3fb5"/></linearGradient></defs>'
        f"{rail}{''.join(edges)}{nodes}</svg>"
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700&display=swap" rel="stylesheet">'
        f"<style>{style}</style></head><body><div class=\"wrap\">"
        f'<div class="top"><div class="phase"><span class="dot"></span>{html.escape(PHASE_TEXT.get(phase, phase))}</div>'
        f'<div class="pct">{pct}%</div></div>'
        f'<div class="scroll">{svg}</div><div class="bar"><i></i></div>'
        f'<div class="log"><span class="pr">&gt;</span><span class="type">{html.escape(msg)}</span><span class="cur"></span></div>'
        "</div></body></html>"
    )


def embed(doc: str, height: int = FRAME_HEIGHT) -> None:
    """Render an HTML document in an iframe."""
    if hasattr(st, "iframe"):
        st.iframe(doc, height=height)  # Removed the 'alt' parameter that caused the crash
    else:
        import streamlit.components.v1 as components
        components.html(doc, height=height)


def draw(slot, status: dict, durations: dict, message: str, phase: str) -> None:
    """Redraw the canvas into an st.empty() placeholder."""
    with slot.container():
        embed(build_html(status, durations, message, phase))
