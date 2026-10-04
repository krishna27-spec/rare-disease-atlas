"""Rare Disease Atlas: the Streamlit app. Reads only data/graph/ (and the LLM for one explanation).

Flow: Search -> Understand -> Connect -> Verify -> Act. All styling lives in src/webapp/ui.py; the graph page in
src/webapp/network.py; the landing animation in src/webapp/intro.py."""
import json
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.webapp import intro, ui
from src.webapp.data import EDGE_ID, NEIGHBOUR_MIN, Graph
from src.webapp.explain import next_steps
from src.webapp.network import build_html

st.set_page_config(page_title="Rare Disease Atlas", page_icon="🧬", layout="wide", initial_sidebar_state="expanded")
st.html(ui.CSS)


@st.cache_data
def load() -> Graph:
    return Graph()


@st.cache_data(show_spinner="Asking the AI to explain, using only cited facts...")
def cached_steps(disease: str, cand_json: str) -> dict:
    return next_steps(disease, json.loads(cand_json))


@st.cache_data(show_spinner="Drawing the evidence graph...")
def cached_graph(disease: str) -> tuple[str, dict]:
    return build_html(load(), disease)


G = load()
DEFAULT = "MONDO:0009657"   # MPS IIIC: Maria's child
SUGGESTIONS = ["Sanfilippo C", "HGSNAT", "seizure", "Tay-Sachs", "cherry red spot"]
KIND_ICON = {"disease": "disease", "gene": "gene", "symptom": "symptom"}
LIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
STOPPED = {"TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN"}

ss = st.session_state
ss.setdefault("disease", DEFAULT)
ss.setdefault("entered", st.query_params.get("intro") == "0")


def enter():
    ss.entered = True


# ------------------------------------------------------------------ landing
if not ss.entered:
    st.html(intro.CSS)
    with st.container(key="intro_canvas"):
        st.iframe(intro.html(), height=720)
    with st.container(key="intro_brand"):
        st.html(f'<div class="brand"><div class="logo">{ui.icon("gene", 22, ui.LAVENDER)}</div>'
                '<div><div style="font-weight:600;color:#F5F3FA">Rare Disease Atlas</div></div></div>')
    with st.container(key="intro_skip"):
        st.button("Skip intro", on_click=enter, type="secondary")
    with st.container(key="intro_cta"):
        st.html('<div class="kicker">AI Atlas for the World’s Rare Diseases</div><h1>Rare Disease Atlas</h1>'
                '<div class="tagline">Connect the science. Find the path forward.</div>'
                '<div class="what">From one gene to the pathways, symptoms, related diseases, studies and people '
                'around it, with the evidence behind every link.</div>')
        st.button("Enter the Atlas", on_click=enter, type="primary", icon=":material/arrow_forward:",
                  icon_position="right")
    st.stop()


# ------------------------------------------------------------------ helpers
def evidence_cards(eids: list[str], limit: int = 6) -> None:
    """The full record behind a claim, as 'why is this connected?' cards."""
    eids = [e for e in dict.fromkeys(eids) if e]
    cards = []
    for eid in eids[:limit]:
        e = G.edge(eid)
        if e:
            cards.append(ui.evidence_card(e, G.label(e["subject"]), G.label(e["object"]), eid))
    if len(eids) > limit:
        cards.append(f'<div class="small">… and {len(eids) - limit} more edges.</div>')
    if cards:
        st.html("".join(cards))


def evidence(eids: list[str], label: str = "Evidence") -> None:
    eids = [e for e in dict.fromkeys(eids) if e]
    if eids:
        with st.expander(f"{label} ({len(eids)})", icon=":material/verified:"):
            evidence_cards(eids)


def cite(text: str) -> str:
    """Escape a sentence and turn the edge IDs in it into small citation chips."""
    t = re.sub(r"\[([^\[\]]*)\]", lambda m: m.group(1) if EDGE_ID.search(m.group(1)) else m.group(0), escape(text))
    return EDGE_ID.sub(lambda m: f'<span class="cite">{m.group(0)}</span>', t)


