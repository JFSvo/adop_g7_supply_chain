import json
import shutil
import sys
from pathlib import Path
 
def find_root():
    for folder in Path(__file__).resolve().parents:
        if (folder / "veriorigin_supply_chain_tool" / "provenance_analysis.py").is_file() and (folder / "corpus").is_dir():
            return folder
    sys.exit("Could not find the repository root: keep this script inside the adop_g7_supply_chain folder.")
 
 
ROOT = find_root()
 
 
def first_event(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return json.loads(line)
    return None
 
 
def main(source):
    found = {}
    for path in sorted(Path(source).glob("*.jsonl")):
        event = first_event(path)
        if event is None:
            print(f"Skipping {path.name}: empty file.")
            continue
        found.setdefault(event["session_id"], {})[event["scenario_tag"]] = path
    for session_id, files in sorted(found.items()):
        target = ROOT / "corpus" / f"live-session-{session_id}"
        if target.exists():
            print(f"Already in corpus: {session_id}")
            continue
        target.mkdir(parents=True)
        for scenario, path in files.items():
            shutil.copyfile(path, target / f"{scenario}.jsonl")
        print(f"Added {target.relative_to(ROOT)} ({', '.join(sorted(files))})")
 
 
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
 