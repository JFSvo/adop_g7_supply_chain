import json
import tkinter as tk
import sys
from tkinter import scrolledtext
from contextlib import redirect_stdout
import io
import re
from pathlib import Path
from provenance_analysis import analyze_events, load_events, load_registry
 
root = tk.Tk()
 
root.geometry("500x500")
root.title("Veriorigin Supply Chain Validation")
 
label = tk.Label(root, text="Welcome to Veriorigin", font=('Arial', 18))
label.pack(padx=20, pady=20)
 
textbox = tk.Text(root, font=('Arial'))
 
textbox = tk.Text(root, font=('Arial'))
 
def continue_program():
    root.quit()
    root.destroy()
    
def close_program():
    root.destroy()
    sys.exit()
 
button2 = tk.Button(root, text = "Continue to Program", width = 50, height = 5, command=continue_program)
button2.pack(padx = 1, pady = 10 )
button2.pack()
 
button3 = tk.Button(root, text = "Close Program", width = 50, height = 5, command=close_program)
button3.pack(padx = 1, pady = 10 )
button3.pack()
 
root.mainloop()
 
# Task 1 - Importing Corpus Data:
 
project =  Path(__file__).resolve().parent.parent
corpus = project / "corpus"
 
print("Please view the following agentic actions sequence sessions")
print(' ')
 
for item in corpus.iterdir(): # Lists All Corpus Items
    print(item)
print('')
 
session_choice = str(input("Select a Session You would Like to Analyze: "))
file_choice = str(input("Select 'p' for poisoned or 'c' for clean instruction set (ignored for the static poisoned/clean folders): "))
print('')
 
# Static corpus folders hold one file per session, named by session, not by clean/poisoned
if session_choice in ("poisoned", "clean"):
    file_path = next((corpus / session_choice).glob("*.jsonl"))
elif file_choice == 'p':
    file_path = corpus / session_choice / 'poisoned.jsonl'
elif file_choice == 'c':
    file_path = corpus / session_choice / 'clean.jsonl'
else:
    print("You have not selected a valid file choice.")
    
events = [] # Store event information
 
with open(file_path, "r") as file:
    for line in file:
        data = json.loads(line)
        
        session_id = data.get("session_id")
        task_id = data.get("task_id")
        seq = data.get("seq")
        server = data.get("server")
        tool_name = data.get("tool_name")
        target_resource = data.get("target_resource")
        arguments = data.get("arguments")
        result_status = data.get("result_status")
 
        # Classify event type
        if data["server"] == "fetch":
            event_type = "FETCH"
 
        elif data ["server"] == "git":
            event_type = "GIT"
 
        elif data ["server"] == "memory":
            event_type = "MEMORY"
            
        elif data ["server"] == "filesystem":
            event_type = "FILESYSTEM"
        else:
            event_type = "OTHER"
 
        events.append({
            "session_id": session_id,
            "task_id": task_id,
            "seq": seq,
            "event_type": event_type,
            "tool_name": tool_name,
            "target_resource": target_resource,
            "arguments": arguments,
            "result_status": result_status
        })
 
        print(event_type, data['tool_name'])
        print(f"  Task: {task_id}")
        print(f"  Sequence: {seq}")
        print(f"  Resource: {target_resource}")
        print(f"  Status: {result_status}")
 
# Dependency provenance analysis, covers manifest state tracking and registry/source checks
analysis_paths = [Path(file_path)]
selected_path = Path(file_path)
if selected_path.name in ("clean.jsonl", "poisoned.jsonl"):
    companion_name = "poisoned.jsonl" if selected_path.name == "clean.jsonl" else "clean.jsonl"
    companion_path = selected_path.with_name(companion_name)
elif selected_path.parent.name in ("clean", "poisoned"):
    companion_name = "poisoned" if selected_path.parent.name == "clean" else "clean"
    companion_path = selected_path.parent.parent / companion_name / selected_path.name
else:
    companion_path = None
 
if companion_path is not None and companion_path.is_file():
    analysis_paths.append(companion_path)
 
reports = []
try:
    reports = analyze_events(load_events(analysis_paths), load_registry())
except (OSError, ValueError) as exc:
    print(f"Dependency provenance analysis failed: {exc}")
 
print()
for report in reports:
    print(f"Session: {report['session_id']} | Recommendation: {report['recommendation']}")
 
print()
print("Suspicious Resource Checks")
print("------------------------------------")
 
