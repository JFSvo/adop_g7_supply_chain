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
  resources.py                  # Helper methods used in the provenance analysis and UI
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

- Python 3.11+ (already required by the testbed)

The following pip packages are also required:

- PySide6, for the GUI:
- PyInstaller, to build a single packaged executable
- pytest, to run the unit tests

These may be installed by running `pip install -r requirements.txt`.


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

## Building a Standalone Executable ##

For less technical users who may prefer running VeriOrigin as its own executable rather than from the command line, a binary can be generated using PyInstaller. After installing the PyInstaller pip package as specified in the Requirements section, running the command `pyinstaller veriorigin_analyzer.spec` will create a new executable in the `dist/` folder.

### 

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
![alt text](veriorigin_supply_chain_tool/dependency_findings_tab.png)

### Expected Output Supply Chain Risk Report (Dependency Findings tab)
![alt text](veriorigin_supply_chain_tool/trace_tab.png)

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
## Feedback-to-change table

Each Deliverable 2 and Deliverable 3 feedback item, what we changed, and the commit. Items that only affected the written report are listed separately with their report section.

### Deliverable 2 feedback: code changes

| Feedback item | What we changed | Commit(s) |
| --- | --- | --- |
| State an assumption revised with testbed evidence | Live runs showed the attack stopping at agent memory, not at a commit; added memory rules (`DEPENDENCY_RECORDED_IN_MEMORY`) and more live sessions | [656a737](https://github.com/JFSvo/adop_g7_supply_chain/commit/656a737), [a3d4491](https://github.com/JFSvo/adop_g7_supply_chain/commit/a3d4491) |
| Expand the validation plan | Evaluation script with a hand-labeled answer key, targets per criterion, session import | [29f53a9](https://github.com/JFSvo/adop_g7_supply_chain/commit/29f53a9), [327f5e4](https://github.com/JFSvo/adop_g7_supply_chain/commit/327f5e4), [8cb6074](https://github.com/JFSvo/adop_g7_supply_chain/commit/8cb6074) |
| Design the user experience for the supply chain lead | Qt interface replacing terminal output, recommendation shown firs, & v0.8 Review tab with per-dependency cards | [b771a57](https://github.com/JFSvo/adop_g7_supply_chain/commit/b771a57), [bc42c66](https://github.com/JFSvo/adop_g7_supply_chain/commit/bc42c66), [087482c](https://github.com/JFSvo/adop_g7_supply_chain/commit/087482c), [f013e6b](https://github.com/JFSvo/adop_g7_supply_chain/commit/f013e6b) |
| PoC: README named a missing entry point | README points to `veriorigin_analyzer.py` | [193fab2](https://github.com/JFSvo/adop_g7_supply_chain/commit/193fab2) |
| PoC: analyzer and module printed overlapping rules | Early-signal rules removed from the analyzer; one rule set in `provenance_analysis.py` | [656a737](https://github.com/JFSvo/adop_g7_supply_chain/commit/656a737) |
| PoC: approval-claim false positive on the clean session | Approval claim that matches the registry is now info, not medium | [656a737](https://github.com/JFSvo/adop_g7_supply_chain/commit/656a737) |
| PoC: single file always raised INCOMPLETE_SESSION | Companion clean/poisoned file loaded automatically | [656a737](https://github.com/JFSvo/adop_g7_supply_chain/commit/656a737) |
| PoC: "Test message" commit added an agent-modified file | Testbed `checkout.js` and reference corpus restored | [0434a3b](https://github.com/JFSvo/adop_g7_supply_chain/commit/0434a3b) |

### Deliverable 2 feedback: addressed in the report

| Feedback item | What we changed | Where |
| --- | --- | --- |
| Score the threats | Likelihood and impact per threat in a ranked risk register | D3 2.1 |
| Fix threat-model inconsistencies | Interfaces I1ΓÇôI8 only, OWASP step references fixed, LLM05 corrected, scenario marked hypothetical, & T6/T9 split | D3 2 |
| Name the compliance requirement | NIST SSDF (SP 800-218); privacy grounding added in D4 | D3 1; D4 2.2 |
| Add a reference list | References section added | D3/D4 References |
| Presentation details | Title page, group and members, garbled sentences fixed, & appendix diagrams enlarged | D3 |

### Deliverable 3 feedback: code changes

| Feedback item | What we changed | Commit(s) |
| --- | --- | --- |
| Manifest baseline truncated, so existing dependencies were flagged | Committed `testbed-repo/package.json` loaded as the baseline | [6e96985](https://github.com/JFSvo/adop_g7_supply_chain/commit/6e96985), [04ee33f](https://github.com/JFSvo/adop_g7_supply_chain/commit/04ee33f), [c00a867](https://github.com/JFSvo/adop_g7_supply_chain/commit/c00a867) |
| Registry parser dropped approved versions and sources | Vetted registry moved to structured JSON (`vetted_registry.json`) | [b66e7db](https://github.com/JFSvo/adop_g7_supply_chain/commit/b66e7db), [04ee33f](https://github.com/JFSvo/adop_g7_supply_chain/commit/04ee33f), [c00a867](https://github.com/JFSvo/adop_g7_supply_chain/commit/c00a867) |
| False-positive root cause | Paths resolved against the sandbox root, failed path guesses are info. FP 15/35 to 0/35 | [97409c6](https://github.com/JFSvo/adop_g7_supply_chain/commit/97409c6), [c00a867](https://github.com/JFSvo/adop_g7_supply_chain/commit/c00a867), [2d296dc](https://github.com/JFSvo/adop_g7_supply_chain/commit/2d296dc) |
| `git_init` resolved against the server's directory | Resolved against the repository base, answer key relabeled | [17c69f5](https://github.com/JFSvo/adop_g7_supply_chain/commit/17c69f5), [c00a867](https://github.com/JFSvo/adop_g7_supply_chain/commit/c00a867), [6f47ac9](https://github.com/JFSvo/adop_g7_supply_chain/commit/6f47ac9) |
| Taint only flowed from fetches | Sensitive and out-of-scope reads followed by a memory write are linked (`SENSITIVE_DATA_TO_MEMORY`) | [9bf782c](https://github.com/JFSvo/adop_g7_supply_chain/commit/9bf782c) |
| Memory rule only checked the dependencies namespace | Unvetted package names matched in any memory namespace | [09b8000](https://github.com/JFSvo/adop_g7_supply_chain/commit/09b8000) |
| Write-attempt rule parsed fragile text | Manifest content parsed as JSON first, text pattern as fallback; tests for T4ΓÇôT6 | [130e366](https://github.com/JFSvo/adop_g7_supply_chain/commit/130e366) |
| Answer key labeled by the team | Second blind labeler not completed - four held-out sessions labeled. disclosed as a limitation | [f8c9105](https://github.com/JFSvo/adop_g7_supply_chain/commit/f8c9105) |
| PoC: text dumps, no score, no decision record | Per-dependency cards, 0ΓÇô100 risk score with breakdown, Approve/Escalate decision log with reviewer ID, & UTC time and log SHA-256 | [d0cff8e](https://github.com/JFSvo/adop_g7_supply_chain/commit/d0cff8e), [f013e6b](https://github.com/JFSvo/adop_g7_supply_chain/commit/f013e6b), [3b40d91](https://github.com/JFSvo/adop_g7_supply_chain/commit/3b40d91) |
| Interface must look like a product | Review, Evidence and Decisions tabs, plain-language risks, evidence links, & standalone executable | [a0892c8](https://github.com/JFSvo/adop_g7_supply_chain/commit/a0892c8), [3b40d91](https://github.com/JFSvo/adop_g7_supply_chain/commit/3b40d91), [dbd74db](https://github.com/JFSvo/adop_g7_supply_chain/commit/dbd74db), [0a67a3e](https://github.com/JFSvo/adop_g7_supply_chain/commit/0a67a3e) |
| Results shown as raw text | Raw-text tabs retired; plain-language Review tab and text export | [3b40d91](https://github.com/JFSvo/adop_g7_supply_chain/commit/3b40d91) |
| False positives are the first question | Before/after results: FP 43% to 0%, detection 76% to 100% on the same 14 sessions | [2d296dc](https://github.com/JFSvo/adop_g7_supply_chain/commit/2d296dc) |
| Evidence at task level, not record level | Evidence (sequence) column in the per-task results, sequence numbers cited in report tables | [46d7f30](https://github.com/JFSvo/adop_g7_supply_chain/commit/46d7f30) |

### Deliverable 3 feedback: addressed in the report

| Feedback item | What we changed | Where |
| --- | --- | --- |
| "Where does it plug in?" | Pull-request check described as the v1/v2 merge gate (not built) | D4 roadmap; pitch |
| Show how 9.8 and 9.4 were computed | Not carried into D4: the risk register and its CVSS scores were removed, and no scores are cited | ΓÇö |
| Figure numbering; diagram too small | Figures renumbered, diagram at full page width | D4 |
| Staged roadmap only in the video | Stages with exit criteria, merge gate as a pull-request check | D4 roadmap |
 