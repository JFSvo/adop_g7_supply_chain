import json
import tkinter as tk
from pathlib import Path

root = tk.Tk()

# root.title("Supply Chain Dependency Verification Tool")
# root.minsize(width = 500, height = 500)
# root.maxsize(width = 700, height = 700)

root.geometry("500x500")
root.title("Supply Chain Dependency Verification Tool")

label = tk.Label(root, text="Agentic Monitoring Tool, by SC Inc", font=('Arial', 18))
label.pack(padx=20, pady=20)

textbox = tk.Text(root, font=('Arial'))

button2 = tk.Button(root, text = "Continue to Program", width = 50, height = 5, command=root.destroy)
button2.pack(padx = 1, pady = 10 )
button2.pack()

root.mainloop()

# root.geometry("500x500")
# root.title("Supply Chain Dependency Verification Tool")

# label = tk.Label(root, text="SCA Tool by Group 7", font=('Arial', 18))
# label.pack(padx=20, pady=20)

# textbox = tk.Text(root, font=('Arial'))

# Task 1 - Importing Corpus Data:

project = Path(r"adop_g7_supply_chain")
corpus = project / "corpus"

print("Please view the following agentic actions sequence sessions")
print(' ')

for item in corpus.iterdir(): # Lists All Corpus Items
    print(item)

print(' ')

# tk.messagebox.showinfo(title=None, message=None, **options)

session_choice = str(input("Select a Session You would Like to Analyze: "))
file_choice = str(input("Would you like to view the clean or poisoned agentic actions? "))

file_path = corpus / session_choice / f"{file_choice}.jsonl"

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

# Rule 1 - Assess MCP Server Pull Order
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
                    print()


# Rule 2 - Check for Suspicious Files
def check_suspicious_files(event):

    SUSPICIOUS_RESOURCES = [
        ".js",
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

for event in events:
    check_suspicious_files(event)
