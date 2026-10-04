"""The interactive evidence graph for the 'Connect' tab (vis-network, one self-contained HTML page).

Centre = the chosen disease; around it its closest diseases, their genes, the specific (non-generic) shared
pathways, and symptoms that a paper stated. Line colour and style = evidence type (green solid curated, cyan solid
text-mined, amber dashed inferred). Clicking a line answers "Why is this connected?" with its source, date,
confidence and, for text-mined edges, the exact quote. Clicking a node focuses its neighbourhood. All edge data is
embedded in the page, so no server round trip is needed."""
import json
import textwrap
from html import escape
from pathlib import Path

import pyvis

from src.webapp.data import NEIGHBOUR_MIN
from src.webapp import ui

MAX_PHENO = 3        # text-mined symptoms drawn per disease (the rest are in the evidence boxes)
MAX_PATHWAYS = 4
NODE_SIZE = {"centre": 34, "disease": 25, "gene": 18, "pathway": 18, "symptom": 16}
KIND_LABEL = {"centre": "Selected disease", "disease": "Related disease", "gene": "Gene", "pathway": "Pathway",
              "symptom": "Symptom (phenotype)"}
DASH = 'stroke-dasharray="5 4"'
VIS_JS = Path(pyvis.__file__).parent / "lib" / "vis-9.1.2" / "vis-network.min.js"


def wrap(text: str, width: int = 18) -> str:
    return "\n".join(textwrap.wrap(text, width, break_long_words=False)) or text


def build_html(G, d: str) -> tuple[str, dict]:
    """Returns (html, counts) where counts says how many edges of each evidence type are drawn."""
    nodes: list[dict] = []
    edges: list[dict] = []
    drawn_nodes: set[str] = set()
    node_info: dict[str, dict] = {}
    edge_data: dict[str, dict] = {}
    counts = {"curated": 0, "text_mined": 0, "inferred": 0}

    def node(nid: str, label: str, kind: str, full: str = ""):
        if nid in drawn_nodes:
            return
        centre = kind == "centre"
        nodes.append({"id": nid, "label": wrap(label), "shape": "image", "image": ui.node_image(kind),
                      "size": NODE_SIZE[kind], "kind": kind,
                      "font": {"size": 17 if centre else 14, "color": ui.TEXT if centre else ui.TEXT2,
                               "face": "Inter, system-ui, sans-serif", "strokeWidth": 4, "strokeColor": ui.BG}})
        node_info[nid] = {"label": full or label, "kind": KIND_LABEL[kind], "id": nid,
                          "img": ui.node_image(kind), "sel": ui.node_image(kind, selected=True)}
        drawn_nodes.add(nid)

    def edge(eid: str, a: str, b: str, label: str = "", curve: float = 0.0):
        e = G.edge(eid)
        if not e or eid in edge_data:
            return
        t = e["evidence_type"]
        rec = {k: (e[k] if not isinstance(e[k], float) or e[k] == e[k] else "") for k in
               ("evidence_type", "predicate", "source", "source_record", "source_url", "retrieved",
                "confidence", "evidence_text", "method", "reviewer_verdict")}
        subj, obj = G.label(e["subject"]), G.label(e["object"])
        contra = e.get("contradicts")
        rec.update(subject=subj, object=obj, a=a, b=b,
                   contradicts=[str(c) for c in (contra if contra is not None else [])],
                   why=ui.relation_sentence(e, subj, obj), matters=ui.WHY_IT_MATTERS.get(t, ""),
                   word=ui.confidence_word(float(e["confidence"]), t))
        edge_data[eid] = rec
        colour = ui.EDGE_COLOURS[t]
        edges.append({"id": eid, "from": a, "to": b, "label": label, "dashes": [6, 6] if t == "inferred" else False,
                      "color": {"color": colour, "highlight": colour, "hover": colour, "opacity": 0.75},
                      "width": 2.2 if t != "curated" else 1.8,
                      "smooth": {"type": "curvedCW", "roundness": curve} if curve else {"type": "continuous"},
                      "font": {"color": ui.AMBER, "size": 12, "strokeWidth": 4, "strokeColor": ui.BG,
                               "face": "JetBrains Mono, monospace"},
                      "title": f"{ui.EVIDENCE[t][1]} · click to see why"})
        counts[t] += 1

    node(d, G.label(d), "centre")
    nb = G.neighbours_of(d)
    nb = nb[nb.score >= NEIGHBOUR_MIN].head(4)
    members = [(d, "centre")] + [(r.neighbour_id, "disease") for r in nb.itertuples()]
    for r in nb.itertuples():
        node(r.neighbour_id, r.neighbour, "disease")
        edge(r.similar_edge_id, d, r.neighbour_id, label=f"{r.score:.2f}")

    ed = G.edges
    for dis, _ in members:
        # genes: curated link and, if a paper also states it, the text-mined link (curved so both show)
        ge = ed[(ed.object == dis) & (ed.predicate == "gene_associated_with_disease")]
        for r in ge.itertuples():
            node(r.subject, r.subject, "gene", f"{r.subject}: {G.label(r.subject)}")
            edge(r.edge_id, dis, r.subject, curve=0.0 if r.evidence_type == "curated" else 0.35)
        # symptoms stated in papers (text-mined only; the curated HPO list has hundreds)
        pe = ed[(ed.subject == dis) & (ed.predicate == "has_phenotype") & (ed.evidence_type == "text_mined")]
        for r in pe.sort_values("confidence", ascending=False).drop_duplicates("object").head(MAX_PHENO).itertuples():
            node(r.object, G.label(r.object), "symptom")
            edge(r.edge_id, dis, r.object)

    # specific shared pathways, drawn through the genes that carry them (edges are gene -> pathway, curated)
    seen_paths: set[str] = set()
    for r in nb.itertuples():
        for p in json.loads(r.shared_pathways):
            if p["id"] in seen_paths or len(seen_paths) >= MAX_PATHWAYS:
                continue
            seen_paths.add(p["id"])
            node(p["id"], p["name"], "pathway")
            for eid in p["edge_ids"]:
                e = G.edge(eid)
                if e and e["subject"] in drawn_nodes:
                    edge(eid, e["subject"], p["id"])

    return _page(nodes, edges, node_info, edge_data, counts, G.label(d)), counts


