"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit
from generate import ModelUnavailable
from mcp_client import call_tool, MCPError


_PRICE_RE = re.compile(r"under\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
# An optional leading "US " keeps "size US 8" from being read as size "US".
_SIZE_RE = re.compile(r"\bsize[:\s]+((?:us\s+)?[A-Za-z0-9/.]+)", re.I)
_TRAILING_CONNECTOR_RE = re.compile(r"\s*\b(in|for)\s*$", re.I)


def _parse_query(query: str) -> dict:
    """
    Pull a description, a size, and a price ceiling out of a plain-language
    query. Regex, not the model — the query shapes in app.py's EXAMPLE_QUERIES
    are consistent enough ("under $X", "size X") that a couple of patterns
    cover them without spending a model call just to parse text.

    Whatever isn't claimed by the price or size pattern is the description.
    """
    remainder = query
    max_price = None
    size = None

    match = _PRICE_RE.search(remainder)
    if match:
        max_price = float(match.group(1))
        remainder = remainder[: match.start()] + remainder[match.end():]

    match = _SIZE_RE.search(remainder)
    if match:
        size = match.group(1)
        remainder = remainder[: match.start()] + remainder[match.end():]

    remainder = _TRAILING_CONNECTOR_RE.sub("", remainder)
    description = re.sub(r"\s+", " ", remainder).strip()

    return {"description": description, "size": size, "max_price": max_price}


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early — written for the user
        "error_detail": None,        # the technical reason behind it, for debugging
        "warnings": [],              # things worth knowing that didn't stop the run
        "item_ids": {},              # the listing id seen at each hand-off (criterion 3)
    }


def _hand_off(session: dict, stage: str, item: dict) -> bool:
    """
    Record the listing id a stage received, and check it's the one search found.

    The ids are read off the object each stage was actually given, not copied
    from the session afterwards — so if something re-sorts, re-selects, or
    overwrites the item between steps, the mismatch shows up here instead of
    as a fit card about the wrong jacket.
    """
    session["item_ids"][stage] = item.get("id")
    found = session["item_ids"]["searched"]
    if item.get("id") == found:
        return True
    session["error"] = (
        f"State mismatch: search found listing {found}, but {stage} "
        f"received {item.get('id')}. Stopped before using the wrong item."
    )
    trace.step("state check", inputs=str(session["item_ids"]), note=session["error"])
    return False


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict, item_overrides: dict | None = None) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.
        item_overrides: test only — fields to overwrite on the selected
                  listing (e.g. {"price": None}). Normal callers leave it out.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    count = 0

    count += 1
    trace.check_iterations(count)
    session["parsed"] = _parse_query(query)
    trace.step("parse query (regex)", inputs=query, returned=str(session["parsed"]))

    count += 1
    trace.check_iterations(count)
    search_args = {
        "description": session["parsed"]["description"],
        "size": session["parsed"]["size"],
        "max_price": session["parsed"]["max_price"],
    }
    try:
        session["search_results"] = call_tool("search_listings", search_args)
    except MCPError as exc:
        session["error"] = (
            "The listings search couldn't be reached, so nothing was searched. "
            f"({str(exc).splitlines()[0]})"
        )
        trace.step("search_listings (via MCP)", inputs=str(search_args),
                   note="MCP call failed, stopping")
        return session
    trace.step("search_listings (via MCP)", inputs=str(search_args),
               returned=session["search_results"])

    # THE BRANCH. Nothing to work with — stop before suggest_outfit runs.
    if not session["search_results"]:
        session["error"] = (
            "No listings matched. Try raising the price ceiling, dropping "
            "the size filter, or using different keywords in the description."
        )
        trace.step("branch", note="search came back empty, stopping before suggest_outfit")
        return session

    session["item_ids"]["searched"] = session["search_results"][0].get("id")
    item = session["search_results"][0]
    if item_overrides:
        # Test seam for run_eval.py (criterion 4): lets a scenario hand the
        # loop a listing with a field missing, which the real data never has.
        item = {**item, **item_overrides}
    session["selected_item"] = item
    if not _hand_off(session, "selected", session["selected_item"]):
        return session
    trace.step("select first result", returned=session["selected_item"])

    if session["selected_item"].get("price") is None:
        warning = (
            f"Listing {session['selected_item'].get('id')} has no listed price; "
            "the fit card will say so rather than guess one."
        )
        session["warnings"].append(warning)
        trace.step("warning", note=warning)

    try:
        count += 1
        trace.check_iterations(count)
        if not _hand_off(session, "suggest_outfit", session["selected_item"]):
            return session
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"], session["wardrobe"]
        )
        trace.step("suggest_outfit", inputs=session["selected_item"],
                   returned=session["outfit_suggestion"],
                   note="" if session["wardrobe"].get("items") else "empty wardrobe: general advice")

        count += 1
        trace.check_iterations(count)
        if not _hand_off(session, "create_fit_card", session["selected_item"]):
            return session
        session["fit_card"] = call_tool("create_fit_card", {
            "outfit": session["outfit_suggestion"],
            "new_item": session["selected_item"],
        })
        trace.step("create_fit_card (via MCP)", inputs=session["selected_item"],
                   returned=session["fit_card"])
        trace.step("state check", returned=str(session["item_ids"]),
                   note="same listing id at every hand-off")
    except (ModelUnavailable, MCPError) as exc:
        # suggest_outfit runs in this process and raises ModelUnavailable.
        # create_fit_card runs on the MCP server, where the same failure
        # arrives here as an MCPError carrying the server's message.
        # Still tell the user what search found, so they can carry on by hand.
        found = session["selected_item"]
        lost = "fit card" if session["outfit_suggestion"] else "outfit or fit card"
        # The user gets a plain message; the provider's wording (which talks
        # about API keys and .env files) goes in the session and the trace for
        # whoever is debugging.
        session["error"] = (
            f"The model couldn't be reached right now, so there's no {lost}. "
            f"Search did find '{found.get('title')}' "
            f"({'$' + str(found.get('price')) if found.get('price') is not None else 'no price listed'}"
            f" on {found.get('platform')}), so you can look at it yourself. "
            "Please try again in a moment."
        )
        session["error_detail"] = str(exc)
        trace.step("model unavailable", note=f"stopping: {exc}")

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
