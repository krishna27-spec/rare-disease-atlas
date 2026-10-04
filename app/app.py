"""Rare Disease Atlas: the Streamlit app. Reads only data/graph/ (and the LLM for one explanation).

Six views of the same Atlas, in any order: Explore, Biology, Connections, Research, Communities, Evidence.
Simple information first; sources, scores, quotes and IDs one click deeper. All styling lives in
src/webapp/ui.py, the graph page in src/webapp/network.py, the landing animation in src/webapp/intro.py."""
import json
import logging
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from src.webapp import intro, ui
from src.webapp.data import EDGE_ID, NEIGHBOUR_MIN, Graph
from src.webapp.explain import next_steps
from src.webapp.network import build_html

st.set_page_config(page_title="Rare Disease Atlas", page_icon="🧬", layout="wide", initial_sidebar_state="auto")
st.html(ui.CSS)
log = logging.getLogger("atlas")


@st.cache_data
def load() -> Graph:
    return Graph()


@st.cache_data(show_spinner="Asking the AI to explain, using only cited facts...")
def cached_steps(disease: str, cand_json: str) -> dict:
    return next_steps(disease, json.loads(cand_json))


@st.cache_data(show_spinner="Building the biological map...")
def cached_graph(disease: str) -> tuple[str, dict]:
    return build_html(load(), disease)


G = load()
E = G.edges
DEFAULT = "MONDO:0009657"   # MPS IIIC: Maria's child
SUGGESTIONS = ["Sanfilippo C", "HGSNAT", "seizure", "Tay-Sachs", "cherry red spot"]
VIEWS = {"Explore": ":material/explore:", "Biology": ":material/biotech:", "Connections": ":material/hub:",
         "Research": ":material/science:", "Communities": ":material/groups:", "Evidence": ":material/verified:"}
KIND_NAME = {"disease": "Disease", "gene": "Gene", "symptom": "Symptom / trait"}
LIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
REUSABLE = ["natural history study", "registry"]

# Presentation-only orderings, computed from the existing graph. A pathway shared by fewer of our genes is more
# specific ("Heparan sulfate degradation" before "Metabolism"); a symptom recorded for fewer of our diseases is
# more distinctive.
GENES_PER_PATHWAY = E[E.predicate == "participates_in_pathway"].groupby("object").subject.nunique().to_dict()
DISEASES_PER_SYMPTOM = E[E.predicate == "has_phenotype"].groupby("object").subject.nunique().to_dict()

ss = st.session_state
ss.setdefault("entered", st.query_params.get("intro") == "0")
ss.setdefault("disease", None)
ss.setdefault("view", "Explore")
ss.setdefault("bio_sel", "gene")


# ------------------------------------------------------------------ state changes (all via callbacks)
def enter():
    ss.entered, ss.just_entered = True, True


def open_entity(d: str, view: str = "Explore"):
    ss.disease, ss.view, ss.bio_sel = d, view, "gene"
    ss.q, ss.q_home = "", ""


def go(view: str):
    ss.view = view


def set_query(key: str, text: str):
    ss[key] = text


def nav_changed():
    if ss.topnav_sel:
        ss.view = ss.topnav_sel


def browse_pick(key: str):
    if ss.get(key):
        open_entity(ss[key])
        ss[key] = None


# ------------------------------------------------------------------ landing
if not ss.entered:
    st.html(intro.CSS)
    with st.container(key="intro_canvas"):
        st.iframe(intro.html(), height=720)
    with st.container(key="intro_brand"):
        st.html(f'<div class="brand"><div class="logo">{ui.icon("gene", 22, ui.LAVENDER)}</div>'
                '<div class="name">Rare Disease Atlas</div></div>')
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

if ss.pop("just_entered", False):
    st.html(ui.transition_overlay())   # the intro's network zooms past, and the Atlas opens out of it


# ------------------------------------------------------------------ small helpers
def label(x: str) -> str:
    return G.label(x)


def genes_of(d: str) -> list[str]:
    return G.facts(d)["genes"]


def n_symptoms(d: str) -> int:
    """Distinct symptoms (a symptom from HPO and the same one quoted from a paper count once)."""
    return int(E[(E.subject == d) & (E.predicate == "has_phenotype")].object.nunique())


def strong_neighbours(d: str) -> pd.DataFrame:
    return G.neighbours_of(d).query("score >= @NEIGHBOUR_MIN")


def html_if(body: str) -> None:
    """st.html refuses an empty body; empty sections simply render nothing."""
    if body:
        st.html(body)


def evidence_cards(eids: list[str], limit: int = 6) -> None:
    eids = [e for e in dict.fromkeys(eids) if e]
    cards = []
    for eid in eids[:limit]:
        e = G.edge(eid)
        if e:
            cards.append(ui.evidence_card(e, label(e["subject"]), label(e["object"]), eid))
    if len(eids) > limit:
        cards.append(f'<div class="small">… and {len(eids) - limit} more.</div>')
    if cards:
        html_if("".join(cards))


def evidence(eids: list[str], title: str = "Evidence") -> None:
    eids = [e for e in dict.fromkeys(eids) if e]
    if eids:
        with st.expander(f"{title} ({len(eids)})", icon=":material/verified:"):
            evidence_cards(eids)


def cite(text: str) -> str:
    """Escape a sentence and turn the edge IDs in it into small citation chips."""
    t = re.sub(r"\[([^\[\]]*)\]", lambda m: m.group(1) if EDGE_ID.search(m.group(1)) else m.group(0), escape(text))
    return EDGE_ID.sub(lambda m: f'<span class="cite">{m.group(0)}</span>', t)


def status_tag(status: str | None) -> str:
    s = (status or "status unknown").replace("_", " ").lower()
    return f'<span class="status{" live" if status in LIVE else ""}">{escape(s)}</span>'