def _page(nodes, edges, node_info, edge_data, counts, centre_label) -> str:
    legend_nodes = "".join(f'<span>{ui.icon(k, 15, ui.KIND_ACCENT[k])}{lbl}</span>' for k, lbl in
                           [("disease", "Disease"), ("gene", "Gene"), ("pathway", "Pathway"), ("symptom", "Symptom")])
    legend_edges = "".join(
        f'<span><svg width="26" height="8" aria-hidden="true"><line x1="1" y1="4" x2="25" y2="4" stroke="{c}" '
        f'stroke-width="2.4" {DASH if k == "inferred" else ""}/></svg>{lbl}</span>'
        for k, (c, lbl, _) in ui.EVIDENCE.items())
    intro = (f"Showing <b>{counts['curated']}</b> curated, <b>{counts['text_mined']}</b> text-mined and "
             f"<b>{counts['inferred']}</b> inferred connections around <b>{escape(centre_label)}</b>.")
    ev_icons = {k: ui.icon(k, 14, c, 2) for k, (c, _, _) in ui.EVIDENCE.items()}
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<script>{VIS_JS.read_text()}</script>
<style>
:root {{ --bg:{ui.BG}; --bg2:{ui.BG2}; --surface:{ui.SURFACE}; --line:{ui.LINE}; --text:{ui.TEXT}; --text2:{ui.TEXT2};
  --muted:{ui.MUTED}; --purple:{ui.PURPLE}; --lav:{ui.LAVENDER}; --red:{ui.RED}; --cyan:{ui.CYAN}; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; height: 100%; background: var(--bg2); color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.wrap {{ display: grid; grid-template-columns: minmax(0, 1fr) 320px; height: 100vh; }}
.stage {{ position: relative; background:
  radial-gradient(600px 400px at 50% 45%, rgba(139,92,246,.10), transparent 70%),
  radial-gradient(circle at 1px 1px, rgba(167,139,250,.07) 1px, transparent 0) 0 0/22px 22px, var(--bg); }}
#net {{ position: absolute; top: 46px; left: 0; right: 0; bottom: 40px; }}
.bar {{ position: absolute; left: 12px; right: 12px; top: 10px; display: flex; justify-content: space-between; gap: 8px;
  flex-wrap: wrap; pointer-events: none; z-index: 2; }}
.legend {{ display: flex; gap: 4px 11px; flex-wrap: wrap; font-size: 11.5px; color: var(--text2); background: rgba(13,10,21,.82);
  border: 1px solid var(--line); border-radius: 10px; padding: 5px 9px; pointer-events: auto; backdrop-filter: blur(6px); }}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.legend .div {{ width: 1px; background: var(--line); align-self: stretch; }}
.tools {{ position: absolute; right: 12px; bottom: 8px; display: flex; gap: 6px; z-index: 2; }}
button {{ font: inherit; font-size: 12px; color: var(--text); background: rgba(23,19,33,.9); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 10px; cursor: pointer; transition: border-color .15s; }}
button:hover {{ border-color: var(--purple); }}
button:focus-visible {{ outline: 2px solid var(--lav); outline-offset: 2px; }}
.hint {{ position: absolute; left: 12px; bottom: 14px; font-size: 11.5px; color: var(--muted); z-index: 2; }}
.panel {{ border-left: 1px solid var(--line); background: var(--bg2); overflow-y: auto; padding: 18px 18px 22px; }}
.kick {{ color: var(--lav); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; }}
h3 {{ margin: 6px 0 10px; font-size: 18px; letter-spacing: -.01em; }}
p {{ color: var(--text2); font-size: 13.5px; line-height: 1.55; margin: 0 0 10px; }}
p b {{ color: var(--text); }}
.rel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; font-size: 13.5px; margin-bottom: 12px; }}
.rel .pred {{ display: block; color: var(--muted); font-size: 11.5px; margin: 3px 0; }}
.pill {{ display: inline-flex; align-items: center; gap: 5px; padding: 2px 9px; border-radius: 999px; font-size: 11.5px;
  font-weight: 600; color: var(--c); border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  background: color-mix(in srgb, var(--c) 10%, transparent); }}
