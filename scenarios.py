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
    # ── Hardened runs for criteria 3, 4 and 5 ────────────────────────────────
    # Written after the first two runs showed criteria 3-5 passing 5/5 — and
    # after asking why. Each of those criteria, as I first ran it, checked a
    # guard I had built myself (an id check, a price warning, an error handler)
    # against a fault I injected myself, so it could hardly fail. These take the
    # fault from somewhere I don't control, and are run with
    #     python run_eval.py --group hardened --label hardened
    # Pass conditions are written here BEFORE the run.

    # Criterion 3 — state. "spy" records the id that actually reaches each tool,
    # at the call, instead of reading it back from the session. Four different
    # queries, run one after another in the same process, so state leaking from
    # one run into the next would show up too.
    # Pass (per try): search_first == suggest_outfit == create_fit_card ==
    # session["selected_item"]["id"], no error.
    {
        "name": "state: denim jacket",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "spy": True,
        "group": "hardened",
        "criterion": 3,
    },
    {
        "name": "state: platform sneakers",
        "query": "platform sneakers size 8",
        "wardrobe": "example",
        "spy": True,
        "group": "hardened",
        "criterion": 3,
    },
    {
        "name": "state: slip dress",
        "query": "silk slip dress in midi length under $40",
        "wardrobe": "example",
        "spy": True,
        "group": "hardened",
        "criterion": 3,
    },
    {
        "name": "state: track jacket",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "spy": True,
        "group": "hardened",
        "criterion": 3,
    },

    # Criterion 4 — no price, this time from the data. data/fixtures/
    # unpriced_listings.json holds one listing whose price is null and one with
    # no price field at all, read through the real search path on the MCP server.
    # Pass (per try): session["warnings"] is non-empty, and the fit card has
    # neither "None" nor a "$".
    {
        "name": "unpriced listing: price is null",
        "query": "corduroy bucket bag",
        "wardrobe": "example",
        "listings_file": "data/fixtures/unpriced_listings.json",
        "group": "hardened",
        "criterion": 4,
    },
    {
        "name": "unpriced listing: no price field",
        "query": "embroidered satin kimono",
        "wardrobe": "example",
        "listings_file": "data/fixtures/unpriced_listings.json",
        "group": "hardened",
        "criterion": 4,
    },
    {
        # Diagnostic, not one of the five: criterion 4 speaks of "the selected
        # listing", and this fails before anything is selected. Same data, but
        # with a price ceiling — search_listings documents that unpriced
        # listings are excluded when one is set. Pass: the run ends in a normal
        # "No listings matched" message. Fail: any error about the search being
        # unreachable, or a crash.
        "name": "unpriced listing with a price ceiling",
        "query": "corduroy bucket bag under $40",
        "wardrobe": "example",
        "listings_file": "data/fixtures/unpriced_listings.json",
        "group": "hardened",
        "criterion": None,
    },

    # Criterion 5 — two ways of being unreachable other than a bad key.
    # Pass (per try): no crash, session["error"] says the model couldn't be
    # reached and names the listing search found, fit_card is None.
    {
        "name": "model name doesn't exist",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "env": {"AI201_MODEL": "gemini-no-such-model-xyz"},
        "group": "hardened",
        "criterion": 5,
    },
    {
        "name": "network unreachable",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "env": {
            "HTTPS_PROXY": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9",
            "https_proxy": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9",
        },
        "group": "hardened",
        "criterion": 5,
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
