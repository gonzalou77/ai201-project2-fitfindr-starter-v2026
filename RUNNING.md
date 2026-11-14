# Running FitFindr

Everything about how the starter works and how to use it.

---

## Before your first class

Setup happens **before class**. The [environment setup page](../pages/ide_setup)
has the per-operating-system commands and the exact versions.

**Same API key you set up in unit 1.** Nothing new to sign up for. There is one
new package — the MCP SDK, for unit 4 — and it installs with everything else.

From inside this repo after you've forked and cloned it:

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your key into .env
python test.py
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env         # then paste your key into .env
python test.py
```

**You're ready when `python test.py` passes.**

If it doesn't and you've made one honest attempt at the error, post the
**whole** output in the help channel.

> Activate the virtual environment every time you open a new terminal. You
> should see `(.venv)` at the start of your prompt.

---

## Your first five minutes

Start with the data. Your tools will only be as good as your understanding of
what they're reading, and ten minutes here saves an hour of confused debugging.

```bash
python app.py fields                    # what a listing and a wardrobe item hold
python app.py listings --full -n 6      # read six listings all the way through
python app.py examples                  # queries worth trying
python app.py ask 'vintage graphic tee under $30'
```

> **Quote your queries with single quotes**, on every operating system. In
> PowerShell, `"vintage graphic tee under $30"` in double quotes silently
> becomes `vintage graphic tee under ` — PowerShell reads `$30` as a variable
> and substitutes nothing. You get results with no price ceiling and no error
> saying so. Single quotes are literal in PowerShell, bash and zsh alike.

That last one runs the loop. All three tools are stubs, so it will tell you the
loop isn't built yet. **That's the correct starting position** — it runs, and it
does nothing.

---

## Every command

| Command | What it does |
|---|---|
| `python test.py` | Checks your environment. Run it whenever something feels off |
| `python app.py fields` | The fields a listing and a wardrobe item have — **Milestone 1** |
| `python app.py listings` | Browse the data. `--full` for whole records, `-n` for how many |
| `python app.py examples` | Queries worth trying, including one that matches nothing |
| `python app.py ask '...'` | Run the agent on one query — **single quotes** |
| `python app.py ask` | Keep asking until you press Enter on an empty line |
| `python agent.py` | Runs both example paths — one that matches, one that can't |
| `python mcp_server.py` | Starts your MCP server — **unit 4** |
| `python mcp_client.py` | Asks the server what it offers — **unit 4** |
| `python run_eval.py --label before` | Runs every scenario five times and writes the run log — **unit 4** |
| `python serve.py` | Serves the agent over HTTP instead of exiting — **unit 9** |

Useful flags on `ask`:

| Flag | What it does |
|---|---|
| `--trace` | Print the loop step by step, once you've added the trace calls |
| `--empty-wardrobe` | Run as a user with nothing saved — one of unit 4's failure modes |

---

## Which command goes with which milestone

### Unit 3 — the build

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Read the data, run the starter | `app.py fields`, `app.py listings --full`, `app.py ask` |
| 2 | Spec your three tools | README, **Tool Inventory** |
| 3 | Write your acceptance criteria | `criteria.md` |
| 4 | Build the three tools | `tools.py`, tested one at a time from a terminal |
| 5 | Wire the loop and the state | `agent.py::run_agent` |
| 6 | Write it up | README |

### Unit 4 — the test

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Move one tool onto MCP | `mcp_server.py`, then `mcp_client.call_tool` in `run_agent` |
| 2 | Break it on purpose, then trace it | `trace.py`, `app.py ask --trace` |
| 3 | Run your test | `scenarios.py`, then `run_eval.py --label before` |
| 4 | Call each criterion, diagnose the misses | README |
| 5 | Fix one thing and re-run | `run_eval.py --label after` |
| 6 | Say what's still broken | README |

---

## Running it somewhere else — **unit 9**

Everything above exits when the command finishes. A host has nothing to keep
running, so before you can deploy this you need something that stays up.
`serve.py` is that: the same `run_agent()`, behind two HTTP routes.

On your machine:

```bash
python serve.py
curl -X POST http://localhost:5000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query": "vintage graphic tee under $30"}'
```

On a host, the start command is:

```bash
gunicorn serve:app
```

| Thing | What it means |
|---|---|
| `PORT` | The host tells your app which port to listen on by setting this. Both `serve.py` and `gunicorn` read it, and `serve.py` falls back to `5000` on your machine. Don't hard-code a port |
| `POST /ask` | `{"query": "...", "wardrobe": {...}}` — wardrobe optional. Returns the session dict, `error` and all |
| `GET /health` | Says `ok` if the app is awake |
| It answers one request at a time | On purpose. A second request waits for the first to finish, and prints `[serve] another request is still running` while it waits. An MCP tool call starts a whole second Python process, and the free tier's 512 MB has no room for two of those at once — and `generate.py`'s rate-limit counting assumes one caller. The reasoning is written out in `serve.py` |
| `gunicorn serve:app`, exactly | Not `-k gevent`, not `-k eventlet`, not wrapped for uvicorn. `mcp_client.call_tool` uses `asyncio.run()`, which won't start inside a running event loop, so an async worker breaks **every** MCP call — and only once you've deployed it |
| The first request is slow | The free tier puts your app to sleep after about fifteen minutes of nothing. The next request wakes it up and waits for it — around a minute. Not a bug, and worth knowing before you demo it |

`serve.py` ships with **no logging and no timing in it**, on purpose. You add
that yourself in the follow-along, before you deploy — instrumenting first is
the point of the session.

---

## Where everything lives

| File | What it does |
|---|---|
| `config.py` | Every setting worth changing — **TEMPERATURE and the cache are at the top** |
| `tools.py` | Your three tools. **Stubs — you build these** |
| `agent.py` | The planning loop and the session. **Stub — you build this** |
| `generate.py` | The only thing that calls out to a service. Handles pacing and quota |
| `trace.py` | The trace helper, and the loop's stop condition |
| `app.py` | The command line |
| `serve.py` | The same agent over HTTP, for deploying — **unit 9** |
| `mcp_server.py` | Your MCP server — **unit 4, you register the tool** |
| `mcp_client.py` | Calling an MCP tool from your agent. Given to you |
| `scenarios.py` | What your test runs. **You fill this in** |
| `run_eval.py` | Runs the scenarios repeatedly and writes the run log |
| `criteria.md` | Your five acceptance criteria. **You fill this in** |
| `data/` | 40 listings and the wardrobe schema |
| `utils/data_loader.py` | Loading the data. Use this rather than reading the files yourself |
| `results/` | Run logs. **Commit these** — they're your evidence |

---

## The two settings people go looking for

Both are at the top of `config.py`, and the brief points at them by name.

If your fit cards come out **word-for-word identical** every time, it is one of:

- **`CACHE_ENABLED`** — while you build, identical prompts reuse the answer
  already received. That's deliberate; it makes debugging free. `run_eval.py`
  turns it off automatically.
- **`TEMPERATURE`** — at `0.0` the model gives you the same words every time.
  It ships at `0.9`.

---

## About rate limits

**This is the heaviest pair in the course for call volume.** Two of your three
tools call the model, so one agent run is several requests, and a few runs back
to back while debugging can cross the per-minute limit.

`generate.py` handles it:

- **It paces itself** and says when it's waiting. **A pause is the starter
  doing its job, not a bug.**
- **It reuses answers** to prompts already sent, while you build.
- **It stops** if a session makes an unreasonable number of calls, rather than
  draining your day's allowance. For an agent, that usually means a loop isn't
  ending — look for that before raising the number.
- **It counts your calls** and prints the total when you exit.

`config.MAX_ITERATIONS` is the loop's own stop condition. Your loop this unit
is short enough that you may never hit it. Keep it — a missing stop condition
is the most common architectural failure in production agents.

---

## When something goes wrong

| What you see | What it means |
|---|---|
| `The planning loop isn't built yet` | Correct, at the start. That's the TODO in `agent.py` |
| `No GEMINI_API_KEY found` | No `.env`, or the key wasn't pasted in. On Windows check it didn't save as `.env.txt` |
| A message saying the model couldn't be reached | Usually a bad key. This is also **exactly what unit 4 Milestone 2 asks you to trigger on purpose** |
| `[rate limit] ... Waiting 34s` | Working as intended. Leave it |
| `[serve] another request is still running` | Also working as intended. `serve.py` answers one request at a time; yours is queued behind one that's mid-run |
| `QuotaGuard: This session has made 300 requests` | A loop isn't ending. Find it before raising the budget |
| `The loop ran 11 times, past MAX_ITERATIONS` | Same thing, caught earlier |
| `The server doesn't offer a tool called '...'` | Nothing registered in `mcp_server.py` yet, or the name doesn't match |
| MCP returns a string where you expected a list | You're not going through `mcp_client.call_tool`, which unwraps it |
| Fit cards identical every run | `CACHE_ENABLED` or `TEMPERATURE`. See above |
| `--trace` prints nothing | You haven't added `trace.step()` calls yet — unit 4, Milestone 2 |
| `IncompleteFieldDefinitionWarning: Field 'lifespan'` | Harmless noise from the MCP library's dependencies. Not your code, not an error. Ignore it |
| A price ceiling you typed is being ignored | You used double quotes in PowerShell. `$30` vanished. Use single quotes |
| `UnicodeEncodeError: 'charmap' codec can't encode` | Shouldn't happen — `config.py` sets the console to UTF-8. If you see it, you're running a file that doesn't import `config` |

