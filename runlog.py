"""
One structured record per /ask request.

Every request writes exactly one JSON line, in two places:

  • stdout — what a host keeps in its log stream. On Render the disk is wiped
    when the service sleeps, so this is the copy that survives a while.
  • results/runlog.jsonl — a local copy, when the disk allows it.

The README is the copy that lasts. Paste the entries there the session you
produce them; the file in the repo is the one that counts.

Fields (all present on every record, null when not applicable):

  ts              UTC timestamp, ISO 8601, when the request arrived
  request_id      short id, so a line can be matched to a response
  query           what came in
  wardrobe        "example", "custom", or "empty"
  http_status     what was sent back
  outcome         "completed", "rescued", "stopped", "bad_request", "crashed"
  error           the session's error, or the failure text, or null
  selected_id     listing id that reached suggest_outfit, or null
  selected_title  its title, or null
  searches        how many search_listings calls were made (criterion 3 counts these)
  warnings        how many warnings the run recorded (rescues show up here)
  model_calls     model calls made in THIS process during the request
  prompt_tokens   tokens sent, this process only
  output_tokens   tokens returned, this process only
  wait_ms         time spent queued behind another request
  duration_ms     total time inside the handler, warm or cold as it happened

Known gap, stated here so nobody reads it as a total: calls made inside the
MCP server (create_fit_card) run in another process, so model_calls and tokens
leave out the fit card. Cost numbers built from these fields are a lower bound
until that is fixed.
"""

import json
import sys
import time
import uuid
from datetime import datetime, timezone

import config

LOG_FILE = config.RESULTS_DIR / "runlog.jsonl"

FIELDS = (
    "ts", "request_id", "query", "wardrobe", "http_status", "outcome", "error",
    "selected_id", "selected_title", "searches", "warnings", "model_calls",
    "prompt_tokens", "output_tokens", "wait_ms", "duration_ms",
)


def new_request_id() -> str:
    return uuid.uuid4().hex[:8]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def outcome_of(session: dict | None, failure: str | None) -> str:
    """Name what happened in one word, from the session the loop returned."""
    if failure is not None:
        return "crashed"
    if session is None:
        return "bad_request"
    if session.get("error"):
        return "stopped"
    if session.get("warnings"):
        return "rescued"
    return "completed"


def write(record: dict) -> None:
    """
    Write one record. Logging must never break a request that already worked,
    so a failure to write is reported on stderr and otherwise ignored.
    """
    # Every field is present, even when empty. A missing key is the failure
    # criterion 4 is looking for, so the record is filled in before it leaves.
    complete = {field: record.get(field) for field in FIELDS}
    line = json.dumps(complete, ensure_ascii=False, default=str)
    print(f"[runlog] {line}", flush=True)
    try:
        config.RESULTS_DIR.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as exc:
        print(f"[runlog] could not write {LOG_FILE.name}: {exc}", file=sys.stderr, flush=True)
