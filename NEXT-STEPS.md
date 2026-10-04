# NEXT-STEPS.md: from Milestone 6 to submission

**For Claude Code:** read this together with `CLAUDE.md` and `NOTES.md`. `CLAUDE.md` stays the spec and its hard rules still apply. This file replaces its Milestones 7–9 with a tighter, time-boxed plan, because about 8 hours remain. The user is a beginner: explain each step in one or two plain sentences, run things to prove they work, and commit after each step.

**Time budget (about 8 hours left):**

| Step | What | Time box |
|---|---|---|
| 0 | Check the current state | 15 min |
| 1 | Milestone 7: connections | 1 h |
| 2 | Milestone 8: Streamlit app | 3 h |
| 3 | Milestone 9: 10× page, README, deploy | 1.5 h |
| 4 | Demo rehearsal and video | 1.5 h |
| 5 | Optional extras, only if ahead | n/a |

If a step runs past its time box, stop, tell the user, take the simpler option listed under that step, and move on. **A working, deployed app with an honest, small graph beats a bigger graph with no app.**

## Decisions already made (don't revisit)

- Extraction runs on **Groq** (`openai/gpt-oss-20b`), not molab. Leave `notebooks/extract_molab.py` as is and mention it in the README as the path to scale up.
- **Drop the HGSNAT cross-correction claim.** No new predicate. Remove it from any demo text, app copy or README. It can appear only as "future work" in the video, and without stating it as fact.
- **22 diseases is fine.** Don't add more.
- **Claude reviewer:** skipped unless Step 5 has time.
- The app reads only from `data/graph/`. The LLM is used live only for the plain-language explanation, with a fallback message if the call fails.

---

## Step 0. Check the current state (15 min)

Run these checks and print a short status table for the user (done / not done / numbers):

1. **Git push.** `git status` and `git log origin/main..HEAD --oneline`. If commits are unpushed, ask the user to run, in their own terminal:
   ```bash
   sudo apt install -y gh
   gh auth login        # GitHub.com → HTTPS → Login with a web browser
   gh auth setup-git
   git push
   ```
   Don't handle tokens yourself. Continue with Step 1 while they do it.