def asset_row(r) -> str:
    return (f'<div class="item"><div class="row">{ui.chip(r.kind, "asset" if r.kind in REUSABLE else "trial")}'
            f'{status_tag(r.status)}</div><div class="t" style="margin-top:.35rem"><a href="{escape(r.source_url or "")}" '
            f'target="_blank" rel="noopener">{escape(r.title)}</a></div>'
            f'<div class="m">Sponsor: {escape(r.sponsor or "not listed")}</div></div>')


def sort_assets(a: pd.DataFrame) -> pd.DataFrame:
    order = {"natural history study": 0, "registry": 1, "observational study": 2}
    return a.assign(_k=a.kind.map(order).fillna(3), _l=~a.status.isin(LIVE)).sort_values(["_k", "_l"])


def specific_pathways(d: str) -> list[str]:
    return sorted(G.facts(d)["pathways"], key=lambda p: (GENES_PER_PATHWAY.get(p, 99), label(p)))


def orgs_for(d: str) -> pd.DataFrame:
    if G.orgs.empty or "mondo_ids" not in G.orgs:
        return G.orgs.iloc[0:0]
    return G.orgs[G.orgs.mondo_ids.fillna("").str.contains(d)]


def people_for(ds: set[str]) -> pd.DataFrame:
    return G.people[G.people.diseases.map(lambda s: any(x[0] in ds for x in json.loads(s)))]


def browse(key: str, text: str = "Browse diseases") -> None:
    with st.popover(text, icon=":material/list:"):
        order = G.diseases.sort_values(["group", "name"])
        st.selectbox("Choose a disease", list(order.index), index=None, key=key, on_change=browse_pick, args=(key,),
                     placeholder="All diseases in the Atlas",
                     format_func=lambda x: f"{label(x)}  ·  {G.diseases.loc[x, 'group']}")


# ------------------------------------------------------------------ search
def search_results(q: str, qkey: str) -> None:
    """One clear interpretation first, a few alternatives, the rest behind 'Show more'."""
    hits = G.search(q, limit=12)
    if not hits:
        st.html(ui.callout("empty", "We couldn’t find a supported match.",
                           f"We searched the names and synonyms of {len(G.diseases)} diseases, "
                           f"{int((G.nodes.node_type == 'Gene').sum())} genes and "
                           f"{int((G.nodes.node_type == 'Phenotype').sum())} symptoms for “{escape(q)}”."
                           "<ul><li>another disease name or synonym (e.g. Sanfilippo C)</li><li>a gene symbol "
                           "(e.g. HGSNAT)</li><li>a symptom (e.g. seizure)</li></ul>"))
        browse(f"browse_{qkey}")
        return
    top, rest = hits[0], hits[1:]
    with st.container(border=True, key=f"result_{qkey}"):
        if top["kind"] == "disease":
            d, f = top["id"], G.facts(top["id"])
            st.html(f'<div class="hero"><div class="type">{ui.icon("disease", 14, ui.LAVENDER)}Disease</div>'
                    f'<h1 style="font-size:1.7rem !important">{escape(label(d))}</h1>'
                    f'<div class="gene">{ui.icon("gene", 16, ui.KIND_ACCENT["gene"])}Main gene <b style="font-size:1rem">'
                    f'{escape(", ".join(f["genes"]) or "not recorded")}</b></div>'
                    + ui.stats([("pathway", len(f["pathways"]), "pathways"), ("symptom", n_symptoms(d), "symptoms"),
                                ("trial", f["n_trials"], "trials")]) + "</div>")
            with st.container(horizontal=True):
                st.button("Open in the Atlas", key=f"open_{qkey}", type="primary", on_click=open_entity, args=(d,),
                          icon=":material/arrow_forward:", icon_position="right")
                st.button("Connections", key=f"openc_{qkey}", on_click=open_entity, args=(d, "Connections"))
                st.button("Research", key=f"openr_{qkey}", on_click=open_entity, args=(d, "Research"))
        else:
            linked = list(dict.fromkeys(G.diseases_for(top["kind"], top["id"])))
            name = top["label"] if top["kind"] == "gene" else label(top["id"])
            extra = ""
            if top["kind"] == "gene":
                full = label(top["id"])
                paths = E[(E.subject == top["id"]) & (E.predicate == "participates_in_pathway")].object.unique()
                paths = sorted(paths, key=lambda p: (GENES_PER_PATHWAY.get(p, 99), label(p)))[:3]
                extra = (f'<div class="small" style="margin-top:.2rem">{escape(full)}</div>'
                         + (f'<div class="m" style="margin-top:.7rem;color:#B8B3C7">Related pathways</div><div>'
                            + "".join(ui.chip(label(p), "pathway") for p in paths) + "</div>" if paths else ""))
            st.html(f'<div class="hero"><div class="type">{ui.icon(top["kind"], 14, ui.LAVENDER)}'
                    f'{KIND_NAME[top["kind"]]}</div><h1 style="font-size:1.7rem !important">{escape(name)}</h1>{extra}'
                    f'<div class="m" style="margin-top:.7rem;color:#B8B3C7">Associated disease'
                    f'{"s" if len(linked) != 1 else ""} in the Atlas: {len(linked)}</div></div>')
            if linked:
                with st.container(horizontal=True):
                    for x in linked[:4]:
                        st.button(label(x), key=f"lk_{qkey}_{x}", on_click=open_entity,
                                  args=(x, "Connections" if top["kind"] == "gene" else "Explore"),
                                  icon=":material/arrow_forward:", icon_position="right")
                if len(linked) > 4:
                    with st.expander(f"Show {len(linked) - 4} more diseases"):
                        for x in linked[4:]:
                            st.button(label(x), key=f"lkm_{qkey}_{x}", on_click=open_entity, args=(x,), type="tertiary")
            else:
                st.html('<div class="small">No disease in the Atlas is linked to it.</div>')
    if rest:
        st.html('<div class="small" style="margin:.6rem 0 .1rem">Did you mean</div>')
        for h in rest[:3]:
            alt_open(h, qkey)
        if len(rest) > 3:
            with st.expander(f"Show more ({len(rest) - 3})"):
                for h in rest[3:]:
                    alt_open(h, qkey)


