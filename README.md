## VeriOrigin — Supply Chain Dependency Provenance Tool

VeriOrigin is a Student-Developed Agent Trust and Assurance Tool built on top of the instructor-provided ADOP testbed. It implements Canonical Example 4: Supply Chain Dependency Provenance. It consumes the ADOP's point in time tool call logs and flags agent actions that possibly introduce or touch an unvetted dependency, before that change reaches the build. 

## VeriOrigin Tool Location

This tool lives alongside the instructor provided ADOP testbed in a dedicated tool folder.

```bash
adop_g7_supply_chain/
  veriorigin_supply_chain_tool/ # Central tool folder
    veriorigin_prototype.py # Script for running the supply chain verificaiton tool
```

To understand how to configure the testbed, please refer to the original repository's README.md, location in [GMU-CYSE/adop-cyse](https://github.com/GMU-CYSE/adop-cyse). 

This document specifically covers the steps required to run VeriOrigin, assuming all the appropiate testbed dependencies are are installed.

## Requirements

Certain Python libraries are required to ensure the tool runs correctly in testing. Ensure the following packages are installed prior to running the product:

```bash
# reset the synthetic repository to its clean baseline
python -m pip install tkinter

# run the deterministic scripted host (no LLM) to sanity-check the install
python -m pip install sys

# run the full test suite
python -m pip install pathlib
```
## Running VeriOrigin

```bash
# Change directory to root repository folder
cd adop_g7_supply_chain/

# Run tool to pull from a static log corpus sessions
python veriorigin_supply_chain_tool/veriorigin_prototype.py

```
Every live session writes structured telemetry to `corpus/live-session-<date>-<id>/{clean,poisoned}.jsonl`. That telemetry, and only that telemetry, is the input your Trust and Assurance Tool is allowed to consume.

For a guided, step-by-step first run, an explanation of every file above, how to author a new task/scenario, the exact log schema, the two intentional Git-server vulnerabilities, and a checklist your team can use as proof of a completed lab session, go to **[`ADOP_Lab_Guide.md`](./ADOP_Lab_Guide.md)**.

## What you may not do

You may not modify the MCP reference server source code in `adop_testbed/servers/`, modify either agent host to change *what ADOP does*, or assume access to interfaces not documented here (Section F/G.3 of the Project Notebook; restated with the reasoning behind it in the Guided Lab §10).

## Support

Questions about the testbed's infrastructure itself (not the tool your team is designing) go to the course support channel referenced in Section G.4 of the Project Notebook. Instructor: Alexandre B. Barreto (adebarro@gmu.edu).
