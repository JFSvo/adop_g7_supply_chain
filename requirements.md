## How It Works

1. **Ingestion** — reads the selected session's JSON Lines file # Complete

2. **Classify events** — tags each call as FETCH, GIT, MEMORY, FILESYSTEM, or OTHER -  # Complete

3. **Dependency Provenance** - determine where a dependency came from, match it against a trusted source registry # John Svoboda

4. **Apply detection rules** — four deterministic checks: fetch→git sequence,
   fetch→memory sequence, suspicious resource patterns, dependency file changes # Adam Omar

5. **Print flagged events** — results go to the console