"""Milestone 6, last step: turn extracted facts into graph edges (evidence_type = text_mined).

Run:  uv run python -m src.graph.text_mined
Reads  data/cache/edges_text_mined.jsonl (from src.extract), data/cache/abstracts.jsonl, data/graph/*.parquet
Writes data/graph/{nodes,edges}.parquet  (replaces the previous text_mined edges and Paper nodes only)

A fact becomes an edge only if every name resolves to a stable ID already in the graph:
  disease   -> MONDO via src.etl.terms, and it must be one of the paper's own diseases
  gene      -> HGNC symbol (the symbol or its full name)
  phenotype -> HP term (name or HPO synonym)
Anything that does not resolve is dropped and counted. participates_in_pathway facts are dropped:
our pathway edges link genes (not diseases) to Reactome, so a disease->pathway claim has no valid home.
"""
import json
import re
from collections import Counter
from pathlib import Path

import obonet
import pandas as pd
import pyarrow.parquet as pq

from src.etl.download import RAW
from src.etl.genes import gene_aliases
from src.etl.terms import match_diseases, normalise
from src.graph.schema import EDGE_SCHEMA, GRAPH_DIR, NODE_SCHEMA, make_edge, write_table

CACHE = Path("data/cache")
CONF = {"stated": 0.7, "suggested": 0.5}


def phenotype_lookup(hp_ids: set[str]) -> dict[str, str]:
    """normalised phenotype name or synonym -> HP id, for HP terms already in the graph (ambiguous names dropped)."""
    hp = obonet.read_obo(RAW / "hp.obo")
    seen: dict[str, set[str]] = {}
    for hid in hp_ids & set(hp.nodes):
        names = [hp.nodes[hid]["name"]]
        names += [m.group(1) for s in hp.nodes[hid].get("synonym", []) if (m := re.search(r'"(.*?)"', s))]
        for n in names:
            seen.setdefault(normalise(n), set()).add(hid)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def main() -> None:
    facts = [json.loads(l) for l in (CACHE / "edges_text_mined.jsonl").read_text().splitlines()]
    papers = {}
    for l in (CACHE / "abstracts.jsonl").read_text().splitlines():
        r = json.loads(l)
        papers[r["pmid"]] = r
    nodes = pq.read_table(GRAPH_DIR / "nodes.parquet").to_pylist()
    edges = pq.read_table(GRAPH_DIR / "edges.parquet").to_pylist()
    nodes = [n for n in nodes if n["node_type"] != "Paper"]
    edges = [e for e in edges if e["evidence_type"] != "text_mined"]

    genes = gene_aliases({n["node_id"] for n in nodes if n["node_type"] == "Gene"})
    hp_nodes = {n["node_id"] for n in nodes if n["node_type"] == "Phenotype"}
    phenos = phenotype_lookup(hp_nodes)
    curated = {(e["subject"], e["predicate"], e["object"]) for e in edges}

    stats, new_edges, paper_ids = Counter(), [], set()
    for f in facts:
        stats["facts"] += 1
        if f["predicate"] == "participates_in_pathway":
            stats["dropped: pathway predicate has no disease->pathway home"] += 1
            continue
        mondo = [d for d, kind in match_diseases(f["disease"]) if kind == "specific" and d in f["disease_ids"]]
        if len(mondo) != 1:
            stats["dropped: out of scope (disease not one of ours / not this paper's)"] += 1
            continue
        key = normalise(f["object"])
        obj = genes.get(key) if f["predicate"] == "gene_associated_with_disease" else phenos.get(key)
        if obj is None:
            stats["dropped: unresolved (name not in graph)"] += 1
            continue
        pmid = f["pmid"]
        new_edges.append(make_edge(
            mondo[0], f["predicate"], obj, "text_mined", CONF[f["certainty"]], "PubMed", f"PMID:{pmid}",
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", f["date"], evidence_text=f["evidence_text"]))
        paper_ids.add(pmid)
        stats["also curated" if (mondo[0], f["predicate"], obj) in curated else "new to the graph"] += 1
    paper_nodes = [{"node_id": f"PMID:{p}", "node_type": "Paper", "name": papers[p]["title"],
                    "attrs": json.dumps({"pmid": p})} for p in sorted(paper_ids)]
    write_table(nodes + paper_nodes, NODE_SCHEMA, "nodes")
    write_table(edges + new_edges, EDGE_SCHEMA, "edges")
    print(f"{stats['facts']} facts read -> {len(new_edges)} text_mined edges, {len(paper_nodes)} Paper nodes")
    for k, v in stats.items():
        if k != "facts":
            print(f"  {v:5d}  {k}")
    drops = {k.replace("dropped: ", ""): v for k, v in stats.items() if k.startswith("dropped")}
    (GRAPH_DIR / "text_mined_drops.json").write_text(json.dumps(drops, indent=1))


if __name__ == "__main__":
    main()
