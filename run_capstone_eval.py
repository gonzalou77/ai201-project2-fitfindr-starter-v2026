#!/usr/bin/env python3
"""
Run the five capstone criteria, three times each, and write the run log.

    python run_capstone_eval.py                     three runs, the default
    python run_capstone_eval.py --runs 1            one run, for a smoke test
    python run_capstone_eval.py --skip-live         leave criterion 5 out

Nothing changes between runs. The cache is forced off for the whole process
and for the MCP server, so a model answer is never reused from an earlier run
or an earlier trial.

What each criterion needs run against it, and why:

  1. A size-only miss. `90s track jacket in size XS` matches a real listing on
     keywords but nothing in size XS, so the first search is empty and the
     re-plan has to drop the size. Three trials per run.

  2. A ceiling-only miss. `vintage graphic tee under $10` matches on keywords
     but nothing under $10, so the ceiling has to rise to $15. Three trials.

  3. A query nothing can rescue. `designer ballgown size XXS under $5` is empty
     at every relaxation, so the loop has to try exactly three searches and then
     stop before any model call. Three trials. This is the bad path, and it is
     checked by counting searches, not by reading a message.

  4. Log completeness. Ten HTTP requests through the real Flask handler — a
     mix of completing, rescued and stopped queries, plus one malformed body
     that should be rejected with 400. Every one has to leave a record with
     every field present. Ten requests per run, thirty across three runs.

  5. The deployed service. Three warm POSTs to the Render URL. One wake request
     is made first and recorded SEPARATELY as cold, because a cold start
     happens at Render's edge before the app exists and cannot be measured from
     inside it — mixing the two would report a number the criterion does not
     mean.

Writes results/capstone_run_<timestamp>.md with the table and the real output
underneath, and saves the raw live responses next to it.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

import config

# Cache off, here and in the MCP server (mcp_client forwards AI201_*).
# Set before anything calls the model.
config.CACHE_ENABLED = False
os.environ["AI201_CACHE"] = "0"

import generate  # noqa: E402
import runlog  # noqa: E402
from agent import run_agent  # noqa: E402
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe  # noqa: E402

LIVE_URL = os.getenv(
    "FITFINDR_URL",
    "https://ai201-project2-fitfindr-starter-v2026-tewx.onrender.com",
).rstrip("/")

TRIALS = 3

# Criterion 4's ten requests. The mix is deliberate: four complete normally,
# three are rescued by the re-plan, two stop with nothing found, and one is
# malformed. Every one of them must leave a record.
C4_REQUESTS = [
    {"label": "malformed (no query)", "body": {}},
    {"label": "completes", "body": {"query": "vintage graphic tee under $30"}},
    {"label": "rescued (size)", "body": {"query": "90s track jacket in size XS"}},
    {"label": "stops", "body": {"query": "designer ballgown size XXS under $5"}},
    {"label": "completes", "body": {"query": "denim jacket under $50"}},
    {"label": "rescued (ceiling)", "body": {"query": "vintage graphic tee under $10"}},
    {"label": "rescued (size)", "body": {"query": "platform sneakers size 13"}},
    {"label": "stops", "body": {"query": "wedding tuxedo size 52 under $10"}},
    {"label": "completes", "body": {"query": "cargo pants under $30"}},
    {"label": "completes (empty wardrobe)",
     "body": {"query": "trainers size 8", "wardrobe": {"items": []}}},
]


def _evidence(session, extra=""):
    """A short, real line about what a trial produced."""
    return (
        f"error={session['error']!r} | warnings={session['warnings']} | "
        f"attempts={[(a['args'].get('size'), a['args'].get('max_price'), a['found']) for a in session['attempts']]} | "
        f"selected={(session['selected_item'] or {}).get('id')} | "
        f"fit_card={'yes' if session['fit_card'] else 'no'}{extra}"
    )


# ── criteria 1-3: the loop, run directly ─────────────────────────────────────

def criterion_1():
    """Size-only miss is rescued and the warning names the dropped size."""
    session = run_agent("90s track jacket in size XS", get_example_wardrobe())
    warnings = session["warnings"]
    ok = (
        session["error"] is None
        and bool(session["fit_card"])
        and any("XS" in w for w in warnings)
        and len(session["attempts"]) == 2
    )
    return ok, _evidence(session)


def criterion_2():
    """Ceiling miss is rescued at 1.5x and the warning names the new ceiling."""
    session = run_agent("vintage graphic tee under $10", get_example_wardrobe())
    warnings = session["warnings"]
    ok = (
        session["error"] is None
        and bool(session["fit_card"])
        and any("$15" in w for w in warnings)
        and len(session["attempts"]) == 2
    )
    return ok, _evidence(session)


def criterion_3():
    """Nothing matches at any relaxation: exactly three searches, then stop."""
    before = generate.call_count()
    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())
    calls = generate.call_count() - before
    ok = (
        len(session["attempts"]) == 3
        and session["error"] is not None
        and session["outfit_suggestion"] is None
        and session["fit_card"] is None
        and calls == 0
    )
    return ok, _evidence(session, extra=f" | model_calls={calls}")


# ── criterion 4: every request leaves a complete record ──────────────────────

def criterion_4():
    """
    Ten requests through the real Flask handler. Counts the records the system
    actually wrote, by reading results/runlog.jsonl back before and after.
    """
    from serve import app

    path = runlog.LOG_FILE
    before = sum(1 for _ in open(path, encoding="utf-8")) if path.exists() else 0

    client = app.test_client()
    statuses = []
    for request in C4_REQUESTS:
        response = client.post("/ask", json=request["body"])
        statuses.append((request["label"], response.status_code))

    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    written = rows[before:]
    complete = [r for r in written if all(r.get(f, "__missing__") != "__missing__"
                                          for f in runlog.FIELDS)]

    detail = (
        f"requests={len(C4_REQUESTS)} records_written={len(written)} "
        f"records_complete={len(complete)}\n"
        + "\n".join(f"    {label:<28} HTTP {code}" for label, code in statuses)
    )
    return len(complete), len(C4_REQUESTS), detail


# ── criterion 5: the deployed service ────────────────────────────────────────

def live_post(query, timeout=200):
    """One POST to the deployed service. Returns (seconds, status, body)."""
    data = json.dumps({"query": query}).encode()
    request = urllib.request.Request(
        f"{LIVE_URL}/ask", data=data,
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
            return time.perf_counter() - started, response.status, body
    except urllib.error.HTTPError as exc:
        return time.perf_counter() - started, exc.code, {"error": exc.read()[:200].decode("utf-8", "replace")}
    except Exception as exc:  # noqa: BLE001 — a dead service is a result
        return time.perf_counter() - started, None, {"error": f"{type(exc).__name__}: {exc}"}


def criterion_5_trial(query="90s track jacket in size XS"):
    seconds, status, body = live_post(query)
    warnings = body.get("warnings") or []
    ok = (
        status == 200
        and body.get("error") is None
        and bool(body.get("fit_card"))
        and any("XS" in w for w in warnings)
        and seconds < 20
    )
    detail = (
        f"HTTP {status} in {seconds:.2f}s | warnings={warnings} | "
        f"selected={(body.get('selected_item') or {}).get('id')} | "
        f"fit_card={'yes' if body.get('fit_card') else 'no'}"
    )
    return ok, detail, seconds, body


# ── driver ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run the capstone criteria.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--trials", type=int, default=TRIALS)
    parser.add_argument("--skip-live", action="store_true")
    args = parser.parse_args()

    print(f"Cache is OFF. {args.runs} runs, {args.trials} trials per criterion.\n", flush=True)

    results = {n: [] for n in (1, 2, 3, 4, 5)}
    evidence = {n: [] for n in (1, 2, 3, 4, 5)}
    cold = None
    live_bodies = []

    for run in range(1, args.runs + 1):
        print(f"── Run {run} " + "─" * 50, flush=True)

        for number, func in ((1, criterion_1), (2, criterion_2), (3, criterion_3)):
            passed = 0
            for trial in range(1, args.trials + 1):
                ok, detail = func()
                passed += 1 if ok else 0
                evidence[number].append(f"run {run} trial {trial}: {'PASS' if ok else 'FAIL'} — {detail}")
                print(f"  c{number} trial {trial}: {'PASS' if ok else 'FAIL'}", flush=True)
            results[number].append((passed, args.trials))

        passed, total, detail = criterion_4()
        results[4].append((passed, total))
        evidence[4].append(f"run {run}: {passed}/{total} complete\n{detail}")
        print(f"  c4: {passed}/{total} records complete", flush=True)

        if args.skip_live:
            results[5].append((None, args.trials))
            continue

        if cold is None:
            # Wake the instance. Recorded separately — never counted as a trial.
            seconds, status, _ = live_post("90s track jacket in size XS")
            cold = (seconds, status)
            evidence[5].append(
                f"COLD wake request (not a trial): HTTP {status} in {seconds:.2f}s"
            )
            print(f"  c5 cold wake: HTTP {status} in {seconds:.2f}s", flush=True)

        passed = 0
        for trial in range(1, args.trials + 1):
            ok, detail, seconds, body = criterion_5_trial()
            passed += 1 if ok else 0
            live_bodies.append({"run": run, "trial": trial, "seconds": seconds, "body": body})
            evidence[5].append(f"run {run} trial {trial}: {'PASS' if ok else 'FAIL'} — {detail}")
            print(f"  c5 trial {trial}: {'PASS' if ok else 'FAIL'} ({seconds:.2f}s)", flush=True)
        results[5].append((passed, args.trials))

        print(flush=True)

    write_report(results, evidence, cold, live_bodies, args)


TITLES = {
    1: ("A size-only miss is rescued, and says what it gave up", "3 of 3"),
    2: ("A ceiling miss is rescued at 1.5x, and names the new ceiling", "3 of 3"),
    3: ("An impossible query stops after exactly 3 searches, before any model call", "3 of 3"),
    4: ("Every /ask request writes a complete log record", "10 of 10"),
    5: ("The rescue works on the deployed service, warm under 20s", "3 of 3"),
}


def write_report(results, evidence, cold, live_bodies, args):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    path = config.RESULTS_DIR / f"capstone_run_{stamp}.md"

    if live_bodies:
        raw = config.RESULTS_DIR / "live" / f"capstone_live_{stamp}.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(json.dumps(live_bodies, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Capstone run log — {dt.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "- Produced by: `run_capstone_eval.py::main`",
        "- Loop: `agent.py::run_agent` · HTTP: `serve.py::ask` · log: `runlog.py::write`",
        f"- {args.runs} runs, {args.trials} trials per criterion",
        "- Caching OFF in this process and in the MCP server it starts (criteria 1-4)",
        "- The DEPLOYED service (criterion 5) has its own cache, which this process"
        " cannot turn off — it is a different machine and never sees AI201_CACHE",
        f"- Temperature: {config.TEMPERATURE}",
        f"- Deployed service: {LIVE_URL}",
        "",
        "| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |",
        "|---|---|---|---|---|---|",
    ]

    for number in (1, 2, 3, 4, 5):
        title, target = TITLES[number]
        cells = []
        met = True
        for passed, total in results[number]:
            if passed is None:
                cells.append("skipped")
                met = False
            else:
                cells.append(f"{passed}/{total}")
                if passed != total:
                    met = False
        while len(cells) < 3:
            cells.append("—")
        verdict = "MET" if met else "MISSED"
        lines.append(f"| {number}. {title} | {target} | {cells[0]} | {cells[1]} | {cells[2]} | **{verdict}** |")

    if cold:
        lines += [
            "",
            f"Cold start, measured once and kept out of the table: HTTP {cold[1]} in "
            f"**{cold[0]:.2f}s**. Criterion 5 is about warm requests, and a cold wake "
            "happens at Render's edge before the app process exists, so it cannot be "
            "measured from inside the app at all.",
        ]

    lines += ["", "---", "", "## Real output, per criterion", ""]
    for number in (1, 2, 3, 4, 5):
        title, _ = TITLES[number]
        produced = {
            1: "`agent.py::run_agent`, via `run_capstone_eval.py::criterion_1`",
            2: "`agent.py::run_agent`, via `run_capstone_eval.py::criterion_2`",
            3: "`agent.py::run_agent`, via `run_capstone_eval.py::criterion_3`",
            4: "`serve.py::ask` writing through `runlog.py::write`, via `run_capstone_eval.py::criterion_4`",
            5: f"`serve.py::ask` on {LIVE_URL}, via `run_capstone_eval.py::criterion_5_trial`",
        }[number]
        lines += [f"### Criterion {number}. {title}", "", f"Produced by {produced}.", "", "```"]
        lines += evidence[number] or ["(no output — skipped)"]
        lines += ["```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path.relative_to(config.ROOT)}")
    print(generate.usage())


if __name__ == "__main__":
    main()
