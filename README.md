# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools and the planning loop are built — that last command runs the
> whole agent (add `--trace` to see it step by step).
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

FitFindr is a thrift-shopping agent. A user describes what they want in plain language — e.g. `'vintage graphic tee under $30'` — and the agent searches a mock listings dataset, picks the best match, suggests an outfit built around pieces the user already owns (or general styling advice if they haven't saved a wardrobe yet), and writes a short caption for the find in the style of a real social post. If nothing in the data matches the query, the agent stops and says what to change — a higher price ceiling, a different size, or different keywords — instead of continuing with nothing to work with.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the listings data by an optional size and price ceiling, then ranks what's left by keyword overlap with a free-text description.
- **Inputs:** `description` (str) — keywords describing what the user wants, e.g. `"vintage graphic tee"`. `size` (str or None) — matched case-insensitively against whole parts of a listing's `size` field, so `"M"` matches `"S/M"` but not `"XL"`, and a leading `"US"` is ignored (`"US 8"` matches `"US 8"` but not `"US 8.5"`); `None` skips size filtering. `max_price` (float or None) — maximum price, inclusive; `None` skips price filtering. A listing with no price never passes a price ceiling.
- **Returns:** A list of listing dicts, best match first, capped at `config.SEARCH_RESULT_LIMIT`. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
- **When it has nothing:** An empty list — never `None`, never an exception.

### `suggest_outfit`

- **What it does:** Calls the model to suggest one or two outfits pairing a candidate thrifted item with the user's existing wardrobe.
- **Inputs:** `new_item` (dict) — a listing dict, the item under consideration. `wardrobe` (dict) — a wardrobe dict with an `items` key holding a list of wardrobe item dicts; the list may be empty.
- **Returns:** A non-empty string with outfit suggestions, naming specific wardrobe pieces the user already owns when the wardrobe has items.
- **When it has nothing:** When `wardrobe["items"]` is empty, returns general styling advice for the item on its own — not an empty string, not a raised exception.

### `create_fit_card`

- **What it does:** Calls the model to write a short, postable caption for the find — mentions the item, its price, and its platform once each, and names the vibe.
- **Inputs:** `outfit` (str) — the suggestion string returned by `suggest_outfit()`. `new_item` (dict) — the listing dict for the item.
- **Returns:** A two-to-four sentence caption string. Wording varies between calls (governed by `TEMPERATURE` / `CACHE_ENABLED` in `config.py`), so identical input can produce different output — that's expected, not a bug.
- **When it has nothing:** If `outfit` is empty or whitespace-only, returns a descriptive message rather than raising. If the item's `price` is `None`, the caption says the price wasn't listed rather than printing `None` or inventing a figure.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` naming what to change (e.g. raise the price ceiling or drop the size filter) and stop — `suggest_outfit` is never called. Otherwise take `search_results[0]` as `session["selected_item"]` and continue to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::_parse_query`. One pattern pulls out `"under $X"` as `max_price`; another pulls out `"size X"` as `size`; whatever text is left over (after trimming a dangling connector word like a trailing "in") becomes the description. No model call — the example queries follow a consistent enough shape that two patterns cover them.

**Other stops and checks in `run_agent`:** `search_listings` and `create_fit_card` are called over MCP (`mcp_server.py`, via `mcp_client.call_tool`); `suggest_outfit` is still a direct call. If the search call fails, `session["error"]` says so and the run stops. If the model can't be reached — `ModelUnavailable` from `suggest_outfit`, or the same failure arriving as an `MCPError` from `create_fit_card` — `session["error"]` gives a plain message that names the listing search found so the user can look themselves, and the technical reason goes in `session["error_detail"]` and the trace. Before each tool that takes the item, `agent.py::_hand_off` records the listing id it received in `session["item_ids"]` and stops with an error if it differs from the id search returned. A selected item with no price adds a note to `session["warnings"]` and the run continues.

**What moves through the session:** `query` → `parsed` (the description/size/max_price pulled out of the query) → `search_results` (everything `search_listings` returned) → `selected_item` (the one chosen, which is what actually reaches `suggest_outfit`) → `outfit_suggestion` → `fit_card`. `error` is set instead of the later fields when the branch above stops the run early.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1: Casual Y2K Contrast**
Pair the Y2K butterfly baby tee with your **baggy straight-leg jeans, dark wash** to balance out the tight silhouette of the top. Layer the **black cropped zip hoodie** unzipped over the baby tee, and finish the look with your **chunky white sneakers** and the **black crossbody bag**.

**Outfit 2: Soft Grunge Mix**
Tuck the butterfly baby tee into your **wide-leg khaki trousers**, cinched at the waist with the **brown leather belt**. Throw the **vintage black denim jacket** over your shoulders and ground the softer tones of the tee and trousers with your **black combat boots**.

  Fit card: Found this butterfly print Y2K baby tee on Depop for just $18 and I'm obsessed with the early 2000s mall-goth energy. Tossed it on with baggy jeans and chunky sneakers for the ultimate casual contrast, but it's definitely gonna be on heavy rotation with my combat boots too. ✨🦋

0 model calls this session, 2 served from cache
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': "Y2K Baby Tee — Butterfly Print", 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
**Outfit 1: Casual Streetwear**
Pair the Vintage Levi's 501 Jeans with the **white ribbed tank top** tucked in, layered under the **black cropped zip hoodie**. Finish this look with the **chunky white sneakers** and the **black crossbody bag**.

**Outfit 2: Grungy Contrast**
Pair the jeans with the **oversized grey crewneck sweatshirt** and cinch the waist using the **brown leather belt**. Throw the **vintage black denim jacket** over top and anchor the outfit with the **black combat boots** and the **black crossbody bag**.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Nothing beats the wash on these vintage Levi's 501s—they're the ultimate lazy Sunday fit paired with crisp white sneakers. Snagged them for just $38.00 and I honestly might live in this exact uniform all fall. Grab them on my depop before I change my mind and keep them for myself!
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I had Claude spec and build `search_listings` from the docstring already in `tools.py`, which explicitly warns that a naive substring test on size is buggy — `"s" in "us 9"` and `"l" in "xl"` both come back `True`.
- *What came back:* An implementation using a token-based size matcher (`_size_tokens`/`_sizes_match`) that splits a size string like `"S/M"` into whole components (`{"s", "m"}`) instead of testing substrings, so a query for `"M"` matches `"S/M"` but not `"XL"`.
- *What I changed:* Nothing in the code — but I didn't take the fix on faith. I ran `_sizes_match('L', 'XL')` and `_sizes_match('S', 'US 9')` directly from a terminal to confirm both of the docstring's named bugs actually come back `False` under the new matcher, alongside a positive case (`_sizes_match('M', 'S/M')` → `True`), before accepting it into the Tool Inventory.

**Moment 2**

- *What I asked for:* Per the Milestone 4 instructions, I had Claude run `create_fit_card` three times on the same item and read the outputs, to check they weren't word-for-word identical.
- *What came back:* All three outputs were identical. Claude's first read was to name the two possible causes from `config.py` — `CACHE_ENABLED` or `TEMPERATURE` at `0.0` — then actually check rather than guess: it read `config.py`'s live values (`TEMPERATURE = 0.9`, `CACHE_ENABLED = True`), and called `generate()` directly with `cache=False` on the same prompt, which produced two genuinely different captions.
- *What I changed:* Nothing — the identical output was the cache correctly reusing an identical prompt while building, exactly as `config.py`'s comments describe, not a bug in the tool. The useful part of this exchange was the verification step (disabling the cache to isolate the real cause) rather than stopping at the first plausible explanation.

**Moment 3** (unit 4)

- *What I asked for:* To move a second tool onto MCP — `create_fit_card`, which calls the model — beyond the one the milestone requires, to see what a model-calling tool does when it runs on the server.
- *What came back:* Claude registered it, then before trusting it checked what crosses into the server process. It found the MCP SDK starts the server with only a short list of environment variables, so the `AI201_CACHE=0` that `run_eval.py` sets never reached it — five "uncached" eval tries would have returned one cached caption five times. It then triggered a bad key on the server and found the error arrived as "unhandled errors in a TaskGroup" with advice to check that the server runs, instead of the real reason.
- *What I changed:* I kept Claude's three fixes — forward `AI201_*` and `GEMINI_*` variables in `mcp_client.py`, unwrap the real `MCPError` in `call_tool`, and catch both `ModelUnavailable` and `MCPError` in `run_agent`. That meant editing `mcp_client.py`, which the starter calls given code, so it is worth knowing it was changed. The exit-time model-call count is still too low for calls made on the server; I left that and wrote it down in What's Still Broken.

**Moment 4** (unit 4)

- *What I asked for:* After the first `run_eval.py --label before` came back 5 of 5 on every criterion, I asked for a harsher scenario, because a table with no misses couldn't show where the agent breaks.
- *What came back:* Claude probed `search_listings` offline with a dozen or so queries before writing anything and found two kinds of failure: `trainers` and `tshirt` returned nothing even though the data holds sneakers and tees, and `denim jackets` returned five results with the jeans on top. It proposed three scenarios — two for criterion 1 and the plural one as a diagnostic, since criterion 1 only asks that the run complete.
- *What I changed:* I kept the split. The two criterion-1 queries then missed 0 of 5, which became the diagnosis and the one improvement. Claude also pointed out, and I wrote into the README, that these scenarios were chosen after seeing the first run, so passing them after the fix is weaker evidence than the plural queries nobody designed around.


<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools — `vintage graphic tee under $30` | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 1. (harsher) synonym — `trainers size 8` | 4 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |
| 1. (harsher) spelling variant — `tshirt under $30` | 4 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |
| 2. Impossible query stops before `suggest_outfit` — `designer ballgown size XXS under $5` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item id from search to both later tools — `90s track jacket in size M` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Item with no price is caught — `vintage graphic tee under $30`, price forced to `None` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Unreachable model is noted — invalid API key | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Source: `results/run_2026-10-07_1918_before-harsh.md` (nine scenarios, five tries each, cache off). PASS/FAIL is against the revised wording of each criterion in `criteria.md`, which are the pass conditions written into `scenarios.py`. The same run also covered two diagnostic scenarios that aren't one of the five: an **empty wardrobe** (`denim jacket under $50`, completed 5/5 with general styling advice, no crash) and a **plural** query (`denim jackets under $50`, completed 5/5 — on the wrong item, see Diagnoses).

An earlier run, `results/run_2026-10-07_1911_before.md`, had the first six scenarios and the same results on criteria 1 (matching query), 2, 3, 4 and 5. I added the two harsher criterion-1 queries and the plural diagnostic afterwards (commit `634c340`, before the second run) because every try in the first run passed, which showed nothing about where the keyword matcher stops.

**Real output from one try** — `vintage graphic tee under $30`, try 1 of the matching-query scenario. The outfit came from `tools.py::suggest_outfit`, the caption from `tools.py::create_fit_card` (called through `agent.py::run_agent`), and the session fields from `agent.py::run_agent`:

```
selected_item:  Y2K Baby Tee — Butterfly Print ($18.0, depop)   [lst_002]
item_ids:       {'searched': 'lst_002', 'selected': 'lst_002', 'suggest_outfit': 'lst_002', 'create_fit_card': 'lst_002'}

Outfit suggestion:
**Outfit 1: Casual Y2K Contrast**
*   **Top:** Y2K Baby Tee — Butterfly Print
*   **Bottoms:** Baggy straight-leg jeans (dark wash)
*   **Outerwear:** Black cropped zip hoodie (worn open)
*   **Shoes:** Chunky white sneakers
*   **Accessories:** Black crossbody bag

*Why it works:* The fitted silhouette of the baby tee balances the volume of the baggy dark-wash jeans, while the black cropped zip hoodie frames the pink and purple butterfly graphic without hiding it. Tie it together with the chunky white sneakers and the black crossbody bag for an effortless, throwback daily look.

**Outfit 2: Edgy Streetwear Mix**
*   **Top:** Y2K Baby Tee — Butterfly Print
*   **Bottoms:** Wide-leg khaki trousers
*   **Accessories:** Brown leather belt + Black crossbody bag
*   **Shoes:** Black combat boots

*Why it works:* Tucking the butterfly baby tee into the wide-leg khaki trousers and cinching them with the brown leather belt creates a defined waist against the relaxed pants. The black combat boots add a tough, grounded edge that contrasts nicely with the sweet pastel tones of the butterfly print.

Fit card:
Found the ultimate Y2K butterfly baby tee and I’m literally never taking it off. It’s giving major 2000s mall-rat energy and I'm obsessed with how fitted it is. Grabbed it on Depop for just $18.0, so obviously it had to come home with me!
```

The block above is **criterion 1**. Real output for the other criteria, each from try 1 of its scenario in `results/run_2026-10-07_1918_before-harsh.md`. Every model-involved scenario produced five different fit cards and five different outfits across its five tries, so these were real reruns with the cache off, not one cached answer repeated.

**Criterion 2** — `designer ballgown size XXS under $5`. Produced by `agent.py::run_agent` (the branch), with the search done by `tools.py::search_listings` over MCP. 0 search results; no outfit or fit card:

```
stopped early: No listings matched. Try raising the price ceiling, dropping the size filter, or using different keywords in the description.

[1] parse query (regex)
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
[3] branch
      →    search came back empty, stopping before suggest_outfit
```

**Criterion 3** — `90s track jacket in size M`. The ids are recorded by `agent.py::_hand_off` inside `agent.py::run_agent`, and the trace line comes from `trace.py::step`. One id at all four points:

```
selected_item: 90s Track Jacket — Navy/White Stripe ($45.0, poshmark)

[6] state check
      out: {'searched': 'lst_004', 'selected': 'lst_004', 'suggest_outfit': 'lst_004', 'create_fit_card': 'lst_004'}
      →    same listing id at every hand-off
```

**Criterion 4** — `vintage graphic tee under $30` with the selected listing's price forced to `None` (`run_agent`'s `item_overrides`, set by the scenario). The warning is added by `agent.py::run_agent`; the caption is written by `tools.py::create_fit_card`, run on the MCP server. The `$None` in the trace is just how `trace.py::_short` prints a missing price; the caption has neither "None" nor a dollar figure:

```
[3] select first result
      out: Y2K Baby Tee — Butterfly Print ($None, depop)
[4] warning
      →    Listing lst_002 has no listed price; the fit card will say so rather than guess one.
[5] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($None, depop)
      out: **Outfit 1: The Y2K Contrast** Pair the Y2K butterfly baby tee with your **baggy straight-leg jeans (dark wash…
[6] create_fit_card (via MCP)
      in:  Y2K Baby Tee — Butterfly Print ($None, depop)
      out: manifesting this exact butterfly baby tee on my depop feed since the seller didn't even drop a price tag. hone…

Fit card:
manifesting this exact butterfly baby tee on my depop feed since the seller didn't even drop a price tag. honestly just picturing it with baggy dark wash denim and chunky sneakers for the ultimate unbothered 2000s mall rat aesthetic. need it in my wardrobe yesterday.
```

**Criterion 5** — `vintage graphic tee under $30` with an invalid API key for that scenario only (`run_eval.py::run_once`). Produced by `agent.py::run_agent`'s `except (ModelUnavailable, MCPError)` handler, with the failure raised in `generate.py::generate`. This is the wording at the time of the run; I made it plainer afterwards (see "The three failure modes" under Loop Trace):

```
The model couldn't be reached, so there's no outfit or fit card. Search did find 'Y2K Baby Tee — Butterfly Print' ($18.0 on depop), so you can look at it yourself. Reason: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

[3] select first result
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] model unavailable
      →    stopping: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | **MISSED** | Met on the plain query (5/5), missed on the two harsher ones (0/5 each). I counted the harsher queries because the criterion's own reason names synonyms and phrasing the listings don't use as the expected way to miss, and `trainers` and `tshirt` are exactly that for items the data holds (sneakers in `lst_019`, tees in `lst_002`). A reader who counts only queries that already share a word with a listing would call this MET; I think that reading makes the criterion unable to fail. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET | 5 of 5 tries stopped at the `branch` step with the "raise the price ceiling, drop the size filter…" message. I checked each trace for a `suggest_outfit` or `create_fit_card` step and each result for an outfit or fit card; there were none. |
| 3 | Same item id from search to both later tools | 5 of 5 | MET | 5 of 5 tries (all selecting `90s Track Jacket — Navy/White Stripe`) show one id across `searched`, `selected`, `suggest_outfit` and `create_fit_card`, and no error. This criterion tests a guard I added (`agent.py::_hand_off`), which only fails if an id changes, so 5/5 shows it holds on the normal path. The eval never forces a mismatch; I forced one offline (overwriting the id with `lst_999`) and the run stopped with a state-mismatch error. |
| 4 | An item with no price is caught | 5 of 5 | MET | The scenario forces `price` to `None`. 5 of 5 tries added a warning to `session["warnings"]`, and no fit card contained "None" or a dollar sign — each said the price wasn't listed. |
| 5 | An unreachable model is noted | 5 of 5 | MET | With an invalid key, 5 of 5 tries returned without raising, set `session["error"]` saying the model couldn't be reached, named the listing search found (`Y2K Baby Tee — Butterfly Print`, $18.0, depop), and left `fit_card` as `None`. |

**Diagnoses**

**Criterion 1 — one miss, two symptoms, one cause. The place is a tool: `tools.py::search_listings`.** The `trainers size 8` and `tshirt under $30` queries both returned an empty list in every try, so the loop correctly stopped and told the user what to change — the branch did its job, and the model was never involved. The mechanism is in `_keywords` and `_keyword_overlap`: a listing matches only if a whole word in the query is also a whole word in the listing's title, description, category or style tags. "trainers" never appears in the data (the listings say "sneakers"), and "tshirt" never appears (they say "tee" and "shirt"), so both score zero everywhere and are filtered out. The plural query shows the same cause without a failed run: in `denim jackets under $50`, "jackets" appears nowhere in the data (only "jacket" does), so only "denim" matched, all five denim listings scored exactly 1, and a stable sort left the first of them in file order on top — Levi's 501 Jeans, which was selected in 5 of 5 tries, then styled and captioned as if it were the jacket the user asked for. That run counts as a pass on "completes all three tools", which is a gap in what criterion 1 measures, not a point in the agent's favour.

Two further notes, neither a miss. First, my reason for criterion 1 said 4 of 5 "leaves room" for synonym misses. That didn't hold up: search is deterministic, so a given query matches all five tries or none, and a vocabulary miss shows up as 0 of 5, not 4. Second, the model-call count printed on exit and in the run log is lower than the real number, because calls made inside the MCP server aren't counted (see "On the MCP move").



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Both traces are from `results/run_2026-10-07_1918_before-harsh.md` (try 1 of each scenario), printed by `trace.py::step` from calls in `agent.py::run_agent`. The two MCP calls are steps 2 and 5 of the happy path.

**Happy path** — `vintage graphic tee under $30` (six steps)

```
[1] parse query (regex)
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select first result
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: **Outfit 1: Casual Y2K Contrast** *   **Top:** Y2K Baby Tee — Butterfly Print *   **Bottoms:** Baggy straight-…
[5] create_fit_card (via MCP)
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Found the ultimate Y2K butterfly baby tee and I’m literally never taking it off. It’s giving major 2000s mall-…
[6] state check
      out: {'searched': 'lst_002', 'selected': 'lst_002', 'suggest_outfit': 'lst_002', 'create_fit_card': 'lst_002'}
      →    same listing id at every hand-off