def alt_open(h: dict, qkey: str) -> None:
    text = f"{h['label']} — {KIND_NAME[h['kind']]}"
    if h["kind"] == "disease":
        st.button(text, key=f"alt_{qkey}_{h['id']}", type="tertiary", on_click=open_entity, args=(h["id"],))
    else:
        st.button(text, key=f"alt_{qkey}_{h['id']}", type="tertiary", on_click=set_query, args=(qkey, h["label"]))


# ------------------------------------------------------------------ sidebar: navigation only
d = ss.disease
with st.sidebar:
    st.html(f'<div class="brand" style="margin-bottom:1rem"><div class="logo">{ui.icon("gene", 20, ui.LAVENDER)}</div>'
            '<div class="name">Rare Disease Atlas</div></div>')
    if d:
        st.html('<div class="side-label">Current disease</div>')
        with st.container(key="current"):
            st.button(label(d), on_click=go, args=("Explore",), help="Back to the overview", width="stretch")
        st.html('<div class="side-rule"></div>')
        with st.container(key="sidenav", gap="small"):
            for v, ic in VIEWS.items():
                st.button(v, key=f"nav_{v}", icon=ic, on_click=go, args=(v,), width="stretch",
                          type="primary" if ss.view == v else "secondary")
        st.html('<div class="side-rule"></div>')
    browse("browse_side")
    if st.button("Replay intro", type="tertiary", icon=":material/replay:"):
        ss.entered = False
        st.rerun()


def footer() -> None:
    st.html('<div class="footer"><details><summary>ⓘ Research tool · Not medical advice</summary><p>This Atlas is a '
            'research exploration tool. It is not medical advice. Always confirm medical decisions with qualified '
            'clinicians and researchers.</p></details></div>')


# ------------------------------------------------------------------ home: one clear starting point
if not d:
    st.html('<div class="home"><h1>What would you like to explore?</h1><p>Search a disease, gene or symptom, or start '
            'from an example below.</p></div>')
    with st.container(key="searchbox_home"):
        qh = st.text_input("Search the Atlas", key="q_home", label_visibility="collapsed",
                           placeholder="e.g. Sanfilippo C, HGSNAT, seizure")
    if qh:
        search_results(qh, "q_home")
    else:
        with st.container(horizontal=True, gap="small", vertical_alignment="center"):
            st.html('<span class="small">Try</span>', width="content")
            for s in SUGGESTIONS:
                st.button(s, key=f"sg_{s}", on_click=set_query, args=("q_home", s))
        st.html(f'<div class="sec"><h3>Or start with an example: {escape(label(DEFAULT))}</h3>'
                '<p class="sec-sub">The disease in our demo story. Each option opens the same Atlas at a different view.'
                '</p></div>')
        c, _ = st.columns([1.15, 1])
        with c, st.container(key="shortcuts", gap="small"):
            for text, view, ic in [("Understand a disease", "Explore", ":material/explore:"),
                                   ("Explore its biology", "Biology", ":material/biotech:"),
                                   ("Find related diseases", "Connections", ":material/hub:"),
                                   ("Find research & studies", "Research", ":material/science:"),
                                   ("Find patient communities", "Communities", ":material/groups:")]:
                st.button(text, key=f"sc_{view}", icon=ic, on_click=open_entity, args=(DEFAULT, view), width="stretch")
    footer()
    st.stop()


# ------------------------------------------------------------------ atlas: search + six views
with st.container(key="searchbox"):
    q = st.text_input("Search the Atlas", key="q", label_visibility="collapsed",
                      placeholder="Search a disease, gene or symptom")
if q:
    search_results(q, "q")

ss.topnav_sel = ss.view
with st.container(key="topnav"):
    st.segmented_control("View", list(VIEWS), key="topnav_sel", on_change=nav_changed, required=True,
                         label_visibility="collapsed", format_func=lambda v: f"{VIEWS[v]} {v}")

f = G.facts(d)
name = label(d)
nbs = strong_neighbours(d)


def entity_line() -> None:
    st.html(f'<div class="entity">{ui.icon("disease", 16, ui.LAVENDER)}<b>{escape(name)}</b>'
            f'<span>{escape(", ".join(f["genes"]))}</span></div>')


def view_explore() -> None:
    # the example pathway: the most specific one this disease shares with a close relative
    shared = {p["id"]: p["name"] for r in nbs.itertuples() for p in json.loads(r.shared_pathways)}
    paths = sorted(shared, key=lambda p: GENES_PER_PATHWAY.get(p, 99)) or specific_pathways(d)
    n_orgs = len(orgs_for(d))
    lead = (f"<b>{escape(name)}</b> is linked to the gene <b>{escape(', '.join(f['genes']))}</b>. " if f["genes"] else
            f"No causal gene for <b>{escape(name)}</b> is recorded in our data. ")
    if paths:
        lead += f"Its gene takes part in biological pathways such as <b>{escape(label(paths[0]))}</b>. "
    lead += (f"The Atlas connects it to {len(nbs)} related disease{'s' if len(nbs) != 1 else ''}, "
             f"{f['n_trials']} registered trials and studies, and {n_orgs} patient organisation"
             f"{'s' if n_orgs != 1 else ''}.")
    group = G.diseases.loc[d, "group"]
    note = G.comparison_note(d)
    st.html(f"""<div class="hero" style="margin-top:1.2rem"><div class="type">{ui.icon("disease", 14, ui.LAVENDER)}Rare disease
      · {escape(group)}</div><h1>{escape(name)}</h1>
      {f'<div class="gene">{ui.icon("gene", 18, ui.KIND_ACCENT["gene"])}<b>{escape(", ".join(f["genes"]))}</b>causal gene</div>' if f["genes"] else ''}
      <p class="lead">{lead}</p>{f'<p class="small" style="max-width:720px;margin-top:.5rem">{escape(note)}</p>' if note else ''}
      {ui.stats([("pathway", len(f["pathways"]), "pathways"), ("symptom", n_symptoms(d), "symptoms"),
                 ("trial", f["n_trials"], "trials"), ("grant", f["n_grants"], "grants"),
                 ("disease", len(nbs), "close relatives")])}</div>""")
    st.html(ui.section("Where would you like to go next?"))
    with st.container(key="next"):
        c1, c2 = st.columns(2, gap="small")
        items = [("How it works", "Biology", ":material/biotech:"), ("Related diseases", "Connections", ":material/hub:"),
                 ("Research & studies", "Research", ":material/science:"),
                 ("Patient communities", "Communities", ":material/groups:"),
                 ("Why trust this?", "Evidence", ":material/verified:")]
        for i, (text, view, ic) in enumerate(items):
            (c1 if i % 2 == 0 else c2).button(f"{text}  →", key=f"nx_{view}", icon=ic, on_click=go, args=(view,), width="stretch")