def kicker(step: str, title: str, sub: str = "", ic: str | None = None) -> None:
    st.html(ui.section(title, step, ic, sub))


def set_query(text: str):
    ss.q = text


def jump():
    ss.disease = ss.jump
    ss.q = ""


# ------------------------------------------------------------------ header + search
st.html(f"""<div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">
  <div class="brand"><div class="logo">{ui.icon("gene", 22, ui.LAVENDER)}</div>
    <div><h1>Rare Disease Atlas</h1><div class="tag">Find the families, studies and people already working on
    diseases like yours, with the evidence for each link.</div></div></div>
  <div class="disclaimer">{ui.icon("info", 16, ui.AMBER)}<span>Research exploration tool. <b>Not medical advice.</b>
    Always confirm with clinicians and researchers.</span></div></div>""")

with st.container(key="searchbox"):
    q = st.text_input("Search the Atlas", key="q", label_visibility="collapsed",
                      placeholder="Search a disease, gene or symptom: e.g. Sanfilippo C, HGSNAT, seizure")
if not q:
    with st.container(horizontal=True, key="suggest", gap="small", vertical_alignment="center"):
        st.html('<span class="small">Try</span>', width="content")
        for s in SUGGESTIONS:
            st.button(s, key=f"sg_{s}", on_click=set_query, args=(s,), type="secondary")

disease = ss.disease
if q:
    hits = G.search(q)
    if not hits:
        n_genes, n_ph = int((G.nodes.node_type == "Gene").sum()), int((G.nodes.node_type == "Phenotype").sum())
        st.html(ui.callout("empty", f"No supported route found for “{q}”",
                           f"<p><b>What we searched:</b> the names and synonyms of our {len(G.diseases)} neuronopathic "
                           f"lysosomal storage diseases, {n_genes} genes and {n_ph} symptoms. Nothing matched closely "
                           "enough.</p><p><b>What evidence would change this:</b> this disease being added to the Atlas "
                           "with its gene, symptoms, trials and studies. Try a disease name, a gene symbol such as "
                           "HGSNAT, or a symptom such as seizure.</p>"))
    else:
        st.html('<div class="row" style="margin:.2rem 0 .1rem"><span class="small">Matches:</span>'
                + "".join(ui.chip(f"{h['label']} · {h['kind']}", KIND_ICON.get(h["kind"])) for h in hits[:5]) + "</div>")
        top = hits[0]
        if top["kind"] == "disease":
            disease = top["id"]
            others = [h for h in hits[1:] if h["kind"] == "disease"][:3]
            if others:
                opts = [G.label(disease)] + [h["label"] for h in others]
                choice = st.pills("Did you mean", opts, default=opts[0], key=f"dym_{q}")
                pick = {h["label"]: h["id"] for h in others}
                disease = pick.get(choice, disease)
        else:
            linked = G.diseases_for(top["kind"], top["id"])
            st.html(f'<div class="small">{ui.icon(KIND_ICON.get(top["kind"], "info"), 14, ui.LAVENDER)} '
                    f'<b style="color:#F5F3FA">{escape(top["label"])}</b> ({top["kind"]}) is linked to '
                    f'{len(linked)} of our diseases. Pick one:</div>')
            if linked:
                labels = {G.label(x): x for x in linked}
                disease = labels[st.selectbox("Disease", list(labels))]
    ss.disease = disease

