import json
import tkinter as tk
from tkinter import filedialog
import sys
import re
from pathlib import Path

root = tk.Tk()

root.geometry("500x500")
root.title("VeriOrigin Supply Chain Validation")

label = tk.Label(root, text="Welcome to VeriOrigin", font=('Arial', 18))
label.pack(padx=20, pady=20)



textbox = tk.Text(root, font=('Arial'))

def continue_program():
    global file_path 
    file_path = filedialog.askopenfilename(initialdir="./corpus", title="Select Session to Analyze", filetypes=[("JSON Lines", ".jsonl")])
    root.quit()
    root.destroy()
    
def close_program():
    root.destroy()
    sys.exit()

button2 = tk.Button(root, text = "Analyze Session", width = 50, height = 5, command=continue_program)
button2.pack(padx = 1, pady = 10 )
button2.pack()

button3 = tk.Button(root, text = "Close Program", width = 50, height = 5, command=close_program)
button3.pack(padx = 1, pady = 10 )
button3.pack()

root.mainloop()

project =  Path(__file__).resolve().parent.parent
    
events = [] # Store event information

print("MCP Server Tool Call Summary")
print()
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
print("ADOP Agentic Action Supply Chain Risk Report:")
print()
# Deterministic Rules:

# Rule 1 - Check Dependencies Against the Vetted Registry

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

print("Unvetted Dependencies")
print("------------------------------------")
vetted = load_vetted_registry()

for event in events:
    check_vetted_registry(event, vetted)
            
# Rule 2 - See if a fetched dependency was saved into memory

print("Stored Resource Dependencies in Memory")
print("------------------------------------")
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

# Rule 3 - Assess how a fetched dependency moved towards a commit

print("Fetch to Git Sequences")
print("------------------------------------")
def assess_mcp_server_pull_order(events):

    for event in events:

        if event["event_type"] == "FETCH":

            for later_event in events:

                if (
                    later_event["event_type"] == "GIT"
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

assess_mcp_server_pull_order(events)

# Rule 4 - See if dependencies were modified 
print("Potential Dependency Changes")
print("------------------------------------")
def check_dependency_change(event):
    
    dependencies = [
        "package.json",
        "requirements.txt"
    ]

    if event["event_type"] == "GIT" or event["event_type"] == "FILESYSTEM":

        target = str(event["target_resource"]).lower()

        if any(file in target for file in dependencies):
            print(
                f"Potential dependency change detected: "
                f"{event['target_resource']}"
            )
            print()
        
for event in events: 
    check_dependency_change(event)

# Rule 5 - Check for suspicious files pulled into the repository

print("Suspicious Resources")
print("------------------------------------")
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
        print()
    
check_suspicious_files(event)



