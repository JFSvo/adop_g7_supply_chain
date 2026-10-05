import json
import tkinter as tk
import sys
from tkinter import scrolledtext
from contextlib import redirect_stdout
import io
from pathlib import Path
from provenance_analysis import analyze_events, load_events, load_registry, print_reports

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
file_choice = str(input("Select 'p' for poisoned or 'c' for clean instruction set: "))
print('')

if file_choice == 'p':
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

print()
print("Potential Suspicious Relationship Sequences")
print("------------------------------------")

# Deterministic Rules:

# Rule 1 - Assess MCP Server Fetch vs. Git Tool Call Order
def assess_mcp_server_pull_order(events):

    for event in events:

        if event["event_type"] == "FETCH" and event["tool_name"] == "fetch" and event["result_status"] == "success":

            for later_event in events:

                if (
                    later_event["event_type"] == "GIT"
                    and later_event["session_id"] == event["session_id"]
                    and later_event["result_status"] == "success"
                    and later_event["task_id"] == event["task_id"]
                    and later_event["seq"] > event["seq"]
                ):

                    print(
                        f"Task: {event['task_id']} | "
                        f"FETCH seq {event['seq']} --> "
                        f"GIT seq {later_event['seq']}"
                    )

                    print(f"  Fetched resource: {event['target_resource']}")
                    print(f"  Git tool: {later_event['tool_name']}")
                    print()


# Rule 2 - Check for Suspicious Files
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

assess_mcp_server_pull_order(events)

# Rule 3 - Check for Dependency Changes

def check_dependency_change(event):
    if event.get("result_status") != "success":
        return

    arguments = event.get("arguments") or {}
    target = str(arguments.get("path") or event.get("target_resource") or "")
    filename = target.replace("\\", "/").rsplit("/", 1)[-1]

    if filename not in ("package.json", "requirements.txt"):
        return

    is_write = event.get("event_type") == "FILESYSTEM" and event.get("tool_name") == "write_file"
    is_staged = event.get("event_type") == "GIT" and event.get("tool_name") == "git_add"

    if not (is_write or is_staged):
        return

    action = "written" if is_write else "staged"
    print(
        f"Dependency manifest {action}: {target} | "
        f"Task: {event.get('task_id')} | Sequence: {event.get('seq')}"
    )

    if not is_write or filename != "package.json":
        return

    try:
        manifest = json.loads(arguments.get("content", ""))
    except (json.JSONDecodeError, TypeError):
        print("  Dependency details unavailable: invalid package.json content.")
        return

    if not isinstance(manifest, dict):
        print("  Dependency details unavailable: package.json must contain an object.")
        return

    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        dependencies = manifest.get(section, {})
        if not isinstance(dependencies, dict):
            print(f"  Dependency details unavailable: {section} must contain an object.")
            continue

        for package, version in sorted(dependencies.items()):
            print(f"  Observed dependency: {package} {version} ({section})")

for event in events:
            check_suspicious_files(event)
            check_dependency_change(event)

# Rule 4 - Assess MCP Server Fetch vs. Git Tool Call Order
def check_fetch_to_memory(events):

    for event in events:

        if event["event_type"] == "FETCH" and event["tool_name"] == "fetch" and event["result_status"] == "success":

            for later_event in events:

                if (
                    later_event["event_type"] == "MEMORY"
                    and later_event["tool_name"] == "memory_set"
                    and later_event["session_id"] == event["session_id"]
                    and later_event["result_status"] == "success"
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
                    print()

check_fetch_to_memory(events)

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

try:
    print_reports(analyze_events(load_events(analysis_paths), load_registry()))
except (OSError, ValueError) as exc:
    print(f"Dependency provenance analysis failed: {exc}")