# ------------------------------------------------------------------ sidebar: navigation, legend, about
with st.sidebar:
    st.html(f'<div class="brand"><div class="logo">{ui.icon("gene", 20, ui.LAVENDER)}</div>'
            '<div><div style="font-weight:650;color:#F5F3FA">Rare Disease Atlas</div>'
            '<div class="small">Neuronopathic lysosomal storage diseases</div></div></div>')
    order = G.diseases.sort_values(["group", "name"])
    ss.jump = disease
    st.selectbox("Browse diseases", list(order.index), key="jump", on_change=jump,
                 format_func=lambda x: f"{G.label(x)}  ·  {G.diseases.loc[x, 'group']}")
    st.html('<div class="kicker" style="margin-top:1rem">How to read the evidence</div><div class="navlist">'
            + "".join(f'<div style="margin:.25rem 0">{ui.pill(k)}<div class="small" style="margin:.2rem 0 0 .2rem">'
                      f'{escape(m)}</div></div>' for k, (_, _, m) in ui.EVIDENCE.items())
            + f'<div style="margin:.35rem 0">{ui.icon("contradiction", 14, ui.RED)} <span class="small">Red marks '
              'contradicting evidence, when the graph has any.</span></div></div>')
    et = G.edges.evidence_type.value_counts()
    st.html('<div class="kicker" style="margin-top:1rem">In this Atlas</div>'
            f'<div class="small">{len(G.diseases)} diseases · {int((G.nodes.node_type == "Gene").sum())} genes · '
            f'{int((G.nodes.node_type == "Phenotype").sum())} symptoms · {int((G.nodes.node_type == "Trial").sum())} '
            f'trials · {int((G.nodes.node_type == "Grant").sum())} grants<br>{len(G.edges):,} edges: '
            f'{et.get("curated", 0):,} curated, {et.get("text_mined", 0)} text-mined, {et.get("inferred", 0)} inferred</div>')
    st.html('<div class="disclaimer" style="margin-top:1rem">Not medical advice. A research exploration tool.</div>')
    if st.button("Replay intro", type="tertiary", icon=":material/replay:"):
        ss.entered = False
        st.rerun()

# ------------------------------------------------------------------ entity hero (understand, in brief)
f = G.facts(disease)
name = G.label(disease)
group = G.diseases.loc[disease, "group"] if disease in G.diseases.index else ""
nb_all = G.neighbours_of(disease)
genes_txt = ", ".join(f["genes"])
summary = [f"The Atlas links <b>{escape(name)}</b> to the gene{'s' if len(f['genes']) > 1 else ''} "
           f"<b>{escape(genes_txt)}</b>." if f["genes"] else
           f"No causal gene for <b>{escape(name)}</b> is recorded in our data."]
if f["pathways"]:
    summary.append(f"{'These genes take' if len(f['genes']) > 1 else 'That gene takes'} part in "
                   f"<b>{len(f['pathways'])}</b> Reactome pathways.")
summary.append(f"It sits in cluster {f['cluster']} with <b>{len(f['cluster_members']) - 1}</b> other diseases that have "
               "similar symptoms and biology.")
summary.append(f"We hold {f['n_phenotypes']} recorded symptoms, {f['n_trials']} registered trials and "
               f"{f['n_grants']} NIH grants for it.")
st.html(f"""<div class="hero">
  <div><div class="type">{ui.icon("disease", 15, ui.LAVENDER)}Disease</div><h2>{escape(name)}</h2>
    <div class="ids">{ui.chip(disease, mono=True)}{ui.chip(group) if group else ""}{ui.chip(f"Cluster {f['cluster']}")}</div>
    <p class="summary">{" ".join(summary)}</p>
    {f'<p class="summary" style="margin-top:.5rem;font-size:.85rem">{escape(G.comparison_note(disease))}</p>' if G.comparison_note(disease) else ""}
  </div>
  <div class="tiles">
    {ui.tile("gene", "Causal gene(s)", genes_txt or "none found", "Orphadata / papers")}
    {ui.tile("pathway", "Pathways", len(f["pathways"]), "Reactome")}
    {ui.tile("symptom", "Symptoms", f["n_phenotypes"], "HPO annotations")}
    {ui.tile("trial", "Trials", f["n_trials"], "ClinicalTrials.gov")}
    {ui.tile("grant", "Grants", f["n_grants"], "NIH RePORTER")}
    {ui.tile("disease", "Close relatives", int((nb_all.score >= NEIGHBOUR_MIN).sum()), f"similarity ≥ {NEIGHBOUR_MIN}")}
  </div></div>""")
