"""A deterministic mock world: every tool returns fixed, verifiable data.

Determinism is what makes tasks checkable — the correct answer to every task
is known in advance because the world never changes. Lookups are normalized
(casefolded, substring-tolerant) so a model passing "Paris, France" instead
of "paris" isn't penalized for formatting.
"""

from __future__ import annotations

import math

FIXED_NOW = "2026-06-09T12:00:00Z"

WEATHER = {
    "paris": {"temp_c": 17, "condition": "cloudy"},
    "tokyo": {"temp_c": 24, "condition": "sunny"},
    "london": {"temp_c": 12, "condition": "rainy"},
    "mexico city": {"temp_c": 21, "condition": "clear"},
    "sydney": {"temp_c": 19, "condition": "windy"},
}

EMPLOYEES = {
    "alice": {"department": "Physics", "email": "alice@acme.io", "office": "B2"},
    "bob": {"department": "Engineering", "email": "bob@acme.io", "office": "A1"},
    "carol": {"department": "Finance", "email": "carol@acme.io", "office": "C3"},
    "dave": {"department": "Engineering", "email": "dave@acme.io", "office": "A2"},
    "frank": {"department": "Engineering", "email": "frank@acme.io", "office": "A3"},
}

# Head of Engineering (Frank) is also an employee, so chained lookups resolve.
DEPARTMENTS = {
    "physics": {"budget_usd": 120000, "head": "Erin"},
    "engineering": {"budget_usd": 340000, "head": "Frank"},
    "finance": {"budget_usd": 95000, "head": "Grace"},
}

USD_RATES = {"usd": 1.0, "eur": 1.10, "mxn": 0.055, "gbp": 1.27, "jpy": 0.0067}

STOCKS = {"acme": 142.50, "globex": 71.20, "initech": 12.80}

NOTES = {
    "groceries": "buy eggs, milk, tortillas",
    "wifi": "router password is hunter2-prime",
    "gym": "membership renews on July 3",
}


def _norm_lookup(table: dict, key: str) -> tuple[str | None, dict | str | float | None]:
    """Find a table entry whose key appears in (or equals) the query, casefolded."""
    q = key.strip().casefold()
    if q in table:
        return q, table[q]
    for k in table:
        if k in q or q in k:
            return k, table[k]
    return None, None


# ── Tool implementations ─────────────────────────────────────────────────────

def get_weather(city: str) -> str:
    k, v = _norm_lookup(WEATHER, city)
    if v is None:
        return f"Error: no weather data available for {city!r}"
    return f"Weather in {k.title()}: {v['temp_c']}°C, {v['condition']}"


def get_stock_price(ticker: str) -> str:
    k, v = _norm_lookup(STOCKS, ticker)
    if v is None:
        return f"Error: unknown ticker {ticker!r}"
    return f"{k.upper()}: {v:.2f} USD per share"


def get_current_time() -> str:
    return f"Current date and time: {FIXED_NOW}"


def calculator(expression: str) -> str:
    allowed = set("0123456789+-*/().,% eE")
    if not all(c in allowed for c in expression):
        return "Error: expression contains disallowed characters"
    try:
        result = eval(  # noqa: S307 — character allowlist + empty builtins
            expression.replace(",", ""), {"__builtins__": {}},
            {k: getattr(math, k) for k in dir(math) if not k.startswith("_")},
        )
        if isinstance(result, float):
            return f"{result:.10g}"  # 173.40/6 → "28.9", not "28.900000000000002"
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def lookup_employee(name: str) -> str:
    k, v = _norm_lookup(EMPLOYEES, name)
    if v is None:
        return f"Error: no employee named {name!r}"
    return f"{k.title()}: department={v['department']}, email={v['email']}, office={v['office']}"


def lookup_department(name: str) -> str:
    k, v = _norm_lookup(DEPARTMENTS, name)
    if v is None:
        return f"Error: no department named {name!r}"
    return f"{k.title()}: budget={v['budget_usd']} USD, head={v['head']}"


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    f = str(from_currency).strip().casefold()
    t = str(to_currency).strip().casefold()
    if f not in USD_RATES or t not in USD_RATES:
        return f"Error: supported currencies are {sorted(USD_RATES)}"
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return "Error: amount must be a number"
    result = amt * USD_RATES[f] / USD_RATES[t]
    return f"{amt:g} {f.upper()} = {result:.2f} {t.upper()}"


def search_notes(query: str) -> str:
    q = query.strip().casefold()
    hits = [f"[{k}] {v}" for k, v in NOTES.items() if q in k or q in v.casefold() or k in q]
    return "\n".join(hits) if hits else f"No notes matching {query!r}"


def send_message(recipient: str, body: str) -> str:
    return f"Message delivered to {recipient}"


# ── Registry ─────────────────────────────────────────────────────────────────

def _schema(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


TOOLS: dict[str, dict] = {
    "get_weather": {
        "fn": get_weather,
        "schema": _schema(
            "get_weather", "Get the current weather for a city.",
            {"city": {"type": "string", "description": "City name"}}, ["city"],
        ),
    },
    "get_stock_price": {
        "fn": get_stock_price,
        "schema": _schema(
            "get_stock_price", "Get the latest stock price in USD for a ticker symbol.",
            {"ticker": {"type": "string", "description": "Ticker symbol, e.g. ACME"}}, ["ticker"],
        ),
    },
    "get_current_time": {
        "fn": get_current_time,
        "schema": _schema("get_current_time", "Get the current date and time (UTC).", {}, []),
    },
    "calculator": {
        "fn": calculator,
        "schema": _schema(
            "calculator", "Evaluate an arithmetic expression, e.g. '173.40 / 6'.",
            {"expression": {"type": "string", "description": "Math expression"}}, ["expression"],
        ),
    },
    "lookup_employee": {
        "fn": lookup_employee,
        "schema": _schema(
            "lookup_employee", "Look up an employee's department, email, and office by name.",
            {"name": {"type": "string", "description": "Employee first name"}}, ["name"],
        ),
    },
    "lookup_department": {
        "fn": lookup_department,
        "schema": _schema(
            "lookup_department", "Look up a department's budget and head by department name.",
            {"name": {"type": "string", "description": "Department name"}}, ["name"],
        ),
    },
    "convert_currency": {
        "fn": convert_currency,
        "schema": _schema(
            "convert_currency", "Convert an amount between currencies (USD, EUR, MXN, GBP, JPY).",
            {
                "amount": {"type": "number", "description": "Amount to convert"},
                "from_currency": {"type": "string", "description": "Source currency code"},
                "to_currency": {"type": "string", "description": "Target currency code"},
            },
            ["amount", "from_currency", "to_currency"],
        ),
    },
    "search_notes": {
        "fn": search_notes,
        "schema": _schema(
            "search_notes", "Search the user's personal notes by keyword.",
            {"query": {"type": "string", "description": "Search keyword"}}, ["query"],
        ),
    },
    "send_message": {
        "fn": send_message,
        "schema": _schema(
            "send_message", "Send a chat message to a person.",
            {
                "recipient": {"type": "string", "description": "Recipient name"},
                "body": {"type": "string", "description": "Message text"},
            },
            ["recipient", "body"],
        ),
    },
}


def registry_for(tool_names: list[str]) -> tuple[list[dict], dict]:
    """Return (schemas, dispatch) for the named tools."""
    unknown = [t for t in tool_names if t not in TOOLS]
    if unknown:
        raise KeyError(f"Unknown tools: {unknown}")
    schemas = [TOOLS[t]["schema"] for t in tool_names]
    dispatch = {t: TOOLS[t]["fn"] for t in tool_names}
    return schemas, dispatch
