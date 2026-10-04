"""Presentation only: colour tokens, the page CSS, the entity icon set and small HTML building blocks.

Nothing here reads or changes graph data; it only formats values the app already has. Every string that comes
from the data is escaped before it goes into HTML."""
from html import escape
from urllib.parse import quote

# ------------------------------------------------------------------ tokens
BG, BG2, SURFACE, SURFACE2 = "#08070D", "#0D0A15", "#171321", "#1E1830"
PURPLE_DEEP, PURPLE, LAVENDER = "#6D3BFF", "#8B5CF6", "#A78BFA"
TEXT, TEXT2, MUTED, LINE = "#F5F3FA", "#B8B3C7", "#8A8497", "#2A2338"
GREEN, AMBER, RED, CYAN = "#5FD39A", "#F2B84B", "#F07178", "#67C6D6"

# Evidence type -> (colour, short label, one-line meaning). Lines in the graph use the same colours, and
# each type also has its own glyph and line style so meaning never depends on colour alone.
EVIDENCE = {
    "curated": (GREEN, "Curated", "From a curated database or registry"),
    "text_mined": (CYAN, "Text-mined", "An AI read a paper; the exact quote was checked against the abstract"),
    "inferred": (AMBER, "Inferred", "Computed by the Atlas: a hypothesis to test, not an observation"),
}
EDGE_COLOURS = {k: v[0] for k, v in EVIDENCE.items()}

# Node kind -> accent. Nodes stay in the purple family and are told apart by glyph; lines carry the evidence colour.
KIND_ACCENT = {"disease": LAVENDER, "centre": PURPLE, "gene": "#D0A6FF", "variant": "#D0A6FF",
               "pathway": "#9FA8FF", "symptom": "#E4DDF2", "paper": TEXT2, "trial": CYAN, "asset": CYAN,
               "org": LAVENDER, "person": TEXT2, "grant": TEXT2}

# ------------------------------------------------------------------ icons (24px grid, stroke = currentColor)
_ICON_PATHS = {
    "disease": '<circle cx="12" cy="12" r="8.5"/><circle cx="13.5" cy="10.5" r="3"/><circle cx="8.5" cy="14.5" r=".9" '
               'fill="currentColor"/><circle cx="14.5" cy="16" r=".7" fill="currentColor"/>',
    "gene": '<path d="M7 3c0 4.5 10 4.5 10 9s-10 4.5-10 9"/><path d="M17 3c0 4.5-10 4.5-10 9s10 4.5 10 9"/>'
            '<path d="M8.6 6h6.8M8.6 18h6.8M10 12h4"/>',
    "variant": '<path d="M7 3c0 4.5 10 4.5 10 9s-10 4.5-10 9"/><path d="M17 3c0 4.5-10 4.5-10 9s10 4.5 10 9"/>'
               '<circle cx="12" cy="12" r="3.2"/>',
    "pathway": '<circle cx="5" cy="6" r="2.2"/><circle cx="19" cy="9" r="2.2"/><circle cx="9" cy="18.5" r="2.2"/>'
               '<path d="M7.1 6.6l9.8 1.9M17.3 10.6l-6.6 6.4M8.4 16.3L5.6 8.2"/>',
    "symptom": '<path d="M3 12h4l2.2-5 3.6 10 2.4-6.5 1.3 1.5H21"/>',
    "paper": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 15.5h6M9 9h2.5"/>',
    "trial": '<path d="M9.5 3h5M10.5 3v5.5L5.2 18.3A1.8 1.8 0 0 0 6.8 21h10.4a1.8 1.8 0 0 0 1.6-2.7L13.5 8.5V3"/>'
             '<path d="M7.6 14.5h8.8"/>',
    "asset": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 5V3M15 5V3M8 14h3M8 17h6"/>',
    "org": '<circle cx="12" cy="7.5" r="2.6"/><circle cx="5.5" cy="10" r="2.1"/><circle cx="18.5" cy="10" r="2.1"/>'
           '<path d="M7.5 20c0-3 2-5 4.5-5s4.5 2 4.5 5M2.5 18.5c0-2.2 1.3-3.8 3-3.8M21.5 18.5c0-2.2-1.3-3.8-3-3.8"/>',
    "person": '<circle cx="12" cy="8" r="3.6"/><path d="M5 20.5c.6-3.9 3.4-6.2 7-6.2s6.4 2.3 7 6.2"/>',
    "grant": '<circle cx="12" cy="9" r="5.5"/><path d="M9 13.8L7.5 21l4.5-2.4 4.5 2.4-1.5-7.2"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    "curated": '<path d="M12 3l7 3v5.5c0 4.4-3 8-7 9.5-4-1.5-7-5.1-7-9.5V6z"/><path d="M8.8 12l2.2 2.2 4.4-4.6"/>',
    "text_mined": '<path d="M5 17.5c2.6-.4 3.8-2.4 3.8-5.4V7H4.5v5h4.2M14.2 17.5c2.6-.4 3.8-2.4 3.8-5.4V7h-4.3v5h4.3"/>',
    "inferred": '<path d="M4 12h2.5M9 12h2.5M14 12h2.5"/><circle cx="20" cy="12" r="1.6"/><path d="M5 7.5l3-3M5 16.5l3 3"/>',
    "contradiction": '<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 9.5v5M12 17.4v.1"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "check": '<path d="M5 12.5l4.2 4.2L19 7"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.1"/>',
    "spark": '<path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l2.8 2.8M15.2 15.2L18 18M6 18l2.8-2.8M15.2 8.8L18 6"/>',
}


