"""Demo mode: simulates the LangGraph stream and produces sample data.

Emits the same normalized events as backend._stream_real():
  node_start / node_end / interrupt / complete / error
All content is generated sample data - nothing here calls an API or a database.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Iterator

_ORDER = ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"]
SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "PKR": "Rs ", "AED": "AED "}
TRAVEL_WORDS = re.compile(r"trip|travel|visit|flight|hotel|vacation|holiday|itinerary|getaway|tour|plan a|weekend", re.I)

ACTIVITIES: dict[str, list[tuple[str, str]]] = {
    "Food": [("Morning", "Breakfast at a local café, then a guided market walk"), ("Evening", "Dinner at a well-reviewed neighborhood restaurant")],
    "Culture": [("Morning", "Visit the city's flagship museum before the crowds"), ("Afternoon", "Old-town walking tour with a local guide")],
    "Nature": [("Morning", "Hike or cycle through the nearest park or waterfront trail"), ("Afternoon", "Picnic lunch with a scenic viewpoint")],
    "Nightlife": [("Evening", "Rooftop drinks, then live music in the entertainment district")],
    "Shopping": [("Afternoon", "Browse design shops and the main shopping street")],
    "Adventure": [("Morning", "Half-day outdoor activity (kayaking, climbing or a day trip)")],
    "Relaxation": [("Afternoon", "Spa or slow afternoon at a quiet café")],
    "History": [("Morning", "Heritage sites and a castle or palace visit")],
}


def _sleep(seconds: float, speed: float) -> None:
    time.sleep(seconds / max(speed, 0.01))


def is_travel_request(query: str) -> bool:
    return bool(TRAVEL_WORDS.search(query or ""))


def money(amount: float, currency: str) -> str:
    return f"{SYMBOL.get(currency, '$')}{round(amount, -1):,.0f}"


def _plan(form: dict) -> dict:
    days = max(int(form.get("days", 5)), 1)
    budget = float(form.get("budget", 3000))
    t = max(int(form.get("travelers", 1)), 1)
    split = {"Flights": 0.33, "Hotels": 0.29, "Food": 0.13, "Transport": 0.07, "Activities": 0.11, "Buffer": 0.04}
    return {
        "days": days, "budget": budget, "travelers": t, "cur": form.get("currency", "USD"),
        "dest": form.get("destination") or "Lisbon", "origin": form.get("origin") or "London",
        "interests": form.get("interests") or ["Food", "Culture"], "split": {k: budget * v for k, v in split.items()},
        "start": _start(form),
    }


def _start(form: dict) -> date:
    try:
        return datetime.fromisoformat(str(form.get("start"))).date()
    except (TypeError, ValueError):
        return date.today() + timedelta(days=30)


def itinerary_days(plan: dict) -> list[dict]:
    interests = plan["interests"] or ["Culture"]
    out = []
    for d in range(1, plan["days"] + 1):
        if d == 1:
            title, items = "Arrive and settle in", [("Afternoon", f"Land in {plan['dest']}, transfer to the hotel and drop bags"), ("Evening", "Easy dinner nearby and an early night")]
        elif d == plan["days"] and plan["days"] > 1:
            title, items = "Last bites and departure", [("Morning", "Final coffee, souvenir shopping and hotel check-out"), ("Afternoon", f"Transfer to the airport for the flight to {plan['origin']}")]
        else:
            focus = interests[(d - 2) % len(interests)]
            title = f"{focus} day"
            items = list(ACTIVITIES.get(focus, ACTIVITIES["Culture"]))
            extra = interests[(d - 1) % len(interests)]
            if extra != focus:
                items += [x for x in ACTIVITIES.get(extra, [])[:1]]
            order = {"Morning": 0, "Afternoon": 1, "Evening": 2}
            items.sort(key=lambda x: order.get(x[0], 1))
        out.append({"day": d, "title": title, "items": [{"time": t, "text": x} for t, x in items]})
    return out


def _texts(form: dict) -> dict:
    p = _plan(form)
    cur, dest = p["cur"], p["dest"]
    flight_cost = p["split"]["Flights"] / p["travelers"]
    flights = (
        f"**Route:** {p['origin']} → {dest}\n\n"
        f"- **Emirates** – 1 stop, about 9h 40m, {money(flight_cost * 1.12, cur)}\n"
        f"- **Qatar Airways** – 1 stop, about 10h 05m, {money(flight_cost, cur)}\n"
        f"- **Turkish Airlines** – 1 stop, about 11h 20m, {money(flight_cost * 0.88, cur)}\n\n"
        "Peak season warning: book 6–8 weeks ahead for the best fares. Mid-week departures are usually cheaper."
    )
    hotels = "\n".join(
        f"Title: {n} - Stay Guide\nURL: https://example.com/hotels/{i}\nContent: {n} rated {r}/5 by guests. From {money(p['split']['Hotels'] / p['days'] / max(1, p['travelers'] // 2 + p['travelers'] % 2) * f, cur)} per night."
        for i, (n, r, f) in enumerate([(f"{dest} Central Grand", 4.6, 1.2), (f"The {dest} Garden Inn", 4.3, 0.9), (f"Riverside Loft {dest}", 4.5, 1.0)])
    )
    weather = "Current weather: 22°C, clear sky\nForecast:\n" + "\n".join(
        f"{(p['start'] + timedelta(days=i)).isoformat()} temp: {19 + i % 4 * 2}° {['clear sky', 'few clouds', 'light rain', 'scattered clouds'][i % 4]}" for i in range(min(p["days"], 5))
    )
    budget = "Estimated costs:\n" + "\n".join(f"- {k}: {money(v, cur)}" for k, v in p["split"].items() if k != "Buffer")
    budget += f"\n\nThe plan looks feasible and sits within the {money(p['budget'], cur)} limit with a small buffer. Book flights early to protect the margin."
    itin = "\n\n".join(
        f"## Day {d['day']}: {d['title']}\n" + "\n".join(f"- {i['time']}: {i['text']}" for i in d["items"]) for d in itinerary_days(p)
    )
    return {"flights": flights, "hotels": hotels, "weather": weather, "budget": budget, "itinerary": itin}


def structured_sample(form: dict, state: dict | None = None) -> dict:
    """Card-ready data that matches the sample texts (used instead of parsing in demo mode)."""
    p = _plan(form)
    cur, dest = p["cur"], p["dest"]
    fc = p["split"]["Flights"] / p["travelers"]
    nights = p["days"]
    room = max(1, p["travelers"] // 2 + p["travelers"] % 2)
    conds = ["Clear sky", "Few clouds", "Light rain", "Scattered clouds"]
    items = [{"label": k, "amount": round(v, -1)} for k, v in p["split"].items() if k != "Buffer"]
    return {
        "flights": [
            {"airline": "Emirates", "from": p["origin"], "to": dest, "depart": "09:40", "arrive": "21:20", "duration": "9h 40m · 1 stop", "price": money(fc * 1.12, cur), "note": "Best comfort, free checked bag"},
            {"airline": "Qatar Airways", "from": p["origin"], "to": dest, "depart": "13:15", "arrive": "01:20 +1", "duration": "10h 05m · 1 stop", "price": money(fc, cur), "note": "Good connection times"},
            {"airline": "Turkish Airlines", "from": p["origin"], "to": dest, "depart": "06:30", "arrive": "19:50", "duration": "11h 20m · 1 stop", "price": money(fc * 0.88, cur), "note": "Lowest fare of the three"},
        ],
        "hotels": [
            {"name": f"{dest} Central Grand", "area": "City centre", "rating": 4.6, "price": money(p["split"]["Hotels"] / nights / room * 1.2, cur), "note": "Walkable to the main sights; breakfast included.", "url": ""},
            {"name": f"The {dest} Garden Inn", "area": "Quiet residential district", "rating": 4.3, "price": money(p["split"]["Hotels"] / nights / room * 0.9, cur), "note": "Calm base with good transit links.", "url": ""},
            {"name": f"Riverside Loft {dest}", "area": "Waterfront", "rating": 4.5, "price": money(p["split"]["Hotels"] / nights / room, cur), "note": "Apartment-style rooms with a kitchenette.", "url": ""},
        ],
        "weather": [
            {"label": (p["start"] + timedelta(days=i)).strftime("%a %d"), "condition": conds[i % 4], "high": 21 + i % 4 * 2, "low": 14 + i % 3, "unit": "C"}
            for i in range(min(p["days"], 7))
        ],
        "budget": {"currency": SYMBOL.get(cur, "$"), "limit": p["budget"], "items": items, "verdict": "The plan looks feasible and sits within your limit with a small buffer."},
        "itinerary": itinerary_days(p),
    }


# ----------------------------------------------------------------------------- event streams
def mock_stream(form: dict, query: str, preferred: list[str] | None, speed: float = 1.0) -> Iterator[dict]:
    p, t = _plan(form), _texts(form)
    llm = 0
    yield {"type": "node_start", "node": "supervisor"}
    _sleep(1.1, speed)
    if not is_travel_request(query):
        reason = "That doesn't look like a travel planning request. Describe a trip (where, when and what you enjoy) and the agents will get to work."
        yield {"type": "node_end", "node": "supervisor", "update": {"selected_agents": [], "trip_constraints": {}, "supervisor_reasoning": reason, "final_response": reason, "llm_calls": 2}}
        return
    selected = [a for a in _ORDER if a in (preferred or _ORDER) or a == "itinerary_agent"]
    constraints = {
        "destination": p["dest"], "origin": p["origin"], "duration": f"{p['days']} days", "budget": money(p["budget"], p["cur"]),
        "travel_style": form.get("style", "Balanced"), "special_preferences": p["interests"],
    }
    llm += 2
    yield {"type": "node_end", "node": "supervisor", "update": {
        "selected_agents": selected, "trip_constraints": constraints, "llm_calls": llm,
        "supervisor_reasoning": f"{len(selected)} specialists cover flights, stay, weather, cost and the day plan for {p['dest']}.",
    }}
    keys = {"flight_agent": "flight_results", "hotel_agent": "hotel_results", "weather_agent": "weather_results", "budget_agent": "budget_results", "itinerary_agent": "itinerary"}
    texts = {"flight_agent": t["flights"], "hotel_agent": t["hotels"], "weather_agent": t["weather"], "budget_agent": t["budget"], "itinerary_agent": t["itinerary"]}
    for agent in selected:
        yield {"type": "node_start", "node": agent}
        _sleep(1.0 + 0.15 * (agent == "itinerary_agent"), speed)
        upd: dict[str, Any] = {keys[agent]: texts[agent]}
        if agent in ("flight_agent", "budget_agent", "itinerary_agent"):
            llm += 1
            upd["llm_calls"] = llm
        if agent == "itinerary_agent":
            upd["approval_request"] = f"Please review this draft travel plan.\n\n{t['itinerary']}\n\nReply with approval or feedback."
        yield {"type": "node_end", "node": agent, "update": upd}
    yield {"type": "node_start", "node": "human_approval"}
    _sleep(0.5, speed)
    yield {"type": "interrupt", "payload": {
        "question": "Do you approve this itinerary?", "draft_itinerary": t["itinerary"],
        "expected_response": {"approved": True, "feedback": "Optional feedback for revision"},
    }}


def mock_resume(form: dict, state: dict, approved: bool, feedback: str, speed: float = 1.0) -> Iterator[dict]:
    p, t = _plan(form), _texts(form)
    yield {"type": "node_start", "node": "human_approval"}
    _sleep(0.4, speed)
    yield {"type": "node_end", "node": "human_approval", "update": {"approved": approved, "human_feedback": feedback}}
    yield {"type": "node_start", "node": "final_response"}
    _sleep(1.3, speed)
    head = f"# Your {p['days']}-day {p['dest']} plan\n\n"
    body = f"{t['itinerary']}\n\n## Budget\n{t['budget']}\n\n## Getting there\n{t['flights']}"
    if approved:
        text = head + body
    elif feedback.startswith("[REJECTED]"):
        text = (
            f"# Plan set aside\n\nUnderstood, the {p['dest']} draft is off the table. Two directions worth considering:\n\n"
            f"- **A shorter trip:** keep {p['dest']} but cut to {max(p['days'] // 2, 2)} days and spend the savings on a better hotel.\n"
            f"- **A different destination:** pick somewhere closer to {p['origin']} to cut flight costs by roughly a third."
        )
    else:
        text = f"# Revised {p['dest']} plan\n\n> Updated for your feedback: {feedback}\n\n" + body
    yield {"type": "node_end", "node": "final_response", "update": {"final_response": text, "llm_calls": int(state.get("llm_calls", 0)) + 1}}
    yield {"type": "complete"}
