"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are implemented. Their inputs, return values, and empty cases are
specified in the README's **Tool Inventory** section.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings

_PAREN_RE = re.compile(r"\(.*?\)")
_SIZE_SPLIT_RE = re.compile(r"[\s/]+")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {"a", "an", "the", "for", "with", "in", "on", "of", "and"}


def _size_tokens(size_str: str) -> set[str]:
    """
    Break a size string into whole components, ignoring parenthetical notes.

    "S/M" -> {"s", "m"}, "US 8.5" -> {"8.5"}, "XL (oversized)" -> {"xl"}.
    Splitting on whitespace/slash rather than every character is what stops
    "M" from matching inside "XL" the way a plain substring test would. A bare
    "US" is a prefix, not a size, so it's dropped — otherwise "US 8" would also
    match "US 8.5" and "US 9" through the shared "us" token.
    """
    cleaned = _PAREN_RE.sub("", size_str).strip().lower()
    return {
        token for token in _SIZE_SPLIT_RE.split(cleaned) if token and token != "us"
    }


def _sizes_match(query_size: str, listing_size: str) -> bool:
    return bool(_size_tokens(query_size) & _size_tokens(listing_size))


def _keywords(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


def _keyword_overlap(listing: dict, keywords: set[str]) -> int:
    haystack = " ".join([
        listing["title"],
        listing["description"],
        listing["category"],
        " ".join(listing["style_tags"]),
    ])
    return len(keywords & _keywords(haystack))


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    candidates = []
    for listing in load_listings():
        if max_price is not None and (
            listing["price"] is None or listing["price"] > max_price
        ):
            # A listing with no price can't be shown to fit under a ceiling.
            continue
        if size is not None and not _sizes_match(size, listing["size"]):
            continue
        candidates.append(listing)

    keywords = _keywords(description)
    scored = [(listing, _keyword_overlap(listing, keywords)) for listing in candidates]
    scored = [pair for pair in scored if pair[1] > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [listing for listing, _ in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_desc = (
        f"{new_item.get('title')} — {new_item.get('category')}, "
        f"colors: {', '.join(new_item.get('colors') or [])}, "
        f"style: {', '.join(new_item.get('style_tags') or [])}"
    )
    system = (
        "You are a styling assistant for a thrift-shopping app. Keep "
        "suggestions concrete and specific to the pieces mentioned, not "
        "generic fashion advice."
    )

    items = wardrobe.get("items") or []
    if not items:
        prompt = (
            f"A thrifter is considering buying this item:\n{item_desc}\n\n"
            "They don't have any wardrobe items saved yet. Suggest one or two "
            "general outfit ideas for this piece on its own — what kind of "
            "pieces would pair well with it, in terms of color, style, and "
            "silhouette."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {piece.get('name')} ({piece.get('category')}, "
            f"colors: {', '.join(piece.get('colors') or [])})"
            for piece in items
        )
        prompt = (
            f"A thrifter is considering buying this item:\n{item_desc}\n\n"
            f"Their existing wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest one or two specific outfits that pair this item with "
            "pieces from their wardrobe above, naming the pieces by name."
        )

    return generate(prompt, system=system)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "No fit card yet — couldn't come up with an outfit for this item."

    price = new_item.get("price")
    if price is None:
        # Thrift listings can lack a price. Without this branch the prompt
        # says "Price: $None" and the caption repeats it or makes one up.
        price_text = "not listed"
        mention = (
            "Mention the item and its platform once each, say the price "
            "wasn't listed (don't write a number or invent one),"
        )
    else:
        price_text = f"${price}"
        mention = "Mention the item, its price, and its platform once each,"

    prompt = (
        f"Item: {new_item.get('title')}\n"
        f"Price: {price_text}\n"
        f"Platform: {new_item.get('platform')}\n"
        f"Outfit idea: {outfit}\n\n"
        "Write a short caption (two to four sentences) that someone would "
        "actually post about this thrifted find — it should read like a real "
        "social post, not a product description. " + mention + " and be "
        "specific about the vibe."
    )
    system = "You write casual, specific social captions for thrifted fashion finds."
    return generate(prompt, system=system)
