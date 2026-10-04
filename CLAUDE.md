# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# CLAUDE.md: Rare Disease Atlas (Hack-Nation hackathon, Oct 3–4 2026)

You are helping a beginner build a hackathon project in about 14 working hours. The user is new to biology and to this stack. **Explain what you're doing in plain language, work in small steps, and run things to prove they work before moving on.** Prefer boring, simple code over clever code.

## What we are building

An evidence-backed knowledge graph plus a web app for the "AI Atlas for the World's Rare Diseases" challenge (OpenAI × Buffalo Initiative × Hack-Nation).

- **Nodes:** Disease, Gene, Variant (counts only), Pathway, Phenotype (symptom), PatientOrg, Paper, Trial, Investigator, Grant, Asset (registry, natural history study, animal model, biomarker).
- **Edges:** typed facts between nodes. **Every edge has a source, a retrieval date, a confidence and an evidence type.** This is the core judging criterion; never create an edge without them.
- **User:** "Maria", leader of a patient group for an untreated rare disease. The app answers three questions: *Who shares our disease characteristics? What useful work already exists? What should we do together next?* When nothing is supported it says so, explains what was searched, and says what evidence is missing.
- **Scope:** about 30 neuronopathic lysosomal storage disorders. MPS IIIA/B/C/D (Sanfilippo), the NCLs (CLN1, CLN2, CLN3, CLN5, CLN6, CLN7, CLN8), Niemann-Pick type C1/C2, GM1 gangliosidosis, GM2 (Tay-Sachs, Sandhoff), metachromatic leukodystrophy, Krabbe, alpha-mannosidosis, mucolipidosis IV, plus MPS I and MPS II for contrast.
- **Demo story:** Maria's child has **MPS IIIC (gene HGSNAT)**. The graph links her through the heparan sulfate degradation pathway to MPS IIIA/IIIB, their natural history studies, trials, investigators and patient groups. It also shows what differs, e.g. HGSNAT is a lysosomal membrane enzyme, so cross-correction approaches used for MPS IIIA may not transfer. **That claim must be backed by a cited source in the graph, or dropped.**

Judging: graph quality, evidence integrity, patient progress, 10× impact case, ambition and product craft. Deliverables: working prototype, repo with README (architecture and how to rebuild the dataset), team video, 1-minute walkthrough.

## Hard rules

1. **No fabricated facts.** Text-mined edges must store the exact sentence (`evidence_text`) and PMID. After every LLM extraction, verify in code that `evidence_text` appears in the abstract (normalise whitespace and case). Drop the edge if it doesn't.
2. **Three evidence types, always labelled:** `curated` (from a database file or API), `text_mined` (LLM read a paper), `inferred` (our code computed it, e.g. similarity). Inferred edges must fill `method`.
3. **Stable IDs, never free-text names, as node keys:** MONDO for diseases (keep OMIM and ORPHA as xrefs), HGNC symbol for genes, HP for phenotypes, Reactome stable IDs (`R-HSA-…`) for pathways, `PMID:` for papers, `NCT…` for trials, NIH project numbers for grants.
4. **Secrets live only in `.env`.** Never print, log or commit keys. `.env` must be in `.gitignore` from the very first commit. The repo will be public.
5. **Cache every download and API response** under `data/raw/` and `data/cache/` (both gitignored). Re-runs must not re-download. Respect rate limits: NCBI 10 req/s with an API key, 3/s without; ClinicalTrials.gov and RePORTER at most a few requests per second.
6. **The app never calls the LLM to build the graph.** The graph is built offline into `data/graph/` files; the app only reads them. The live app uses the LLM only for the plain-language explanation, and it must still work (with a fallback message) if the LLM is down.
7. **Not medical advice.** The app shows a visible disclaimer.
8. Don't add features beyond the current milestone without asking. If a data source fails, tell the user and continue with the others.

## Tech stack

- Python 3.11+, managed with **uv** (`uv add <pkg>`, `uv run <cmd>`).
- Data and ETL: `pandas` or `polars`, `requests`, `obonet` or `pronto` (OBO parsing), `lxml` (Orphadata XML), `networkx` (graph and Louvain clustering).
- Notebooks: **marimo** (`.py` notebooks in `notebooks/`) for exploration and the GPU extraction run on molab. Start with `marimo edit --watch notebooks/<name>.py` so the user sees your edits live.
- App: **Streamlit** + `streamlit-agraph` or `pyvis` for the graph view (`app/app.py`). Deploy to Streamlit Community Cloud or Hugging Face Spaces.
- LLM: **gpt-oss** (OpenAI open-weight) via the OpenAI-compatible API. Use the `openai` Python package with a configurable `base_url`, so one code path works for every provider (see below).
- Optional second reviewer: Claude via the `anthropic` package, model `claude-haiku-4-5` (or `claude-sonnet-5-5` for harder cases). It checks whether each text-mined edge is supported by its sentence. Budget is $25 total; use the Message Batches API for bulk.

## LLM provider configuration (`src/llm.py`)