.sec {{ margin: 14px 0 0; }}
.sec > b {{ display: block; color: var(--muted); font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase;
  font-weight: 600; margin-bottom: 5px; }}
.sec div, .sec span {{ font-size: 13px; color: var(--text2); line-height: 1.5; }}
blockquote {{ margin: 4px 0 0; padding: 8px 11px; border-left: 2px solid var(--cyan); background: rgba(103,198,214,.07);
  color: var(--text); font-size: 13px; font-style: italic; border-radius: 0 8px 8px 0; line-height: 1.5; }}
.meter {{ display: flex; align-items: center; gap: 8px; }}
.meter .b {{ flex: 1; height: 6px; border-radius: 6px; background: rgba(255,255,255,.08); overflow: hidden; }}
.meter .b i {{ display: block; height: 100%; border-radius: 6px; transition: width .35s ease; }}
a {{ color: var(--lav); text-decoration: none; }} a:hover {{ text-decoration: underline; }}
.contra {{ color: var(--red) !important; }}
.foot {{ margin-top: 14px; font: 11px 'JetBrains Mono', ui-monospace, monospace; color: var(--muted); word-break: break-all; }}
.conn {{ display: flex; width: 100%; text-align: left; gap: 8px; align-items: center; margin: 5px 0; padding: 8px 10px; }}
.conn .sw {{ width: 18px; height: 3px; border-radius: 2px; flex: none; }}
.fade {{ animation: f .22s ease; }}
@keyframes f {{ from {{ opacity: 0; transform: translateY(3px); }} to {{ opacity: 1; transform: none; }} }}
@media (max-width: 760px) {{ .wrap {{ grid-template-columns: 1fr; grid-template-rows: 62vh auto; height: auto; }}
  .stage {{ height: 62vh; }} .panel {{ border-left: none; border-top: 1px solid var(--line); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
</style></head><body>
<div class="wrap">
  <div class="stage" role="application" aria-label="Knowledge graph. Click a line to see why two things are connected.">
    <div class="bar">
      <div class="legend">{legend_nodes}<span class="div"></span>{legend_edges}</div>
    </div>
    <div class="tools"><button id="fit" title="Fit the whole graph">Fit view</button>
      <button id="reset" title="Clear the focus">Clear focus</button></div>
    <div id="net"></div>
    <div class="hint">Click a line: why? · Click a node: focus · Scroll: zoom</div>
  </div>
  <aside class="panel" id="panel" aria-live="polite"></aside>
</div>
<script>
const NODES = {json.dumps(nodes)};
const EDGES = {json.dumps(edges)};
const INFO = {json.dumps(node_info)};
const EV = {json.dumps(edge_data)};
const EVC = {json.dumps({k: [c, lbl] for k, (c, lbl, _) in ui.EVIDENCE.items()})};
const EVI = {json.dumps(ev_icons)};
const INTRO = {json.dumps(intro)};
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const nodes = new vis.DataSet(NODES), edges = new vis.DataSet(EDGES);
const network = new vis.Network(document.getElementById('net'), {{nodes, edges}}, {{
  physics: {{ solver: 'barnesHut', barnesHut: {{ gravitationalConstant: -5200, springLength: 125, centralGravity: .55,
    springConstant: .05, avoidOverlap: 1, damping: .5 }}, stabilization: {{ iterations: 400 }} }},
  nodes: {{ shapeProperties: {{ interpolation: true }}, chosen: false }},
  edges: {{ selectionWidth: 2, hoverWidth: 1.6, chosen: true }},
  interaction: {{ hover: true, tooltipDelay: 120, navigationButtons: false, keyboard: {{ enabled: true, bindToWindow: false }} }}
}});
const panel = document.getElementById('panel');
const fit = () => network.fit({{ animation: {{ duration: 450, easingFunction: 'easeInOutQuad' }} }});
network.once('stabilizationIterationsDone', () => {{ network.setOptions({{ physics: false }}); fit(); }});
setTimeout(() => network.fit(), 1200);
// the graph often loads inside a hidden tab (size 0): re-fit once it gets a real size, and on resize
let lastW = 0;
new ResizeObserver(([en]) => {{ const w = en.contentRect.width;
  if (w > 0 && Math.abs(w - lastW) > 40) {{ lastW = w; network.redraw(); network.fit(); }} }}).observe(document.getElementById('net'));
document.getElementById('fit').onclick = fit;
document.getElementById('reset').onclick = () => {{ unfocus(); network.unselectAll(); home(); fit(); }};

function home() {{
  panel.innerHTML = '<div class="fade"><div class="kick">Verify</div><h3>Why is this connected?</h3>'
    + '<p>' + INTRO + '</p><p>Click any <b>line</b> to see the relationship, the evidence behind it, its source and how '
    + 'confident we are. Click a <b>node</b> to focus on what it touches.</p>'
    + Object.entries(EVC).map(([k, v]) => '<div class="sec"><span class="pill" style="--c:' + v[0] + '">' + EVI[k] + v[1]
      + '</span></div>').join('')
    + '<p style="margin-top:10px">Solid green: curated database · solid cyan: quoted from a paper · dashed amber: '
    + 'computed by the Atlas (a hypothesis).</p></div>';
}}
function focus(ids, edgeIds) {{
  nodes.update(NODES.map(n => ({{ id: n.id, opacity: ids.has(n.id) ? 1 : .18,
    image: INFO[n.id].img }})));
  edges.update(EDGES.map(e => ({{ id: e.id, color: {{ ...e.color, opacity: edgeIds.has(e.id) ? 1 : .08 }},
    font: edgeIds.has(e.id) ? e.font : {{ ...e.font, color: 'rgba(0,0,0,0)', strokeWidth: 0 }} }})));
}}
function unfocus() {{
  nodes.update(NODES.map(n => ({{ id: n.id, opacity: 1, image: INFO[n.id].img }})));
  edges.update(EDGES.map(e => ({{ id: e.id, color: e.color, font: e.font }})));
}}
function meter(v, c, word) {{
  return '<div class="meter"><div class="b"><i style="width:' + Math.round(Math.min(1, v) * 100) + '%;background:' + c
    + '"></i></div><span>' + esc(word) + ' · ' + Number(v).toFixed(2) + '</span></div>';
}}
function showEdge(id) {{
  const e = EV[id]; if (!e) return;
  focus(new Set([e.a, e.b]), new Set([id]));
  nodes.update([{{ id: e.a, image: INFO[e.a].sel }}, {{ id: e.b, image: INFO[e.b].sel }}]);
  const [c, lbl] = EVC[e.evidence_type];
  panel.innerHTML = '<div class="fade"><div class="kick">Why is this connected?</div>'
    + '<h3>' + esc(e.subject) + ' &harr; ' + esc(e.object) + '</h3>'
    + '<div class="rel"><span class="pill" style="--c:' + c + '">' + EVI[e.evidence_type] + lbl + '</span>'
    + '<span class="pred">Relationship: ' + esc(e.predicate.replace(/_/g, ' ')) + '</span>'
    + '<b>' + esc(e.subject) + '</b> &rarr; <b>' + esc(e.object) + '</b></div>'
    + '<p>' + esc(e.why) + '</p>'
    + '<div class="sec"><b>Why it matters</b><div>' + esc(e.matters) + '</div></div>'
    + (e.evidence_text ? '<div class="sec"><b>Evidence (exact quote)</b><blockquote>&ldquo;' + esc(e.evidence_text) + '&rdquo;</blockquote></div>' : '')
    + (e.method ? '<div class="sec"><b>How it was computed</b><div>' + esc(e.method) + '</div></div>' : '')
    + '<div class="sec"><b>Source</b><div>' + esc(e.source) + ' &middot; ' + esc(e.source_record)
    + (e.source_url ? ' &middot; <a href="' + esc(e.source_url) + '" target="_blank" rel="noopener">open source &#8599;</a>' : '')
    + '<br>Retrieved ' + esc(e.retrieved) + '</div></div>'
    + '<div class="sec"><b>Confidence</b>' + meter(e.confidence, c, e.word) + '</div>'
    + '<div class="sec"><b>Contradictory evidence</b><div' + (e.contradicts.length ? ' class="contra">Contradicted by ' + e.contradicts.map(esc).join(', ')
       : '>None recorded in the graph for this connection') + '</div></div>'
    + '<div class="sec"><b>Independent review</b><div>' + (e.reviewer_verdict === 'not_reviewed' ? 'Not yet reviewed' : esc(e.reviewer_verdict)) + '</div></div>'
    + '<div class="foot">edge ' + esc(id) + '</div></div>';
}}
function showNode(id) {{
  const info = INFO[id]; if (!info) return;
  const conn = EDGES.filter(e => e.from === id || e.to === id);
  const ids = new Set([id]); conn.forEach(e => {{ ids.add(e.from); ids.add(e.to); }});
  focus(ids, new Set(conn.map(e => e.id)));
  nodes.update([{{ id, image: info.sel }}]);
  panel.innerHTML = '<div class="fade"><div class="kick">' + esc(info.kind) + '</div><h3>' + esc(info.label) + '</h3>'
    + '<p><span style="font-family:JetBrains Mono,monospace;font-size:12px;color:var(--muted)">' + esc(info.id) + '</span></p>'
    + '<p>' + conn.length + ' connection' + (conn.length === 1 ? '' : 's') + ' drawn here. Pick one to see why it exists:</p>'
    + conn.map(e => {{ const d = EV[e.id]; const other = e.from === id ? INFO[e.to] : INFO[e.from];
        return '<button class="conn" data-e="' + esc(e.id) + '"><span class="sw" style="background:' + EVC[d.evidence_type][0]
          + (d.evidence_type === 'inferred' ? ';opacity:.7' : '') + '"></span><span>' + esc(d.predicate.replace(/_/g, ' '))
          + ' &middot; <b style="color:var(--text)">' + esc(other.label) + '</b></span></button>'; }}).join('')
    + '</div>';
  panel.querySelectorAll('button.conn').forEach(b => b.onclick = () => {{ network.selectEdges([b.dataset.e]); showEdge(b.dataset.e); }});
}}
network.on('click', p => {{
  if (p.nodes.length) showNode(p.nodes[0]);
  else if (p.edges.length) showEdge(p.edges[0]);
  else {{ unfocus(); home(); }}
}});
network.on('hoverNode', () => document.body.style.cursor = 'pointer');
network.on('blurNode', () => document.body.style.cursor = 'default');
network.on('hoverEdge', () => document.body.style.cursor = 'pointer');
network.on('blurEdge', () => document.body.style.cursor = 'default');
home();
</script></body></html>"""