st.html(ui.flow(1))

tab_over, tab_like, tab_exist, tab_next, tab_10x, tab_about = st.tabs(
    [":material/biotech: Understand", ":material/hub: Connect · who is like us", ":material/inventory_2: What exists",
     ":material/flag: Act · next steps", ":material/rocket_launch: 10× route", ":material/fact_check: Evidence & method"])

# ------------------------------------------------------------------ understand
with tab_over:
    kicker("Step 2 · Understand", "The biology in brief", "Summary first. Open any evidence box to see the source.",
           "disease")
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.html('<div class="card"><h4>' + ui.icon("gene", 18, ui.KIND_ACCENT["gene"]) + 'Causal gene(s)</h4>'
                + ('<div style="margin-top:.4rem">' + "".join(ui.chip(g, "gene") for g in f["genes"]) + "</div>"
                   if f["genes"] else '<p>No gene link was found in our sources.</p>')
                + '<p>Variants in this gene are what the curated sources link to the disease. Genes are the starting '
                  'point: the same gene can act through different mechanisms.</p></div>')
        evidence(f["gene_edges"], "Why we link this gene")
        st.html('<div class="card"><h4>' + ui.icon("disease", 18, ui.LAVENDER) + f'Cluster {f["cluster"]}</h4>'
                '<p>Diseases grouped together because their symptoms and biology are similar.</p>'
                '<div style="margin-top:.5rem">' + "".join(ui.chip(m, "disease") for m in f["cluster_members"])
                + "</div></div>")
    with c2:
        paths = [G.label(p) for p in f["pathways"]]
        st.html('<div class="card"><h4>' + ui.icon("pathway", 18, ui.KIND_ACCENT["pathway"]) + 'Pathways of its gene(s)</h4>'
                '<p>Biological processes the gene’s product takes part in (Reactome). Diseases that share a specific '
                'pathway may share research.</p><div style="margin-top:.5rem">'
                + ("".join(ui.chip(p, "pathway") for p in paths[:8]) or '<span class="small">None found.</span>')
                + (f'<span class="small">+{len(paths) - 8} more below</span>' if len(paths) > 8 else "") + "</div></div>")
        if len(paths) > 8:
            with st.expander(f"All {len(paths)} pathways"):
                st.html("".join(ui.chip(p, "pathway") for p in paths))
        st.html('<div class="card"><h4>' + ui.icon("curated", 18, ui.GREEN) + 'How sure is each link?</h4>'
                '<p>Every connection in the Atlas carries its evidence type, source, retrieval date and confidence.</p>'
                '<div style="margin-top:.5rem">' + "".join(
                    f'<div style="margin:.35rem 0">{ui.pill(k)} <span class="small">{escape(m)}</span></div>'
                    for k, (_, _, m) in ui.EVIDENCE.items()) + "</div></div>")