def icon(kind: str, size: int = 18, colour: str = LAVENDER, stroke: float = 1.6) -> str:
    """An icon as an <img> with a data-URI SVG (st.html strips inline <svg>, but keeps data-URI images)."""
    body = _ICON_PATHS.get(kind, _ICON_PATHS["info"]).replace("currentColor", colour)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{colour}" '
           f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    return (f'<img class="ic" src="data:image/svg+xml;charset=utf-8,{quote(svg)}" width="{size}" height="{size}" '
            'alt="" aria-hidden="true">')


def node_image(kind: str, selected: bool = False) -> str:
    """A data-URI SVG glyph for one graph node: dark disc, accent ring, entity icon in the middle."""
    accent = KIND_ACCENT.get(kind, LAVENDER)
    centre = kind == "centre"
    glyph = _ICON_PATHS["disease" if centre else kind].replace("currentColor", TEXT if centre else accent)
    fill = "#2A1B52" if centre else SURFACE
    halo = (f'<circle cx="32" cy="32" r="30" fill="none" stroke="{PURPLE}" stroke-opacity=".35" stroke-width="2"/>'
            if centre or selected else "")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">{halo}'
           f'<circle cx="32" cy="32" r="25" fill="{fill}" stroke="{PURPLE if selected else accent}" '
           f'stroke-width="{3 if selected or centre else 2}"/>'
           f'<g transform="translate(17 17) scale(1.25)" fill="none" stroke="{accent if not centre else TEXT}" '
           f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{glyph}</g></svg>')
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


# ------------------------------------------------------------------ plain-language reading of one edge
def confidence_word(conf: float, etype: str) -> str:
    if etype == "inferred":
        return "Computed score"
    return "Strong" if conf >= 0.85 else "Moderate" if conf >= 0.6 else "Tentative"


def relation_sentence(e: dict, subj: str, obj: str) -> str:
    """Restates the edge in words. Uses only the edge's own fields: no extra claims."""
    src, p = e.get("source") or "The source", e.get("predicate", "")
    if e.get("evidence_type") == "text_mined":
        return (f"A published abstract ({e.get('source_record') or 'PubMed'}) states that {subj} "
                f"{p.replace('_', ' ')} {obj}. The quoted sentence below was checked word for word against it.")
    return {
        "gene_associated_with_disease": f"{src} records {subj} as a gene whose variants are linked to {obj}.",
        "has_phenotype": f"{src} lists “{obj}” as a recorded feature of {subj}.",
        "participates_in_pathway": f"{src} places the gene {subj} in the pathway “{obj}”.",
        "similar_to": (f"The Atlas computed that {subj} and {obj} are alike, from shared symptoms (rarer symptoms "
                       "count more) and shared pathways."),
        "studied_in_trial": f"{src} lists {subj} as a condition studied in {obj}.",
        "has_asset": f"{src} lists {obj} as a study or resource for {subj}.",
        "investigator_of": f"{src} names {subj} as an investigator on {obj}.",
        "funded_by": f"{src} lists the grant {obj} as funding work on {subj}.",
        "serves_disease": f"{src} shows {subj} serving people with {obj}.",
    }.get(p, f"{src} records: {subj} — {p.replace('_', ' ')} — {obj}.")


