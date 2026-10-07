"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Criterion 3 — state. Pass: the closing "state check" step in the
        # trace shows one id for searched / selected / suggest_outfit /
        # create_fit_card, and session["error"] is None.
        "name": "item id survives the loop",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 — fit card. The real data has no unpriced listing, so
        # run_agent's item_overrides hands the loop one. Pass: the trace shows
        # a "warning" step, session["warnings"] is non-empty, and the fit card
        # contains neither "None" nor a dollar figure.
        "name": "listing with no price",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "item_overrides": {"price": None},
        "criterion": 4,
    },
    {
        # Criterion 5 — model unreachable. run_eval swaps in an invalid key for
        # this scenario only. Pass: session["error"] says the model couldn't be
        # reached and names the listing search found, no crash, fit_card None.
        "name": "model unreachable",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "bad_api_key": True,
        "criterion": 5,
    },
    # ── Harsher runs for criterion 1 ─────────────────────────────────────────
    # The first three criterion-1 style queries all share exact words with the
    # listings, so they can't show where the keyword matcher stops. These
    # describe things the data does hold — sneakers, tees — in words it doesn't
    # use. A person would call each a match; set intersection won't.
    {
        # "trainers" is the UK word for the sneakers in lst_019 and lst_035.
        "name": "synonym query completes",
        "query": "trainers size 8",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # "tshirt" is one word; the listings say "tee" and "shirt".
        "name": "spelling variant completes",
        "query": "tshirt under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # Completes, but on the wrong item: "jackets" != "jacket", so only
        # "denim" matches and the top result is jeans. Diagnostic — criterion 1
        # only asks that the run complete, so it can't see this one.
        "name": "plural picks the wrong item",
        "query": "denim jackets under $50",
        "wardrobe": "example",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
