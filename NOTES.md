
## M6 (2026-10-04)
- Groq free tier is ~4 abstracts/min here: only 26/774 abstracts read so far. The bulk run must happen on molab (notebooks/extract_molab.py, untested) or over several days of Groq. After it: download edges_text_mined.jsonl + extractions.jsonl into data/cache/, then `uv run python -m src.graph.text_mined`.
- extractions.jsonl holds 14 abstracts read with the older prompt (objects were sentences); extractions_v1.jsonl is a backup copy. Delete both to restart cleanly.
- Resolver keeps ~19% of facts (strict by design): disease must be one of the paper's diseases, gene/phenotype must already be in the graph. Pathway facts are dropped (no disease->pathway predicate home).
- Not done: Claude reviewer; HGSNAT cross-correction claim (needs a new predicate, awaiting user).

## Milestones 7-9 (2026-10-04) , following NEXT-STEPS.md
- Off-topic filter: src/etl/filter_abstracts.py (712 of 774 kept; yeast Cln1 paper out). Extraction now reads abstracts_filtered.jsonl, Sanfilippo first. Groq limit is 8000 tokens/min, so ~4 abstracts/min with 1 worker; llm.py backoff raised to 8 tries (max 30 s).
- text_mined.py: gene aliases via src/etl/genes.py (HGNC names), drop reasons counted (text_mined_drops.json -> STATS.md). Writes edges directly rather than merge_layer, because merge_layer drops by predicate and would delete curated has_phenotype edges.
- connections.py: contradictions = 0 (no negation in extraction), shared_people, cluster_assets, neighbours.
- App: app/app.py + src/webapp/{data,explain,ten_x}.py (helpers are NOT in app/ because a package named `app` collides with app/app.py). Tested with streamlit AppTest.
- Search cutoff 88 plus substring pass; out-of-scope queries (e.g. "cystic fibrosis") show the no-supported-route screen. No disease in our 22 lacks assets entirely, so the disease-level no-route branch is not reachable with current data (still implemented).
- 10x tab uses nhs_timelines.csv (ClinicalTrials.gov dates); FDA guidance is cited only qualitatively. No setup-time figure was found, none is stated.
- Patient orgs: 5 rows from homepage reads on 2026-10-04; BDSRA scope not verified. HGSNAT cross-correction claim dropped per NEXT-STEPS.
- Not done: Claude reviewer, molab run, Streamlit Cloud deploy (needs the user's share.streamlit.io login), video.
