#!/usr/bin/env python3
"""
Pull the deployed FitFindr service's logs from Render into results/live/.

    python export_render_logs.py                   last 7 days
    python export_render_logs.py --since 2026-11-10T00:00:00Z

Needs RENDER_API_KEY and RENDER_SERVICE_ID in .env (see .env.example). The key
is read from the environment and never printed or written to a file.

Writes two files, both committed to the repo:

  results/live/render_logs.jsonl    every log line Render returned, as-is
  results/live/render_runlog.jsonl  just the [runlog] records the service wrote,
                                    one JSON object per line, same fields as
                                    results/runlog.jsonl

Uses only the standard library, so it adds nothing to requirements.txt.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config  # loads .env

API = "https://api.render.com/v1"
OUT = config.RESULTS_DIR / "live"


def get_json(path: str, params: dict | None, token: str) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        sys.exit(f"Render API returned HTTP {exc.code} for {path}: {body}\n"
                 "Check RENDER_API_KEY and RENDER_SERVICE_ID in .env.")


def service_owner(service_id: str, token: str) -> tuple[str, str]:
    """The workspace (owner) the service belongs to. The logs API needs it."""
    svc = get_json(f"/services/{service_id}", None, token)
    return svc["ownerId"], svc.get("name", service_id)


def fetch_all_logs(owner_id: str, service_id: str, start: str, end: str, token: str) -> list[dict]:
    """Walk every page. Render returns hasMore plus the next window to ask for."""
    logs: list[dict] = []
    while True:
        page = get_json("/logs", {
            "ownerId": owner_id,
            "resource": service_id,
            "startTime": start,
            "endTime": end,
            "direction": "forward",
            "limit": 100,
        }, token)
        logs.extend(page.get("logs", []))
        if not page.get("hasMore"):
            return logs
        start, end = page["nextStartTime"], page["nextEndTime"]


def runlog_records(logs: list[dict]) -> list[dict]:
    """The service prints each record as '[runlog] {json}'. Pull those out."""
    records = []
    for entry in logs:
        message = entry.get("message", "")
        marker = message.find("[runlog] ")
        if marker == -1:
            continue
        try:
            records.append(json.loads(message[marker + len("[runlog] "):]))
        except json.JSONDecodeError:
            # A line that starts like a record but isn't one is kept in the raw
            # file and skipped here, rather than hidden or guessed at.
            continue
    return records


def main():
    parser = argparse.ArgumentParser(description="Export the Render service's logs.")
    parser.add_argument("--since", help="start time, ISO 8601 UTC, e.g. 2026-11-10T00:00:00Z")
    args = parser.parse_args()

    import os
    token = os.getenv("RENDER_API_KEY", "").strip()
    service_id = os.getenv("RENDER_SERVICE_ID", "").strip()
    if not token or not service_id or "your_" in token or "your_" in service_id:
        sys.exit("RENDER_API_KEY and RENDER_SERVICE_ID must be set in .env.")

    now = datetime.now(timezone.utc)
    start = args.since or (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    owner_id, name = service_owner(service_id, token)
    logs = fetch_all_logs(owner_id, service_id, start, end, token)
    records = runlog_records(logs)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "render_logs.jsonl", "w", encoding="utf-8") as f:
        for entry in logs:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with open(OUT / "render_runlog.jsonl", "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"service: {name}")
    print(f"window:  {start} to {end}")
    print(f"log lines: {len(logs)}  |  [runlog] records: {len(records)}")
    print(f"wrote {(OUT / 'render_logs.jsonl').relative_to(config.ROOT)}")
    print(f"wrote {(OUT / 'render_runlog.jsonl').relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
