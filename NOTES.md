
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

## Graph view rework (2026-10-04)
- Stray "None" under the old graph was Streamlit "magic" printing the value of `nodes.append(...) if ... else None`; the agraph block was removed.
- Graph is now pyvis (src/webapp/network.py), shown first in "Who is like us"; edge clicks show source/date/confidence/quote from data embedded in the page. Screenshot: docs/mps3c_graph.png.
- Generic Reactome pathways (roots + direct children, src/graph/reactome.py) are excluded from similarity, shared-pathway lists and the graph. Clusters after: MPS I, II, IIIA-D still together; Alpha-mannosidosis became its own cluster (was with GM1/Krabbe group).
- Text-mined edges for MPS IIIC existed already (7 before, now fewer after the new quote check) but the old graph never drew them; now drawn orange.
- Bug found and fixed: a text-mined edge SGSH -> MPS IIID came from a quote naming N-acetylglucosamine-6-sulphatase (GNS). text_mined.py now requires the quote to name the gene/symptom (or an alias); 5 facts dropped for this.
- "(contrast)" removed from names; app shows a graph-derived comparison note (Graph.comparison_note).

## UI redesign (branch ui-redesign, 2026-10-04)
- Frontend only: app/app.py, src/webapp/{ui,intro,network,ten_x}.py, .streamlit/config.toml. No change to data.py, explain.py, ETL, graph build or data files.
- ui.py holds the colour tokens, page CSS, icon set and HTML blocks. st.html strips inline <svg>, so icons are <img> tags with data-URI SVGs.
- Evidence colours changed to match the spec: curated green (solid), text-mined cyan (solid), inferred amber (dashed). Each also has its own glyph, so meaning is not colour-only.
- Landing: canvas animation in intro.py (helix -> one variant -> graph of entity types). Labels are entity types, not data. Holds until "Enter the Atlas"; "Skip intro" is always there. `?intro=0` in the URL skips it (handy for demos and tests). Honours prefers-reduced-motion.
- Graph page (network.py) no longer uses pyvis's template; it reuses pyvis's bundled vis-network JS with the same node/edge selection as before. Clicking a line shows "Why is this connected?"; clicking a node dims everything outside its neighbourhood. It re-fits when its tab becomes visible (it loads inside a hidden tab at size 0).
- Confidence words shown in the UI: Strong >= 0.85, Moderate >= 0.6, Tentative below; inferred edges show "Computed score". Documented in the Evidence & method tab.
- The plain-language "why" sentence for each edge (ui.relation_sentence) only restates the edge's own fields (source, predicate, subject, object).
- The reference video (portrait, 4.6 MB, watermarked) was used for mood only, not shipped.

## UX simplification (branch ui-redesign, 2026-10-04)
- Six views instead of a five-step flow: Explore, Biology, Connections, Research, Communities, Evidence. Only the active view renders (`ss.view`), so the LLM call runs only on Research. The top nav (segmented control) and the sidebar list share that state.
- After the intro: a home screen ("What would you like to explore?") with search, suggestions and five shortcuts into MPS IIIC. Entering plays a one-off zoom of the intro's network (`ui.transition_overlay`).
- Search shows one interpreted result card (disease / gene / symptom), up to 3 "Did you mean" alternatives, the rest behind "Show more". No match -> plain message + Browse diseases.
- Friendly evidence labels: Verified source (curated), Research literature (text-mined), Atlas-derived (inferred); technical names in tooltips and "Evidence details". Strength shown in words; the number is on hover.
- Removed from the permanent UI: step bar, sidebar legend, Atlas stats (now Evidence -> About the Atlas), top disclaimer (now a footer that expands).
- Graph: layout computed once off screen, then frozen; revealed in stages (disease -> gene -> pathways -> related diseases + symptoms); "Expand connections" or clicking a node reveals the rest. Edge click: light pulse, capped zoom, "Why is this connected?" with quote and technical record folded. The last selection per disease is kept in localStorage.
- Presentation-only orderings: pathways by how many of our genes share them (fewest first), symptoms by how many of our diseases have them (fewest first). Symptom counts are distinct symptoms (the backend's n_phenotypes counts edges, so an HPO + paper duplicate counted twice).
- Biology "How the gene is affected" is read from the Orphadata association type on the gene edge (e.g. "loss of function"); shown only when present.
- Research opportunities: the best study for the disease, then one reusable study/registry per related disease, then the rest. Built from existing asset and neighbour rows.
- Tested with AppTest: all 6 views x 22 diseases, home, searches and every Biology step, 0 failures.
