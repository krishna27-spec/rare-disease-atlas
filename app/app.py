"""Rare Disease Atlas: the Streamlit app. Reads only data/graph/ (and the LLM for one explanation)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from src.webapp.data import COLOURS, NEIGHBOUR_MIN, Graph
from src.webapp.explain import next_steps

st.set_page_config(page_title="Rare Disease Atlas", page_icon="🧬", layout="wide")


@st.cache_data
def load() -> Graph:
    return Graph()


@st.cache_data(show_spinner="Asking the AI to explain, using only cited facts...")
def cached_steps(disease: str, cand_json: str) -> dict:
    return next_steps(disease, json.loads(cand_json))


G = load()
DEFAULT = "MONDO:0009657"   # MPS IIIC: Maria's child


def badge(etype: str) -> str:
    return f":{ {'curated': 'blue', 'text_mined': 'orange', 'inferred': 'gray'}[etype] }-badge[{etype.replace('_', '-')}]"


def evidence(eids: list[str], label: str = "evidence") -> None:
    """A small expander with the full record behind a claim: source, date, confidence, quote."""
    eids = [e for e in dict.fromkeys(eids) if e]
    if not eids:
        return
    with st.expander(f"{label} ({len(eids)})"):
        for eid in eids[:6]:
            e = G.edge(eid)
            if not e:
                continue
            st.markdown(f"{badge(e['evidence_type'])} `{eid}` **{G.label(e['subject'])}** → {e['predicate']} → "
                        f"**{G.label(e['object'])}**")
            st.caption(f"Source: {e['source']} · record: {e['source_record']} · retrieved {e['retrieved']} · "
                       f"confidence {e['confidence']:.2f} · reviewer: {e['reviewer_verdict']}")
            if e["evidence_text"]:
                st.markdown(f"> “{e['evidence_text']}”")
            if e["source_url"]:
                st.markdown(f"[Open source]({e['source_url']})")
            if e["method"]:
                st.caption(f"How computed: {e['method']}")
        if len(eids) > 6:
            st.caption(f"... and {len(eids) - 6} more edges.")


# ------------------------------------------------------------------ top bar and search
st.title("🧬 Rare Disease Atlas")
st.caption("Find the families, studies and people already working on diseases like yours, with the evidence for each link.")
st.warning("Research exploration tool. **Not medical advice.** Always confirm with clinicians and researchers.", icon="⚠️")

q = st.text_input("Search a disease, gene or symptom", placeholder="e.g. Sanfilippo C, HGSNAT, seizures")
disease = st.session_state.get("disease", DEFAULT)
if q:
    hits = G.search(q)
    if not hits:
        st.error(f"No supported route found for “{q}”.")
        st.markdown(f"**What we searched:** the names and synonyms of our {len(G.diseases)} neuronopathic lysosomal "
                    f"storage diseases, {int((G.nodes.node_type == 'Gene').sum())} genes and "
                    f"{int((G.nodes.node_type == 'Phenotype').sum())} symptoms. Nothing matched closely enough.")
        st.markdown("**What evidence would change this:** this disease being added to the Atlas with its gene, symptoms, "
                    "trials and studies. Try a disease name, a gene symbol such as HGSNAT, or a symptom such as seizure.")
    else:
        top = hits[0]
        if top["kind"] == "disease":
            disease = top["id"]
            st.caption(f"Showing results for **{G.label(disease)}** ({disease}), matched from “{q}”")
            others = [h for h in hits[1:] if h["kind"] == "disease"][:3]
            if others:
                choice = st.radio("Did you mean", [G.label(disease)] + [h["label"] for h in others], horizontal=True)
                pick = {h["label"]: h["id"] for h in others}
                disease = pick.get(choice, disease)
        else:
            linked = G.diseases_for(top["kind"], top["id"])
            st.caption(f"**{top['label']}** ({top['kind']}) is linked to {len(linked)} of our diseases. Pick one:")
            if linked:
                labels = {G.label(x): x for x in linked}
                disease = labels[st.selectbox("Disease", list(labels))]
    st.session_state["disease"] = disease

f = G.facts(disease)
st.subheader(f"{G.label(disease)}  ·  {disease}")

tab_over, tab_like, tab_exist, tab_next, tab_10x, tab_about = st.tabs(
    ["Overview", "Who is like us", "What exists", "What to do next", "10× idea", "About the evidence"])

# ------------------------------------------------------------------ overview
with tab_over:
    c = st.columns(5)
    c[0].metric("Causal gene(s)", ", ".join(f["genes"]) or "none found")
    c[1].metric("Pathways", len(f["pathways"]))
    c[2].metric("Symptoms (HPO)", f["n_phenotypes"])
    c[3].metric("Trials", f["n_trials"])
    c[4].metric("Grants", f["n_grants"])
    st.markdown(f"**Cluster {f['cluster']}** groups diseases with similar symptoms and biology: "
                + ", ".join(f["cluster_members"]) + ".")
    if f["pathways"]:
        st.markdown("**Pathways of its gene(s):** " + "; ".join(G.label(p) for p in f["pathways"][:8])
                    + (" ..." if len(f["pathways"]) > 8 else ""))
    evidence(f["gene_edges"], "evidence for the gene link")
    st.markdown("**Evidence colours used throughout:** :blue-badge[curated] from a database or API · "
                ":orange-badge[text-mined] an AI read a paper, quote stored and checked · "
                ":gray-badge[inferred] our code computed it")

# ------------------------------------------------------------------ who is like us
with tab_like:
    nb = G.neighbours_of(disease)
    st.markdown("Ranked by similarity of symptoms (weighted towards rare, informative ones) and shared biology.")
    for r in nb.itertuples():
        weak = r.score < NEIGHBOUR_MIN
        st.markdown(f"### {r.rank}. {r.neighbour}" + ("  (weak match)" if weak else ""))
        st.progress(min(float(r.score), 1.0), text=f"similarity {r.score:.2f} "
                    f"(symptoms {r.phenotype_score:.2f}, pathways {r.pathway_score:.2f})")
        paths = json.loads(r.shared_pathways)
        shared_ph = json.loads(r.shared_phenotypes)
        only_here, only_nb = json.loads(r.only_here), json.loads(r.only_neighbour)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Why similar**")
            if paths:
                st.markdown(f"- {r.n_shared_pathways} shared pathways, e.g. " + "; ".join(p["name"] for p in paths[:3]))
            if shared_ph:
                st.markdown("- Shared informative symptoms: " + ", ".join(p["name"] for p in shared_ph))
            sg = json.loads(r.shared_genes)
            st.markdown(f"- Shared genes: {', '.join(sg) if sg else 'none (different causal genes)'}")
            evidence([r.similar_edge_id] + [i for p in paths for i in p["edge_ids"][:1]]
                     + [i for p in shared_ph for i in p["edge_ids"][:1]], "why: evidence")
        with c2:
            st.markdown("**What's different**")
            st.markdown(f"- Causal genes: {', '.join(json.loads(r.genes)) or '?'} here vs "
                        f"{', '.join(json.loads(r.neighbour_genes)) or '?'} there")
            if only_here:
                st.markdown(f"- Symptoms listed here but not for {r.neighbour}: " + ", ".join(p["name"] for p in only_here))
            if only_nb:
                st.markdown(f"- Listed for {r.neighbour} but not here: " + ", ".join(p["name"] for p in only_nb))
            evidence([i for p in only_here + only_nb for i in p["edge_ids"][:1]] + json.loads(r.gene_edge_ids), "difference: evidence")
    # graph view: disease in the centre, neighbours, genes
    st.markdown("#### Graph view")
    nodes, edges_, seen = [Node(id=disease, label=G.label(disease), size=28, color="#2ca02c")], [], {disease}
    for r in nb.head(4).itertuples():
        nodes.append(Node(id=r.neighbour_id, label=r.neighbour, size=20, color="#bbbbbb")); seen.add(r.neighbour_id)
        edges_.append(Edge(source=disease, target=r.neighbour_id, label=f"{r.score:.2f}", color=COLOURS["inferred"], dashes=True))
        for g in json.loads(r.neighbour_genes):
            if g not in seen:
                nodes.append(Node(id=g, label=g, size=12, color="#d9e6f2")); seen.add(g)
            edges_.append(Edge(source=r.neighbour_id, target=g, color=COLOURS["curated"]))
        for p in json.loads(r.shared_pathways)[:1]:
            if p["id"] not in seen:
                nodes.append(Node(id=p["id"], label=p["name"][:30], size=12, shape="box", color="#f4e3c1")); seen.add(p["id"])
            edges_ += [Edge(source=disease, target=p["id"], color=COLOURS["curated"]),
                       Edge(source=r.neighbour_id, target=p["id"], color=COLOURS["curated"])]
    for g in f["genes"]:
        nodes.append(Node(id=g, label=g, size=14, color="#d9e6f2")) if g not in seen else None
        seen.add(g); edges_.append(Edge(source=disease, target=g, color=COLOURS["curated"]))
    agraph(nodes=nodes, edges=edges_, config=Config(width=900, height=420, directed=False, physics=True))
    st.caption("Blue lines: curated database links. Grey dashed: our inferred similarity. Click a disease above for the evidence.")

# ------------------------------------------------------------------ what exists
with tab_exist:
    near = [disease] + G.neighbours_of(disease).query("score >= @NEIGHBOUR_MIN").neighbour_id.tolist()
    a = G.assets[G.assets.disease_id.isin(near)]
    if a.empty:
        st.info("No studies, registries or trials were found for this disease or its closest neighbours.")
    st.markdown("#### Studies, registries and trials")
    for dname, grp in a.groupby("disease", sort=False):
        grp = grp.sort_values("kind", key=lambda s: s.map({"natural history study": 0, "registry": 1}).fillna(2))
        with st.expander(f"{dname}: {len(grp)} items" + ("  (this disease)" if dname == G.label(disease) else ""),
                         expanded=dname == G.label(disease)):
            for r in grp.head(15).itertuples():
                st.markdown(f"- **{r.kind}**: [{r.title}]({r.source_url}) · {r.status or 'status n/a'} · {r.sponsor or 'sponsor n/a'} "
                            f"· `{r.edge_id}`")
            if len(grp) > 15:
                st.caption(f"{len(grp) - 15} more not shown.")
    st.markdown("#### People")
    ppl = G.people[G.people.diseases.map(lambda s: any(x[0] in near for x in json.loads(s)))]
    if ppl.empty:
        st.caption("No investigator in our data is listed across several of these diseases.")
    for r in ppl.head(8).itertuples():
        ds = [x[1] for x in json.loads(r.diseases)]
        st.markdown(f"- **{r.person}**, {r.affiliation or 'affiliation n/a'}: works across {r.n_diseases} diseases "
                    f"({', '.join(ds[:4])}{'...' if len(ds) > 4 else ''})")
    st.markdown("#### Patient organisations")
    if G.orgs.empty:
        st.caption("No patient organisations curated yet (data/manual/patient_orgs.csv).")
    else:
        o = G.orgs[G.orgs.mondo_ids.fillna("").str.contains(disease)] if "mondo_ids" in G.orgs else G.orgs
        for r in o.itertuples():
            st.markdown(f"- [{r.name}]({r.url}) · serves: {r.diseases_served} · registry/study: {r.registry_or_study} "
                        f"· checked {r.date_checked}")
        if o.empty:
            st.caption("No curated patient organisation covers this disease yet.")

# ------------------------------------------------------------------ what to do next
with tab_next:
    if G.no_route(disease):
        st.error("No supported route found for this disease.")
        st.markdown("**What we searched**")
        for s in G.searched_summary(disease):
            st.markdown(f"- {s}")
        st.markdown("**What evidence would change this:** a natural history study or registry for this disease; "
                    "papers linking its gene to a pathway shared with a better-studied disease; a patient group "
                    "reporting the same symptoms.")
    else:
        cands = G.candidates(disease)
        res = cached_steps(G.label(disease), json.dumps(cands))
        st.markdown("#### Suggested next steps")
        if res["steps"]:
            for s in res["steps"]:
                st.markdown(f"- {s}")
            st.caption("Written by an AI from the cited facts only; every sentence was checked to cite real edges.")
        else:
            if res["error"]:
                st.caption(res["error"] + " Showing the candidate actions found in the graph instead.")
            for c in cands[:3]:
                st.markdown(f"- {c['text']} " + " ".join(f"[{i}]" for i in c["edge_ids"][:3]))
        evidence([i for c in cands[:6] for i in c["edge_ids"]], "all evidence behind these steps")
        with st.expander("All candidate actions found in the graph"):
            for c in cands:
                st.markdown(f"- {c['text']}")
        st.info("**What an expert must check before acting:** whether each study is still recruiting or active, "
                "whether the diseases are close enough for the protocol to transfer, and whether the contact is current. "
                "This tool finds leads; it does not judge them.")

# ------------------------------------------------------------------ 10x
with tab_10x:
    from src.webapp.ten_x import render
    render(G, disease)

# ------------------------------------------------------------------ about
with tab_about:
    st.markdown((Path(__file__).resolve().parent.parent / "data" / "graph" / "STATS.md").read_text())
    st.markdown("""### How confidence is set
- **curated**: Orphadata germline-causing gene 0.95 (0.85 when found through a parent disease); HPO annotation 0.9 (lower if "occasional"); trials, grants and investigators 0.8 to 0.9.
- **text_mined**: 0.7 if the abstract states it, 0.5 if it only suggests it.
- **inferred**: the similarity score itself; the method is stored on each edge.

### How text-mined facts are checked
An AI reads each abstract, but a fact is kept only if its quoted sentence appears word for word in the abstract. Names must then resolve to stable IDs already in the graph (MONDO, HGNC, HP); otherwise the fact is dropped and counted above.

### Data sources
MONDO, HPO, Orphadata, HGNC, Reactome, ClinVar (counts), PubMed, ClinicalTrials.gov, NIH RePORTER. Each edge shows its own retrieval date.""")