Still stuck after one honest attempt? Post in the help channel with the full
error, what you ran, and what you expected.

---

## A note on committing

At least four new commits in unit 3, at least four more in unit 4. Your commit
history is what shows your criteria existed before your results did.

**Do not delete and recreate this repository.** You submit the same URL both
units.

`results/` is deliberately **not** in `.gitignore`.

---

## Capstone run path

Two ways to run the capstone extension: the hosted service, which needs nothing
installed, and the local command line, which writes a log record for every run.

### The hosted service

**https://ai201-project2-fitfindr-starter-v2026-tewx.onrender.com**

- `GET /` — a one-page description of the service.
- `GET /health` — returns `{"ok": true}`.
- `POST /ask` — runs the agent.

```bash
curl -s -X POST https://ai201-project2-fitfindr-starter-v2026-tewx.onrender.com/ask   -H 'Content-Type: application/json'   -d '{"query": "vintage graphic tee under $30"}'
```

It runs on Render's free plan, so it sleeps after about 15 minutes idle. The
first request after a pause takes roughly **30 seconds** while the instance
wakes; a warm request takes about **20 seconds**. Neither is an error. Wait
rather than retrying — a retry during a wake just starts the clock again.

**How it got there.** A Render Blueprint built from `render.yaml` in this repo,
with the GitHub repository connected so that a push to `main` triggers a build.
Four files carry the configuration:

