
## M6 (2026-10-04)
- Groq free tier is ~4 abstracts/min here: only 26/774 abstracts read so far. The bulk run must happen on molab (notebooks/extract_molab.py, untested) or over several days of Groq. After it: download edges_text_mined.jsonl + extractions.jsonl into data/cache/, then `uv run python -m src.graph.text_mined`.
- extractions.jsonl holds 14 abstracts read with the older prompt (objects were sentences); extractions_v1.jsonl is a backup copy. Delete both to restart cleanly.
- Resolver keeps ~19% of facts (strict by design): disease must be one of the paper's diseases, gene/phenotype must already be in the graph. Pathway facts are dropped (no disease->pathway predicate home).
- Not done: Claude reviewer; HGSNAT cross-correction claim (needs a new predicate, awaiting user).