WHY_IT_MATTERS = {
    "curated": "Comes straight from a curated database or registry: the most direct kind of evidence in the Atlas.",
    "text_mined": "Read from a paper by an AI. The quote is real, but the claim is one paper's finding: treat it "
                  "as a lead to check.",
    "inferred": "Calculated by the Atlas, not observed. Use it to decide what to investigate, not as a conclusion.",
}


# ------------------------------------------------------------------ HTML building blocks
def pill(etype: str) -> str:
    colour, label, meaning = EVIDENCE.get(etype, (MUTED, etype, ""))
    return (f'<span class="pill" style="--c:{colour}" title="{escape(meaning)}">'
            f'{icon(etype, 13, colour, 2)}{escape(label)}</span>')


def chip(text: str, kind: str | None = None, mono: bool = False) -> str:
    ic = icon(kind, 13, KIND_ACCENT.get(kind, LAVENDER)) if kind else ""
    return f'<span class="chip{" mono" if mono else ""}">{ic}{escape(str(text))}</span>'


def meter(value: float, etype: str = "curated", label: str | None = None) -> str:
    v = max(0.0, min(float(value), 1.0))
    colour = EVIDENCE.get(etype, (PURPLE,))[0]
    text = label if label is not None else f"{confidence_word(v, etype)} · {v:.2f}"
    return (f'<div class="meter" role="img" aria-label="{escape(text)}"><div class="bar"><span style="width:{v * 100:.0f}%;'
            f'background:{colour}"></span></div><span class="mtext">{escape(text)}</span></div>')


def _clean(v):
    return "" if v is None or (isinstance(v, float) and v != v) else v


def evidence_card(e: dict, subj: str, obj: str, eid: str) -> str:
    """'Why is this connected?' for one edge: relationship, reason, evidence, source, confidence, contradictions."""
    e = {k: (v if k == "contradicts" else _clean(v)) for k, v in e.items()}
    t = e.get("evidence_type", "")
    conf = float(e.get("confidence") or 0)
    quote_html = (f'<blockquote>“{escape(e["evidence_text"])}”</blockquote>' if e.get("evidence_text") else "")
    method = f'<div class="kv"><b>How computed</b>{escape(e["method"])}</div>' if e.get("method") else ""
    link = (f' · <a href="{escape(e["source_url"])}" target="_blank" rel="noopener">open source ↗</a>'
            if e.get("source_url") else "")
    contra = list(e.get("contradicts") if e.get("contradicts") is not None else [])
    contra_html = (f'<div class="kv warn">{icon("contradiction", 14, RED)}<b>Contradicted by</b>'
                   f'{", ".join(escape(c) for c in contra)}</div>' if contra else
                   f'<div class="kv quiet">{icon("check", 14, MUTED)}No contradicting edge recorded in the graph</div>')
    reviewer = e.get("reviewer_verdict") or "not_reviewed"
    reviewer_txt = "not yet independently reviewed" if reviewer == "not_reviewed" else reviewer
    return f"""<div class="ev" style="--c:{EVIDENCE.get(t, (MUTED,))[0]}">
  <div class="ev-top">{pill(t)}<span class="ev-rel"><b>{escape(subj)}</b>
    <span class="pred">{escape(e.get('predicate', '').replace('_', ' '))}</span> <b>{escape(obj)}</b></span></div>
  <p class="ev-why">{escape(relation_sentence(e, subj, obj))}</p>
  {quote_html}
  <div class="ev-grid">
    <div class="kv"><b>Source</b>{escape(e.get('source', ''))} · {escape(str(e.get('source_record', '')))}{link}</div>
    <div class="kv"><b>Retrieved</b>{escape(str(e.get('retrieved', '')))}</div>
    <div class="kv"><b>Confidence</b>{meter(conf, t)}</div>
    <div class="kv"><b>Why it matters</b>{escape(WHY_IT_MATTERS.get(t, ''))}</div>
    {method}
    {contra_html}
  </div>
  <div class="ev-foot"><code>{escape(eid)}</code> · reviewer: {escape(reviewer_txt)}</div>
</div>"""


