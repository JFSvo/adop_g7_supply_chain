# VeriOrigin — Supply Chain Dependency Provenance Tool
![alt text](veriorigin_supply_chain_tool/VeriOrigin_logo.png)

VeriOrigin is a Student-Developed Agent Trust and Assurance Tool built on top of the instructor-provided ADOP testbed. It implements Canonical Example 4: Supply Chain Dependency Provenance. It consumes the ADOP's point in time tool call logs and flags agent actions that possibly introduce or touch an unvetted dependency, before that change reaches the build. This is aimed at supply chain security leads at defense contractors, who must decide whether an AI-added dependency can proceed or must be escalated.

## VeriOrigin Tool Location

This tool lives alongside the instructor provided ADOP testbed in a dedicated tool folder, with the validation scripts in a separate evaluation folder

```bash
# VeriOrigin folder
veriorigin_supply_chain_tool/
  veriorigin_analyzer.py        # Entry point: session picker, readable trace, findings output
  user_interface.py             # Qt (PySide6) window with session picker, results, and export
  provenance_analysis.py        # All detection rules: dependency state, registry/source checks, scope checks
  test_provenance_analysis.py   # Unit testing framework

# Validation folder
evaluation/
  evaluation.py                 # Validation against the hand-labeled answer key
  import_sessions.py            # Copies new live-session files into corpus/
  ground_truth.csv              # Answer key: one row per task execution
  results.md   
```

To understand how to configure the testbed, please refer to the original repository's README.md, location in [GMU-CYSE/adop-cyse](https://github.com/GMU-CYSE/adop-cyse). 

This document specifically covers the steps required to run VeriOrigin, assuming all the appropriate testbed dependencies are installed.

## Requirements

VeriOrigin uses only the Python standard library. No extra pip installs
are needed beyond your existing testbed environment.

- Python 3.11+ (already required by the testbed)
- PySide6, for the GUI: `pip install PySide6`
- pytest, to run the unit tests: `pip install pytest`

## Running VeriOrigin

```bash
# Change directory to root repository folder
cd adop_g7_supply_chain/

# Run the VeriOrigin GUI
python veriorigin_supply_chain_tool/veriorigin_analyzer.py

```
A window will open. Click **Analyze Session** to choose a session file, or **Quit** to exit.

A file dialog opens in the corpus/ folder. Select any clean.jsonl or poisoned.jsonl file. Live session folders are created by running `python -m adop_testbed.scripts.live_mode`. See [GMU-CYSE/adop-cyse](https://github.com/GMU-CYSE/adop-cyse) for details.

ADOP writes one session across two files: the clean and poisoned runs. VeriOrigin loads the matching companion file automatically, so the session is analysed as one complete timeline. The first line of the output lists the files that were analysed.

Results appear in four tabs: Trace, Dependency Findings (which includes the reccomendation), Early Signals, and Boundary Findings. Export Analysis saves all four as a .log file. Back returns to choosing the session.

## Live Mode

VeriOrigin was validated on Live mode, which included a total of 10 sessions based on the agent's actions. Live mode was chosen because the static sessions were already scripted. The live runs show how a real agent is capable of behaving, which revealed what stage in the pipeline the attack stopped.

### Running without the GUI

The detection module can also be run directly, which is useful for backend and repeatable testing:

```bash
# Analyse a session (the companion file is added automatically)
python veriorigin_supply_chain_tool/provenance_analysis.py corpus/live-session-live-2026-09-07-b62f31/poisoned.jsonl

# Analyse only the given file, and save the findings as JSON
python veriorigin_supply_chain_tool/provenance_analysis.py corpus/poisoned/session-01.jsonl --no-companion --output findings.json
```

### Running the unit tests

```bash
cd veriorigin_supply_chain_tool
python -m pytest -q test_provenance_analysis.py
```

## Example Input and Expected Output 

### MCP Server Call Sequence Trace (Trace Tab)
![alt text](veriorigin_supply_chain_tool/VeriOrigin_logo.png)

### Expected Output Supply Chain Risk Report (Dependency Findings tab)
![alt text](veriorigin_supply_chain_tool/VeriOrigin_logo.png)

###

## Telemetry Analysis

VeriOrigin consumes only the permitted data from the adop_g7_supply_chain/corpus path, and the vetted-source registry at adop_g7_supply_chain/data/mock-web/vetted-source-registry.md. The tool focuses on extracting relevant fields, without relying on the annotations for context. The following lists all the fields the detection rules collect:

```bash
session_id, task_id, seq, server, tool_name, target_resource, arguments, result_status, scenario_tag
```
## Testing

VeriOrigin's dependency analysis logic is covered by an automated test suite (`test_provenance_analysis.py`, 40 tests), including validation against the project's own reference corpus.

## Validation

evaluation/evaluation.py compares VeriOrigin's findings against a ground truth list, which includes a row for each task across the 10 sessions.

```bash
python evaluation/evaluation.py # compute results and write to the evaluation/results.md output file
```

### Validation Example Output

```bash
| Criterion | Target | Result |
| --- | --- | --- |
| Traceability | ≥ 90% | 2 of 2 dependency additions traced to session, task and source |
| Suspicious-case detection | ≥ 90% | 11 of 11 (100%) |
| · injected_content | ≥ 90% | 1 of 1 (100%) |
| · path_escape | ≥ 90% | 8 of 8 (100%) |
| · unvetted_dependency | ≥ 90% | 2 of 2 (100%) |
| False positives (clean tasks) | ≤ 10% | 12 of 26 (46%) |
| Auditability | 100% | 38 of 38 (100%) |
| Critical assumption: unlinked additions | 0 | 0 |
| Data assumption: incomplete sessions | 0 | 0 |

Poisoned tasks flagged although no unsafe action occurred: 2.

Full results written to evaluation\results.md
```