```

**Empty search** — `designer ballgown size XXS under $5` (three steps)

```
[1] parse query (regex)
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
[3] branch
      →    search came back empty, stopping before suggest_outfit
```

The empty trace is half the length: it stops at step 3 and never reaches `suggest_outfit` or `create_fit_card`, so the branch is doing something.

**The three failure modes, triggered one at a time from the command line** (queries I hadn't run before, so none came from the build cache). Each was already handled by code written earlier in this unit, so none of them crashed, hung, or went silent, and no new handler was needed.

1. **Empty search** — `python app.py ask 'wedding tuxedo size 52 under $10' --trace`. The trace stopped at `[3] branch` (the same three steps as above) and the agent said:

   ```
   No listings matched. Try raising the price ceiling, dropping the size filter, or using different keywords in the description.
   ```

   The last line was `0 model calls this session` — it never reached a model tool.

2. **Empty wardrobe** — `python app.py ask 'cargo pants under $30' --empty-wardrobe`. It found `Low-Rise Cargo Pants — Khaki — $27.0 on poshmark` and `suggest_outfit` returned general advice rather than an error or an empty string: two outfit directions built from pieces *to look for* ("a fitted black or neon pink ribbed baby tee", "a thin metallic silver belt, a nylon shoulder bag", "beat-up canvas skate shoes (like Vans Old Skools)") with nothing claimed as owned. The fit card followed normally.

3. **Model unavailable** — I changed the last character of `GEMINI_API_KEY` for that one command (set in the shell, not saved to `.env`, so `.env` never changed and there was nothing to put back), then ran `python app.py ask 'silk button down under $40' --trace`. The search step ran, then the trace stopped at `[4] model unavailable` and the agent said:

   ```
   The model couldn't be reached, so there's no outfit or fit card. Search did find 'Silk Button-Down — Sage Green' ($28.0 on depop), so you can look at it yourself. Reason: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
   ```

   No stack trace and no hang. It named what broke (the key), what the user can do (check `.env` or make a new key), and what search had already found. The last line reported 1 model call and did not say "served from cache", so the failure was real.

   **Then I changed the wording.** That message was written for me, not for a user: it talks about an API key and a `.env` file, which an end user has no access to, and it said the reason twice. `agent.py::run_agent` now puts a plain message in `session["error"]` and keeps the provider's text in a new `session["error_detail"]` and in the trace step. Same failure, re-run with a fresh query (`'denim vest under $40' --trace`):

   ```
   The model couldn't be reached right now, so there's no outfit or fit card. Search did find 'Denim Vest — Medium Wash, Studded' ($27.0 on depop), so you can look at it yourself. Please try again in a moment.
   ```

   The trace still shows the key rejection at step 4, for whoever is debugging. I checked the other route too — a failure only in the fit-card step, which arrives from the MCP server — and it says "no fit card" instead of "no outfit or fit card", with no mention of keys. The criterion 5 scenario still passes 5 of 5 against the pass condition in `criteria.md` (it says the model couldn't be reached and names the listing). The saved run logs in `results/` were produced before this change, so they still show the old wording.

One thing the second run showed that isn't a failure: its closing line said `1 model calls this session` when two model calls actually ran, because the fit-card call happens inside the MCP server and isn't counted (see "On the MCP move").

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

**What changed:** `mcp_server.py` registers `search_listings` and `create_fit_card` (the milestone asks for one; I moved a second to see what a tool that calls the model does across the boundary). `agent.py::run_agent` now calls both through `mcp_client.call_tool`; `suggest_outfit` is still a direct call. The trace names them `search_listings (via MCP)` and `create_fit_card (via MCP)`.

**`search_listings` behaved identically.** I ran four queries directly and over MCP (`graphic tee` with a price ceiling, `90s track jacket` size M, `platform sneakers` size US 8, and the impossible `designer ballgown` size XXS under $5). They returned 6, 4, 1 and 0 results, and each MCP list was equal to the direct list. The empty case came back as `[]`, not `None`, so the loop's branch still fires. The one thing the move did show: the first description I wrote said sizes were "(s)small, (m)medium", which isn't how matching works, because the tool had never had to explain itself to anyone. I rewrote it to say whole-part matching, the units on `max_price`, and the empty case.

**`create_fit_card` behaved differently in three ways**, all because the server is a separate process:

- *The cache switch didn't cross.* The MCP SDK starts the server with only a short list of environment variables, so `run_eval.py`'s `AI201_CACHE=0` never reached it, and five "uncached" tries would have returned one cached caption five times. `mcp_client.py` now forwards `AI201_*` and `GEMINI_*` variables. Checked: two uncached calls through the server give two different captions.
- *The error was buried.* A bad API key on the server raised inside the client's async task groups and surfaced as "unhandled errors in a TaskGroup" plus advice to check that the server runs. `call_tool` now digs out the real `MCPError`, so the message reads "The model rejected your API key…".
- *The error type changed.* The same failure that is a `ModelUnavailable` when `suggest_outfit` runs in-process arrives as an `MCPError` from the server, so `run_agent` catches both.

**Still not fixed:** the "N model calls this session" line printed on exit only counts calls made in the main process, so it now leaves out the fit-card call. Rate-limit pacing is also per-process, so the server can exceed 15 requests a minute; `generate.py`'s retry on a 429 covers that.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** one change, in one function. `tools.py::_keywords` now passes every word through a new `_normalize` before comparing, on both the query and the listings: simple plurals are stripped (`jackets` → `jacket`, `dresses` → `dress`; words ending `ss`/`us`/`is` and words of three letters or fewer are left alone), and two aliases are treated as one word (`trainers` → `sneaker`, `tshirt` → `tee`). The tool description in `mcp_server.py` was updated to say so, including that other synonyms aren't recognised. Commit `cf8aec8`. Nothing else in the matching or the loop changed.

**Which failure it was meant to fix:** the criterion 1 miss, diagnosed above as a tool problem in `search_listings`: matching on exact whole words, so `trainers size 8` and `tshirt under $30` found nothing, and `denim jackets under $50` matched only "denim" and picked the jeans.

**Checked before the real run** (offline, no model calls, old `tools.py` from git against the new one): the three failing queries now find results, the other six scenario and example queries keep the same top result, and each of the 40 listings still finds itself first when its own title is the query (40/40 before and after). Plural queries I hadn't designed anything around went from nothing to a sensible top result — `blazers`, `cardigans`, `dresses under $40`, `shirts under $25`, `tees`, `hats`.

### Run Log — After

Source: `results/run_2026-10-07_1938_after.md` — the same nine scenarios, five tries each, cache off, as `before-harsh`. Fit cards were distinct 5/5 on every scenario that uses the model.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools — `vintage graphic tee under $30` | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 1. (harsher) synonym — `trainers size 8` | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 1. (harsher) spelling variant — `tshirt under $30` | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before `suggest_outfit` — `designer ballgown size XXS under $5` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item id from search to both later tools — `90s track jacket in size M` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Item with no price is caught — price forced to `None` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Unreachable model is noted — invalid API key | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Before and after, side by side:**

| Row | Before | After |
|---|---|---|
| 1. plain query | 5/5 MET | 5/5 MET |
| 1. synonym `trainers size 8` | 0/5 MISSED — stopped, no results | 5/5 MET — selects `Platform Sneakers — White Chunky Sole` |
| 1. spelling `tshirt under $30` | 0/5 MISSED — stopped, no results | 5/5 MET — selects `Y2K Baby Tee — Butterfly Print` |
| 2. impossible query | 5/5 MET | 5/5 MET |
| 3. item id | 5/5 MET | 5/5 MET |
| 4. no price | 5/5 MET | 5/5 MET |
| 5. model unreachable | 5/5 MET | 5/5 MET |
| diagnostic: plural `denim jackets under $50` | completed 5/5 on the **wrong item** (`Levi's 501 Jeans`) | completed 5/5 on `Denim Jacket — Light Wash, Cropped` |
| diagnostic: empty wardrobe | completed 5/5 | completed 5/5 |

