"""Turn free-text agent output into structured data for the result cards.

Your agents return prose (flight/budget/itinerary) or a stringified search result
(hotels), so the UI uses two layers:
  1. build_structuring_prompt() + parse_llm_json(): one optional LLM call that
     converts every section to JSON (best quality).
  2. heuristic_structure(): regex fallbacks that never raise and never call an API.
Anything that cannot be parsed comes back empty and the UI shows the raw text instead.

Normalized schema (all keys always present):
  flights   [{airline, from, to, depart, arrive, duration, price, note}]
  hotels    [{name, area, rating, price, note, url}]
  weather   [{label, condition, high, low, unit}]
  budget    {currency, limit, items:[{label, amount}], verdict}
  itinerary [{day, title, items:[{time, text}]}]
"""
from __future__ import annotations

import json
import re
from typing import Any

CUR = r"(?:USD|EUR|GBP|PKR|AED|Rs\.?|[$€£])"
NUM = r"\d[\d,]*(?:\.\d+)?"
AIRLINE_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z]+\s){1,2}(?:Airlines?|Airways|Air)|Air [A-Z][a-z]+(?: [A-Z][a-z]+)?|Emirates|Etihad|Qatar Airways|Turkish Airlines|PIA|flydubai|"
    r"Ryanair|easyJet|Lufthansa|KLM|Ana|ANA|JAL|Japan Airlines|Cathay Pacific|Singapore Airlines|Thai Airways)\b"
)
DAY_RE = re.compile(r"(?im)^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?[ \t]*day[ \t]*(\d+)\b[ \t:.\-–—]*([^\n]*)")
TIME_RE = re.compile(
    r"^(?:\*\*)?\s*((?:early |late )?(?:morning|afternoon|evening|night|noon|midday|\d{1,2}(?::\d{2})?\s?(?:am|pm|AM|PM)?"
    r"(?:\s?[-–]\s?\d{1,2}(?::\d{2})?\s?(?:am|pm|AM|PM)?)?))(?:\*\*)?\s*[:\-–—)]\s*(.+)$",
    re.I,
)
COND_WORDS = [
    ("thunder", "Thunderstorm"), ("storm", "Storm"), ("snow", "Snow"), ("drizzle", "Drizzle"), ("rain", "Rain"),
    ("shower", "Showers"), ("fog", "Fog"), ("mist", "Mist"), ("haze", "Haze"), ("overcast", "Overcast"),
    ("cloud", "Cloudy"), ("clear", "Clear"), ("sun", "Sunny"),
]


# ----------------------------------------------------------------------------- helpers
def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _s(value: Any, limit: int = 400) -> str:
    return "" if value is None else str(value).strip()[:limit]


def _clean(text: str) -> str:
    return re.sub(r"[*_`#>]+", "", text).strip(" -–—•\t")


def _currency_symbol(text: str) -> str:
    m = re.search(CUR, text or "")
    if not m:
        return "$"
    tok = m.group(0)
    return {"USD": "$", "EUR": "€", "GBP": "£", "Rs": "Rs ", "Rs.": "Rs "}.get(tok, tok if len(tok) == 1 else tok + " ")


def _extract_json(text: str) -> dict:
    start, end = text.index("{"), text.rindex("}") + 1
    return json.loads(text[start:end])


# ----------------------------------------------------------------------------- LLM structuring
SCHEMA = """{
  "flights":   [{"airline":"","from":"","to":"","depart":"","arrive":"","duration":"","price":"","note":""}],
  "hotels":    [{"name":"","area":"","rating":null,"price":"","note":"","url":""}],
  "weather":   [{"label":"","condition":"","high":null,"low":null,"unit":"C"}],
  "budget":    {"currency":"$","limit":null,"items":[{"label":"","amount":0}],"verdict":""},
  "itinerary": [{"day":1,"title":"","items":[{"time":"","text":""}]}]
}"""


def build_structuring_prompt(state: dict) -> tuple[str, str]:
    def cut(key: str, n: int = 3200) -> str:
        return str(state.get(key, "") or "")[:n]

    system = "You convert travel-planning notes into strict JSON for UI cards. Return JSON only."
    prompt = f"""Convert the notes below into JSON matching this schema exactly:
{SCHEMA}

Rules:
- Use only facts present in the notes. Use null or "" when unknown. Never invent prices, ratings or times.
- At most 4 flights, 6 hotels, 7 weather days. Hotel price is per night (include currency).
- Budget amounts are plain numbers in one currency; "limit" is the user's stated budget if any.
- Itinerary: one object per day, 3-6 items per day, "time" like "Morning" or "09:00".
- Omit sections with no data by returning an empty list (or an empty items list for budget).

Trip constraints: {state.get("trip_constraints", {})}

FLIGHT NOTES:
{cut("flight_results")}

HOTEL SEARCH RESULTS:
{cut("hotel_results", 4500)}

WEATHER DATA:
{cut("weather_results")}

BUDGET NOTES:
{cut("budget_results")}

ITINERARY:
{cut("itinerary", 5000)}
"""
    return system, prompt