# ------------------------------------------------------------------ connect: who is like us
with tab_like:
    kicker("Step 3 · Connect", "How this disease connects to its closest relatives",
           "Click a line in the graph to see why it exists: that is the Verify step.", "pathway")
    html, drawn = cached_graph(disease)
    st.iframe(html, height=640)
    st.html(f'<div class="small" style="margin-top:.4rem">Drawn: {drawn["curated"]} curated, {drawn["text_mined"]} '
            f'text-mined, {drawn["inferred"]} inferred edges. Generic Reactome pathways (Metabolism, Disease, Immune '
            'System, ...) are left out.</div>')

    kicker("Ranked", "Who is like us",
           "Ranked by similarity of symptoms (weighted towards rare, informative ones) and shared biology.")
    nb = G.neighbours_of(disease)
    if nb.empty:
        st.html(ui.callout("empty", "No similar diseases computed", "The similarity step found no neighbours."))
    for r in nb.itertuples():
        weak = r.score < NEIGHBOUR_MIN
        paths = json.loads(r.shared_pathways)
        shared_ph = json.loads(r.shared_phenotypes)
        only_here, only_nb = json.loads(r.only_here), json.loads(r.only_neighbour)
        sg = json.loads(r.shared_genes)
        g_here, g_there = ", ".join(json.loads(r.genes)) or "?", ", ".join(json.loads(r.neighbour_genes)) or "?"
        headline = (f"Shares {r.n_shared_pathways} pathway{'s' if r.n_shared_pathways != 1 else ''} and "
                    f"{len(shared_ph)} informative symptom{'s' if len(shared_ph) != 1 else ''}. "
                    + (f"Same gene: {', '.join(sg)}." if sg else f"Different causal gene ({g_here} here, {g_there} there)."))
        note = G.comparison_note(r.neighbour_id)
        st.html(f"""<div class="card" style="{'opacity:.72' if weak else ''}">
          <div class="row" style="justify-content:space-between">
            <h4><span class="rank">{r.rank}</span>{ui.icon("disease", 18, ui.LAVENDER)}{escape(r.neighbour)}
              {'<span class="weak">weak match</span>' if weak else ''}</h4>
            <div style="min-width:260px">{ui.meter(float(r.score), "inferred", f"similarity {r.score:.2f}")}</div></div>
          <div class="meta">symptoms {r.phenotype_score:.2f} · pathways {r.pathway_score:.2f} · computed, not observed</div>
          <p>{escape(headline)}</p>{f'<p class="small">{escape(note)}</p>' if note else ''}</div>""")
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("Why similar? Show the evidence", icon=":material/link:"):
                lines = []
                if paths:
                    lines.append(f"<li>{r.n_shared_pathways} shared pathways, e.g. "
                                 + "; ".join(escape(p["name"]) for p in paths[:3]) + "</li>")
                if shared_ph:
                    lines.append("<li>Shared informative symptoms: " + ", ".join(escape(p["name"]) for p in shared_ph) + "</li>")
                lines.append(f"<li>Shared genes: {escape(', '.join(sg)) if sg else 'none (different causal genes)'}</li>")
                st.html(f'<ul style="color:#B8B3C7;font-size:.9rem;margin:0 0 .4rem">{"".join(lines)}</ul>')
                evidence_cards([r.similar_edge_id] + [i for p in paths for i in p["edge_ids"][:1]]
                               + [i for p in shared_ph for i in p["edge_ids"][:1]])
        with c2:
            with st.expander("What’s different? Show the evidence", icon=":material/compare_arrows:"):
                lines = [f"<li>Causal genes: {escape(g_here)} here vs {escape(g_there)} there</li>"]
                if only_here:
                    lines.append(f"<li>Symptoms listed here but not for {escape(r.neighbour)}: "
                                 + ", ".join(escape(p["name"]) for p in only_here) + "</li>")
                if only_nb:
                    lines.append(f"<li>Listed for {escape(r.neighbour)} but not here: "
                                 + ", ".join(escape(p["name"]) for p in only_nb) + "</li>")
                st.html(f'<ul style="color:#B8B3C7;font-size:.9rem;margin:0 0 .4rem">{"".join(lines)}</ul>')
                evidence_cards([i for p in only_here + only_nb for i in p["edge_ids"][:1]] + json.loads(r.gene_edge_ids))