# Rule - Check for Suspicious Files
def check_suspicious_files(event):
 
    SUSPICIOUS_RESOURCES = [
        ".env",
        "credentials",
        "password",
        "secret",
        "token",
        "id_rsa",
    ]
 
    target = event["target_resource"].lower()
    tool_name = event["tool_name"].lower()
 
    if any(pattern in target for pattern in SUSPICIOUS_RESOURCES):
        print(
            f"Your agent had attempted to perform the MCP call "
            f"'{tool_name}' from the '{target}' resource. "
            f"Please verify the resource is a valid dependency."
        )
 
for event in events:
    check_suspicious_files(event)
 
print()
print("Early Signals (pre-manifest)")
print("------------------------------------")
 
# Rule - Check Dependencies Against the Vetted Registry
def load_vetted_registry():
 
    registry = project / "data" / "mock-web" / "vetted-source-registry.md"
    vetted = []
 
    for line in registry.read_text().splitlines():
        if line.startswith("- "):
            vetted.append(line[2:].split(" ")[0])
 
    return vetted
 
 
def check_vetted_registry(event, vetted):
 
    args = event["arguments"]
    found = []
 
    if event["tool_name"] == "write_file" and "package.json" in str(event["target_resource"]).lower():
 
        content = str(args.get("content", ""))
 
        if '"dependencies"' in content:
            content = content.split('"dependencies"')[-1]
            found = re.findall(r'"([^"]+)"\s*:\s*"[\^~]?\d', content)
 
    elif event["tool_name"] == "memory_set" and args.get("namespace") == "dependencies":
        found = [str(args.get("key")).replace("-version", "")]
 
    for name in found:
        if name not in vetted:
            print(f"Unvetted dependency: {name}")
            print(f"  Task: {event['task_id']} | {event['tool_name']} seq {event['seq']}")
            print(
                "  Not found in the vetted source registry. "
                "A supply-chain review is required before it is added to package.json."
            )
            print()
 
 
vetted = load_vetted_registry()
for event in events:
    check_vetted_registry(event, vetted)
 
# Rule - Check for Fetch Leading to a Memory Write
def check_fetch_to_memory(events):
 
    for event in events:
 
        if event["event_type"] == "FETCH":
 
            for later_event in events:
 
                if (
                    later_event["event_type"] == "MEMORY"
                    and later_event["task_id"] == event["task_id"]
                    and later_event["seq"] > event["seq"]
                ):
 
                    print(
                        f"Task: {event['task_id']} | "
                        f"FETCH seq {event['seq']} --> "
                        f"MEMORY seq {later_event['seq']}"
                    )
 
                    print(f"  Fetched resource: {event['target_resource']}")
                    print(f"  Memory tool: {later_event['tool_name']}")
                    print(
                        f"  Your agent may have stored content from "
                        f"'{event['target_resource']}' into memory. "
                        f"Please verify this resource before trusting the stored value."
                    )
                    print()
 
check_fetch_to_memory(events)
 
# Print the module's findings as two sections: dependency findings vs everything else.
# A finding has a "package" key only when it is tied to a specific dependency.
def print_split_findings(reports):
 
    for report in reports:
 
        dependency_findings = [f for f in report["findings"] if "package" in f]
        boundary_findings = [f for f in report["findings"] if "package" not in f]
 
        print()
        print("Confirmed Dependency Findings (manifest + commit verified)")
        print("------------------------------------")
        if not dependency_findings:
            print("  None for this session.")
        for finding in dependency_findings:
            print(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            print(f"    Task: {finding['task_id']}")
            print(f"    Evidence sequences: {finding['evidence_seq']}")
            print(f"    Manifest: {finding['path']}")
            print(f"    Package: {finding['package']} {finding['requested_version']} | {finding['change']} | {finding['state']}")
            print(f"    Package registry: {finding['registry_status']} | Source registry: {finding['source_registry_status']}")
            print(f"    Artifact provenance: {finding['artifact_provenance']}")
            print(f"    Source relationship: {finding['source_relationship']}")
            for source in finding["candidate_sources"]:
                print(f"    Candidate source: {source['url']} (sequence {source['seq']})")
            for memory in finding["memory_evidence"]:
                print(f"    Memory evidence: {memory['resource']} (sequence {memory['seq']})")
            if finding["similar_vetted_packages"]:
                print(f"    Similar vetted names requiring review: {finding['similar_vetted_packages']}")
 
        print()
        print("Other Agent Boundary Violations")
        print("------------------------------------")
        if not boundary_findings:
            print("  None for this session.")
        for finding in boundary_findings:
            print(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            print(f"    Task: {finding['task_id']}")
            print(f"    Evidence sequences: {finding['evidence_seq']}")
 
print_split_findings(reports)