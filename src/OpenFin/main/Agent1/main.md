# main.py

## Key Objective
Orchestrates the full Agent 1 pipeline: watches for uploaded data files, sequentially runs subAgent 1 for data processing, starts subAgent 5 observation, runs subAgents 2/3/4 in parallel for report/insight generation, runs subAgent 5 for PDF conversion, and verifies all outputs. No LLM calls — only subagent initiation and monitoring.

## Tools / Algorithms Used
- **concurrent.futures.ThreadPoolExecutor**: Parallel execution of three subagents (2, 3, 4) with max 3 workers.
- **File I/O polling**: Scans `data/uploaded-data/` for new CSV/XLSX files; deduplicates via `uploaded_files.json` register.
- **Activity log monitoring**: Reads each subagent's `log.txt` to detect "idle" status for sequencing.
- **Python module imports**: Directly imports and calls subagent `run()` functions (subAgent1–5).

## Key Objects

### `run_once() -> Dict`
- **Parameters**: None.
- **Use**: Run full pipeline once on any available files. Scans for new files, processes them, exits.

### `run_pipeline() -> Dict`
- **Parameters**: None.
- **Use**: Core pipeline sequence: subAgent1 → subAgent5 start → parallel 2/3/4 → subAgent5 → verify → idle.

### `watch_and_run(poll_interval: float = 5.0, max_iterations: int = 10)`
- **Parameters**: `poll_interval` - seconds between polls; `max_iterations` - max pipeline runs.
- **Use**: Continuous watch loop with keyboard interrupt handling. Runs pipeline on each batch.

### `step_run_subagent1() -> bool`
- **Parameters**: None.
- **Use**: Imports and calls subAgent1.process_all(). Marks processed files in register. Waits for idle.

### `step_start_subagent5()`
- **Parameters**: None.
- **Use**: Calls subAgent5.start_observation() to begin watching base-gens/insight-gens.

### `step_run_parallel_agents() -> Dict`
- **Parameters**: None.
- **Use**: Executes subAgents 2, 3, 4 in ThreadPoolExecutor with heuristic mode (no API required). Returns per-agent result counts.

### `step_run_subagent5() -> bool`
- **Parameters**: None.
- **Use**: Calls subAgent5.run() to convert all unconverted JSONs to PDFs. Waits for idle.

### `step_end_subagent5()`
- **Parameters**: None.
- **Use**: Calls subAgent5.end_observation().

### `step_verify_results()`
- **Parameters**: None.
- **Use**: Counts files in output directories (base-gens, insight-gens, base-reports, insights) and prints per-subagent status.

### `_scan_new_files() -> List[str]`
- **Parameters**: None.
- **Use**: Compares upload directory contents against `uploaded_files.json` register; returns unprocessed files.

### `_wait_for_subagent_idle(subagent_dir, label, timeout) -> bool`
- **Parameters**: `subagent_dir` - directory name (e.g. "subAgent1"); `label` - display name; `timeout` - max seconds.
- **Use**: Polls subagent log.txt every 1s until "idle" found or timeout reached.

### `_read_subagent_log(subagent_dir) -> str`
- **Parameters**: `subagent_dir` - directory name.
- **Use**: Reads subagent's log.txt content; returns empty string if not found.

### `_set_activity(status: str)`
- **Parameters**: `status` - activity description.
- **Use**: Writes current activity to Agent 1's log.txt in overwrite mode (specs-compliant).

### `_load_register() -> set`
- **Parameters**: None.
- **Use**: Loads processed file names from `uploaded_files.json`. Returns empty set on first run.

### `_save_register(processed: set)`
- **Parameters**: `processed` - set of processed filenames.
- **Use**: Persists register to `uploaded_files.json`.

### `_mark_processed(filename: str)`
- **Parameters**: `filename` - filename to mark as processed.
- **Use**: Adds filename to register and saves immediately.