One function, `chat(messages, json_schema=None) -> str`, reads these from `.env`:

```
LLM_BASE_URL=...   # see table
LLM_API_KEY=...
LLM_MODEL=...
```

| Provider | LLM_BASE_URL | LLM_MODEL | Notes |
|---|---|---|---|
| vLLM on molab GPU | `http://localhost:8000/v1` (inside the molab notebook) | `openai/gpt-oss-20b` (or `openai/gpt-oss-120b`; fits in 96 GB) | Free, best for the bulk extraction run |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-20b` | Free tier is about 30 req/min and 200K tokens/day, roughly 150 abstracts/day |
| OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-oss-20b:free` | Free: 50 req/day (1,000/day after buying $10 credit) |
| Ollama (local) | `http://localhost:11434/v1` | `gpt-oss:20b` | User's GPU has 8 GB of VRAM, so it's slow. Backup only |

Ask for JSON output and validate it with Pydantic; retry once on invalid JSON, then skip and log. Add exponential backoff on HTTP 429.

## Data sources (download scripts in `src/etl/`)

Verify each URL on first run. If one 404s, check the source's download page and tell the user what changed.

| Source | What we take | Where |
|---|---|---|
| MONDO | Disease IDs, names, synonyms, xrefs (OMIM, ORPHA) | `https://purl.obolibrary.org/obo/mondo.obo` (large; parse once, keep only our ~30 diseases and their synonyms) |
| HPO annotations | Disease → phenotype with frequency | `https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/phenotype.hpoa` and `genes_to_phenotype.txt` (same release) |
| HPO ontology | Phenotype names and hierarchy (for information content) | `https://purl.obolibrary.org/obo/hp.obo` |
| Orphadata | Disease ↔ gene, gene type of association | `https://www.orphadata.com/data/xml/en_product6.xml` (CC BY 4.0). Product 1 (nomenclature/xrefs) and 4 (phenotypes) also exist at the same path pattern |
| HGNC | Gene symbols, IDs, Entrez IDs | `https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt` |
| Reactome | Gene (Entrez) → pathway | `https://reactome.org/download/current/NCBI2Reactome_All_Levels.txt` + `ReactomePathways.txt` (filter to `Homo sapiens`) |
| ClinVar | Count of pathogenic/likely pathogenic variants per gene | `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/gene_specific_summary.txt` (small; avoid the 400 MB variant_summary) |
| PubMed | Abstracts, authors, affiliations, year | E-utilities `esearch` + `efetch` (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`), `NCBI_API_KEY` and `tool`/`email` params. About 30 most recent + 10 most cited per disease |
| PubTator3 (optional) | Pre-tagged genes/diseases in abstracts | `https://www.ncbi.nlm.nih.gov/research/pubtator3-api/` |
| ClinicalTrials.gov | Trials: conditions, interventions, phase, status, sites, sponsor, contacts | API v2 `https://clinicaltrials.gov/api/v2/studies?query.cond=<disease>` |
| NIH RePORTER | Grants, PIs, institutions, amounts | `POST https://api.reporter.nih.gov/v2/projects/search` |
| Patient organisations | Name, URL, diseases served, registry or natural history study yes/no, date checked | **Hand-curated** `data/manual/patient_orgs.csv` (from NORD, Global Genes, EURORDIS, Orphanet). Mark as `curated`, source = the org's URL |
| Assets | Natural history studies, registries, models | From trials (study type "observational"), RePORTER, and the patient org CSV |

OMIM needs an API key the user may not get in time. Don't depend on it; MONDO + Orphanet + HPO cover gene–disease links.

## Edge schema (`data/graph/edges.parquet` + `nodes.parquet`)

```
edge_id, subject, predicate, object,
evidence_type   # curated | text_mined | inferred
confidence      # 0–1
source          # e.g. "HPO annotations", "Orphadata product 6", "PubMed", "ClinicalTrials.gov"
source_record   # PMID:..., NCT..., file + row key
source_url
retrieved       # ISO date
evidence_text   # exact quote for text_mined, else empty
method          # for inferred edges
contradicts     # list of edge_ids
reviewer_verdict# supported | unsupported | partial | not_reviewed (Claude second check)
```

Predicates (Biolink-style names): `causes`, `gene_associated_with_disease`, `has_phenotype`, `participates_in_pathway`, `studied_in_trial`, `investigator_of`, `funded_by`, `serves_disease` (patient org), `has_asset`, `similar_to` (inferred), `contradicts`.

Confidence rules (keep simple and documented in README): curated from Orphadata "Disease-causing germline mutation(s)" = 0.95; HPO annotation = 0.9 (lower if frequency is "occasional"); text_mined "stated" = 0.7, "suggested" = 0.5; +0.15 if the Claude reviewer says supported, cap 0.95; inferred = the similarity score.

## Repo layout

```
CLAUDE.md  README.md  .env.example  .gitignore  pyproject.toml
src/llm.py  src/etl/*.py  src/graph/build.py  src/graph/similarity.py
notebooks/explore.py  notebooks/extract_molab.py
data/manual/  (committed)   data/raw/ data/cache/ (gitignored)   data/graph/ (committed, small)
app/app.py
```

## Milestones (do them in order; show the user the result of each)

1. **Setup:** uv project, `.gitignore` (with `.env`, `data/raw`, `data/cache`), `.env.example`, `src/llm.py`, plus a script that sends "hello" to the configured LLM. Done when the user sees a reply from gpt-oss.
2. **Disease list:** `data/manual/diseases.csv` with MONDO ID, name, gene(s), group. Look the IDs up in MONDO, don't guess them, and show the user the table to confirm.
3. **Biology layer:** MONDO synonyms, HPO phenotypes, Orphadata genes, HGNC, Reactome pathways, ClinVar counts as curated edges. Done when the MPS IIIC node has gene, pathway and phenotype edges and the counts are printed.
4. **Similarity and clusters:** phenotype similarity weighted by information content (IC = −log(fraction of our diseases with that phenotype, propagated up the HPO tree)), shared-pathway score, combined score, Louvain clusters. Done when MPS IIIA–D land in one cluster and the top shared phenotypes for each pair are listed.
5. **Research layer:** ClinicalTrials.gov, RePORTER, PubMed metadata. Write `data/cache/abstracts.jsonl` (pmid, title, abstract, disease_ids).
6. **Extraction:** `notebooks/extract_molab.py`, a marimo notebook the user runs on molab with the GPU on. It installs vLLM, starts `vllm serve openai/gpt-oss-20b` in the background, waits for it, reads the uploaded `abstracts.jsonl`, extracts edges with the JSON schema, checks quotes, and writes `edges_text_mined.jsonl` for the user to download into `data/cache/`. The same code must also run locally against Groq/OpenRouter with `.env` (fallback). Then optionally run the Claude reviewer on the extracted edges via Batches.
7. **Connections:** contradictions (same subject/object, opposite certainty), investigators appearing under two diseases in different clusters, assets shared within clusters.
8. **App:** one search box (name/synonym/gene/symptom → node, fuzzy match on MONDO synonyms), a graph view coloured by evidence type, an edge panel (source, date, confidence, quote, contradictions, reviewer verdict), a "Who is like us" ranked list with why and what differs, and "What to do next": assets, people, orgs, 1–3 next steps generated only from cited edge IDs, plus a "No supported route" screen.
9. **10× page, README, deploy:** milestone = starting a natural history study; existing timeline from a cited source versus the reuse route; assumptions listed. README covers architecture and the one-command rebuild (`uv run python -m src.graph.build`). Deploy and give the user the link.

## When unsure

Ask the user one short question, with a recommended default, and carry on with the default if they don't answer. Keep a running `NOTES.md` of decisions and anything that failed, so a new session can pick up where this one stopped.

## Current state and commands (as built; milestones 1–5 in progress)

Run everything from the repo root with `uv run`. There is no test suite or linter configured yet; verify by running a script and printing its summary.

```
uv run python -m src.hello_llm          # M1: LLM smoke test (reads .env)
uv run python -m src.etl.download       # downloads data/raw/* once (skips existing files)
uv run python -m src.etl.biology        # M3: writes data/graph/{nodes,edges}.parquet
uv run python -m src.graph.similarity   # M4: similarity_pairs.csv, clusters.csv, similar_to edges
uv run python -m src.etl.research       # M5: trials, grants, PubMed -> graph + data/cache/abstracts.jsonl
```

Order matters: `biology` creates the parquet files; later layers read them. `src/graph/build.py` (the planned one-command rebuild) does not exist yet.

### Architecture notes that span files

- `src/graph/schema.py` is the single gate for graph writes. Always build edges with `make_edge()` (it asserts source, date, confidence, evidence type, `method` for inferred, `evidence_text` for text_mined). Edge IDs are a hash of subject|predicate|object|source|source_record, so re-runs are stable.
- Layers are idempotent: `merge_layer(nodes, edges, node_types, predicates)` drops that layer's old node types and predicates, then adds the new rows. A new layer must declare which node types and predicates it owns, or re-runs will duplicate or clobber other layers. `biology.py` rewrites the whole graph (via `write_table`) and so must run first.
- `src/etl/terms.py` maps free text to our diseases (`match_diseases`, `search_phrases`) using MONDO names and synonyms. It returns `specific` vs `broad` (family) matches, and `research.py` gives broad matches lower confidence.
- `src/etl/research.py` caches each API response through `cached(source, key, fetch)` under `data/cache/`. Use it for any new API call so re-runs don't re-download.
- Known data quirk: MONDO files CLN10 (CTSD) under CLN1, so `biology.py` excludes that subtree via `EXCLUDE_SUBTREES`. Genes found only through a parent disease get `INDIRECT_CONFIDENCE`.
- Git: `.claude/skills` and `.agents/skills` are marimo skill files installed by the setup; `setup-steps.md` is the user's setup guide (molab for the GPU run, laptop for everything else).
