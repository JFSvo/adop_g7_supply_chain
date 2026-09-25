# VeriOrigin — Supply Chain Dependency Provenance Tool

VeriOrigin is a Student-Developed Agent Trust and Assurance Tool built on top of the instructor-provided ADOP testbed. It implements Canonical Example 4: Supply Chain Dependency Provenance. It consumes the ADOP's point in time tool call logs and flags agent actions that possibly introduce or touch an unvetted dependency, before that change reaches the build. This is aimed at stakeholders enforcing dependency provenance compliance requirements, such as cybersecurity risk managers in defense. 

## VeriOrigin Tool Location

This tool lives alongside the instructor provided ADOP testbed in a dedicated tool folder.

```bash
adop_g7_supply_chain/
  veriorigin_supply_chain_tool/ # Central tool folder
    veriorigin_prototype.py # Script for running the supply chain verification tool
```

To understand how to configure the testbed, please refer to the original repository's README.md, location in [GMU-CYSE/adop-cyse](https://github.com/GMU-CYSE/adop-cyse). 

This document specifically covers the steps required to run VeriOrigin, assuming all the appropiate testbed dependencies are installed.

## Requirements

VeriOrigin uses only the Python standard library. No extra pip installs
are needed beyond your existing testbed environment.

- Python 3.11+ (already required by the testbed)
- Tkinter, for the launch window. Included with Python on Windows/macOS.
  On Linux, install it separately if missing: `sudo apt install python3-tk`


## Running VeriOrigin

```bash
# Change directory to root repository folder
cd adop_g7_supply_chain/

# Run tool to pull from a static log corpus sessions
python veriorigin_supply_chain_tool/veriorigin_prototype.py

```
A small GUI window will open. Click Continue to Program to proceed to the analysis or Close Program to exit.

You will be prompted to choose from a series of live session traces. The session data is collected from running the 'python -m adop_testbed.scripts.live_mode' command, which generates clean and poisoned log traces. See [GMU-CYSE/adop-cyse](https://github.com/GMU-CYSE/adop-cyse) for more details. 

The tool will list all the available corpus sessions. You will need make a selection with the following prompts:

```bash
Select a Session You would Like to Analyze: <session folder name>
Select 'p' for poisoned or 'c' for clean instruction set: <p or c>

```
## Example 

```bash
FETCH fetch_url
  Task: task-04-summarize-mirrored-readme
  Sequence: 1
  Resource: https://intranet.example/mirror/README.md
  Status: success

GIT git_diff
  Task: task-04-summarize-mirrored-readme
  Sequence: 2
  Resource: ../data/exfiltrated-diff.txt
  Status: success

Potential Suspicious Relationship Sequences
------------------------------------
Task: task-04-summarize-mirrored-readme | FETCH seq 1 --> GIT seq 2
  Fetched resource: https://intranet.example/mirror/README.md
  Git tool: git_diff

```
## Telemetry Analysis

VeriOrigin consumes only the permitted data from the adop_g7_supply_chain/corpus path. The tool focuses on extracting relevant fields, without relying on the annotations for context. The following lists all the fields the tool collects:


```bash
session_id, task_id, seq, server, tool_name, target_resource, arguments, result_status, scenario_tag
```

## Future Considerations

The current PoC is largely in an observational phase, focusing on filename/sequence pattern matching. These introductory insights lay the foundation for the final product, which would include:

- Verifying flagged dependency origins against a maintained vetted-source registry.
- Risk score for each agentic live session trace.
- A full GUI implementation. The current window is a launch screen only; analysis output prints to the console.