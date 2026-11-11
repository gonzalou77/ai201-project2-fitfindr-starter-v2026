# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**

`search_listings` scores by keyword overlap — a set intersection between the words in the query's description and the words in a listing's title/description/category/style_tags. That's a plain keyword match, not a semantic one, so a real match can still score zero and get filtered out if the query's wording doesn't share an exact word with the listing (a synonym, a typo, or a phrasing the listing just doesn't use). 4 of 5 leaves room for that kind of miss without pretending the matcher is smarter than it is.

> **Tweaked:** My search is a literal keyword-overlap match, not a semantic one — if my query phrasing doesn't share an exact word with a listing's title, description, category, or style tags, that listing scores zero and gets dropped even if a person would call it a match. 4 of 5 accounts for that gap without claiming my matcher understands synonyms or paraphrasing it was never built to catch.
>
> **Why tweaked:** The original said the same thing but talked about the code in third person ("search_listings scores...") instead of owning the limitation as my own design choice. Shortened it too — the original repeated "match" language in a way that padded the paragraph without adding a new reason.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**

This path doesn't depend on how well the wording matched — it depends on one deterministic fact: whether `session["search_results"]` is an empty list. `agent.py::run_agent` branches on that with a plain `if not session["search_results"]:`, no scoring or judgment call involved, so there's no fuzziness for this one to fail on the way criterion 1 can. 5 of 5 is reasonable exactly because this branch has nothing probabilistic left in it by the time it runs.

> **Tweaked:** This branch doesn't involve any matching judgment — it just checks whether `search_results` came back empty, a plain boolean with no ambiguity in it. Since there's no fuzzy scoring left in this path, I expect it to hold every time.
>
> **Why tweaked:** The original quoted the literal `if not session["search_results"]:` line from `agent.py`, which repeats what "Where it lives" already points to two sections up in the README — restating the code here didn't add to the reasoning, so I cut it down to just the claim: this path is boolean, criterion 1's isn't.

---

## 3. Something about state
Given a query that provides an item id, it will be alerted that id is the same for the search found is the same item id the next tool received. This should be caught 5 out of 5 times.
<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->



**Why this target:**
Id provides a unique identifier. It is the simplest approach for accomplishing this criteria, rather than other traits which may be very common across listings such as sizes and brands.

> **Revised in unit 4:** For a matching query, in 5 of 5 tries the listing id that `search_listings` returned first is the same id held in `session["selected_item"]` and the same id received by `suggest_outfit` and by `create_fit_card`. `run_agent` records the id at each hand-off in `session["item_ids"]`; if any differs it sets `session["error"]` and stops.
>
> **Why revised:** The original said "a query that provides an item id", but queries never carry an id — the agent only learns one after search runs — so there was no way to run it as written. The check itself (compare ids) is unchanged; this just says where each id comes from and what counts as a mismatch.


---

## 4. Something about the fit card
5 out of 5 times an item without a price will be caught.


<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->



**Why this target:**
Nothing is more aggravating than an item with a price listing. Is it in stock or not?

> **Revised in unit 4:** When the selected listing's `price` is `None`, in 5 of 5 tries `run_agent` adds a message to `session["warnings"]`, and the fit card contains neither the text "None" nor a dollar figure.
>
> **Why revised:** "Caught" didn't say what anyone could observe, and every one of the 40 listings has a price, so no normal query ever produced an unpriced item to catch. This names the observable (a warning in the session, a clean fit card) and the scenario supplies the unpriced listing through `item_overrides`.


---

## 5. Your choice
5 out of 5 times it will be noted when the model cant be reached.
<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->



**Why this target:**
We tend to over rely on models to do the work for us. We should be able to tell when we have to immediately start searching ourselves. Noone likes to waste time.

> **Revised in unit 4:** When the model can't be reached (an invalid API key), in 5 of 5 tries `run_agent` returns without raising, `session["error"]` says the model couldn't be reached and names the listing search found (title, price, platform), and `session["fit_card"]` is `None`.
>
> **Why revised:** "It will be noted" didn't say where or what. The point of my reason — knowing right away that I have to go look myself — is that the message hands over what search found, so that is what is now checked.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->

---

## Capstone

Written before any capstone run. Each target is for **three trials** per
criterion. Criteria 1, 2, 3 and 5 are about the extension (re-plan and
deployment). Criterion 4 is about the logging layer built with it.

**1. A size-only miss is rescued, and says what it gave up.**

`90s track jacket in size XS` returns no listings at size XS. The agent drops
the size filter, searches again, and completes all three tools, with a warning
naming the dropped size. **Target: 3 of 3 trials.**

**Why this target:** Size is the one filter the data routinely misses, and the
first search has zero results for a real item the user would want (the
track jacket exists in size M). Three of three is the right bar because the
search is deterministic: a given query either re-plans to the same result every
time or it does not, so a miss on any trial is a real defect, not noise.

**2. A ceiling miss is rescued at the stated factor, and names the new ceiling.**

`vintage graphic tee under $10` returns nothing. The agent raises the ceiling
to $15 (config.RELAX_PRICE_FACTOR = 1.5), searches again, and completes, with a
warning naming $15. **Target: 3 of 3 trials.**

**Why this target:** The factor is the one number the re-plan invents, so the
warning has to report it exactly or the user cannot tell a $15 result from a
$10 one. Three of three because the second search is deterministic on the same
data.

**3. An impossible query stops after exactly three searches, before any model call.**

`designer ballgown size XXS under $5` makes exactly three searches (original,
size dropped, ceiling raised to $7.50), all empty, then stops with an error
naming what to change. `suggest_outfit` and `create_fit_card` are never called.
**Target: 3 of 3 trials, and `len(session["attempts"]) == 3` in each.**

**Why this target:** It proves the loop is bounded and the stop still fires
after the new branch. The count of three is a property of the code, so it
should hold every trial; anything else means the re-plan loop changed.

**4. Every /ask request writes a complete log record.**

Across three trials of a 10-request script (a mix of completing, rescued and
stopped queries, plus one malformed request), **every** request writes one log
record, and every record has all the fields the README extract lists: timestamp,
query, outcome, error, selected id, search attempts, model calls, tokens, and
duration in milliseconds. **Target: 3 of 3 trials, 30 of 30 records complete.**

**Why this target:** A log is only useful if it is never silently missing a
field, and the Render disk is wiped, so the record copied into the README has to
be complete by itself. Thirty of thirty, not 29 of 30, because one dropped
record means the cost and latency numbers quietly exclude a request.

**5. The rescue works on the deployed service, and the timing is reported warm and cold separately.**

On the Render URL, `90s track jacket in size XS` returns HTTP 200 with a non-empty
`warnings` list and a fit card, in three trials. The first request after an idle
period is recorded as cold. **Target: 3 of 3 warm trials return 200 with the rescue,
and each warm request completes within 20 seconds.**

**Why this target:** Warm and cold are different things. The cold wake happens at
Render's edge, before the app runs, so the in-app timer can only ever see warm
time. Keeping them separate means a slow cold start is not hidden in the warm
number, and a 20-second warm bound leaves room for one rate-limit pause from
`generate.py` (up to about 60 seconds on a true limit, but the free tier's
15-per-minute pacing is designed to stay under that in a single request).

> The 20-second bound is a guess until the first run. If the first warm run
> lands well under it, the bound is loose and I will say so in the verdict. If
> it lands over it, the diagnosis is what decides the next move, not a raised
> target.
