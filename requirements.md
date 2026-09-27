## How It Works

1. **Ingestion** — reads the selected session's JSON Lines file # Complete

2. **Classify events** — tags each call as FETCH, GIT, MEMORY, FILESYSTEM, or OTHER -  # Complete

3. **Dependency Provenance** - determine where a dependency came from, match it against a trusted source registry # John Svoboda
   - extract the dependencies added in a commit by parsing the changed manifest files (package.json, requirements.txt, lockfiles);
   - find the matching Fetch record by package name, URL and timestamp;
   - then check that URL, and ideally the version, against the registry.

5. **Apply detection rules and policy engine** — four deterministic checks: fetch→git sequence,
   fetch→memory sequence, suspicious resource patterns, dependency file changes # Adam Omar

6. **Risk Scoring** — assign score and reccomendation (approve, review, reject) based on the findings to present to stakeholders # Akki Kishore

7. **GUI and improvement** - look at ways to improve the GUI tkinter interface or polish code # Yasser Khan / Andrew Diaz

## Development Steps

1.	Finalize the normalized Event structure.

2.	Finalize Relationship and ProvenanceRecord structures.

3.	Integrate ingestion with event classification.

4.	Integrate event correlation with provenance analysis.

5.	Integrate provenance with policy rules.

6.	Integrate policy findings with risk scoring.

7.	Connect the final structured results to the Tkinter interface.

8.	Test the complete pipeline against clean and poisoned/unvetted sessions.

