"""Rebuild the whole graph from the downloaded/cached data in one command.

Run:  uv run python -m src.graph.build
Each step reuses data/raw and data/cache, so nothing is re-downloaded. The LLM extraction (src.extract) is NOT
run here: it is slow and uses an LLM. Run it separately; this build just reads its cached output.
Order matters: biology creates the graph files, the later steps add to them."""
import subprocess
import sys

STEPS = [
    "src.etl.download",         # data/raw (skips files already there)
    "src.etl.biology",          # diseases, genes, phenotypes, pathways
    "src.etl.research",         # trials, grants, investigators, assets, PubMed abstracts
    "src.etl.timelines",        # real durations of Sanfilippo natural history studies (for the 10x tab)
    "src.graph.similarity",     # similar_to edges and clusters
    "src.etl.filter_abstracts", # drop off-topic abstracts before extraction
    "src.extract",              # only flattens already-extracted facts (limit 0)
    "src.graph.text_mined",     # facts -> text_mined edges
    "src.graph.connections",    # tables for the app
    "src.graph.stats",          # data/graph/STATS.md
]

if __name__ == "__main__":
    for mod in STEPS:
        args = ["--limit", "0"] if mod == "src.extract" else []
        print(f"\n=== {mod} ===", flush=True)
        if subprocess.run([sys.executable, "-m", mod, *args]).returncode:
            sys.exit(f"Step {mod} failed; fix it and re-run.")