def view_biology() -> None:
    entity_line()
    st.html(ui.view_head("How does this disease work?",
                         "Follow the chain from the disease to its gene, the biological pathways it takes part in, "
                         "and the symptoms people experience. Click a step to see more."))
    gene_edges = E[(E.object == d) & (E.predicate == "gene_associated_with_disease") & (E.evidence_type == "curated")]
    mech = ""
    for rec in gene_edges.source_record:
        parts = str(rec).split("|")
        if len(parts) > 2 and parts[2]:
            mech = re.sub(r"\s+in$", "", parts[2].strip())
    brackets = re.findall(r"\(([^()]+)\)", mech)       # "mutation(s) (loss of function)" -> "loss of function"
    mech_short = brackets[-1] if brackets else (mech or "not recorded")
    ph = E[(E.subject == d) & (E.predicate == "has_phenotype")]
    steps = [("disease", f"{name}", "Disease"), ("gene", ", ".join(f["genes"]) or "not recorded", "Gene"),
             ("mech", mech_short, "How the gene is affected"), ("path", f"{len(f['pathways'])} pathways", "Biology"),
             ("pheno", f"{ph.object.nunique()} symptoms", "What people experience")]
    left, right = st.columns([1, 1.5], gap="large")
    with left, st.container(key="chain", gap="small"):
        for i, (k, text, small) in enumerate(steps):
            st.button(f"{small}: **{text}**", key=f"bio_{k}", on_click=set_query, args=("bio_sel", k), width="stretch",
                      type="primary" if ss.bio_sel == k else "secondary")
            if i < len(steps) - 1:
                st.html('<div class="arrow">↓</div>')
    with right:
        sel = ss.bio_sel
        if sel == "disease":
            syn = [s for s in list(G.diseases.loc[d, "synonyms"]) if s.lower() != name.lower()][:6]
            st.html(ui.section(name, "Disease") + f'<div>{ui.chip(d, mono=True)}{ui.chip(G.diseases.loc[d, "group"])}</div>'
                    + (f'<p class="small" style="margin-top:.6rem">Also known as: {escape("; ".join(syn))}</p>' if syn else ""))
            st.button("See its related diseases  →", on_click=go, args=("Connections",), type="tertiary")
        elif sel == "gene":
            st.html(ui.section("The gene", "Variants in this gene are what the curated sources link to the disease."))
            for g in f["genes"]:
                row = G.nodes[G.nodes.node_id == g].iloc[0]
                cv = row.clinvar_pathogenic_alleles
                st.html(f'<div class="item"><div class="t">{ui.icon("gene", 16, ui.KIND_ACCENT["gene"])} {escape(g)}</div>'
                        f'<div class="w">{escape(row["name"])}</div><div class="m">{escape(str(row.hgnc_id or ""))}'
                        + (f' · {int(cv)} pathogenic or likely pathogenic variants listed in ClinVar' if cv == cv else "")
                        + "</div></div>")
            evidence(f["gene_edges"], "Why we link this gene")
        elif sel == "mech":
            st.html(ui.section("How the gene is affected"))
            if mech:
                st.html(f'<p class="vsub">Orphanet records this gene–disease link as: <b style="color:#F5F3FA">'
                        f'{escape(mech)}</b>.</p>'
                        + ('<p class="small" style="margin-top:.5rem">“Loss of function” means the variants stop the '
                           'gene’s product from working.</p>' if "loss of function" in mech.lower() else ""))
                evidence(gene_edges.edge_id.tolist(), "Source")
            else:
                st.html(ui.callout("empty", "Not recorded", "Orphanet does not record how the gene is affected for this "
                                   "disease, so the Atlas does not state a mechanism."))
        elif sel == "path":
            paths = specific_pathways(d)
            st.html(ui.section(f"{len(paths)} pathways", "Biological processes the gene’s product takes part in "
                               "(Reactome). Most specific first."))
            st.html("<div>" + "".join(ui.chip(label(p), "pathway") for p in paths[:5]) + "</div>")
            if len(paths) > 5:
                with st.expander(f"Show all {len(paths)} pathways"):
                    html_if("".join(ui.chip(label(p), "pathway") for p in paths))
            pick = st.selectbox("Why is a pathway linked?", paths, index=None, format_func=label,
                                placeholder="Pick a pathway to see its evidence")
            if pick:
                evidence_cards(E[(E.object == pick) & E.subject.isin(f["genes"])
                                 & (E.predicate == "participates_in_pathway")].edge_id.tolist())
        elif sel == "pheno":
            ph = ph.assign(_n=ph.object.map(DISEASES_PER_SYMPTOM).fillna(99), _t=ph.evidence_type != "text_mined")
            ph = ph.sort_values(["_t", "_n"]).drop_duplicates("object")
            st.html(ui.section(f"{len(ph)} symptoms and traits",
                               "Most distinctive first: symptoms recorded for fewer of our diseases come first. "
                               "Symptoms quoted from published studies are marked."))
            st.html("<div>" + "".join(ui.chip(label(o) + (" ◌" if t == "text_mined" else ""), "symptom")
                                      for o, t in zip(ph.object[:10], ph.evidence_type[:10])) + "</div>"
                    + '<div class="small">◌ = from research literature</div>')
            if len(ph) > 10:
                with st.expander(f"Show all {len(ph)}"):
                    html_if("".join(ui.chip(label(o), "symptom") for o in ph.object))
            pick = st.selectbox("Why is a symptom linked?", ph.object.tolist(), index=None, format_func=label,
                                placeholder="Pick a symptom to see its evidence")
            if pick:
                evidence_cards(E[(E.subject == d) & (E.object == pick)].edge_id.tolist())