- **`render.yaml`** — `runtime: python`, `plan: free`, build command
  `pip install -r requirements.txt`, start command
  `gunicorn -c gunicorn.conf.py serve:app`, health check path `/health`.
- **`.python-version`** — pins **3.11**. Render's default is 3.14, which
  several packages in `requirements.txt` do not support. Without this pin the
  build fails.
- **`gunicorn.conf.py`** — binds `0.0.0.0:$PORT` (Render assigns the port at
  runtime), one sync worker, and `timeout = 180`. Gunicorn's 30-second default
  would kill a request that was working correctly, since an agent run takes
  5–20 seconds plus any rate-limit pause.
- **`GEMINI_API_KEY`** — set in the Render dashboard, never in the repo.
  `render.yaml` declares it with `sync: false`, so no value is ever committed.

One thing `render.yaml` will **not** do for you: adding an environment variable
to the Blueprint does not apply it to a service that already exists. Render
syncs `envVars` when the service is first created. On an existing service, set
the variable in the dashboard (or via the API) and then trigger a deploy — a
push on its own rebuilds the code and leaves the variable behind. This cost a
whole set of measurements; see "The Improvement" in the README.

### Running it locally, with logs

This path runs from the command line on your own machine, and every run writes
a record to `results/runlog.jsonl`.

**What you need**

- Python **3.11, 3.12, or 3.13.** Not 3.14. Several packages in `requirements.txt`
  don't support it yet.
- A Gemini API key, from https://aistudio.google.com. Put it in a file named
  `.env` in the repo root, as `GEMINI_API_KEY=...`. `.env` is git-ignored, so the
  key never reaches GitHub.

**Setup, from a fresh clone**

**macOS / Linux**

```bash
git clone https://github.com/gonzalou77/ai201-project2-fitfindr-starter-v2026.git
cd ai201-project2-fitfindr-starter-v2026
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# open .env and set GEMINI_API_KEY to your key
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/gonzalou77/ai201-project2-fitfindr-starter-v2026.git
cd ai201-project2-fitfindr-starter-v2026
py -3.11 -m venv .venv               # the py launcher picks 3.11; plain "python" may be another version
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# open .env and set GEMINI_API_KEY to your key
```

If `py -3.11` says no such version, install Python 3.11 from python.org first.
The `pip` notice about a newer pip version is harmless.

**Run one query**

```bash
python app.py ask 'vintage graphic tee under $30'
```

Use single quotes. In PowerShell, `"under $30"` in double quotes silently loses
the price. Add `--trace` to see each step of the loop, and `--empty-wardrobe` to
run with no saved wardrobe.

The answer prints to the terminal, and one record is appended to
`results/runlog.jsonl`. Each line is one JSON object. Read the last one with:

```bash
tail -n 1 results/runlog.jsonl
```

**Turn the cache off**

By default the model's answers are cached on disk, so a repeated query costs
nothing and says nothing about the model. To get a real answer every time:

```bash
AI201_CACHE=0 python app.py ask 'vintage graphic tee under $30'      # macOS / Linux
$env:AI201_CACHE="0"; python app.py ask 'vintage graphic tee under $30'   # PowerShell
```

**Measure what a run costs**

```bash
python cost.py                  # ten runs, cache off, prints tokens and seconds per run
```

The method is written at the top of `cost.py`.

**Run the failure path on purpose**

```bash
GEMINI_API_KEY=not-a-real-key python app.py ask 'vintage graphic tee under $30'
```

It prints that the model couldn't be reached, and it still writes a record with
`outcome` set to `stopped` and the reason in `error`.

**If something breaks**

| You see | Likely cause |
|---|---|
| `ModuleNotFoundError` | the venv isn't active. Run the activate line again, then `pip install -r requirements.txt` |
| "The model couldn't be reached" with `GEMINI_API_KEY` in the message | the key in `.env` is missing or wrong. Check for spaces or quotes around it |
| Python 3.14 errors during `pip install` | you're on 3.14. Install 3.11 and make a new venv |
| A query finds nothing that obviously should match | check the query against `python app.py examples`, and the listings with `python app.py listings --full` |
| `results/` missing | created on first run. If it still isn't there, the folder is not writable |