def section(title: str, kicker: str = "", ic: str | None = None, sub: str = "") -> str:
    k = f'<div class="kicker">{escape(kicker)}</div>' if kicker else ""
    i = icon(ic, 20, LAVENDER) if ic else ""
    s = f'<p class="sec-sub">{escape(sub)}</p>' if sub else ""
    return f'<div class="sec">{k}<h3>{i}{escape(title)}</h3>{s}</div>'


def tile(ic: str, label: str, value: str, sub: str = "") -> str:
    return (f'<div class="tile"><div class="tile-l">{icon(ic, 15, LAVENDER)}{escape(label)}</div>'
            f'<div class="tile-v">{escape(str(value))}</div><div class="tile-s">{escape(sub)}</div></div>')


def callout(kind: str, title: str, body_html: str) -> str:
    colour, ic = {"warn": (AMBER, "contradiction"), "info": (CYAN, "info"), "empty": (LAVENDER, "search"),
                  "ok": (GREEN, "check"), "error": (RED, "contradiction")}[kind]
    return (f'<div class="callout" style="--c:{colour}">{icon(ic, 20, colour)}<div><b>{escape(title)}</b>'
            f'<div class="cbody">{body_html}</div></div></div>')


def flow(active: int) -> str:
    steps = ["Search", "Understand", "Connect", "Verify", "Act"]
    parts = []
    for i, s in enumerate(steps):
        state = "done" if i < active else "on" if i == active else ""
        parts.append(f'<span class="step {state}"><i>{i + 1}</i>{s}</span>')
    return '<div class="flow" aria-label="Search, understand, connect, verify, act">' + \
        '<span class="sep"></span>'.join(parts) + "</div>"


# ------------------------------------------------------------------ page CSS
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {{ --bg:{BG}; --bg2:{BG2}; --surface:{SURFACE}; --surface2:{SURFACE2}; --purple:{PURPLE};
  --deep:{PURPLE_DEEP}; --lav:{LAVENDER}; --text:{TEXT}; --text2:{TEXT2}; --muted:{MUTED}; --line:{LINE};
  --green:{GREEN}; --amber:{AMBER}; --red:{RED}; --cyan:{CYAN}; }}
