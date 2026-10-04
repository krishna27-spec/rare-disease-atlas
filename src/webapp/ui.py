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

# Evidence type -> (colour, friendly label, one-line meaning, technical name). The friendly label is what
# people see first; the technical name (the backend's evidence_type) appears in tooltips and detail panels.
# Each type also has its own glyph and line style, so meaning never depends on colour alone.
EVIDENCE = {
    "curated": (GREEN, "Verified source", "From a curated database or registry.", "curated"),
    "text_mined": (CYAN, "Research literature",
                   "Extracted from a published abstract by an AI; the exact quote was checked word for word against "
                   "the source.", "text-mined"),
    "inferred": (AMBER, "Atlas-derived",
                 "Computed by the Atlas from related evidence: a hypothesis to investigate, not a direct observation.",
                 "inferred"),
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
        return "Computed similarity"
    return "Strong evidence" if conf >= 0.85 else "Moderate evidence" if conf >= 0.6 else "Tentative evidence"


def relation_sentence(e: dict, subj: str, obj: str) -> str:
    """Restates the edge in words. Uses only the edge's own fields: no extra claims."""
    src, p = e.get("source") or "The source", e.get("predicate", "")
    if e.get("evidence_type") == "text_mined":
        return (f"A published study ({e.get('source_record') or 'PubMed'}) states that {subj} "
                f"{p.replace('_', ' ')} {obj}.")
    return {
        "gene_associated_with_disease": f"{source_name(src)} records {subj} as a gene whose variants are linked to {obj}.",
        "has_phenotype": f"{source_name(src)} lists “{obj}” as a recorded symptom or trait of {subj}.",
        "participates_in_pathway": f"{source_name(src)} places the gene {subj} in the pathway “{obj}”.",
        "similar_to": (f"The Atlas computed that {subj} and {obj} are alike, from shared symptoms (rarer symptoms "
                       "count more) and shared pathways."),
        "studied_in_trial": f"{source_name(src)} lists {subj} as a condition studied in {obj}.",
        "has_asset": f"{source_name(src)} lists {obj} as a study or resource for {subj}.",
        "investigator_of": f"{source_name(src)} names {subj} as an investigator on {obj}.",
        "funded_by": f"{source_name(src)} lists the grant {obj} as funding work on {subj}.",
        "serves_disease": f"{source_name(src)} shows {subj} serving people with {obj}.",
    }.get(p, f"{source_name(src)} records: {subj} — {p.replace('_', ' ')} — {obj}.")


WHY_IT_MATTERS = {
    "curated": "Comes straight from a curated database or registry: the most direct kind of evidence in the Atlas.",
    "text_mined": "One paper's finding, quoted exactly. Treat it as a lead to check, not as settled fact.",
    "inferred": "Calculated by the Atlas, not observed. Use it to decide what to investigate, not as a conclusion.",
}

_SOURCE_NAMES = {"PubMed": "Published study", "ClinicalTrials.gov": "ClinicalTrials.gov registry",
                 "NIH RePORTER": "NIH RePORTER grant record", "HPO annotations": "Human Phenotype Ontology",
                 "Orphadata product 6": "Orphanet (Orphadata)", "Reactome": "Reactome pathway database",
                 "Atlas similarity": "The Atlas similarity model"}


def source_name(src: str) -> str:
    return _SOURCE_NAMES.get(src, src)


def source_ref(e: dict) -> str:
    """The short record people can look up: a PMID or NCT number, else the first part of the record key."""
    rec = str(e.get("source_record") or "")
    return rec.split("|")[0] if rec else ""


# ------------------------------------------------------------------ HTML building blocks
def pill(etype: str) -> str:
    colour, label, meaning, tech = EVIDENCE.get(etype, (MUTED, etype, "", etype))
    return (f'<span class="pill" style="--c:{colour}" title="{escape(meaning)} (technical type: {tech})">'
            f'{icon(etype, 13, colour, 2)}{escape(label)}</span>')


def chip(text: str, kind: str | None = None, mono: bool = False) -> str:
    ic = icon(kind, 13, KIND_ACCENT.get(kind, LAVENDER)) if kind else ""
    return f'<span class="chip{" mono" if mono else ""}">{ic}{escape(str(text))}</span>'


def meter(value: float, etype: str = "curated", label: str | None = None) -> str:
    """Evidence strength as words and a bar; the number is in the tooltip."""
    v = max(0.0, min(float(value), 1.0))
    colour = EVIDENCE.get(etype, (PURPLE,))[0]
    text = label if label is not None else confidence_word(v, etype)
    tip = (f"Score {v:.2f}, assigned by the Atlas evidence model" if etype != "inferred"
           else f"Similarity score {v:.2f}, computed by the Atlas")
    return (f'<div class="meter" title="{tip}" role="img" aria-label="{escape(text)} ({v:.2f})"><div class="bar">'
            f'<span style="width:{v * 100:.0f}%;background:{colour}"></span></div>'
            f'<span class="mtext">{escape(text)}</span></div>')


def _clean(v):
    return "" if v is None or (isinstance(v, float) and v != v) else v


def evidence_card(e: dict, subj: str, obj: str, eid: str) -> str:
    """'Why is this connected?' for one edge. Level 2 shows the claim, its strength and source; the quote and the
    technical record (retrieved date, record key, edge ID, review status) sit behind 'Evidence details'."""
    e = {k: (v if k == "contradicts" else _clean(v)) for k, v in e.items()}
    t = e.get("evidence_type", "")
    conf = float(e.get("confidence") or 0)
    ref = source_ref(e)
    link = (f'<a href="{escape(e["source_url"])}" target="_blank" rel="noopener">View source ↗</a>'
            if e.get("source_url") else "")
    contra = list(e.get("contradicts") if e.get("contradicts") is not None else [])
    contra_html = (f'<details class="contra"><summary>{icon("contradiction", 14, RED)} Conflicting evidence · '
                   f'{len(contra)} record{"s" if len(contra) != 1 else ""} disagree</summary>'
                   f'<div class="small">{", ".join(escape(c) for c in contra)}</div></details>' if contra else
                   '<div class="small quiet">No contradictory evidence recorded.</div>')
    reviewer = e.get("reviewer_verdict") or "not_reviewed"
    quote_html = f'<blockquote>“{escape(e["evidence_text"])}”</blockquote>' if e.get("evidence_text") else ""
    method = f'<div class="kv"><b>How computed</b>{escape(e["method"])}</div>' if e.get("method") else ""
    return f"""<div class="ev" style="--c:{EVIDENCE.get(t, (MUTED,))[0]}">
  <div class="ev-top">{pill(t)}<span class="ev-rel">{escape(subj)} <span class="pred">→</span> {escape(obj)}</span></div>
  <p class="ev-why">{escape(relation_sentence(e, subj, obj))}</p>
  <div class="ev-row">{meter(conf, t)}<span class="src">{escape(source_name(e.get('source', '')))}{f' · {escape(ref)}' if ref and t != 'inferred' else ''}</span>{link}</div>
  {contra_html}
  <details class="more"><summary>Evidence details</summary>
    {quote_html}
    <div class="ev-grid">
      <div class="kv"><b>Why it matters</b>{escape(WHY_IT_MATTERS.get(t, ''))}</div>
      <div class="kv"><b>Relationship</b>{escape(e.get('predicate', '').replace('_', ' '))}</div>
      <div class="kv"><b>Source record</b>{escape(str(e.get('source_record', '')))}</div>
      <div class="kv"><b>Retrieved</b>{escape(str(e.get('retrieved', '')))}</div>
      <div class="kv"><b>Score</b>{conf:.2f} ({escape(EVIDENCE.get(t, ('', '', '', t))[3])})</div>
      <div class="kv"><b>Independent review</b>{'not yet reviewed' if reviewer == 'not_reviewed' else escape(reviewer)}</div>
      {method}
      <div class="kv"><b>Edge ID</b><code>{escape(eid)}</code></div>
    </div>
  </details>
</div>"""


def view_head(question: str, sub: str = "", kicker: str = "") -> str:
    k = f'<div class="kicker">{escape(kicker)}</div>' if kicker else ""
    s = f'<p class="vsub">{escape(sub)}</p>' if sub else ""
    return f'<div class="vhead">{k}<h2>{escape(question)}</h2>{s}</div>'


def section(title: str, sub: str = "", ic: str | None = None) -> str:
    i = icon(ic, 18, LAVENDER) if ic else ""
    s = f'<p class="sec-sub">{escape(sub)}</p>' if sub else ""
    return f'<div class="sec"><h3>{i}{escape(title)}</h3>{s}</div>'


def callout(kind: str, title: str, body_html: str) -> str:
    colour, ic = {"warn": (AMBER, "contradiction"), "info": (CYAN, "info"), "empty": (LAVENDER, "search"),
                  "ok": (GREEN, "check"), "error": (RED, "contradiction")}[kind]
    return (f'<div class="callout" style="--c:{colour}">{icon(ic, 20, colour)}<div><b>{escape(title)}</b>'
            f'<div class="cbody">{body_html}</div></div></div>')


def stats(items: list[tuple[str, str, str]]) -> str:
    """A quiet row of key numbers: (icon, value, label)."""
    return '<div class="stats">' + "".join(
        f'<div class="stat">{icon(ic, 16, LAVENDER)}<b>{escape(str(v))}</b><span>{escape(lbl)}</span></div>'
        for ic, v, lbl in items) + "</div>"


def legend_inline() -> str:
    return '<div class="legend">' + "".join(
        f'<span title="{escape(m)}">{pill(k)}</span>' for k, (_, _, m, _) in EVIDENCE.items()) + "</div>"


def transition_overlay() -> str:
    """Played once after 'Enter the Atlas': the intro's network (same layout, as a still image) zooms past the
    viewer and fades, so the Atlas appears to open out of it."""
    import math
    W, H, ox, oy, rx, ry = 1600, 1000, 800, 340, 520, 210
    pts = [(ox + math.cos(-math.pi / 2 + (i + .5) * 2 * math.pi / 8) * rx,
            oy + math.sin(-math.pi / 2 + (i + .5) * 2 * math.pi / 8) * ry) for i in range(8)]
    lines = "".join(f'<path d="M{ox} {oy} Q{(ox + x) / 2 - (y - oy) * .18 * (1 if i % 2 else -1)} '
                    f'{(oy + y) / 2 + (x - ox) * .18 * (1 if i % 2 else -1)} {x} {y}" stroke="{LAVENDER}" '
                    f'stroke-opacity=".5" fill="none" stroke-width="1.4"/>' for i, (x, y) in enumerate(pts))
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="9" fill="{SURFACE}" stroke="{LAVENDER}" stroke-width="1.6"/>'
                   f'<circle cx="{x}" cy="{y}" r="3" fill="{LAVENDER}"/>' for x, y in pts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">'
           f'<rect width="{W}" height="{H}" fill="{BG}"/>{lines}{dots}'
           f'<circle cx="{ox}" cy="{oy}" r="30" fill="none" stroke="{LAVENDER}" stroke-width="2"/></svg>')
    return (f'<div class="enter-zoom" aria-hidden="true" style="background-image:url(\'data:image/svg+xml;'
            f'charset=utf-8,{quote(svg)}\')"></div>')