def view_connections() -> None:
    entity_line()
    st.html(ui.view_head("What is connected to it?",
                         "The map starts with the closest links. Expand it, or click a node to go further. Click a "
                         "line to see why it exists."))
    html, _ = cached_graph(d)
    st.iframe(html, height=640)
    st.html(ui.section("Related diseases", "Ranked by shared symptoms (rarer ones count more) and shared biology. "
                       "The Atlas computed these links, so treat them as leads to check.", "disease"))
    nb = G.neighbours_of(d)
    if nb.empty:
        st.html(ui.callout("empty", "No related diseases found", "The similarity model found no neighbours."))
    for r in nb.head(5).itertuples():
        weak = r.score < NEIGHBOUR_MIN
        paths, shared_ph = json.loads(r.shared_pathways), json.loads(r.shared_phenotypes)
        only_here, only_nb = json.loads(r.only_here), json.loads(r.only_neighbour)
        sg = json.loads(r.shared_genes)
        g_here, g_there = ", ".join(json.loads(r.genes)) or "?", ", ".join(json.loads(r.neighbour_genes)) or "?"
        why = ([f"Shares {r.n_shared_pathways} biological pathway{'s' if r.n_shared_pathways != 1 else ''}"]
               if r.n_shared_pathways else []) + \
              ([f"{len(shared_ph)} distinctive symptom{'s' if len(shared_ph) != 1 else ''} in common"] if shared_ph else []) + \
              [f"same gene ({', '.join(sg)})" if sg else f"different gene ({g_there})"]
        st.html(f'<div class="item"><div class="row" style="justify-content:space-between"><div class="t">'
                f'{ui.icon("disease", 16, ui.LAVENDER)} {escape(r.neighbour)}'
                f'{" <span class=status>weak match</span>" if weak else ""}</div>'
                f'{ui.meter(float(r.score), "inferred", "Similarity")}</div>'
                f'<div class="w">{escape(" · ".join(why))}</div></div>')
        with st.expander("Why are they related?"):
            lines = []
            if paths:
                lines.append("<li><b>Shared pathways:</b> " + "; ".join(escape(p["name"]) for p in paths[:4]) + "</li>")
            if shared_ph:
                lines.append("<li><b>Shared symptoms:</b> " + ", ".join(escape(p["name"]) for p in shared_ph) + "</li>")
            lines.append(f"<li><b>What differs:</b> gene {escape(g_here)} here vs {escape(g_there)} there"
                         + (f"; recorded only here: {', '.join(escape(p['name']) for p in only_here[:4])}" if only_here else "")
                         + (f"; only for {escape(r.neighbour)}: {', '.join(escape(p['name']) for p in only_nb[:4])}"
                            if only_nb else "") + "</li>")
            st.html(f'<ul style="color:#B8B3C7;font-size:.9rem;line-height:1.6">{"".join(lines)}</ul>'
                    f'<div class="small" style="margin:.2rem 0 .3rem">Similarity score {r.score:.2f} (symptoms '
                    f'{r.phenotype_score:.2f}, pathways {r.pathway_score:.2f})</div>')
            evidence_cards([r.similar_edge_id] + [i for p in paths for i in p["edge_ids"][:1]]
                           + [i for p in shared_ph for i in p["edge_ids"][:1]] + json.loads(r.gene_edge_ids), limit=4)


def opportunities() -> list[dict]:
    """Reusable studies and registries, for this disease and its close relatives. Built from existing rows only."""
    own, shared = [], []
    for a in sort_assets(G.useful_assets(d)[lambda x: x.kind.isin(REUSABLE)]).itertuples():
        own.append({"k": "Already for this disease", "title": f"{a.kind.capitalize()} for {name}", "asset": a,
                    "related": "This disease itself",
                    "why": "It already exists for this disease: joining or learning from it may beat starting a new one.",
                    "ids": [a.edge_id]})
    for n in nbs.itertuples():
        paths = sorted(json.loads(n.shared_pathways), key=lambda p: GENES_PER_PATHWAY.get(p["id"], 99))  # most specific
        reason = f"shares the pathway “{paths[0]['name']}”" if paths else "has similar symptoms"
        for i, a in enumerate(sort_assets(G.useful_assets(n.neighbour_id)[lambda x: x.kind.isin(REUSABLE)]).head(2).itertuples()):
            shared.append({"rank": i, **{"k": "Shared research opportunity", "title": f"{n.neighbour}: {a.kind}", "asset": a,
                        "related": f"{n.neighbour} {reason}",
                        "why": ("The two diseases share a pathway, so its study design or outcome measures might be "
                                "reusable." if paths else "The two diseases have similar symptoms, so its study design "
                                "might be reusable."),
                        "ids": [a.edge_id, n.similar_edge_id] + (paths[0]["edge_ids"][:1] if paths else [])}})
    # the best study for this disease first, then one per related disease, then the rest
    shared.sort(key=lambda o: o["rank"])        # stable: keeps the neighbours' similarity order within each rank
    return own[:1] + shared + own[1:]