Real output, the synonym query that used to stop (`tools.py::search_listings` over MCP, from try 1 of the after log):

```
[1] parse query (regex)
      in:  trainers size 8
      out: {'description': 'trainers', 'size': '8', 'max_price': None}
[2] search_listings (via MCP)
      in:  {'description': 'trainers', 'size': '8', 'max_price': None}
      out: 1 items: Platform Sneakers — White Chunky Sole
[3] select first result
      out: Platform Sneakers — White Chunky Sole ($48.0, poshmark)
```

**Did it help, and how do I know:** Yes — criterion 1 went from MISSED (0/5 on two of its three queries) to MET (5/5 on all three), and the plural query stopped picking the wrong item, with nothing else moving: criteria 2–5 stayed 5/5 and the three queries that already worked kept their top result. I know it was the change and not luck because the search is deterministic (the selected item is the same in all five tries of each scenario), and because the offline before/after comparison ran the same queries through both versions of the function.

Two cautions on that. First, I wrote the three harsher scenarios after seeing the first run, so they were always going to pass once I fixed exactly what they exposed; the better evidence that it generalises is the plural queries I hadn't designed around, and the 40/40 title check showing nothing got worse. Second, **two things changed between the `before-harsh` and `after` runs**, not one: this improvement (`cf8aec8`) and, earlier, the plainer wording of the model-unavailable message (`8587f53`). The second only changes the text criterion 5 prints — its pass condition (says the model couldn't be reached, names the listing, no fit card) is unchanged and was met 5/5 in both — so it can't account for the criterion 1 difference, but it is why the criterion 5 output in the two logs reads differently. Rate-limit pauses in the after run (16s, 22s, 17s, 26s) all retried and finished.

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

