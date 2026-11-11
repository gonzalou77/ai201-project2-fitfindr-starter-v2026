#!/usr/bin/env python3
"""
What one FitFindr run costs, measured.

    python cost.py                 ten runs of the default query, cache off
    python cost.py --runs 10 --query 'denim jacket under $50'

Each run is one real call through run_agent(), with the cache forced off so
nothing is answered from a previous run. Per run it measures:

  • suggest_outfit tokens — counted in this process, around the call.
  • create_fit_card tokens — the fit card runs inside the MCP server, a separate
    process, so its counts never reach this one. To measure them, the same
    function is called here, in-process, with the outfit and listing that run
    actually produced. That is a second model call per run, made only to
    count its tokens. It is measured, not estimated from the pricing page.
  • wall-clock seconds for the run_agent() call.

Every run is also written to results/runlog.jsonl by runlog.py, the same
record the CLI writes, so the cost runs are in the log too.

Prints one line per run, then the average. The per-run numbers go in the
README under What It Costs, with this method.
"""

import argparse
import os
import sys
import time

import config

# Cache off, for the whole process, and for the MCP server (it reads the same
# variable through mcp_client's forwarding). Set before anything calls the model.
config.CACHE_ENABLED = False
os.environ["AI201_CACHE"] = "0"

import generate  # noqa: E402
import runlog  # noqa: E402
from agent import run_agent  # noqa: E402
from tools import create_fit_card  # noqa: E402
from utils.data_loader import get_example_wardrobe  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Measure what one run costs.")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--query", default="vintage graphic tee under $30")
    args = parser.parse_args()

    rows = []
    for n in range(1, args.runs + 1):
        wardrobe = get_example_wardrobe()

        before = generate.token_counts()
        calls_before = generate.call_count()
        started = time.perf_counter()
        session = run_agent(args.query, wardrobe)
        seconds = time.perf_counter() - started
        after = generate.token_counts()
        suggest_tokens = after["total"] - before["total"]

        # The fit card, counted here, from the run's own inputs.
        card_tokens = 0
        if not session["error"] and session["outfit_suggestion"]:
            before_card = generate.token_counts()
            create_fit_card(session["outfit_suggestion"], session["selected_item"])
            card_tokens = generate.token_counts()["total"] - before_card["total"]

        row = {
            "run": n,
            "outcome": runlog.outcome_of(session, None),
            "suggest_tokens": suggest_tokens,
            "card_tokens": card_tokens,
            "total_tokens": suggest_tokens + card_tokens,
            "seconds": round(seconds, 2),
        }
        rows.append(row)
        print(
            f"run {n:2d}: {row['outcome']:<9} suggest {suggest_tokens:4d} + "
            f"card {card_tokens:4d} = {row['total_tokens']:4d} tokens, "
            f"{row['seconds']:.2f}s",
            flush=True,
        )

        # Same record the CLI writes, so the cost runs appear in the log.
        runlog.write({
            "ts": runlog.now_iso(),
            "request_id": runlog.new_request_id(),
            "query": args.query,
            "wardrobe": "example",
            "http_status": None,
            "outcome": row["outcome"],
            "error": session["error"],
            "selected_id": (session["selected_item"] or {}).get("id"),
            "selected_title": (session["selected_item"] or {}).get("title"),
            "searches": len(session["attempts"]),
            "warnings": len(session["warnings"]),
            "model_calls": generate.call_count() - calls_before,
            "prompt_tokens": after["prompt"] - before["prompt"],
            "output_tokens": after["output"] - before["output"],
            "wait_ms": 0,
            "duration_ms": round(seconds * 1000),
        })

    done = [r for r in rows if r["outcome"] in ("completed", "rescued")]
    if not done:
        print("\nNo run completed, so there is no cost to average.", file=sys.stderr)
        return
    avg = lambda key: sum(r[key] for r in done) / len(done)  # noqa: E731
    print(
        f"\naverage over {len(done)} completed runs: "
        f"suggest {avg('suggest_tokens'):.0f} + card {avg('card_tokens'):.0f} = "
        f"{avg('total_tokens'):.0f} tokens, {avg('seconds'):.2f}s"
    )


if __name__ == "__main__":
    main()