# ------------------------------------------------------------------ what exists
with tab_exist:
    kicker("Existing work", "Studies, registries and trials",
           f"For {name} and its close relatives (similarity ≥ {NEIGHBOUR_MIN}).", "asset")
    near = [disease] + G.neighbours_of(disease).query("score >= @NEIGHBOUR_MIN").neighbour_id.tolist()
    a = G.assets[G.assets.disease_id.isin(near)]
    if a.empty:
        st.html(ui.callout("empty", "Nothing registered yet",
                           "No studies, registries or trials were found for this disease or its closest neighbours."))
    for dname, grp in a.groupby("disease", sort=False):
        grp = grp.sort_values("kind", key=lambda s: s.map({"natural history study": 0, "registry": 1}).fillna(2))
        with st.expander(f"{dname}: {len(grp)} items" + ("  (this disease)" if dname == name else ""),
                         expanded=dname == name, icon=":material/science:"):
            rows = []
            for r in grp.head(15).itertuples():
                status = r.status or "status n/a"
                cls = "live" if r.status in LIVE else "stop" if r.status in STOPPED else ""
                kind_icon = "asset" if r.kind in ("registry", "natural history study") else "trial"
                rows.append(f"""<div style="padding:.55rem 0;border-bottom:1px solid #2A2338">
                  <div class="row">{ui.chip(r.kind, kind_icon)}<span class="status {cls}">{escape(status.replace('_', ' ').lower())}</span>
                  <span class="cite">{escape(r.edge_id)}</span></div>
                  <div style="margin-top:.25rem;font-size:.92rem"><a href="{escape(r.source_url or '')}" target="_blank" rel="noopener">{escape(r.title)}</a></div>
                  <div class="small">Sponsor: {escape(r.sponsor or 'n/a')}</div></div>""")
            if len(grp) > 15:
                rows.append(f'<div class="small" style="margin-top:.4rem">{len(grp) - 15} more not shown.</div>')
            st.html("".join(rows))

    kicker("People", "Investigators who work across these diseases", "Possible bridges between communities.", "person")
    ppl = G.people[G.people.diseases.map(lambda s: any(x[0] in near for x in json.loads(s)))]
    if ppl.empty:
        st.html(ui.callout("empty", "No shared investigators",
                           "No investigator in our data is listed across several of these diseases."))
    cards = []
    for r in ppl.head(8).itertuples():
        ds = [x[1] for x in json.loads(r.diseases)]
        cards.append(f'<div class="card"><h4>{ui.icon("person", 18, ui.TEXT2)}{escape(r.person)}</h4>'
                     f'<div class="meta">{escape(r.affiliation or "affiliation n/a")}</div>'
                     f'<p>Works across {r.n_diseases} diseases</p><div style="margin-top:.4rem">'
                     + "".join(ui.chip(x, "disease") for x in ds[:4]) + (f'<span class="small">+{len(ds) - 4} more</span>'
                                                                         if len(ds) > 4 else "") + "</div></div>")
    if cards:
        cols = st.columns(2)
        for i, c in enumerate(cards):
            cols[i % 2].html(c)

    kicker("Community", "Patient organisations", "Hand-checked from each organisation’s own website.", "org")
    if G.orgs.empty:
        st.html(ui.callout("empty", "None curated yet", "No patient organisations curated yet (data/manual/patient_orgs.csv)."))
    else:
        o = G.orgs[G.orgs.mondo_ids.fillna("").str.contains(disease)] if "mondo_ids" in G.orgs else G.orgs
        for r in o.itertuples():
            st.html(f'<div class="card"><h4>{ui.icon("org", 18, ui.LAVENDER)}<a href="{escape(r.url)}" target="_blank" '
                    f'rel="noopener">{escape(r.name)}</a></h4><div class="meta">Checked {escape(str(r.date_checked))}</div>'
                    f'<p><b style="color:#F5F3FA">Serves:</b> {escape(str(r.diseases_served))}<br>'
                    f'<b style="color:#F5F3FA">Registry or study:</b> {escape(str(r.registry_or_study))}</p></div>')
        if o.empty:
            st.html(ui.callout("empty", "No patient organisation on file", "No curated patient organisation covers this "
                               "disease yet."))

