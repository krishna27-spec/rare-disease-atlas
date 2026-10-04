# Handoff: Rare Disease Atlas (status as of 2026-10-04)

Paste or upload this file to a new Claude chat and ask: **"Read this and tell me exactly what to do next."**

## The project in brief
Hack-Nation hackathon (Oct 3-4 2026), challenge "AI Atlas for the World's Rare Diseases". I'm a beginner (new to biology and this stack), so explain in plain language, in small steps. Repo: https://github.com/krishna27-spec/rare-disease-atlas (full spec in `CLAUDE.md`, decisions in `NOTES.md` if present).

We build an **evidence-backed knowledge graph + Streamlit app** for ~22 neuronopathic lysosomal storage diseases. Demo user "Maria" has a child with **MPS IIIC (gene HGSNAT)**. The app answers: who shares our disease characteristics, what useful work exists, what should we do together next.

**Hard rules:** no fabricated facts; every edge has source, retrieval date, confidence and evidence type (`curated` / `text_mined` / `inferred`); text-mined edges store the exact sentence and PMID, verified in code against the abstract; stable IDs (MONDO, HGNC, HP, Reactome, PMID, NCT); secrets only in `.env`; the app never calls the LLM to build the graph; visible "not medical advice" disclaimer; no features beyond the current milestone without asking.

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Setup, `src/llm.py`, hello test (Groq, `openai/gpt-oss-20b`) | done |
| 2 | `data/manual/diseases.csv` with verified MONDO IDs | done |
| 3 | Biology layer: genes, phenotypes, pathways, ClinVar counts (`src/etl/biology.py`) | done |
| 4 | Similarity + Louvain clusters (`src/graph/similarity.py`) | done |
| 5 | Research layer: trials, grants, investigators, assets, PubMed (`src/etl/research.py`, `terms.py`) | done; 774 abstracts in `data/cache/abstracts.jsonl` |
| 6 | LLM extraction | **PARTLY DONE, not complete** (see below) |
| 7-9 | Connections, Streamlit app, 10x page + README + deploy | not started |

Graph now: 22 diseases, 23 genes, 674 phenotypes, 79 pathways, 342 trials, 306 investigators, 233 grants, 126 assets. About 4,300 edges, all `curated` except 44 `inferred` `similar_to` edges.

## Milestone 6: what exists
- `src/extract.py`: asks the LLM for facts per abstract (predicates `gene_associated_with_disease`, `has_phenotype`, `participates_in_pathway`; certainty stated/suggested; exact `evidence_text`). Keeps a fact only if the quote is found in the abstract. Resumable. Writes `data/cache/extractions.jsonl` and `data/cache/edges_text_mined.jsonl`. Run: `uv run python -m src.extract --limit 20` (add `--workers 16` for a vLLM server).
- `src/llm.py`: `chat` and `chat_json`. A Groq 400 "json_validate_failed" is now treated as invalid output, retried once, then skipped.
- `notebooks/extract_molab.py`: marimo notebook for molab GPU (installs vLLM, serves gpt-oss-20b, runs extraction). **Written but never run.**
- Test so far: 8 abstracts on Groq gave 15 verified facts, 0 dropped for a missing quote, 2 abstracts failed with empty output (retried on next run).

## Milestone 6: what is NOT done
1. **Full extraction not run.** Only ~8 of 774 abstracts have been read. Needs either the molab GPU run or Groq (free tier is only ~150 abstracts/day).
2. **The molab notebook is untested.** It needs: GPU on, `abstracts.jsonl` uploaded, and either `src/llm.py` + `src/extract.py` uploaded or the repo cloned (repo must be pushed and public). Results (`edges_text_mined.jsonl`, `extractions.jsonl`) must be downloaded into `data/cache/`.
3. **No step turns facts into graph edges yet.** Needed: `src/graph/text_mined.py` that resolves free-text names to stable IDs (disease via `src/etl/terms.py` restricted to the paper's `disease_ids`; gene to HGNC symbol; phenotype to HP via name/synonym; pathway to Reactome), drops anything unresolved (and counts it), builds edges with `make_edge()` (source "PubMed", `source_record` "PMID:...", confidence 0.7 stated / 0.5 suggested), adds Paper nodes, and writes via `merge_layer` in `src/graph/schema.py`.
4. **Known quality issues in raw output:** phenotype "objects" are sometimes whole sentences; genes sometimes come back as protein names (e.g. "tripeptidyl-peptidase I"); some facts are about out-of-scope diseases (e.g. adrenoleukodystrophy); the disease matcher lets in off-topic papers (the first abstract is about the yeast protein "Cln1").
5. **Optional Claude reviewer** (`claude-haiku-4-5`, Message Batches, $25 budget) to set `reviewer_verdict` was not started.
6. **Demo claim unsupported:** "HGSNAT is a membrane enzyme, so cross-correction approaches used for MPS IIIA may not transfer" must be backed by a cited source in the graph or dropped. The current extraction can't capture it. Waiting on my answer whether to add a new predicate for it.

## Git state
Local commits are made through `9d9af56` (Milestone 6 part 1). **Push failed:** the machine has no GitHub credentials (`gh` not installed). I need to run `git push` myself with a username and personal access token, or set up SSH. This blocks the molab notebook from cloning the repo. `CLAUDE.md` and `.env` handling is fine (`.env` is gitignored).

## Environment
Ubuntu, Python 3.14 via uv, 8 GB GPU (too small, use molab or Groq). `.env` has Groq LLM settings plus NCBI keys. Run scripts with `uv run python -m src.<module>`. A molab notebook was connected for pairing (marimo-pair skill) earlier; it may have expired.

## What I want from you (the new Claude)
1. Confirm you understand the state; list anything here that looks inconsistent.
2. Tell me the **exact next steps in order**, with commands, in plain language. Expected order: fix the git push, run a bigger extraction test (molab or Groq), write `src/graph/text_mined.py` and print counts, decide the cross-correction predicate, optionally run the reviewer, then milestone 7.
3. Ask me at most one short question if blocked, with a recommended default.