html, body, [data-testid="stAppViewContainer"], .stApp {{ background: var(--bg) !important; }}
.stApp {{ background:
  radial-gradient(1100px 520px at 85% -10%, rgba(109,59,255,.10), transparent 60%),
  radial-gradient(800px 500px at -10% 30%, rgba(139,92,246,.05), transparent 60%), var(--bg) !important; }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button, .stApp textarea {{
  font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.stApp code, .mono {{ font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace !important; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
  letter-spacing: -.015em; color: var(--text); }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding-top: 1.6rem; max-width: 1320px; }}
a {{ color: var(--lav) !important; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
::selection {{ background: rgba(139,92,246,.35); }}
*:focus-visible {{ outline: 2px solid var(--lav) !important; outline-offset: 2px; }}

/* sidebar */
[data-testid="stSidebar"] {{ background: var(--bg2) !important; border-right: 1px solid var(--line); }}
[data-testid="stSidebar"] .stMarkdown p {{ color: var(--text2); font-size: .86rem; }}

/* inputs */
.stTextInput input {{ background: var(--surface) !important; border-radius: 12px !important; color: var(--text) !important;
  font-size: 1.02rem; padding: .85rem 1rem .85rem 2.6rem !important; }}
.stTextInput [data-baseweb="input"] {{ border-radius: 12px !important; border: 1px solid var(--line) !important;
  background: var(--surface) !important; transition: border-color .15s, box-shadow .15s; }}
.stTextInput [data-baseweb="input"]:focus-within {{ border-color: var(--purple) !important;
  box-shadow: 0 0 0 4px rgba(139,92,246,.18) !important; }}
.st-key-searchbox {{ position: relative; }}
.st-key-searchbox::before {{ content: ""; position: absolute; left: 14px; bottom: 15px; width: 18px; height: 18px; z-index: 2;
  background: no-repeat center/18px url("data:image/svg+xml;charset=utf-8,{quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + LAVENDER + '" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>')}"); }}
.stSelectbox [data-baseweb="select"] > div {{ background: var(--surface) !important; border-color: var(--line) !important; border-radius: 10px !important; }}

/* buttons */
.stButton > button, .stLinkButton > a {{ border-radius: 10px !important; border: 1px solid var(--line) !important;
  background: var(--surface) !important; color: var(--text) !important; transition: all .15s ease; }}
.stButton > button:hover {{ border-color: var(--purple) !important; color: #fff !important; transform: translateY(-1px); }}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {{
  background: linear-gradient(180deg, {PURPLE}, {PURPLE_DEEP}) !important; border: 1px solid rgba(167,139,250,.55) !important;
  color: #fff !important; font-weight: 600; box-shadow: 0 8px 28px rgba(109,59,255,.28); }}
.stButton > button[kind="tertiary"] {{ background: transparent !important; border: none !important; color: var(--text2) !important; }}
[data-testid="stBaseButton-pills"], [data-testid="stBaseButton-pillsActive"] {{ border-radius: 999px !important; }}
[data-testid="stBaseButton-pillsActive"] {{ background: rgba(139,92,246,.18) !important; border-color: var(--purple) !important; color: #fff !important; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: .25rem; border-bottom: 1px solid var(--line); overflow-x: auto; }}
.stTabs [data-baseweb="tab"] {{ height: 44px; padding: 0 .95rem; border-radius: 10px 10px 0 0; color: var(--text2);
  font-weight: 500; transition: color .15s, background .15s; }}
.stTabs [data-baseweb="tab"]:hover {{ color: var(--text); background: rgba(139,92,246,.07); }}
.stTabs [aria-selected="true"] {{ color: #fff !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--purple) !important; height: 2px; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 1.1rem; animation: fadein .25s ease; }}

/* expanders = quiet cards */
[data-testid="stExpander"] details {{ background: var(--bg2); border: 1px solid var(--line) !important; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ color: var(--text2); font-weight: 500; }}
[data-testid="stExpander"] summary:hover {{ color: var(--text); }}
[data-testid="stExpander"] details[open] summary {{ color: var(--text); border-bottom: 1px solid var(--line); }}

/* iframes (graph) */
iframe {{ border-radius: 16px; border: 1px solid var(--line) !important; background: var(--bg2); }}

@keyframes fadein {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes shimmer {{ 0% {{ background-position: -400px 0; }} 100% {{ background-position: 400px 0; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}

/* ---- components ---- */
.ic {{ display: inline-block; vertical-align: -3px; flex: none; }}
.brand {{ display: flex; align-items: center; gap: .8rem; margin: .2rem 0 .3rem; }}
.brand .logo {{ width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  background: linear-gradient(145deg, rgba(139,92,246,.28), rgba(109,59,255,.08)); border: 1px solid rgba(167,139,250,.35); }}
.brand h1 {{ font-size: 1.45rem !important; margin: 0 !important; padding: 0 !important; font-weight: 700; }}
.brand .tag {{ color: var(--text2); font-size: .88rem; margin-top: 1px; }}
.disclaimer {{ display: flex; gap: .55rem; align-items: center; font-size: .8rem; color: var(--text2);
  background: rgba(242,184,75,.06); border: 1px solid rgba(242,184,75,.22); border-radius: 10px; padding: .45rem .75rem; }}
.disclaimer b {{ color: var(--amber); }}
.kicker {{ color: var(--lav); font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; margin-bottom: .2rem; }}
.sec {{ margin: 1.3rem 0 .6rem; }}
.sec h3 {{ display: flex; align-items: center; gap: .5rem; font-size: 1.12rem !important; margin: 0 !important; padding: 0 !important; font-weight: 600; }}
.sec-sub {{ color: var(--text2) !important; font-size: .9rem; margin: .25rem 0 0 !important; }}

.hero {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 1.4rem; align-items: stretch;
  background: linear-gradient(160deg, rgba(23,19,33,.95), rgba(13,10,21,.95)); border: 1px solid var(--line);
  border-radius: 18px; padding: 1.35rem 1.45rem; margin: .9rem 0 .4rem; position: relative; overflow: hidden; animation: fadein .3s ease; }}
.hero::after {{ content: ""; position: absolute; right: -80px; top: -80px; width: 260px; height: 260px; border-radius: 50%;
  background: radial-gradient(circle, rgba(139,92,246,.16), transparent 70%); pointer-events: none; }}
.hero .type {{ display: inline-flex; gap: .4rem; align-items: center; color: var(--lav); font-size: .75rem;
  letter-spacing: .12em; text-transform: uppercase; font-weight: 600; }}
.hero h2 {{ font-size: 1.85rem !important; margin: .25rem 0 .35rem !important; padding: 0 !important; font-weight: 700; line-height: 1.15; }}
.hero .ids {{ display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .75rem; }}
.hero .summary {{ color: var(--text2); line-height: 1.6; font-size: .97rem; margin: 0; }}
.hero .summary b {{ color: var(--text); font-weight: 600; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: .6rem; align-content: start; }}
.tile {{ background: rgba(8,7,13,.55); border: 1px solid var(--line); border-radius: 12px; padding: .7rem .8rem; }}
.tile-l {{ display: flex; gap: .4rem; align-items: center; color: var(--text2); font-size: .76rem; }}
.tile-v {{ color: var(--text); font-size: 1.35rem; font-weight: 650; margin-top: .2rem; line-height: 1.2; word-break: break-word; }}
.tile-s {{ color: var(--muted); font-size: .72rem; margin-top: .1rem; }}

.chip {{ display: inline-flex; align-items: center; gap: .35rem; padding: .2rem .6rem; border-radius: 999px; font-size: .8rem;
  background: rgba(139,92,246,.08); border: 1px solid rgba(167,139,250,.22); color: var(--text); margin: 0 .3rem .35rem 0; }}
.chip.mono {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: .74rem; color: var(--text2);
  background: rgba(255,255,255,.03); border-color: var(--line); }}
.pill {{ display: inline-flex; align-items: center; gap: .3rem; padding: .14rem .55rem; border-radius: 999px; font-size: .74rem;
  font-weight: 600; color: var(--c); border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  background: color-mix(in srgb, var(--c) 10%, transparent); white-space: nowrap; }}

.flow {{ display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; margin: .8rem 0 .2rem; font-size: .8rem; color: var(--muted); }}
.flow .step {{ display: inline-flex; align-items: center; gap: .4rem; }}
.flow .step i {{ font-style: normal; width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
  border: 1px solid var(--line); font-size: .7rem; }}
.flow .step.done {{ color: var(--text2); }} .flow .step.done i {{ background: rgba(139,92,246,.2); border-color: rgba(167,139,250,.4); }}
.flow .step.on {{ color: var(--text); font-weight: 600; }} .flow .step.on i {{ background: var(--purple); border-color: var(--purple); color: #fff; }}
.flow .sep {{ width: 22px; height: 1px; background: var(--line); }}

.meter {{ display: flex; align-items: center; gap: .55rem; }}
.meter .bar {{ flex: 1; min-width: 60px; max-width: 160px; height: 6px; border-radius: 6px; background: rgba(255,255,255,.07); overflow: hidden; }}
.meter .bar span {{ display: block; height: 100%; border-radius: 6px; transition: width .4s ease; }}
.meter .mtext {{ font-size: .78rem; color: var(--text2); white-space: nowrap; }}

.ev {{ border: 1px solid var(--line); border-left: 3px solid var(--c); border-radius: 12px; padding: .8rem .95rem;
  background: var(--surface); margin: .55rem 0; animation: fadein .2s ease; }}
.ev-top {{ display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }}
.ev-rel {{ font-size: .92rem; color: var(--text); }}
.ev-rel .pred {{ color: var(--muted); font-size: .8rem; margin: 0 .25rem; }}
.ev-why {{ color: var(--text2) !important; font-size: .88rem; margin: .5rem 0 .35rem !important; line-height: 1.5; }}
.ev blockquote {{ margin: .45rem 0 .55rem; padding: .5rem .8rem; border-left: 2px solid var(--cyan); background: rgba(103,198,214,.06);
  color: var(--text); font-size: .88rem; border-radius: 0 8px 8px 0; font-style: italic; }}
.ev-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: .35rem 1rem; margin-top: .3rem; }}
.kv {{ font-size: .8rem; color: var(--text2); display: flex; flex-direction: column; gap: .15rem; }}
.kv b {{ color: var(--muted); font-weight: 500; font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; }}
.kv.warn, .kv.quiet {{ flex-direction: row; align-items: center; gap: .4rem; }}
.kv.warn {{ color: var(--red); }} .kv.quiet {{ color: var(--muted); }}
.ev-foot {{ margin-top: .5rem; color: var(--muted); font-size: .72rem; }}
.ev-foot code {{ background: transparent; color: var(--muted); padding: 0; font-size: .72rem; }}

.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: .9rem 1rem; margin: .5rem 0;
  transition: border-color .15s, transform .15s; animation: fadein .25s ease; }}
.card:hover {{ border-color: rgba(167,139,250,.4); }}
.card h4 {{ margin: 0 0 .2rem !important; padding: 0 !important; font-size: 1rem !important; font-weight: 600; display: flex; gap: .5rem; align-items: center; }}
.card .meta {{ color: var(--muted); font-size: .8rem; }}
.card p {{ color: var(--text2) !important; font-size: .9rem; margin: .35rem 0 0 !important; line-height: 1.5; }}
.rank {{ display: inline-grid; place-items: center; min-width: 26px; height: 26px; border-radius: 8px; font-size: .8rem; font-weight: 700;
  background: rgba(139,92,246,.16); color: var(--lav); border: 1px solid rgba(167,139,250,.3); }}
.weak {{ color: var(--amber); font-size: .75rem; font-weight: 500; border: 1px solid rgba(242,184,75,.35); padding: .05rem .45rem; border-radius: 999px; }}
.row {{ display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }}
.status {{ font-size: .72rem; padding: .08rem .5rem; border-radius: 999px; border: 1px solid var(--line); color: var(--text2); white-space: nowrap; }}
.status.live {{ color: var(--green); border-color: rgba(95,211,154,.4); }}
.status.stop {{ color: var(--muted); }}
.cite {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: .72rem; color: var(--lav); background: rgba(139,92,246,.1);
  border: 1px solid rgba(167,139,250,.25); border-radius: 6px; padding: .02rem .35rem; white-space: nowrap; }}
.opp {{ position: relative; background: linear-gradient(160deg, rgba(139,92,246,.10), rgba(23,19,33,.9)); border: 1px solid rgba(167,139,250,.3);
  border-radius: 14px; padding: 1rem 1.1rem 1rem 3.4rem; margin: .6rem 0; animation: fadein .3s ease; }}
.opp .n {{ position: absolute; left: 1rem; top: 1rem; width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center;
  background: var(--purple); color: #fff; font-weight: 700; font-size: .85rem; }}
.opp p {{ color: var(--text) !important; margin: 0 !important; line-height: 1.55; font-size: .95rem; }}
.callout {{ display: flex; gap: .75rem; align-items: flex-start; border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
  background: color-mix(in srgb, var(--c) 6%, var(--bg2)); border-radius: 12px; padding: .85rem 1rem; margin: .6rem 0; }}
.callout b {{ color: var(--text); }}
.callout .cbody {{ color: var(--text2); font-size: .9rem; margin-top: .25rem; line-height: 1.55; }}
.callout .cbody ul {{ margin: .3rem 0 0; padding-left: 1.1rem; }}
.legend {{ display: flex; flex-wrap: wrap; gap: .5rem 1.1rem; font-size: .8rem; color: var(--text2); }}
.legend span {{ display: inline-flex; gap: .4rem; align-items: center; }}
.skeleton {{ height: 14px; border-radius: 6px; margin: .5rem 0; background: linear-gradient(90deg, var(--surface) 0, var(--surface2) 50%, var(--surface) 100%);
  background-size: 800px 100%; animation: shimmer 1.3s linear infinite; }}
.navlist {{ display: flex; flex-direction: column; gap: .15rem; }}
.small {{ color: var(--muted); font-size: .78rem; }}
@media (max-width: 900px) {{ .hero {{ grid-template-columns: 1fr; }} .hero h2 {{ font-size: 1.5rem !important; }} }}
</style>
"""