def opp_card(o: dict) -> str:
    a = o["asset"]
    return (f'<div class="opp"><div class="k">{escape(o["k"])}</div><h4>{escape(o["title"])}</h4><div class="g">'
            f'<b>Related disease</b><span>{escape(o["related"])}</span>'
            f'<b>Existing resource</b><span><a href="{escape(a.source_url or "")}" target="_blank" rel="noopener">'
            f'{escape(a.title)}</a> {status_tag(a.status)}</span>'
            f'<b>Why it may matter</b><span>{escape(o["why"])}</span>'
            f'<b>Needs expert validation</b><span>Eligibility, and whether the diseases are biologically comparable'
            f'</span></div></div>')


def view_research() -> None:
    entity_line()
    st.html(ui.view_head("What work already exists?",
                         "Studies, resources, people and funding around this disease, with the most reusable first."))
    papers = E[(E.subject == d) & (E.evidence_type == "text_mined")].source_record.unique()
    near = {d} | set(nbs.neighbour_id)
    people = people_for({d})
    reusable = G.useful_assets(d)[lambda x: x.kind.isin(REUSABLE)]
    st.html(ui.stats([("trial", f["n_trials"], "clinical studies"), ("grant", f["n_grants"], "grants"),
                      ("paper", len(papers), "publications read"), ("person", len(people), "researchers"),
                      ("asset", len(reusable), "reusable research resources")]))

    st.html(ui.section("Research opportunities", "Existing studies and registries this community might join or "
                       "reuse. Each one needs expert validation before acting.", "spark"))
    opps = opportunities()
    if not opps:
        st.html(ui.callout("empty", "No supported research connection found.",
                           "The Atlas did not find a natural history study or registry for this disease or its close "
                           "relatives.<br><b>What could help:</b> a new study, a registry, or more research evidence."))
        st.button("Explore related diseases  →", on_click=go, args=("Connections",), type="tertiary")
    html_if("".join(opp_card(o) for o in opps[:3]))
    if len(opps) > 3:
        with st.expander(f"View all {len(opps)} opportunities"):
            html_if("".join(opp_card(o) for o in opps[3:]))
    if opps:
        evidence([i for o in opps[:3] for i in o["ids"]], "Evidence behind these opportunities")

    st.html(ui.section("Suggested next steps", "Plain-language steps written only from the cited graph facts.", "flag"))
    if G.no_route(d):
        st.html(ui.callout("empty", "No supported route found for this disease.",
                           "<b>What we searched</b><ul>" + "".join(f"<li>{escape(s)}</li>" for s in G.searched_summary(d))
                           + "</ul><b>What evidence would change this:</b> a natural history study or registry for this "
                           "disease; papers linking its gene to a pathway shared with a better-studied disease; a "
                           "patient group reporting the same symptoms."))
    else:
        cands = G.candidates(d)
        slot = st.empty()
        slot.html('<div class="skeleton" style="width:85%"></div><div class="skeleton" style="width:70%"></div>')
        res = cached_steps(name, json.dumps(cands))
        slot.empty()
        if res["steps"]:
            html_if("".join(f'<div class="opp"><p>{cite(s)}</p></div>' for s in res["steps"]))
            st.html(f'<div class="small">{ui.icon("text_mined", 13, ui.CYAN)} Written by an AI from the cited facts '
                    'only; every sentence was checked to cite real edges.</div>')
        else:
            st.html(ui.callout("info", "The plain-language summary is unavailable right now.",
                               "The opportunities above and the full list below are the actions found in the graph, "
                               "each with its evidence."))
        st.html('<div class="small" style="margin-top:.4rem">Before acting, an expert should check that each study is '
                'still active, that the diseases are close enough for the protocol to transfer, and that the contact is '
                'current.</div>')
        with st.expander(f"All candidate actions found in the graph ({len(cands)})"):
            st.html('<ul style="color:#B8B3C7;font-size:.9rem">' + "".join(f"<li>{escape(c['text'])}</li>" for c in cands)
                    + "</ul>")
            evidence_cards([i for c in cands[:6] for i in c["edge_ids"]])

    a = sort_assets(G.assets[G.assets.disease_id == d])
    st.html(ui.section("Studies and trials", f"{len(a)} registered for {name}.", "trial"))
    html_if("".join(asset_row(r) for r in a.head(5).itertuples()) or '<div class="small">None registered.</div>')
    if len(a) > 5:
        with st.expander(f"View all {len(a)}"):
            html_if("".join(asset_row(r) for r in a.iloc[5:].itertuples()))
    rel = sort_assets(G.assets[G.assets.disease_id.isin(near - {d})])
    if len(rel):
        with st.expander(f"Studies for related diseases ({len(rel)})"):
            for dn, grp in rel.groupby("disease", sort=False):
                st.html(f'<div class="t" style="margin-top:.6rem">{escape(dn)}</div>'
                        + "".join(asset_row(r) for r in grp.head(6).itertuples()))

    st.html(ui.section("Researchers", "People listed on trials for this disease.", "person"))
    def person_row(r) -> str:
        ds = [x[1] for x in json.loads(r.diseases)]
        return (f'<div class="item"><div class="t">{escape(r.person)}</div><div class="m">'
                f'{escape(r.affiliation or "affiliation not listed")}</div><div class="w">Works across {r.n_diseases} '
                f'diseases: {escape(", ".join(ds[:4]))}{"…" if len(ds) > 4 else ""}</div></div>')
    html_if("".join(person_row(r) for r in people.head(4).itertuples())
            or '<div class="small">No investigator in our data is listed across several diseases including this one.</div>')
    if len(people) > 4:
        with st.expander(f"View all {len(people)}"):
            html_if("".join(person_row(r) for r in people.iloc[4:].itertuples()))

    gr = E[(E.subject == d) & (E.predicate == "funded_by")]
    st.html(ui.section("Funding", f"{len(gr)} NIH grants linked to {name}.", "grant"))
    def grant_row(r) -> str:
        node = G.nodes[G.nodes.node_id == r.object]
        attrs = json.loads(node["attrs"].iloc[0]) if len(node) and node["attrs"].iloc[0] else {}
        meta = " · ".join(str(x) for x in [attrs.get("organization"), attrs.get("fiscal_year")] if x)
        return (f'<div class="item"><div class="t"><a href="{escape(r.source_url or "")}" target="_blank" rel="noopener">'
                f'{escape(label(r.object))}</a></div><div class="m">{escape(r.object)}{" · " + escape(meta) if meta else ""}'
                f'</div></div>')
    html_if("".join(grant_row(r) for r in gr.head(4).itertuples()) or '<div class="small">No grants found.</div>')
    if len(gr) > 4:
        with st.expander(f"View all {len(gr)}"):
            html_if("".join(grant_row(r) for r in gr.iloc[4:].itertuples()))

    if len(papers):
        st.html(ui.section("Publications", "Papers the Atlas read for facts about this disease.", "paper"))
        html_if("".join(f'<div class="item"><div class="t"><a href="https://pubmed.ncbi.nlm.nih.gov/{escape(p.split(":")[-1])}/" '
                        f'target="_blank" rel="noopener">{escape(label(p))}</a></div><div class="m">{escape(p)}</div></div>'
                        for p in papers[:5]))

    st.html(ui.section("The 10× route", "One milestone, two routes: build a natural history study from scratch, or "
                       "reuse what sister diseases built.", "spark"))
    with st.expander("Open the 10× route", icon=":material/rocket_launch:"):
        from src.webapp.ten_x import render
        render(G, d)