def parse_llm_json(text: str) -> dict:
    return normalize(_extract_json(text))


# ----------------------------------------------------------------------------- normalization
def normalize(data: dict) -> dict:
    out = empty_structured()
    for r in data.get("flights") or []:
        if isinstance(r, dict) and (r.get("airline") or r.get("price")):
            out["flights"].append({k: _s(r.get(k), 160) for k in ("airline", "from", "to", "depart", "arrive", "duration", "price", "note")})
    for r in data.get("hotels") or []:
        if isinstance(r, dict) and r.get("name"):
            rating = _num(r.get("rating"))
            out["hotels"].append({
                "name": _s(r.get("name"), 120), "area": _s(r.get("area"), 120),
                "rating": rating if rating is not None and 0 < rating <= 10 else None,
                "price": _s(r.get("price"), 60), "note": _s(r.get("note"), 300), "url": _s(r.get("url"), 400),
            })
    for r in data.get("weather") or []:
        if isinstance(r, dict) and (r.get("label") or r.get("condition")):
            out["weather"].append({
                "label": _s(r.get("label"), 30), "condition": _s(r.get("condition"), 40),
                "high": _num(r.get("high")), "low": _num(r.get("low")),
                "unit": "F" if str(r.get("unit", "C")).upper().startswith("F") else "C",
            })
    b = data.get("budget") or {}
    if isinstance(b, dict):
        items = []
        for it in b.get("items") or []:
            amt = _num(it.get("amount")) if isinstance(it, dict) else None
            if amt and amt > 0:
                items.append({"label": _s(it.get("label"), 40) or "Other", "amount": amt})
        out["budget"] = {
            "currency": _s(b.get("currency"), 6) or "$", "limit": _num(b.get("limit")),
            "items": items, "verdict": _s(b.get("verdict"), 500),
        }
    for i, d in enumerate(data.get("itinerary") or [], start=1):
        if not isinstance(d, dict):
            continue
        items = [
            {"time": _s(x.get("time"), 30), "text": _s(x.get("text"), 400)}
            for x in (d.get("items") or []) if isinstance(x, dict) and x.get("text")
        ]
        if items:
            out["itinerary"].append({"day": int(_num(d.get("day")) or i), "title": _s(d.get("title"), 120), "items": items})
    return out


def empty_structured() -> dict:
    return {
        "flights": [], "hotels": [], "weather": [], "itinerary": [],
        "budget": {"currency": "$", "limit": None, "items": [], "verdict": ""},
    }


def merge_structured(base: dict, better: dict) -> dict:
    """Prefer the LLM result per section; keep the heuristic one where the LLM returned nothing."""
    out = dict(base)
    for key in ("flights", "hotels", "weather", "itinerary"):
        if better.get(key):
            out[key] = better[key]
    if better.get("budget", {}).get("items"):
        out["budget"] = better["budget"]
    return out


# ----------------------------------------------------------------------------- heuristics
def heuristic_structure(state: dict) -> dict:
    out = empty_structured()
    for key, fn, arg in (
        ("flights", _flights, state.get("flight_results")),
        ("hotels", _hotels, state.get("hotel_results")),
        ("weather", _weather, state.get("weather_results")),
        ("itinerary", _itinerary, state.get("itinerary")),
    ):
        try:
            out[key] = fn(str(arg or ""))
        except Exception:  # heuristics must never break the UI
            out[key] = []
    try:
        out["budget"] = _budget(str(state.get("budget_results") or ""), state.get("trip_constraints") or {})
    except Exception:
        pass
    return out


def _flights(text: str) -> list[dict]:
    rows, seen = [], set()
    for line in text.splitlines():
        for m in AIRLINE_RE.finditer(line):
            name = m.group(1).strip()
            if name.lower() in seen or len(rows) >= 4:
                continue
            seen.add(name.lower())
            dur = re.search(r"\b(\d{1,2}\s?h(?:ours?|rs?)?(?:\s?\d{1,2}\s?m(?:in)?)?)\b", line, re.I)
            price = re.search(rf"({CUR}\s?{NUM}(?:\s?[-–]\s?{CUR}?\s?{NUM})?)", line)
            times = re.findall(r"\b(\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?)\b", line)
            rows.append({
                "airline": name, "from": "", "to": "", "depart": times[0] if times else "", "arrive": times[1] if len(times) > 1 else "",
                "duration": dur.group(1) if dur else "", "price": price.group(1) if price else "", "note": _clean(line)[:160],
            })
    return rows


