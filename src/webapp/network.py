"""The interactive evidence graph for the Connections view (vis-network, one self-contained HTML page).

Centre = the chosen disease; around it its closest diseases, their genes, the specific (non-generic) shared
pathways, and symptoms that a paper stated. Line colour and style = evidence type (green solid verified source,
cyan solid research literature, amber dashed Atlas-derived).

The map is revealed in calm stages instead of all at once: the disease, then its gene and pathways, then related
diseases and symptoms. Everything else waits behind "Expand connections" or a click on a node. Positions are
computed once (hidden physics run) and then frozen, so nothing jiggles. Clicking a line answers "Why is this
connected?"; clicking a node focuses its neighbourhood. All edge data is embedded in the page, so no server round
trip is needed."""
import json
import textwrap
from html import escape
from pathlib import Path

import pyvis

from src.webapp.data import NEIGHBOUR_MIN
from src.webapp import ui

MAX_PHENO = 3        # text-mined symptoms drawn per disease (the rest are in the evidence boxes)
MAX_PATHWAYS = 4
NODE_SIZE = {"centre": 34, "disease": 25, "gene": 19, "pathway": 18, "symptom": 16}
KIND_LABEL = {"centre": "Selected disease", "disease": "Related disease", "gene": "Gene", "pathway": "Pathway",
              "symptom": "Symptom / trait"}
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
                      "size": NODE_SIZE[kind], "kind": kind, "title": f"{KIND_LABEL[kind]}: {full or label}",
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
                   word=ui.confidence_word(float(e["confidence"]), t), srcname=ui.source_name(e["source"]),
                   ref=ui.source_ref(e) if t != "inferred" else "")
        edge_data[eid] = rec
        colour = ui.EDGE_COLOURS[t]
        edges.append({"id": eid, "from": a, "to": b, "label": label, "dashes": [6, 6] if t == "inferred" else False,
                      "color": {"color": colour, "highlight": colour, "hover": colour, "opacity": 0.75},
                      "width": 2.2 if t != "curated" else 1.8,
                      "smooth": {"type": "curvedCW", "roundness": curve} if curve else False,
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

    # reveal stages (presentation only): 0 the disease, 1 its genes, 2 their pathways, 3 related diseases and the
    # disease's own symptoms; 9 = shown on "Expand connections" or when a neighbouring node is clicked
    kind = {n["id"]: n["kind"] for n in nodes}
    touching = {x for e in edges for x in (e["from"], e["to"]) if d in (e["from"], e["to"])} - {d}
    genes = {x for x in touching if kind[x] == "gene"}
    paths = {x for e in edges for x in (e["from"], e["to"])
             if kind[x] == "pathway" and ({e["from"], e["to"]} & genes)}
    for n in nodes:
        n["stage"] = (0 if n["id"] == d else 1 if n["id"] in genes else 2 if n["id"] in paths
                      else 3 if n["id"] in touching else 9)
    return _page(nodes, edges, node_info, edge_data, d, G.label(d)), counts


def _page(nodes, edges, node_info, edge_data, centre, centre_label) -> str:
    legend = "".join(
        f'<span title="{escape(meaning)}"><svg width="24" height="8" aria-hidden="true"><line x1="1" y1="4" x2="23" '
        f'y2="4" stroke="{c}" stroke-width="2.4" {"stroke-dasharray=" + chr(34) + "5 4" + chr(34) if k == "inferred" else ""}/>'
        f'</svg>{sym} {lbl}</span>'
        for (k, (c, lbl, meaning, _)), sym in zip(ui.EVIDENCE.items(), ["✓", "◌", "◇"]))
    kinds = "".join(f'<span><img src="{ui.node_image(k)}" width="20" height="20" alt="">{lbl}</span>'
                    for k, lbl in [("disease", "Disease"), ("gene", "Gene"), ("pathway", "Pathway"),
                                   ("symptom", "Symptom")])
    ev = {k: [c, lbl, meaning, tech, ui.icon(k, 14, c, 2)] for k, (c, lbl, meaning, tech) in ui.EVIDENCE.items()}
    data = {"NODES": nodes, "EDGES": edges, "INFO": node_info, "EV": edge_data, "EVC": ev, "CENTRE": centre,
            "CENTRE_LABEL": centre_label}
    return (PAGE.replace("__VIS__", VIS_JS.read_text(encoding="utf-8"))
            .replace("__LEGEND__", legend).replace("__KINDS__", kinds)
            .replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
            .replace("__BG__", ui.BG).replace("__BG2__", ui.BG2).replace("__SURFACE__", ui.SURFACE)
            .replace("__LINE__", ui.LINE).replace("__TEXT2__", ui.TEXT2).replace("__TEXT__", ui.TEXT)
            .replace("__MUTED__", ui.MUTED).replace("__PURPLE__", ui.PURPLE).replace("__LAV__", ui.LAVENDER)
            .replace("__RED__", ui.RED).replace("__CYAN__", ui.CYAN))


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<script>__VIS__</script>
<style>
:root { --bg:__BG__; --bg2:__BG2__; --surface:__SURFACE__; --line:__LINE__; --text:__TEXT__; --text2:__TEXT2__;
  --muted:__MUTED__; --purple:__PURPLE__; --lav:__LAV__; --red:__RED__; --cyan:__CYAN__; }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg2); color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; }
