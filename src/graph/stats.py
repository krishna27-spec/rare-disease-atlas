"""Write data/graph/STATS.md: the numbers the README, the app's evidence tab and the video quote.

Run:  uv run python -m src.graph.stats   (after text_mined and connections)"""
import json
from pathlib import Path

import pandas as pd

from src.graph.schema import GRAPH_DIR

CACHE = Path("data/cache")


def lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def table(series: pd.Series, head: str) -> str:
    return f"| {head} | count |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in series.items()) + "\n"


def main() -> None:
    nodes = pd.read_parquet(GRAPH_DIR / "nodes.parquet")
    edges = pd.read_parquet(GRAPH_DIR / "edges.parquet")
    ext = lines(CACHE / "extractions.jsonl")
    facts = lines(CACHE / "edges_text_mined.jsonl")
    filtered = lines(CACHE / "abstracts_filtered.jsonl")
    n_abs = len(lines(CACHE / "abstracts.jsonl"))
    tm = edges[edges.evidence_type == "text_mined"]
    no_quote = sum(r["dropped"] for r in ext)
    reasons = json.loads((GRAPH_DIR / "text_mined_drops.json").read_text()) if (GRAPH_DIR / "text_mined_drops.json").exists() else {}
    conn = json.loads((GRAPH_DIR / "connections_summary.json").read_text())
    out = ["# Graph statistics\n", f"Built from `data/graph/` on {pd.Timestamp.today().date()}.\n",
           "## Nodes\n", table(nodes.node_type.value_counts(), "node type"),
           "## Edges by evidence type\n", table(edges.evidence_type.value_counts(), "evidence type"),
           "## Edges by predicate\n", table(edges.predicate.value_counts(), "predicate"),
           "## Text-mined facts\n",
           f"- {n_abs} abstracts collected; {len(filtered)} mention one of our diseases or genes "
           f"({n_abs - len(filtered)} off-topic removed before reading).",
           f"- {len(ext)} abstracts read by the LLM; {sum(1 for r in ext if r['facts'])} gave at least one fact.",
           f"- {len(facts)} facts kept after the quote check; {no_quote} more were dropped because the quoted sentence "
           "was not in the abstract.",
           f"- {len(tm)} became graph edges. Dropped while resolving to stable IDs: "
           + ", ".join(f"{v} {k}" for k, v in reasons.items()) + ".",
           "\n## Connections\n", f"- {conn['note']}",
           f"- {conn['shared_people']} investigators work across 2+ diseases ({conn['cross_cluster_people']} across clusters).",
           f"- {conn['assets']} asset/trial rows linked to diseases.\n"]
    (GRAPH_DIR / "STATS.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