No criterion is missed in the after run, but that isn't the same as nothing being left.

- **Criterion 1 passes on the vocabulary I fixed, not on search in general.** Words outside the alias table still find nothing: `sweater`, `jumper`, `sundress`, `gown` and `runners` each return 0 results (checked after the change), even though the data holds a knit cardigan, crewneck sweatshirts, a slip dress and sneakers. Plural stripping generalises; the two-word alias table doesn't, and a table can't scale to a person's vocabulary. What I'd do is replace exact-word matching with something that compares meaning — embeddings, or a model call that rewrites the query into the listings' words — and re-run the same scenarios. I stopped where I did because that is a different design, not a second small change, and the assignment asks for one thing measured properly.
- **Ranking is still unweighted.** A listing needs only one shared word to match, so `tank top` returns 10 results topped by a crochet halter top, and `vintage graphic tee` returns 10 including cargo pants. The first result is what the agent uses, so a weak first result becomes the outfit and the caption. I'd weight title matches above description matches and prefer listings that match more of the query's words. I haven't measured it, so I haven't claimed a number.
- **Criteria 3, 4 and 5 test guards I wrote.** They can only fail if an id changes, a price goes missing, or the model is down. A 5/5 shows the guards hold on those paths; the eval never forces an id mismatch (I forced one offline and the run stopped). Nothing in my five criteria measures whether the selected item is a *good* one, which is exactly the gap the plural query exposed.
- **The exit-time model-call count is too low**, because calls inside the MCP server (the fit cards) aren't counted. Rate-limit pacing is also per process, so the server can go past 15 requests a minute and rely on `generate.py`'s retry. Neither changed a result; both would matter before this ran for real users.
- **Cosmetic:** the trace prints a missing price as `$None` (`trace.py::_short`). The fit card is unaffected.



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