.wrap { display: grid; grid-template-columns: minmax(0, 1fr) 330px; height: 100vh; }
.stage { position: relative; overflow: hidden; background:
  radial-gradient(620px 420px at 50% 48%, rgba(139,92,246,.10), transparent 70%),
  radial-gradient(circle at 1px 1px, rgba(167,139,250,.06) 1px, transparent 0) 0 0/22px 22px, var(--bg); }
#net { position: absolute; top: 44px; left: 0; right: 0; bottom: 48px; }
#layout { position: absolute; left: -9999px; top: 0; width: 900px; height: 700px; visibility: hidden; }
.legend { position: absolute; left: 12px; top: 10px; z-index: 2; display: flex; gap: 4px 14px; flex-wrap: wrap;
  font-size: 12px; color: var(--text2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; cursor: help; }
.loading { position: absolute; inset: 0; display: grid; place-items: center; color: var(--muted); font-size: 13px; z-index: 3; }
.loading i { display: block; width: 34px; height: 34px; margin: 0 auto 10px; border-radius: 50%;
  border: 2px solid rgba(167,139,250,.2); border-top-color: var(--lav); animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.hint { position: absolute; left: 50%; bottom: 58px; transform: translateX(-50%); z-index: 2; font-size: 12.5px;
  color: var(--text); background: rgba(23,19,33,.92); border: 1px solid rgba(167,139,250,.35); border-radius: 999px;
  padding: 7px 14px; white-space: nowrap; transition: opacity .4s; }
.hint.off { opacity: 0; pointer-events: none; }
.tools { position: absolute; left: 10px; right: 10px; bottom: 8px; display: flex; gap: 6px; z-index: 2; align-items: center; }
.tools .sp { flex: 1; }
button { font: inherit; font-size: 12.5px; color: var(--text); background: rgba(23,19,33,.92); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 11px; cursor: pointer; transition: border-color .15s, background .15s; }
button:hover:not(:disabled) { border-color: var(--purple); }
button:disabled { opacity: .5; cursor: default; }
button.main { background: rgba(139,92,246,.18); border-color: rgba(167,139,250,.5); }
button:focus-visible { outline: 2px solid var(--lav); outline-offset: 2px; }
.panel { border-left: 1px solid var(--line); background: var(--bg2); overflow-y: auto; padding: 18px 18px 22px; }
.kick { color: var(--lav); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; }
h3 { margin: 6px 0 10px; font-size: 18px; letter-spacing: -.01em; line-height: 1.3; }
p { color: var(--text2); font-size: 13.5px; line-height: 1.55; margin: 0 0 10px; }
p b { color: var(--text); }
.pill { display: inline-flex; align-items: center; gap: 5px; padding: 2px 9px; border-radius: 999px; font-size: 11.5px;
  font-weight: 600; color: var(--c); border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  background: color-mix(in srgb, var(--c) 10%, transparent); cursor: help; }
.sec { margin: 14px 0 0; }
.sec > b { display: block; color: var(--muted); font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; font-weight: 600; margin-bottom: 5px; }
.sec div, .sec span { font-size: 13px; color: var(--text2); line-height: 1.5; }
blockquote { margin: 6px 0 0; padding: 8px 11px; border-left: 2px solid var(--cyan); background: rgba(103,198,214,.07);
  color: var(--text); font-size: 13px; font-style: italic; border-radius: 0 8px 8px 0; line-height: 1.5; }
.meter { display: flex; align-items: center; gap: 8px; cursor: help; }
.meter .b { width: 110px; height: 6px; border-radius: 6px; background: rgba(255,255,255,.08); overflow: hidden; }
.meter .b i { display: block; height: 100%; border-radius: 6px; width: 0; transition: width .5s ease; }
a { color: var(--lav); text-decoration: none; } a:hover { text-decoration: underline; }
details { margin-top: 12px; border-top: 1px solid var(--line); padding-top: 10px; }
summary { cursor: pointer; color: var(--muted); font-size: 12.5px; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::before { content: "▸ "; } details[open] > summary::before { content: "▾ "; }
summary:hover { color: var(--text); }
.kv { display: grid; grid-template-columns: 92px 1fr; gap: 4px 8px; margin-top: 8px; font-size: 12px; color: var(--text2); word-break: break-word; }
.kv b { color: var(--muted); font-weight: 500; }
.contra { color: var(--red) !important; }
.conn { display: flex; width: 100%; text-align: left; gap: 8px; align-items: center; margin: 5px 0; padding: 8px 10px; }
.conn .sw { width: 18px; height: 3px; border-radius: 2px; flex: none; }
.kinds { display: grid; gap: 6px; margin-top: 8px; font-size: 12.5px; color: var(--text2); }
.kinds span { display: flex; align-items: center; gap: 8px; }
.fade { animation: f .25s ease; }
@keyframes f { from { opacity: 0; transform: translateX(6px); } to { opacity: 1; transform: none; } }
@media (max-width: 760px) {
  .wrap { grid-template-columns: 1fr; grid-template-rows: 64vh auto; height: auto; }
  .stage { height: 64vh; } .panel { border-left: none; border-top: 1px solid var(--line); }
  .hint { white-space: normal; width: 86%; text-align: center; top: 54px; bottom: auto; }
  .tools { flex-wrap: wrap; } #net { bottom: 84px; } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style></head><body>
<div class="wrap">
  <div class="stage" role="application" aria-label="Map of connections. Click a node to explore it; click a line to see why it exists.">
    <div class="legend">__LEGEND__</div>
    <div id="net"></div><div id="layout"></div>
    <div class="loading" id="loading"><div><i></i>Building the biological map…</div></div>
    <div class="hint off" id="hint">Click a node to explore it · Click a connection to see why it exists</div>
    <div class="tools">
      <button class="main" id="expand">Expand connections</button>
      <span class="sp"></span>
      <button id="zin" title="Zoom in" aria-label="Zoom in">+</button>
      <button id="zout" title="Zoom out" aria-label="Zoom out">−</button>
      <button id="fit" title="Fit the whole map">Fit view</button>
      <button id="reset" title="Back to the first view">Reset</button>
    </div>
  </div>
  <aside class="panel" id="panel" aria-live="polite"></aside>
</div>
<script>
const D = __DATA__;
const { NODES, EDGES, INFO, EV, EVC, CENTRE, CENTRE_LABEL } = D;
const byId = Object.fromEntries(NODES.map(n => [n.id, n]));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = { get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
                set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
const panel = document.getElementById('panel'), hint = document.getElementById('hint');
const nodes = new vis.DataSet([]), edges = new vis.DataSet([]);
const network = new vis.Network(document.getElementById('net'), { nodes, edges }, {
  physics: false,
  nodes: { shapeProperties: { interpolation: true }, chosen: false },
  edges: { selectionWidth: 1.5, hoverWidth: 1.4, chosen: true },
  interaction: { hover: true, tooltipDelay: 150, navigationButtons: false, zoomView: true, dragView: true,
                 keyboard: { enabled: true, bindToWindow: false } } });
let pos = {}, shown = new Set(), focusSet = null, focusEdges = null, pulse = null;

// ---------- 1. compute a calm layout once, off screen, then freeze it
const lay = new vis.Network(document.getElementById('layout'),
  { nodes: new vis.DataSet(NODES.map(n => ({ id: n.id, label: n.label, shape: 'dot', size: n.size + 6, font: { size: 14 } }))),
    edges: new vis.DataSet(EDGES.map(e => ({ from: e.from, to: e.to }))) },
  { layout: { randomSeed: 7 }, physics: { solver: 'barnesHut', barnesHut: { gravitationalConstant: -5200,
    springLength: 130, centralGravity: .5, springConstant: .045, avoidOverlap: 1, damping: .5 },
    stabilization: { iterations: 500, updateInterval: 1000 } } });
let started = false;
const start = () => { if (started) return; started = true; pos = lay.getPositions(); lay.destroy(); begin(); };
lay.once('stabilizationIterationsDone', start);
setTimeout(start, 3500);

// ---------- 2. tiny tween engine (positions + opacity), batched per frame
const anims = new Map();
let raf = null;
function tween(id, kind, from, to, dur) { anims.set(kind + id, { id, kind, from, to, t0: performance.now(), dur: still ? 1 : dur }); if (!raf) raf = requestAnimationFrame(tick); }
const ease = t => 1 - Math.pow(1 - t, 3);
function tick(now) {
  const nu = [], eu = [];
  for (const [k, a] of anims) {
    const t = Math.max(0, Math.min(1, (now - a.t0) / a.dur)), e = ease(t);
    if (a.kind === 'n') nu.push({ id: a.id, x: a.from.x + (a.to.x - a.from.x) * e, y: a.from.y + (a.to.y - a.from.y) * e,
                                  opacity: a.from.o + (a.to.o - a.from.o) * e });
    else { const base = byEdge[a.id]; eu.push({ id: a.id, color: { ...base.color, opacity: a.from + (a.to - a.from) * e } }); }
    if (t >= 1) anims.delete(k);
  }
  if (nu.length) nodes.update(nu); if (eu.length) edges.update(eu);
  raf = anims.size ? requestAnimationFrame(tick) : null;
}
const byEdge = Object.fromEntries(EDGES.map(e => [e.id, e]));

// ---------- 3. revealing nodes: each grows out of a node that is already on the map
function parentOf(id) {
  for (const e of EDGES) { if (e.from === id && shown.has(e.to)) return e.to; if (e.to === id && shown.has(e.from)) return e.from; }
  return null;
}
function reveal(ids) {
  const fresh = ids.filter(id => !shown.has(id));
  for (const id of fresh) {
    const par = parentOf(id), p = pos[id], s = par ? network.getPositions([par])[par] || pos[par] : p;
    const n = byId[id];
    nodes.add({ ...n, x: s.x, y: s.y, opacity: 0, fixed: false, physics: false });
    shown.add(id);
    tween(id, 'n', { x: s.x, y: s.y, o: 0 }, { x: p.x, y: p.y, o: focusSet && !focusSet.has(id) ? .15 : 1 }, 700);
  }
  for (const e of EDGES) {
    if (!edges.get(e.id) && shown.has(e.from) && shown.has(e.to)) {
      edges.add({ ...e, color: { ...e.color, opacity: 0 } });
      tween(e.id, 'e', 0, focusEdges && !focusEdges.has(e.id) ? .06 : e.color.opacity, 900);
    }
  }
  updateExpand();
  return fresh;
}
const hidden = () => NODES.filter(n => !shown.has(n.id)).map(n => n.id);
function updateExpand() { const b = document.getElementById('expand'), h = hidden().length;
  b.disabled = !h; b.textContent = h ? `Expand connections (${h} more)` : 'All connections shown'; }
const fit = (ids, dur = 800) => network.fit({ ...(ids ? { nodes: ids } : {}), animation: still || !dur ? false : { duration: dur, easingFunction: 'easeInOutCubic' } });

function begin() {
  document.getElementById('loading').remove();
  network.moveTo({ position: pos[CENTRE], scale: 1.15 });
  const stages = [0, 1, 2, 3].map(s => NODES.filter(n => n.stage === s).map(n => n.id));
  const gap = still ? 0 : 650;
  stages.forEach((ids, i) => setTimeout(() => { reveal(ids); if (i === 3) setTimeout(() => { fit(undefined, 900); afterIntro(); }, 750); }, i * gap));
}
function afterIntro() {
  if (!store.get('rda_hint_seen')) hint.classList.remove('off');
  const last = store.get('rda_sel');           // keep the user's place when they come back to this view
  if (last && last.centre === CENTRE) setTimeout(() => {
    if (last.type === 'edge' && EV[last.id]) { reveal([EV[last.id].a, EV[last.id].b]); network.selectEdges([last.id]); showEdge(last.id, false); }
    if (last.type === 'node' && byId[last.id]) { reveal([last.id]); showNode(last.id, false); }
  }, 950);
}
function seenHint() { hint.classList.add('off'); store.set('rda_hint_seen', true); }

// ---------- 4. focus, camera, pulse
function focus(ids, edgeIds) {
  focusSet = ids; focusEdges = edgeIds;
  nodes.update([...shown].map(id => ({ id, opacity: ids.has(id) ? 1 : .15, image: INFO[id].img })));
  edges.update(edges.getIds().map(id => { const e = byEdge[id];
    return { id, color: { ...e.color, opacity: edgeIds.has(id) ? 1 : .06 },
             font: edgeIds.has(id) ? e.font : { ...e.font, color: 'rgba(0,0,0,0)', strokeWidth: 0 } }; }));
}
function unfocus() {
  focusSet = null; focusEdges = null;
  nodes.update([...shown].map(id => ({ id, opacity: 1, image: INFO[id].img })));
  edges.update(edges.getIds().map(id => ({ id, color: byEdge[id].color, font: byEdge[id].font })));
}
network.on('afterDrawing', ctx => {
  if (!pulse) return;
  const t = (performance.now() - pulse.t0) / 900;
  if (t >= 1) { pulse = null; return; }
  const p = network.getPositions([pulse.a, pulse.b]), A = p[pulse.a], B = p[pulse.b]; if (!A || !B) return;
  const u = ease(t), x = A.x + (B.x - A.x) * u, y = A.y + (B.y - A.y) * u;
  ctx.save(); ctx.shadowColor = pulse.c; ctx.shadowBlur = 16; ctx.fillStyle = 'rgba(255,255,255,' + (0.95 * Math.sin(t * Math.PI)) + ')';
  ctx.beginPath(); ctx.arc(x, y, 4.5, 0, 7); ctx.fill(); ctx.restore();
  requestAnimationFrame(() => network.redraw());
});

// ---------- 5. the side panel
function home() {
  panel.innerHTML = '<div class="fade"><div class="kick">Connections</div><h3>' + esc(CENTRE_LABEL) + '</h3>'
    + '<p>This map starts with the most direct links. Use <b>Expand connections</b> for more, or click a node to open its neighbourhood.</p>'
    + '<p>Click any <b>line</b> to see <b>why</b> two things are connected, and how strong the evidence is.</p>'
    + '<div class="sec"><b>Lines</b>' + Object.values(EVC).map(v => '<div style="margin:6px 0"><span class="pill" style="--c:' + v[0]
      + '" title="' + esc(v[2]) + '">' + v[4] + esc(v[1]) + '</span></div>').join('') + '</div>'
    + '<div class="sec"><b>Shapes</b><div class="kinds">__KINDS__</div></div></div>';
}
function meter(v, c, word, inferred) {
  return '<div class="meter" title="' + (inferred ? 'Similarity score ' : 'Score ') + Number(v).toFixed(2)
    + (inferred ? ', computed by the Atlas' : ', assigned by the Atlas evidence model') + '"><div class="b"><i data-w="'
    + Math.round(Math.min(1, v) * 100) + '" style="background:' + c + '"></i></div><span>' + esc(word) + '</span></div>';
}
function showEdge(id, move = true) {
  const e = EV[id]; if (!e) return;
  focus(new Set([e.a, e.b]), new Set([id]));
  nodes.update([{ id: e.a, image: INFO[e.a].sel }, { id: e.b, image: INFO[e.b].sel }]);
  const [c, lbl, meaning, tech, ic] = EVC[e.evidence_type];
  pulse = { a: e.a, b: e.b, c, t0: performance.now() }; network.redraw();
  if (move) { const p = network.getPositions([e.a, e.b]), A = p[e.a], B = p[e.b];
    network.moveTo({ position: { x: (A.x + B.x) / 2, y: (A.y + B.y) / 2 }, scale: Math.min(1.25, Math.max(network.getScale(), .85)),
                     animation: still ? false : { duration: 700, easingFunction: 'easeInOutCubic' } }); }
  store.set('rda_sel', { centre: CENTRE, type: 'edge', id });
  panel.innerHTML = '<div class="fade"><div class="kick">Why is this connected?</div>'
    + '<h3>' + esc(e.subject) + ' &rarr; ' + esc(e.object) + '</h3>'
    + '<p>' + esc(e.why) + '</p>'
    + '<div class="sec"><b>Evidence</b><span class="pill" style="--c:' + c + '" title="' + esc(meaning) + '">' + ic + esc(lbl) + '</span></div>'
    + '<div class="sec"><b>Evidence strength</b>' + meter(e.confidence, c, e.word, e.evidence_type === 'inferred') + '</div>'
    + '<div class="sec"><b>Source</b><div>' + esc(e.srcname) + (e.ref ? '<br><span style="font-family:JetBrains Mono,monospace;font-size:12px">' + esc(e.ref) + '</span>' : '')
    + (e.source_url ? '<br><a href="' + esc(e.source_url) + '" target="_blank" rel="noopener">View source &#8599;</a>' : '') + '</div></div>'
    + '<div class="sec"><b>Contradictory evidence</b><div' + (e.contradicts.length ? ' class="contra">&#9888; Conflicting evidence: '
       + e.contradicts.length + ' record' + (e.contradicts.length > 1 ? 's' : '') + ' disagree (' + e.contradicts.map(esc).join(', ') + ')'
       : '>No contradictory evidence recorded.') + '</div></div>'
    + (e.evidence_text ? '<details><summary>Exact quote</summary><blockquote>&ldquo;' + esc(e.evidence_text) + '&rdquo;</blockquote></details>' : '')
    + '<details><summary>More details</summary><div class="kv">'
    + '<b>Why it matters</b><span>' + esc(e.matters) + '</span>'
    + '<b>Relationship</b><span>' + esc(e.predicate.replace(/_/g, ' ')) + '</span>'
    + '<b>Type</b><span>' + esc(tech) + '</span>'
    + '<b>Score</b><span>' + Number(e.confidence).toFixed(2) + '</span>'
    + '<b>Record</b><span>' + esc(e.source_record) + '</span>'
    + '<b>Retrieved</b><span>' + esc(e.retrieved) + '</span>'
    + (e.method ? '<b>Method</b><span>' + esc(e.method) + '</span>' : '')
    + '<b>Review</b><span>' + (e.reviewer_verdict === 'not_reviewed' ? 'not yet independently reviewed' : esc(e.reviewer_verdict)) + '</span>'
    + '<b>Edge ID</b><span style="font-family:JetBrains Mono,monospace">' + esc(id) + '</span></div></details></div>';
  requestAnimationFrame(() => panel.querySelectorAll('.meter i').forEach(i => i.style.width = i.dataset.w + '%'));
}
function showNode(id, move = true) {
  const info = INFO[id]; if (!info) return;
  const conn = EDGES.filter(e => e.from === id || e.to === id);
  const ids = new Set([id]); conn.forEach(e => { ids.add(e.from); ids.add(e.to); });
  focus(ids, new Set(conn.map(e => e.id)));
  const grew = reveal([...ids]);
  nodes.update([{ id, image: info.sel }]);
  if (move) setTimeout(() => fit([...ids], 800), grew.length ? 720 : 0);
  store.set('rda_sel', { centre: CENTRE, type: 'node', id });
  panel.innerHTML = '<div class="fade"><div class="kick">' + esc(info.kind) + '</div><h3>' + esc(info.label) + '</h3>'
    + (grew.length ? '<p>Opened ' + grew.length + ' more connection' + (grew.length > 1 ? 's' : '') + ' around it.</p>' : '')
    + '<p>' + conn.length + ' connection' + (conn.length === 1 ? '' : 's') + '. Pick one to see why it exists:</p>'
    + conn.map(e => { const d = EV[e.id]; const other = e.from === id ? INFO[e.to] : INFO[e.from];
        return '<button class="conn" data-e="' + esc(e.id) + '"><span class="sw" style="background:' + EVC[d.evidence_type][0]
          + '"></span><span>' + esc(d.predicate.replace(/_/g, ' ')) + ' &middot; <b style="color:var(--text)">' + esc(other.label)
          + '</b></span></button>'; }).join('')
    + '<details><summary>Technical ID</summary><div class="kv"><b>ID</b><span style="font-family:JetBrains Mono,monospace">' + esc(id) + '</span></div></details></div>';
  panel.querySelectorAll('button.conn').forEach(b => b.onclick = () => { network.selectEdges([b.dataset.e]); showEdge(b.dataset.e); });
}
network.on('click', p => {
  if (!started) return;
  seenHint();
  if (p.nodes.length) showNode(p.nodes[0]);
  else if (p.edges.length) showEdge(p.edges[0]);
  else { unfocus(); home(); store.set('rda_sel', null); }
});
['hoverNode', 'hoverEdge'].forEach(ev => network.on(ev, () => document.body.style.cursor = 'pointer'));
['blurNode', 'blurEdge'].forEach(ev => network.on(ev, () => document.body.style.cursor = 'default'));

// ---------- 6. controls
document.getElementById('expand').onclick = () => {
  seenHint(); unfocus(); home();
  let wave = 0;
  const step = () => { const next = hidden().filter(id => parentOf(id)); if (!next.length) { setTimeout(() => fit(undefined, 900), 650); return; }
    reveal(next); wave++; setTimeout(step, still ? 0 : 420); };
  step();
};
document.getElementById('fit').onclick = () => fit(undefined, 700);
document.getElementById('zin').onclick = () => network.moveTo({ scale: network.getScale() * 1.3, animation: { duration: 300 } });
document.getElementById('zout').onclick = () => network.moveTo({ scale: network.getScale() / 1.3, animation: { duration: 300 } });
document.getElementById('reset').onclick = () => {
  unfocus(); network.unselectAll(); home(); store.set('rda_sel', null);
  const extra = [...shown].filter(id => byId[id].stage === 9);
  edges.remove(edges.getIds().filter(id => extra.includes(byEdge[id].from) || extra.includes(byEdge[id].to)));
  nodes.remove(extra); extra.forEach(id => shown.delete(id)); updateExpand(); fit(undefined, 700);
};
// the map often loads inside a hidden container (size 0): re-fit once it gets a real size
let lastW = 0;
new ResizeObserver(([en]) => { const w = en.contentRect.width;
  if (started && w > 0 && Math.abs(w - lastW) > 40) { lastW = w; network.redraw(); fit(undefined, 0); } else if (w > 0) lastW = w; })
  .observe(document.getElementById('net'));
home();
</script></body></html>"""