# ------------------------------------------------------------------ page CSS
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {{ --bg:{BG}; --bg2:{BG2}; --surface:{SURFACE}; --surface2:{SURFACE2}; --purple:{PURPLE};
  --deep:{PURPLE_DEEP}; --lav:{LAVENDER}; --text:{TEXT}; --text2:{TEXT2}; --muted:{MUTED}; --line:{LINE};
  --green:{GREEN}; --amber:{AMBER}; --red:{RED}; --cyan:{CYAN}; }}
html, body, [data-testid="stAppViewContainer"], .stApp {{ background: var(--bg) !important; }}
.stApp {{ background: radial-gradient(1100px 520px at 85% -10%, rgba(109,59,255,.08), transparent 60%), var(--bg) !important; }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button, .stApp textarea {{
  font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.stApp code, .mono {{ font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace !important; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; letter-spacing: -.015em; color: var(--text); }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding-top: 1.4rem; max-width: 1240px; }}
a {{ color: var(--lav) !important; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
::selection {{ background: rgba(139,92,246,.35); }}
*:focus-visible {{ outline: 2px solid var(--lav) !important; outline-offset: 2px; }}
[data-testid="stMainBlockContainer"] > div {{ animation: fadein .35s ease; }}

/* sidebar: navigation only */
[data-testid="stSidebar"] {{ background: var(--bg2) !important; border-right: 1px solid var(--line); }}
.st-key-sidenav .stButton > button {{ width: 100%; justify-content: flex-start; border: none !important; background: transparent !important;
  color: var(--text2) !important; padding: .45rem .7rem !important; border-radius: 8px !important; transform: none !important; }}
.st-key-sidenav .stButton > button > div, .st-key-current .stButton > button > div {{ justify-content: flex-start; width: 100%; }}
.st-key-sidenav .stButton > button:hover {{ background: rgba(139,92,246,.08) !important; color: var(--text) !important; }}
.st-key-sidenav .stButton > button[kind="primary"] {{ background: rgba(139,92,246,.16) !important; color: #fff !important;
  box-shadow: inset 2px 0 0 var(--purple); font-weight: 600; }}
.st-key-current .stButton > button {{ width: 100%; text-align: left; justify-content: flex-start; background: var(--surface) !important;
  border: 1px solid var(--line) !important; padding: .6rem .8rem !important; white-space: normal; line-height: 1.35; }}
.side-label {{ color: var(--muted); font-size: .68rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; margin: .2rem 0 .3rem; }}
.side-rule {{ border-top: 1px solid var(--line); margin: .7rem 0; }}

/* inputs */
.stTextInput input {{ background: var(--surface) !important; border-radius: 12px !important; color: var(--text) !important;
  font-size: 1rem; padding: .8rem 1rem .8rem 2.6rem !important; }}
.stTextInput [data-baseweb="input"] {{ border-radius: 12px !important; border: 1px solid var(--line) !important;
  background: var(--surface) !important; transition: border-color .15s, box-shadow .15s; }}
.stTextInput [data-baseweb="input"]:focus-within {{ border-color: var(--purple) !important; box-shadow: 0 0 0 4px rgba(139,92,246,.18) !important; }}
.st-key-searchbox, .st-key-searchbox_home {{ position: relative; }}
.st-key-searchbox::before, .st-key-searchbox_home::before {{ content: ""; position: absolute; left: 14px; bottom: 14px; width: 18px; height: 18px; z-index: 2;
  background: no-repeat center/18px url("data:image/svg+xml;charset=utf-8,{quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + LAVENDER + '" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>')}"); }}
.st-key-searchbox_home input {{ font-size: 1.12rem; padding-top: 1rem !important; padding-bottom: 1rem !important; }}
.stSelectbox [data-baseweb="select"] > div {{ background: var(--surface) !important; border-color: var(--line) !important; border-radius: 10px !important; }}

/* buttons */
.stButton > button, .stLinkButton > a, [data-testid="stPopover"] button {{ border-radius: 10px !important; border: 1px solid var(--line) !important;
  background: var(--surface) !important; color: var(--text) !important; transition: all .15s ease; }}
.stButton > button:hover {{ border-color: var(--purple) !important; color: #fff !important; }}
.stButton > button[kind="primary"] {{ background: linear-gradient(180deg, {PURPLE}, {PURPLE_DEEP}) !important;
  border: 1px solid rgba(167,139,250,.55) !important; color: #fff !important; font-weight: 600; }}
.stButton > button[kind="tertiary"] {{ background: transparent !important; border: none !important; color: var(--lav) !important; padding-left: 0 !important; }}
.stButton > button[kind="tertiary"]:hover {{ text-decoration: underline; }}

/* top navigation: six views, not steps */
.st-key-topnav {{ border-bottom: 1px solid var(--line); margin-bottom: .4rem; overflow-x: auto; scrollbar-width: none; }}
.st-key-topnav [role="radiogroup"] {{ flex-wrap: nowrap !important; gap: .15rem; border: none !important; background: transparent !important; width: max-content; }}
.st-key-topnav [data-testid="stButtonGroup"], .st-key-topnav .stButtonGroup {{ width: max-content; }}
.st-key-topnav button[data-variant="segmented_control"] {{ background: transparent !important; border: none !important;
  border-radius: 0 !important; color: var(--text2) !important; padding: .6rem .95rem !important; box-shadow: none !important;
  white-space: nowrap; transition: color .15s, box-shadow .2s; }}
.st-key-topnav button[data-variant="segmented_control"]:hover {{ color: var(--text) !important; background: rgba(139,92,246,.06) !important; }}
.st-key-topnav button[data-variant="segmented_control"][aria-checked="true"] {{ color: #fff !important; font-weight: 600;
  box-shadow: inset 0 -2px 0 var(--purple) !important; background: transparent !important; }}

/* expanders = quiet disclosure */
[data-testid="stExpander"] details {{ background: transparent; border: 1px solid var(--line) !important; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ color: var(--text2); font-weight: 500; }}
[data-testid="stExpander"] summary:hover {{ color: var(--text); }}
iframe {{ border-radius: 16px; border: 1px solid var(--line) !important; background: var(--bg2); }}

@keyframes fadein {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes shimmer {{ 0% {{ background-position: -400px 0; }} 100% {{ background-position: 400px 0; }} }}
@keyframes zoompast {{ 0% {{ opacity: 1; transform: scale(1); }} 70% {{ opacity: .6; }} 100% {{ opacity: 0; transform: scale(5.5); }} }}
.enter-zoom {{ position: fixed; inset: 0; z-index: 999999; pointer-events: none; background-size: cover; background-position: center 34%;
  transform-origin: 50% 34%; animation: zoompast 1.1s cubic-bezier(.55,.05,.35,1) forwards; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} .enter-zoom {{ display: none; }} }}

/* ---- components ---- */
.ic {{ display: inline-block; vertical-align: -3px; flex: none; }}
.brand {{ display: flex; align-items: center; gap: .7rem; }}
.brand .logo {{ width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center;
  background: linear-gradient(145deg, rgba(139,92,246,.28), rgba(109,59,255,.08)); border: 1px solid rgba(167,139,250,.35); }}
.brand .name {{ font-weight: 650; color: var(--text); }}
.kicker {{ color: var(--lav); font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; margin-bottom: .25rem; }}
.vhead {{ margin: 1.1rem 0 1rem; }}
.vhead h2 {{ font-size: 1.55rem !important; margin: 0 !important; padding: 0 !important; font-weight: 650; }}
.vsub {{ color: var(--text2) !important; font-size: .95rem; margin: .35rem 0 0 !important; max-width: 760px; line-height: 1.55; }}
.sec {{ margin: 2.2rem 0 .7rem; }}
.sec h3 {{ display: flex; align-items: center; gap: .5rem; font-size: 1.05rem !important; margin: 0 !important; padding: 0 !important; font-weight: 600; }}
.sec-sub {{ color: var(--muted) !important; font-size: .87rem; margin: .25rem 0 0 !important; }}
.small {{ color: var(--muted); font-size: .8rem; }}
.quiet {{ color: var(--muted); }}

.entity {{ display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap; color: var(--text2); font-size: .9rem; margin-top: .2rem; }}
.entity b {{ color: var(--text); font-size: 1rem; font-weight: 600; }}
.hero h1 {{ font-size: clamp(2rem, 3.4vw, 2.7rem) !important; font-weight: 700; margin: .2rem 0 .1rem !important; padding: 0 !important; letter-spacing: -.03em; line-height: 1.1; }}
.hero .type {{ display: inline-flex; gap: .4rem; align-items: center; color: var(--lav); font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; }}
.hero .gene {{ display: flex; align-items: center; gap: .55rem; margin: .9rem 0 .2rem; color: var(--text2); }}
.hero .gene b {{ font-size: 1.25rem; color: var(--text); font-weight: 650; }}
.hero .lead {{ color: var(--text2); font-size: 1.05rem; line-height: 1.6; max-width: 720px; margin: 1rem 0 0; }}
.hero .lead b {{ color: var(--text); font-weight: 600; }}
.stats {{ display: flex; flex-wrap: wrap; gap: .4rem 1.8rem; margin: 1.1rem 0 .2rem; }}
.stat {{ display: flex; align-items: baseline; gap: .4rem; color: var(--text2); font-size: .9rem; }}
.stat .ic {{ align-self: center; }}
.stat b {{ color: var(--text); font-size: 1.15rem; font-weight: 650; }}

.home h1 {{ font-size: clamp(2rem, 3.6vw, 2.8rem) !important; font-weight: 700; letter-spacing: -.03em; margin: 2.5rem 0 .4rem !important; padding: 0 !important; }}
.home p {{ color: var(--text2) !important; font-size: 1.05rem; margin: 0 0 1.2rem !important; }}
.st-key-shortcuts .stButton > button, .st-key-next .stButton > button {{ width: 100%; justify-content: space-between; text-align: left;
  padding: .9rem 1.1rem !important; background: var(--bg2) !important; font-size: .98rem; }}
.st-key-shortcuts .stButton > button:hover, .st-key-next .stButton > button:hover {{ background: rgba(139,92,246,.08) !important; }}

.chip {{ display: inline-flex; align-items: center; gap: .35rem; padding: .2rem .6rem; border-radius: 999px; font-size: .8rem;
  background: rgba(139,92,246,.08); border: 1px solid rgba(167,139,250,.22); color: var(--text); margin: 0 .3rem .35rem 0; }}
.chip.mono {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: .74rem; color: var(--text2); background: transparent; border-color: var(--line); }}
.pill {{ display: inline-flex; align-items: center; gap: .3rem; padding: .12rem .55rem; border-radius: 999px; font-size: .74rem;
  font-weight: 600; color: var(--c); border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  background: color-mix(in srgb, var(--c) 10%, transparent); white-space: nowrap; cursor: help; }}
.legend {{ display: flex; flex-wrap: wrap; gap: .4rem; }}

.meter {{ display: inline-flex; align-items: center; gap: .55rem; cursor: help; }}
.meter .bar {{ width: 110px; height: 6px; border-radius: 6px; background: rgba(255,255,255,.07); overflow: hidden; }}
.meter .bar span {{ display: block; height: 100%; border-radius: 6px; }}
.meter .mtext {{ font-size: .8rem; color: var(--text2); white-space: nowrap; }}

.ev {{ border: 1px solid var(--line); border-left: 3px solid var(--c); border-radius: 12px; padding: .8rem .95rem; background: var(--bg2); margin: .55rem 0; animation: fadein .2s ease; }}
.ev-top {{ display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }}
.ev-rel {{ font-size: .9rem; color: var(--text); font-weight: 500; }}
.ev-rel .pred {{ color: var(--muted); margin: 0 .15rem; }}
.ev-why {{ color: var(--text2) !important; font-size: .88rem; margin: .45rem 0 .5rem !important; line-height: 1.5; }}
.ev-row {{ display: flex; align-items: center; gap: .5rem 1.1rem; flex-wrap: wrap; font-size: .82rem; color: var(--text2); }}
.ev details {{ margin-top: .45rem; }}
.ev summary {{ cursor: pointer; color: var(--muted); font-size: .8rem; list-style: none; }}
.ev summary::-webkit-details-marker {{ display: none; }}
.ev summary::before {{ content: "▸ "; }} .ev details[open] > summary::before {{ content: "▾ "; }}
.ev summary:hover {{ color: var(--text); }}
.ev details.contra summary {{ color: var(--red); }}
.ev blockquote {{ margin: .5rem 0; padding: .5rem .8rem; border-left: 2px solid var(--cyan); background: rgba(103,198,214,.06);
  color: var(--text); font-size: .88rem; border-radius: 0 8px 8px 0; font-style: italic; }}
.ev-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .4rem 1rem; margin-top: .45rem; }}
.kv {{ font-size: .8rem; color: var(--text2); display: flex; flex-direction: column; gap: .1rem; word-break: break-word; }}
.kv b {{ color: var(--muted); font-weight: 500; font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; }}
.kv code {{ background: transparent; color: var(--text2); padding: 0; font-size: .75rem; }}

.row {{ display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }}
.item {{ padding: .85rem 0; border-bottom: 1px solid var(--line); }}
.item:last-child {{ border-bottom: none; }}
.item .t {{ color: var(--text); font-size: .95rem; font-weight: 500; }}
.item .m {{ color: var(--muted); font-size: .8rem; margin-top: .15rem; }}
.item .w {{ color: var(--text2); font-size: .88rem; margin-top: .3rem; line-height: 1.5; }}
.status {{ font-size: .72rem; padding: .05rem .5rem; border-radius: 999px; border: 1px solid var(--line); color: var(--text2); white-space: nowrap; }}
.status.live {{ color: var(--green); border-color: rgba(95,211,154,.4); }}
.cite {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: .7rem; color: var(--lav); background: rgba(139,92,246,.1);
  border: 1px solid rgba(167,139,250,.25); border-radius: 6px; padding: .02rem .35rem; white-space: nowrap; }}
.opp {{ border: 1px solid rgba(167,139,250,.28); background: linear-gradient(160deg, rgba(139,92,246,.08), rgba(13,10,21,.9));
  border-radius: 14px; padding: 1rem 1.15rem; margin: .7rem 0; animation: fadein .3s ease; }}
.opp .k {{ color: var(--lav); font-size: .7rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; }}
.opp h4 {{ margin: .25rem 0 .55rem !important; padding: 0 !important; font-size: 1.02rem !important; font-weight: 600; }}
.opp .g {{ display: grid; grid-template-columns: 150px 1fr; gap: .35rem .9rem; font-size: .88rem; }}
.opp .g b {{ color: var(--muted); font-weight: 500; font-size: .8rem; }}
.opp .g span {{ color: var(--text2); }}
.opp p {{ color: var(--text) !important; margin: 0 !important; line-height: 1.55; font-size: .95rem; }}
.callout {{ display: flex; gap: .75rem; align-items: flex-start; border: 1px solid color-mix(in srgb, var(--c) 30%, transparent);
  background: color-mix(in srgb, var(--c) 5%, var(--bg2)); border-radius: 12px; padding: .85rem 1rem; margin: .6rem 0; }}
.callout b {{ color: var(--text); }}
.callout .cbody {{ color: var(--text2); font-size: .9rem; margin-top: .25rem; line-height: 1.55; }}
.callout .cbody ul {{ margin: .3rem 0 0; padding-left: 1.1rem; }}
.skeleton {{ height: 14px; border-radius: 6px; margin: .5rem 0; background: linear-gradient(90deg, var(--surface) 0, var(--surface2) 50%, var(--surface) 100%);
  background-size: 800px 100%; animation: shimmer 1.3s linear infinite; }}

/* biology chain */
.st-key-chain .stButton > button {{ width: 100%; text-align: left; justify-content: flex-start; padding: .8rem 1rem !important;
  background: var(--bg2) !important; white-space: normal; line-height: 1.35; }}
.st-key-chain .stButton > button[kind="primary"] {{ background: rgba(139,92,246,.14) !important; border-color: var(--purple) !important; box-shadow: none; }}
.arrow {{ text-align: center; color: var(--muted); line-height: 1; margin: .1rem 0; font-size: 1rem; }}

.footer {{ margin: 3rem 0 1rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .8rem; text-align: center; }}
.footer details summary {{ cursor: pointer; list-style: none; display: inline; }}
.footer details summary::-webkit-details-marker {{ display: none; }}
.footer details p {{ color: var(--text2) !important; max-width: 560px; margin: .5rem auto 0 !important; }}
@media (max-width: 900px) {{ .opp .g {{ grid-template-columns: 1fr; }} }}
</style>
"""