2. **Off-topic filter.** Confirm that abstracts were filtered before extraction to those mentioning at least one of our diseases (names/synonyms from `terms.py`) or genes (symbols plus HGNC aliases and protein names). The yeast Cln1 paper must be out. If not done, add the filter and re-run on the filtered set (resumable, about 150 abstracts on Groq's free tier).
3. **Extraction output.** Count the lines in `data/cache/extractions.jsonl` and `edges_text_mined.jsonl`: abstracts processed, facts found, facts dropped for a missing quote, abstracts that failed.
4. **`src/graph/text_mined.py`.** Check that it exists and does what `HANDOFF.md` item 3 describes: resolve names to stable IDs (diseases restricted to the paper's `disease_ids`; genes to HGNC including protein-name aliases such as "tripeptidyl-peptidase I" → TPP1; phenotypes to HP by exact name/synonym match only; pathways to Reactome), drop unresolved facts and **count them by reason**, drop facts about out-of-scope diseases, set confidence 0.7 stated / 0.5 suggested, add Paper nodes, and merge with `merge_layer`. If missing or partial, finish it.
5. Rebuild the graph and print totals per node type, per evidence type and per predicate. Save the printout to `data/graph/STATS.md`; the README and video will quote these numbers.

**Done when** the user sees one status table, and `STATS.md` exists with counts like "N text-mined facts kept, M dropped (X unresolved, Y out of scope, Z no quote)".

---

## Step 1. Milestone 7: connections (1 hour)

Create `src/graph/connections.py`. It reads the graph and writes small tables to `data/graph/` for the app. Plain Python and pandas; no LLM.

1. **Contradictions** (`contradictions.parquet`): pairs of text-mined edges with the same subject and object where one is `stated` and the other is `contradicted` or a negative. If there are none, write an empty file and record "0 contradictions found among N text-mined facts". That's an honest result, and the app shows it.
2. **Shared investigators** (`shared_people.parquet`): investigators linked (through trials, grants or papers) to two or more diseases, especially in **different clusters**. Columns: person, diseases, clusters, the edge IDs that link them. This is the brief's "network overlap" finding, so print the top 10 for the user.
3. **Reusable assets per cluster** (`cluster_assets.parquet`): for each cluster, its registries, natural history studies (observational trials), models and biomarkers, with the disease each one belongs to. That is the "what already exists that we could reuse" list.
4. **Neighbour explanations** (`neighbours.parquet`): for every disease, its top 5 most similar diseases. For each pair include the score, the shared pathways, the top 5 shared phenotypes ranked by information content (with names), the shared genes, and **what differs**: phenotypes only one disease has (top 5 by IC) and different causal genes. Build "what differs" only from graph data.

**Done when** the script runs in under a minute, and the printout for MPS IIIC shows its neighbours with reasons, any shared people, and the assets in its cluster.

*If short on time:* skip contradictions (write the empty file plus the sentence) and keep items 2–4.

---

## Step 2. Milestone 8: the Streamlit app (3 hours)

`app/app.py`, plus helpers in `app/` if needed. Load the graph once with `@st.cache_data`. Use `st.tabs` for the views. Keep the design clean: lots of white space, one accent colour, and **evidence-type colours used consistently everywhere**: curated = blue, text-mined = orange, inferred = grey (dashed lines in the graph).

Build in this order and show the user after each part with `uv run streamlit run app/app.py`:

**2a. Top bar and search (30 min)**
- Title "Rare Disease Atlas", a one-line purpose, and a visible disclaimer: *"Research exploration tool. Not medical advice. Always confirm with clinicians and researchers."*
- One search box that accepts a disease name or synonym, a gene symbol, or a symptom. Fuzzy-match against MONDO synonyms, HGNC symbols and HP names (`rapidfuzz` is fine). Show "Showing results for MPS IIIC (MONDO:…), matched from 'sanfilipo c'".
- A gene or symptom search lists the diseases linked to it; clicking one opens that disease. Default to MPS IIIC so the demo opens on Maria's disease.

**2b. Overview tab (30 min)**
- Plain-language summary card: causal gene(s), pathway(s), number of phenotypes, number of trials, grants and patient orgs, and cluster name. Every number comes from the graph.
- Mini legend of the evidence types.

**2c. "Who is like us" tab (45 min)**
- Ranked neighbours from `neighbours.parquet`. For each: score bar, "Why similar" (shared pathway, top shared informative symptoms, shared genes) and "What's different" (from the data), each line with a small "evidence" expander showing the edge source, date, confidence and quote or record ID.
- A graph view (`streamlit-agraph` or `pyvis`) with the disease in the centre, its neighbours and the connecting genes and pathways, coloured by evidence type. Keep it to 30 nodes or fewer so it stays readable. *If the graph library fights you for more than 20 minutes, drop it and keep the ranked list.*

**2d. "What exists" tab (30 min)**
- Assets in the cluster (registries, natural history studies, models, trials), grouped by disease, with links to ClinicalTrials.gov / RePORTER / PubMed.
- People: investigators from `shared_people` first, labelled "works across N diseases in this cluster".
- Patient organisations from `data/manual/patient_orgs.csv` (or the graph), with website and the date it was checked.

**2e. "What to do next" tab (45 min)**
- Collect candidate actions **with code, from the graph**. For example: "Contact the team running observational study NCT… for MPS IIIA, which shares the heparan sulfate degradation pathway", "Ask Dr X, who works on both diseases", "Join or adapt registry Y".
- Send the LLM only those candidates and their edge IDs, with the instruction: *write 1–3 next steps for a parent with no medical background; cite the edge IDs in brackets after every claim; use only the facts given; if nothing is given, say no supported next step was found.* In code, check every bracketed ID exists in the input. Remove any sentence without a valid ID.
- Show each step with its citations as expandable evidence. Under it, a box: "What an expert must check before acting".
- **No supported route:** if a disease has no neighbours above the threshold and no assets, show a clear screen: what was searched (sources and counts), that no supported connection was found, and what evidence would change that (e.g. "a natural history study for this disease", "papers linking gene X to pathway Y"). Test this screen with a real disease from our list that has little data.
- If the LLM call fails, show the cited candidate actions as a plain list. The tab must never break.

**2f. "About the evidence" tab (15 min)**
- Show `STATS.md`: counts by evidence type, how confidence is set, how text-mined facts are checked (quote must appear in the abstract), how many facts were dropped and why, and the data sources with retrieval dates. Judges reward this honesty.

**Done when** the MPS IIIC journey works end to end (search → neighbours with reasons → reusable assets and people → cited next steps), and one disease shows the no-supported-route screen.

---

## Step 3. Milestone 9: 10× page, README, deploy (1.5 hours)

**3a. 10× tab in the app (30 min).** One milestone: **starting a natural history study for MPS IIIC.**
- "Usual route": how long setting up a rare-disease natural history study normally takes. **Use a cited source** (a paper or FDA/NIH guidance found via PubMed or the web, with the link). If you can't find one in 15 minutes, show the comparison as stated assumptions, clearly labelled, with no invented figures.
- "Atlas route": find the sister-disease study and team (from the graph), reuse the protocol, outcome measures and registry, and join forces.
- An assumptions list and "what must be validated next".

**3b. README (30 min).** Sections: what it does (a few lines plus a screenshot), the Maria journey, architecture (a simple diagram: sources → ETL → graph files → app, with gpt-oss via Groq for extraction and explanation), the evidence model (edge schema, the three evidence types, confidence rules, quote check), numbers from `STATS.md`, how to rebuild (`uv sync`, `.env.example`, the build commands in order), limitations (22 diseases, about 150 abstracts read, OMIM not used, patient orgs hand-curated, cross-correction question left as future work), and the scale-up path (the molab notebook, more diseases, the Claude reviewer).

**3c. Deploy (30 min).** Streamlit Community Cloud:
1. Make sure `data/graph/` files are committed and small (under about 50 MB in total). Large raw data stays out of git.
2. Add `requirements.txt` (`uv export --no-hashes > requirements.txt`), or check that Streamlit Cloud reads `pyproject.toml`.
3. Tell the user: share.streamlit.io → New app → repo `krishna27-spec/rare-disease-atlas`, branch `main`, file `app/app.py` → Advanced settings → Secrets: paste `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` in TOML format. Make the app read `st.secrets` first, then `.env`.
4. Open the deployed link and run the MPS IIIC journey. Fix anything broken.

*If Streamlit Cloud fails:* Hugging Face Spaces (Streamlit SDK) is the backup.

---

## Step 4. Demo rehearsal and video (1.5 hours)

Help the user by writing `DEMO_SCRIPT.md` with a 1-minute walkthrough (about 150 spoken words) and a longer team video outline (2–3 min). Suggested 1-minute flow:

1. (0–10 s) "Maria's child has MPS IIIC. No treatment, very few families. Where does she start?"
2. (10–25 s) Type "Sanfilippo C". Show the neighbours: MPS IIIA/IIIB share the heparan sulfate pathway and informative symptoms. Click one edge to show its source and quote.
3. (25–40 s) "What exists": a natural history study and investigators already working across these diseases.
4. (40–52 s) "What to do next": cited steps, and what an expert must check.
5. (52–60 s) The 10× idea in one sentence, plus the numbers that show the evidence is honest.

Show the user how to record the screen on Ubuntu: press **Print Screen**, switch to the video-camera icon in the capture bar, select the browser window and click record (or use OBS Studio). Record the app at the deployed link, not localhost.

---

## Step 5. Optional extras (only when Steps 0–4 are done)

In this order:
1. A bit more Groq extraction if the daily quota resets (resumable).
2. The Claude reviewer (`claude-haiku-4-5`, Message Batches) setting `reviewer_verdict` on text-mined edges, plus the +0.15 confidence rule; show the verdict in the evidence expander.
3. The molab GPU run for all filtered abstracts.

## Throughout

- Commit after every step with a clear message, and remind the user to `git push`.
- Update `NOTES.md` with decisions and anything that failed.
- Never show or commit keys.
- If anything in this file conflicts with `CLAUDE.md`'s hard rules, the hard rules win.