# ------------------------------------------------------------------ act: what to do next
with tab_next:
    kicker("Step 5 · Act", "What could we do together next?",
           "Every suggestion is built only from graph edges, and cites them.", "spark")
    if G.no_route(disease):
        st.html(ui.callout("error", "No supported route found for this disease",
                           "<b>What we searched</b><ul>" + "".join(f"<li>{escape(s)}</li>" for s in G.searched_summary(disease))
                           + "</ul><p style='margin-top:.5rem'><b>What evidence would change this:</b> a natural history "
                           "study or registry for this disease; papers linking its gene to a pathway shared with a "
                           "better-studied disease; a patient group reporting the same symptoms.</p>"))
    else:
        cands = G.candidates(disease)
        slot = st.empty()
        slot.html('<div class="skeleton" style="width:85%"></div><div class="skeleton" style="width:70%"></div>'
                  '<div class="skeleton" style="width:78%"></div>')
        res = cached_steps(name, json.dumps(cands))
        slot.empty()
        if res["steps"]:
            st.html("".join(f'<div class="opp"><span class="n">{i}</span><p>{cite(s)}</p></div>'
                            for i, s in enumerate(res["steps"], 1)))
            st.html(f'<div class="small">{ui.icon("text_mined", 13, ui.CYAN)} Written by an AI from the cited facts '
                    'only; every sentence was checked to cite real edges.</div>')
        else:
            if res["error"]:
                st.html(ui.callout("info", "Showing the actions found in the graph",
                                   escape(res["error"]) + " Showing the candidate actions found in the graph instead."))
            st.html("".join(f'<div class="opp"><span class="n">{i}</span><p>{escape(c["text"])} '
                            + " ".join(f'<span class="cite">{x}</span>' for x in c["edge_ids"][:3]) + "</p></div>"
                            for i, c in enumerate(cands[:3], 1)))
        evidence([i for c in cands[:6] for i in c["edge_ids"]], "All evidence behind these steps")
        with st.expander(f"All candidate actions found in the graph ({len(cands)})", icon=":material/list:"):
            st.html('<ul style="color:#B8B3C7;font-size:.9rem">' + "".join(f"<li>{escape(c['text'])}</li>" for c in cands)
                    + "</ul>")
        st.html(ui.callout("warn", "What an expert must check before acting",
                           "Whether each study is still recruiting or active, whether the diseases are close enough for "
                           "the protocol to transfer, and whether the contact is current. This tool finds leads; it does "
                           "not judge them."))

# ------------------------------------------------------------------ 10x
with tab_10x:
    from src.webapp.ten_x import render
    render(G, disease)

# ------------------------------------------------------------------ about
with tab_about:
    kicker("Verify", "About the evidence", "How the graph was built, how sure each link is, and what we checked.",
           "curated")
    st.html(ui.callout("ok" if not G.summary.get("contradictions") else "warn", "Contradictions",
                       escape(G.summary.get("note", ""))))
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown((Path(__file__).resolve().parent.parent / "data" / "graph" / "STATS.md").read_text())
    with c2:
        st.markdown("""### How confidence is set
- **curated**: Orphadata germline-causing gene 0.95 (0.85 when found through a parent disease); HPO annotation 0.9 (lower if "occasional"); trials, grants and investigators 0.8 to 0.9.
- **text_mined**: 0.7 if the abstract states it, 0.5 if it only suggests it.
- **inferred**: the similarity score itself; the method is stored on each edge.

In the interface, confidence is shown as **Strong** (0.85 or more), **Moderate** (0.6 to 0.85) or **Tentative** (below 0.6); inferred edges show their computed score instead.

### How text-mined facts are checked
An AI reads each abstract, but a fact is kept only if its quoted sentence appears word for word in the abstract. Names must then resolve to stable IDs already in the graph (MONDO, HGNC, HP); otherwise the fact is dropped and counted above.

### Data sources
MONDO, HPO, Orphadata, HGNC, Reactome, ClinVar (counts), PubMed, ClinicalTrials.gov, NIH RePORTER. Each edge shows its own retrieval date.""")

st.html('<div class="small" style="text-align:center;margin:2.5rem 0 1rem;border-top:1px solid #2A2338;padding-top:1rem">'
        'Rare Disease Atlas · research exploration tool, not medical advice · built from MONDO, HPO, Orphadata, HGNC, '
        'Reactome, ClinVar, PubMed, ClinicalTrials.gov and NIH RePORTER</div>')