def _hotels(text: str) -> list[dict]:
    rows = []
    blocks = re.findall(r"Title:\s*(.+?)\s*\n\s*URL:\s*(\S+)\s*\n\s*Content:\s*(.+?)(?=\n\s*Title:|\Z)", text, re.S)
    if not blocks:
        blocks = re.findall(r"""['"]title['"]:\s*['"](.+?)['"],\s*['"]url['"]:\s*['"](.+?)['"],\s*['"]content['"]:\s*['"](.+?)['"]\s*[,}]""", text, re.S)
    for title, url, content in blocks[:6]:
        rating = re.search(r"(\d(?:\.\d)?)\s*(?:/\s*5|out of 5|stars?|★)", content, re.I)
        price = re.search(rf"({CUR}\s?{NUM})\s*(?:/|per|a)?\s*night|({NUM})\s?{CUR}?\s*(?:/|per)\s*night", content, re.I)
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        rows.append({
            "name": _clean(re.split(r"\s[-|–—]\s", title)[0])[:90] or host, "area": host,
            "rating": float(rating.group(1)) if rating and 0 < float(rating.group(1)) <= 5 else None,
            "price": (price.group(1) or price.group(2)) if price else "", "note": _clean(content)[:220], "url": url if url.startswith("http") else "",
        })
    return rows


def _weather(text: str) -> list[dict]:
    rows: dict[str, dict] = {}
    dates = list(re.finditer(r"(\d{4}-\d{2}-\d{2})", text))
    for i, m in enumerate(dates):
        end = dates[i + 1].start() if i + 1 < len(dates) else m.end() + 260
        day, chunk = m.group(1), text[m.end(): min(end, m.end() + 260)].lower()
        row = rows.setdefault(day, {"temps": [], "cond": ""})
        row["temps"] += [float(t) for t in re.findall(r"(-?\d{1,2}(?:\.\d+)?)\s*°", chunk)] or [
            float(t) for t in re.findall(r"temp[a-z_]*['\"]?\s*[:=]\s*(-?\d{1,2}(?:\.\d+)?)", chunk)
        ]
        if not row["cond"]:
            row["cond"] = next((label for word, label in COND_WORDS if word in chunk), "")
    out = []
    for day, row in list(rows.items())[:7]:
        if not row["temps"] and not row["cond"]:
            continue
        t = row["temps"]
        out.append({"label": day[5:], "condition": row["cond"], "high": max(t) if t else None, "low": min(t) if t else None, "unit": "F" if "°f" in text.lower() else "C"})
    return out


def _budget(text: str, constraints: dict) -> dict:
    items: dict[str, float] = {}
    line_re = re.compile(
        rf"^[\s>*\-•\d.)]*\**([A-Za-z][A-Za-z &/'+-]{{2,34}}?)\**\s*[:\-–—]\s*(?:~|approx\.?|about|around)?\s*{CUR}?\s?({NUM})"
        rf"(?:\s?(?:-|–|to)\s?{CUR}?\s?({NUM}))?",
        re.I | re.M,
    )
    for m in line_re.finditer(text):
        label = _clean(m.group(1)).title()
        if "total" in label.lower() or "budget" in label.lower() or "limit" in label.lower():
            continue
        lo, hi = _num(m.group(2)), _num(m.group(3))
        if lo is None:
            continue
        items.setdefault(label, (lo + hi) / 2 if hi else lo)
    verdict = next(
        (s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if re.search(r"feasible|realistic|within|exceed|over budget|tight", s, re.I)), ""
    )
    limit = _num(re.sub(r"[^\d.]", "", str(constraints.get("budget", "")).replace(",", ""))) if constraints.get("budget") else None
    return {
        "currency": _currency_symbol(str(constraints.get("budget", "")) + text), "limit": limit,
        "items": [{"label": k, "amount": v} for k, v in items.items() if v > 0][:8], "verdict": _clean(verdict)[:400],
    }


def _itinerary(text: str) -> list[dict]:
    marks = list(DAY_RE.finditer(text))
    days = []
    for i, m in enumerate(marks):
        body = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        items = []
        for raw in body.splitlines():
            line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw).strip()
            if not line or set(line) <= set("-_=* "):
                continue
            tm = TIME_RE.match(line)
            items.append({"time": tm.group(1).strip().title() if tm else "", "text": (tm.group(2) if tm else line).strip()})
        if items:
            days.append({"day": int(m.group(1)), "title": _clean(m.group(2))[:100], "items": items[:8]})
    return days
