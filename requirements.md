## How It Works

1. **Ingestion** — reads the selected session's JSON Lines file # Complete

2. **Classify events** — tags each call as FETCH, GIT, MEMORY, FILESYSTEM, or OTHER -  # Complete

3. **Dependency Provenance** - determine where a dependency came from, match it against a trusted source registry # John Svoboda

4. **Apply detection rules and policy engine** — four deterministic checks: fetch→git sequence,
   fetch→memory sequence, suspicious resource patterns, dependency file changes # Adam Omar

5. **Risk Scoring** — assign score based on the findings to present a risk assessment to stakeholders # Akki Kishore

6. **GUI and improvement** - look at ways to improve the GUI tkinter interface or polish code # Yasser Khan / Andrew Diaz

## Development Steps

1.	Finalize the normalized Event structure.

2.	Finalize Relationship and ProvenanceRecord structures.

3.	Integrate ingestion with event classification.

4.	Integrate event correlation with provenance analysis.

5.	Integrate provenance with policy rules.

6.	Integrate policy findings with risk scoring.

7.	Connect the final structured results to the Tkinter interface.

8.	Test the complete pipeline against clean and poisoned/unvetted sessions.

