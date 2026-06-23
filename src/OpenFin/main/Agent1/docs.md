# Agent 1 — Directory Documentation

## Key Objective
Orchestrates the full financial analysis pipeline. Agent 1 is the central coordinator: it watches for uploaded data files, then sequentially runs all five subagents to process data, generate reports, research insights, identify financial issues, and produce professional PDFs. Agent 1 makes no LLM calls — it only initiates subagents.

## Key Initiating Function / Call Process

```
main.run_once()  [single run]
  ├─ _scan_new_files()            → Check uploaded-data/ for unprocessed files
  ├─ step_run_subagent1()         → Process all CSVs → filtered-data/
  ├─ step_start_subagent5()       → Start observation of base-gens/insight-gens
  ├─ step_run_parallel_agents()   → ThreadPoolExecutor:
  │    ├─ Thread 1: subAgent2.run() → base-gens/*.json
  │    ├─ Thread 2: subAgent3.run() → insight-gens/*.json
  │    └─ Thread 3: subAgent4.run() → insight-gens/*.json
  ├─ step_run_subagent5()         → Convert JSONs → PDFs
  ├─ step_end_subagent5()         → End observation
  └─ step_verify_results()        → Count outputs, show statuses

main.watch_and_run()  [continuous mode]
  └─ Loop: poll uploaded-data/ → run_once() on new files
```

## Tools / Algorithms Used

- **concurrent.futures.ThreadPoolExecutor**: Parallel execution of subAgents 2, 3, 4.
- **File polling**: Scans `uploaded-data/` for new files and `uploaded_files.json` register for deduplication.
- **Activity log monitoring**: Reads each subagent's `log.txt` to check for "idle" status.
- **Queue/register**: `uploaded_files.json` tracks processed files to avoid re-processing.

## Major Files

| File | Purpose |
|------|---------|
| `main.py` | Orchestrator: watch → dispatch → verify |
| `uploaded_files.json` | Register of processed file names (auto-generated) |
| `log.txt` | Activity log ("watching for uploads", "running subAgent 1", "idle") |

## Major Functions

| Object | Parameters | Use |
|--------|------------|-----|
| `run_once()` | None | Run full pipeline on any available files; exits after one pass |
| `run_pipeline()` | None | Core pipeline: subAgent1 → subAgent5 start → parallel 2/3/4 → subAgent5 → end |
| `watch_and_run(poll_interval, max_iterations)` | `poll_interval: float, max_iterations: int` | Continuous watch loop; runs pipeline on each batch of new files |
| `step_run_subagent1()` | None | Import and run subAgent1.process_all(); mark processed files |
| `step_start_subagent5()` | None | Call subAgent5.start_observation() |
| `step_run_parallel_agents()` | None | Execute subAgents 2, 3, 4 in thread pool with heuristic mode |
| `step_run_subagent5()` | None | Call subAgent5.run() to convert JSONs to PDFs |
| `step_end_subagent5()` | None | Call subAgent5.end_observation() |
| `step_verify_results()` | None | Count files in base-gens, insight-gens, base-reports, insights |
| `_scan_new_files()` | None | Find unprocessed files in uploaded-data/ |
| `_wait_for_subagent_idle(dir, label, timeout)` | `dir: str, label: str, timeout: int` | Poll subagent log.txt until idle or timeout |
| `_read_subagent_log(dir)` | `dir: str` | Read subagent's log.txt content |
| `_set_activity(status)` | `status: str` | Write current activity to log.txt (overwrite) |
| `_load_register()` | None | Load processed files set from uploaded_files.json |
| `_save_register(processed)` | `processed: set` | Save processed files set to uploaded_files.json |
| `_mark_processed(filename)` | `filename: str` | Add filename to register and persist |

## Pipeline Flow

```
Uploaded CSVs → main/data/uploaded-data/
  │
  ▼
subAgent1 (process_all)
  │  → Load, analyze, calculate metrics
  │  → Save JSON to main/data/filtered-data/
  │  → Delete source CSVs
  │  → log.txt: "idle"
  ▼
subAgent5 (start_observation)
  │  → log.txt: "idle"
  ▼
┌─ subAgent2 (run) ───────────────────┐
│  → Load filtered-data/              │
│  → Identify + generate reports      │
│  → Save to main/Agent1/base-gens/   │
│  → log.txt: "idle"                  │
├─ subAgent3 (run) ───────────────────┤  (parallel)
│  → Load filtered-data/              │
│  → Research + generate insights     │
│  → Save to main/Agent1/insight-gens/│
│  → log.txt: "idle"                  │
├─ subAgent4 (run) ───────────────────┤
│  → Load filtered-data/              │
│  → Detect issues + generate reports │
│  → Save to main/Agent1/insight-gens/│
│  → log.txt: "idle"                  │
└─────────────────────────────────────┘
  ▼
subAgent5 (run)
  │  → Load JSONs from base-gens/ and insight-gens/
  │  → Convert to B&W PDFs
  │  → Save to main/reports/base-reports/ and main/reports/insights/
  │  → log.txt: "idle"
  ▼
subAgent5 (end_observation)
  │  → log.txt: "idle"
  ▼
Pipeline complete — all reports and PDFs generated
```

## Activity Log (log.txt)

Agent 1 maintains its own `log.txt` with current activity only:
- "watching for uploads" — polling for new files
- "running subAgent 1" — data processing
- "starting subAgent 5 observation" — initializing PDF watcher
- "running subAgents 2, 3, 4 in parallel" — parallel analysis
- "running subAgent 5" — PDF generation
- "ending subAgent 5 observation" — cleanup
- "idle" — waiting or complete