def view_communities() -> None:
    entity_line()
    st.html(ui.view_head("Who else is working on this?",
                         "Patient groups for this disease, communities with shared biology, and the studies and "
                         "registries they could build on together."))
    o = orgs_for(d)
    st.html(ui.section(f"Patient organisations for {name}", "Checked by hand on each organisation’s own website.", "org"))
    def org_row(r) -> str:
        return (f'<div class="item"><div class="t">{ui.icon("org", 16, ui.LAVENDER)} <a href="{escape(r.url)}" '
                f'target="_blank" rel="noopener">{escape(r.name)}</a></div><div class="w">Serves: '
                f'{escape(str(r.diseases_served))}</div><div class="m">Registry or study: {escape(str(r.registry_or_study))}'
                f' · checked {escape(str(r.date_checked))}</div></div>')
    if o.empty:
        st.html(ui.callout("empty", "No patient organisation on file for this disease",
                           "None of the organisations we checked by hand covers it yet. Related communities below may "
                           "be the closest partners."))
    html_if("".join(org_row(r) for r in o.itertuples()))

    st.html(ui.section("Related communities", "Diseases with shared biology. Their families, researchers and "
                       "studies may be natural partners. These links are Atlas-derived: leads, not conclusions.",
                       "disease"))
    mine = set(o.name) if not o.empty else set()
    for n in nbs.itertuples():
        shared_ph = json.loads(n.shared_phenotypes)
        both = G.people[G.people.diseases.map(lambda s: {d, n.neighbour_id} <= {x[0] for x in json.loads(s)})]
        reasons = (["Shares a biological pathway"] if n.n_shared_pathways else []) + \
                  (["Has similar symptoms"] if shared_ph else []) + \
                  ([f"Works with some of the same researchers ({len(both)})"] if len(both) else [])
        their = [r.name for r in orgs_for(n.neighbour_id).itertuples() if r.name not in mine]
        same = [r.name for r in orgs_for(n.neighbour_id).itertuples() if r.name in mine]
        orgs_txt = (f"Their patient groups: {', '.join(their)}" if their else
                    f"Served by the same organisation{'s' if len(same) > 1 else ''}: {', '.join(same)}" if same else
                    "No patient organisation on file")
        st.html(f'<div class="item"><div class="row" style="justify-content:space-between"><div class="t">'
                f'{ui.icon("disease", 16, ui.LAVENDER)} {escape(n.neighbour)}</div>{ui.pill("inferred")}</div>'
                f'<div class="w">{escape(" · ".join(reasons) or "Similar overall")}</div>'
                f'<div class="m">{escape(orgs_txt)}</div></div>')
        with st.expander("Why? Technical details"):
            st.html(f'<div class="small">Similarity {n.score:.2f}: symptoms {n.phenotype_score:.2f}, pathways '
                    f'{n.pathway_score:.2f}; {n.n_shared_pathways} shared pathways, {len(shared_ph)} shared '
                    'distinctive symptoms.' + (f' Shared researchers: {escape(", ".join(both.person.head(5)))}.'
                                               if len(both) else "") + "</div>")
            evidence_cards([n.similar_edge_id], limit=1)
    if nbs.empty:
        st.html(ui.callout("empty", "No closely related community found",
                           "No other disease in the Atlas is similar enough to recommend."))

    near = {d} | set(nbs.neighbour_id)
    reg = sort_assets(G.assets[G.assets.disease_id.isin(near) & G.assets.kind.isin(REUSABLE)])
    st.html(ui.section("Registries and natural history studies",
                       "Shared infrastructure that patient groups could join or learn from.", "asset"))
    def reg_row(r) -> str:
        return asset_row(r).replace('<div class="item"><div class="row">',
                                    f'<div class="item"><div class="row">{ui.chip(r.disease, "disease")}', 1)
    html_if("".join(reg_row(r) for r in reg.head(5).itertuples()) or '<div class="small">None found.</div>')
    if len(reg) > 5:
        with st.expander(f"View all {len(reg)}"):
            html_if("".join(reg_row(r) for r in reg.iloc[5:].itertuples()))

    bridges = people_for(near)
    bridges = bridges[bridges.diseases.map(lambda s: len({x[0] for x in json.loads(s)} & near) >= 2)]
    st.html(ui.section("Researchers who bridge these communities",
                       "People listed on trials for this disease and its relatives.", "person"))
    html_if("".join(f'<div class="item"><div class="t">{escape(r.person)}</div><div class="m">'
                    f'{escape(r.affiliation or "affiliation not listed")}</div><div class="w">Works with: '
                    + escape(", ".join(x[1] for x in json.loads(r.diseases) if x[0] in near)) + "</div></div>"
                    for r in bridges.head(4).itertuples())
            or '<div class="small">No researcher in our data works across these diseases.</div>')


