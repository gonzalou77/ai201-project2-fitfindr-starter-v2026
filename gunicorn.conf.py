"""
Gunicorn settings for running serve.py on a host.

The start command stays exactly `gunicorn serve:app` — the one serve.py and
RUNNING.md both name. Gunicorn loads this file by itself from the working
directory, so everything that would otherwise be a command-line flag lives
here instead, where it can be read and reviewed in the repo, and where it
can't be lost to a host that doesn't expand $PORT inside a start command.

Nothing here changes the agent. serve.py is still the only web entry point,
and run_agent() is still the same one the CLI calls.
"""

import os

# The host tells us which port to listen on. 0.0.0.0 because the request
# arrives from outside the container — bind 127.0.0.1 and only the container
# itself can connect, which from a browser looks exactly like a broken app.
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# ONE sync worker. Three separate reasons, any one of which is enough on its own:
#
#   • An async worker breaks every MCP call. `mcp_client.call_tool` wraps
#     `asyncio.run()`, which refuses to start when an event loop is already
#     running. This is the warning in serve.py, enforced here rather than
#     left to whoever types the start command: never gevent, never eventlet.
#   • serve.py's `_one_at_a_time` lock is a module global, so it only holds
#     within one process. A second worker would run a second agent alongside
#     it and defeat the lock entirely.
#   • generate.py's rate-limit window and call counter are module globals too.
#     Two workers means two counters, each believing it has the whole 15
#     requests a minute, against one shared provider quota.
worker_class = "sync"
workers = 1
threads = 1

# One request is two model calls plus two MCP subprocess spawns, and it may
# also sit in a rate-limit pause — generate.py sleeps up to ~60s to stay
# inside the free tier's 15 requests a minute, and retries a 429 up to
# MAX_RETRIES times. Gunicorn's default 30s timeout kills the worker in the
# middle of that, and the caller gets a 502 for a request that was working.
timeout = 180
graceful_timeout = 30
keepalive = 5

# Send gunicorn's own logs to the host's log stream. This is the server's
# request line and tracebacks — it is NOT the structured logging and timing
# that unit 9 asks you to write inside serve.py yourself.
accesslog = "-"
errorlog = "-"
