# TaskGrid — Distributed Task Scheduler

A locally runnable distributed computation scheduler with three independent HTTP worker processes, load-aware task routing, SQLite persistence, heartbeat monitoring, automatic requeue and a polished operations dashboard.

## Windows / VS Code quick start

1. Install Python 3.11+ and VS Code.
2. Open this folder in VS Code. Open **Terminal > New Terminal** (PowerShell).
3. Run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Double-click `start_all.bat` in File Explorer (or run `cmd /c start_all.bat` in the terminal).
5. Visit http://127.0.0.1:5000 . The startup script opens the browser automatically.

If `py` is not recognized, use `python -m venv .venv` instead.

## Manual startup (4 VS Code terminals)

```powershell
.\.venv\Scripts\python.exe coordinator.py
.\.venv\Scripts\python.exe worker.py --id worker-1 --port 5001
.\.venv\Scripts\python.exe worker.py --id worker-2 --port 5002
.\.venv\Scripts\python.exe worker.py --id worker-3 --port 5003
```

Run each command in its **own terminal**. Dashboard: http://127.0.0.1:5000

## Failure recovery demo

1. Submit a `benchmark` task with `{"seconds":12}`.
2. Note which worker is running it in Recent Tasks.
3. Close that worker's terminal during execution.
4. After roughly 7–10 seconds the task is queued and assigned to another worker. It may finish on a different worker.
5. Check Activity Logs to see reassignment. Restart the closed worker by rerunning its command.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Architecture

Browser -> Flask coordinator (port 5000) -> least-loaded worker (ports 5001/5002/5003) -> result callback -> coordinator SQLite database. Workers heartbeat every 2 seconds; coordinator detects a missing heartbeat after 7 seconds. Worker tasks have a 25-second lease and a maximum of 3 automatic attempts. The coordinator persists tasks and event logs. Worker communication uses JSON/HTTP on loopback. The system is designed for a trusted local lab network only, not production deployment.

## Task API

`POST /api/tasks` JSON `{ "type": "prime", "payload": { "limit": 10000 } }`. Types: `prime`, `fibonacci`, `statistics`, `wordcount`, `benchmark`. `GET /api/state` shows tasks, workers, events.

## Known limitations

- Single coordinator is a single point of failure; task states are restored after restart.
- At-least-once execution: a failed worker's task can execute twice; use only idempotent computations.
- Worker registrations are in memory; restart workers after coordinator restart.
- No authentication or TLS; bind to loopback for local demonstration.
- Dashboard lists the latest 120 tasks; totals represent those displayed tasks.
- Work is capped by task limits and benchmark time.

## SDG mapping

SDG 9 — Industry, Innovation and Infrastructure. Demonstrates scalable scheduling and resilient computing infrastructure.