def view_evidence() -> None:
    entity_line()
    st.html(ui.view_head("Why should I trust this?",
                         "Every connection in the Atlas carries its source, retrieval date and evidence strength. "
                         "Here is what stands behind this disease."))
    mine = E[(E.subject == d) | (E.object == d)]
    counts = mine.evidence_type.value_counts()
    st.html(ui.section("Three kinds of evidence", "Hover a label for the technical definition."))
    html_if("".join(f'<div class="item"><div class="row" style="justify-content:space-between">{ui.pill(k)}'
                    f'<span class="small">{int(counts.get(k, 0))} links for this disease</span></div>'
                    f'<div class="w">{escape(m)}</div></div>' for k, (_, _, m, _) in ui.EVIDENCE.items()))

    st.html(ui.section("Contradictory evidence"))
    contra = [x for x in mine.contradicts if x is not None and len(x)]
    if contra:
        st.html(ui.callout("warn", "Conflicting evidence", f"{len(contra)} link(s) for this disease have a recorded "
                           "contradiction. Open the evidence below to see them."))
    else:
        st.html(ui.callout("ok", "No contradictory evidence recorded.", escape(G.summary.get("note", ""))))

    st.html(ui.section("Where the evidence comes from"))
    src = mine.source.value_counts()
    html_if("".join(f'<div class="item"><div class="row" style="justify-content:space-between"><div class="t">'
                    f'{escape(ui.source_name(s))}</div><span class="small">{n} links</span></div></div>'
                    for s, n in src.items()))

    st.html(ui.section("Browse the evidence", "Pick a kind of link to see each record behind it."))
    kinds = {"The gene link": mine[mine.predicate == "gene_associated_with_disease"],
             "Symptoms quoted from published studies": mine[(mine.predicate == "has_phenotype") & (mine.evidence_type == "text_mined")],
             "Symptoms from the Human Phenotype Ontology": mine[(mine.predicate == "has_phenotype") & (mine.evidence_type == "curated")],
             "Related diseases (Atlas-derived)": mine[mine.predicate == "similar_to"],
             "Trials and studies": mine[mine.predicate.isin(["studied_in_trial", "has_asset"])],
             "Grants": mine[mine.predicate == "funded_by"]}
    kinds = {k: v for k, v in kinds.items() if len(v)}
    pick = st.selectbox("Kind of link", list(kinds), format_func=lambda k: f"{k} ({len(kinds[k])})")
    if pick:
        evidence_cards(kinds[pick].sort_values("confidence", ascending=False).edge_id.tolist(), limit=8)

    st.html(ui.section("About the Atlas"))
    et = E.evidence_type.value_counts()
    with st.expander("Atlas coverage", icon=":material/public:"):
        st.html(ui.stats([("disease", len(G.diseases), "diseases"),
                          ("gene", int((G.nodes.node_type == "Gene").sum()), "genes"),
                          ("symptom", int((G.nodes.node_type == "Phenotype").sum()), "symptoms"),
                          ("trial", int((G.nodes.node_type == "Trial").sum()), "trials"),
                          ("grant", int((G.nodes.node_type == "Grant").sum()), "grants"),
                          ("pathway", f"{len(E):,}", "links")])
                + f'<p class="small">{et.get("curated", 0):,} verified-source, {et.get("text_mined", 0)} research-'
                  f'literature and {et.get("inferred", 0)} Atlas-derived links.</p>')
    with st.expander("How evidence strength is set", icon=":material/tune:"):
        st.markdown("""- **Verified source** (curated): Orphadata germline-causing gene 0.95 (0.85 when found through a parent disease); HPO annotation 0.9 (lower if "occasional"); trials, grants and investigators 0.8 to 0.9.
- **Research literature** (text-mined): 0.7 if the abstract states it, 0.5 if it only suggests it.
- **Atlas-derived** (inferred): the similarity score itself; the method is stored on each link.

The interface shows **Strong evidence** (0.85 or more), **Moderate evidence** (0.6 to 0.85) or **Tentative evidence** (below 0.6); hover the bar to see the number.""")
    with st.expander("How facts from papers are checked", icon=":material/fact_check:"):
        st.markdown("An AI reads each abstract, but a fact is kept only if its quoted sentence appears word for word in "
                    "the abstract. Names must then resolve to stable IDs already in the graph (MONDO, HGNC, HP); "
                    "otherwise the fact is dropped and counted in the full statistics.")
    with st.expander("Data sources and full statistics", icon=":material/database:"):
        st.markdown("MONDO, HPO, Orphadata, HGNC, Reactome, ClinVar (counts), PubMed, ClinicalTrials.gov, NIH RePORTER. "
                    "Each link shows its own retrieval date.")
        st.markdown((Path(__file__).resolve().parent.parent / "data" / "graph" / "STATS.md").read_text(encoding="utf-8"))


RENDER = {"Explore": view_explore, "Biology": view_biology, "Connections": view_connections,
          "Research": view_research, "Communities": view_communities, "Evidence": view_evidence}
try:
    RENDER[ss.view]()
except Exception as exc:   # never show a stack trace to a visitor; keep it in the server log
    if type(exc).__name__ in ("RerunException", "StopException", "RerunData"):
        raise
    log.exception("view %s failed for %s", ss.view, d)
    st.html(ui.callout("error", "Something went wrong while loading this view.",
                       "Your Atlas data is safe. Try again, or open another view."))
    st.button("Try again", icon=":material/refresh:")
footer()
