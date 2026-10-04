"""The 10x tab: one milestone, starting a natural history study for MPS IIIC, usual route vs Atlas route.

No invented numbers: durations come from real ClinicalTrials.gov records (data/graph/nhs_timelines.csv) and the
only general claim is quoted from FDA guidance."""
from html import escape

import pandas as pd
import streamlit as st

from src.webapp import ui
from src.webapp.data import GRAPH

FDA = "https://www.fda.gov/media/122425/download"
MPS3C = "MONDO:0009657"


def _card(title: str, ic: str, colour: str, items: list[str], accent: bool = False) -> str:
    style = ("background:linear-gradient(160deg, rgba(139,92,246,.12), rgba(23,19,33,.95));"
             "border-color:rgba(167,139,250,.35)") if accent else ""
    return (f'<div class="card" style="height:100%;{style}"><h4>{ui.icon(ic, 18, colour)}{title}</h4>'
            '<ul style="color:#B8B3C7;font-size:.92rem;line-height:1.6;margin:.4rem 0 0;padding-left:1.1rem">'
            + "".join(f"<li style='margin:.3rem 0'>{i}</li>" for i in items) + "</ul></div>")


def render(G, disease: str) -> None:
    st.html(ui.section("10× idea: start a natural history study for MPS IIIC without starting from zero",
                       "The 10× route", "spark",
                       "Milestone: a family group wants a natural history study (a study that records how the disease "
                       "progresses without treatment), the evidence regulators ask for before trials."))
    tl = pd.read_csv(GRAPH / "nhs_timelines.csv")
    done = tl[(tl.status == "COMPLETED") & tl.months.notna()]
    sib = tl[tl.disease.str.contains("IIIA|IIIB|IIID")]
    own = tl[tl.disease.str.contains("IIIC")]

    st.html('<div class="tiles" style="margin:.6rem 0 1rem">'
            + ui.tile("trial", "Sanfilippo natural history studies", len(tl), "ClinicalTrials.gov")
            + ui.tile("check", "Completed", len(done), "with a known duration")
            + ui.tile("info", "Median duration", f"{done.months.median():.0f} months",
                      f"range {done.months.min():.0f}–{done.months.max():.0f}")
            + ui.tile("person", "Median enrolment", f"{done.enrollment.median():.0f}", "children")
            + ui.tile("asset", "Already for MPS IIIC", len(own), "check these first") + "</div>")

    usual = [f"FDA draft guidance says prospective natural history studies generally take more time than reusing "
             f"existing data, and longitudinal ones can be lengthy and costly "
             f"(<a href='{FDA}' target='_blank' rel='noopener'>FDA, 2019</a>).",
             f"<b style='color:#F5F3FA'>How long do such studies run?</b> Of the {len(tl)} Sanfilippo natural history "
             f"studies in ClinicalTrials.gov, {len(done)} are completed: median <b style='color:#F5F3FA'>"
             f"{done.months.median():.0f} months</b>, range {done.months.min():.0f} to {done.months.max():.0f} months, "
             f"median enrolment {done.enrollment.median():.0f} children.",
             "We could not find a published figure for the time to <i>set up</i> a study (protocol, ethics approval, "
             "sites, funding), so we do not state one."]
    atlas = [f"The graph shows <b style='color:#F5F3FA'>{len(sib)}</b> natural history studies for MPS IIIA, IIIB and "
             "IIID: protocols, outcome measures and teams to learn from, and ask to collaborate with.",
             f"<b style='color:#F5F3FA'>MPS IIIC already has {len(own)} registered:</b> check these first. Joining may "
             "beat starting a new one."]
    atlas += [f"<a href='{escape(r.source_url)}' target='_blank' rel='noopener'>{escape(r.nct)}</a> {escape(r.title)} · "
              f"{escape(str(r.status))} · {escape(str(r.start))} to {escape(str(r.completion))} · {escape(str(r.sponsor))}"
              for r in own.itertuples()]
    atlas.append("Next step: contact the study teams below (see <i>Act · next steps</i> for cited leads).")
    c1, c2 = st.columns(2, gap="medium")
    c1.html(_card("Usual route: build it from scratch", "asset", ui.MUTED, usual))
    c2.html(_card("Atlas route: reuse what sister diseases already built", "pathway", ui.LAVENDER, atlas, accent=True))

    st.html(ui.section("Existing Sanfilippo natural history studies", "Source data", "trial",
                       f"ClinicalTrials.gov, retrieved {tl.retrieved.iloc[0]}. Duration = registered start to "
                       "registered (planned or actual) completion."))
    show = tl[["nct", "disease", "title", "status", "start", "completion", "months", "enrollment", "sponsor"]]
    st.dataframe(show, hide_index=True, width='stretch')

    c1, c2 = st.columns(2, gap="medium")
    c1.html(ui.callout("warn", "Assumptions",
                       "<ul><li>A study for MPS IIIC could reuse outcome measures from MPS IIIA/IIIB. <i>Not yet "
                       "validated:</i> it needs clinicians to confirm the diseases are close enough (they share the "
                       "heparan sulfate degradation pathway, but have different genes).</li>"
                       "<li>Durations are those of the registered studies; a new study could be shorter or longer.</li>"
                       "<li>We state no time or cost saving, because we have no cited figure for one.</li></ul>"))
    c2.html(ui.callout("info", "What must be validated next",
                       "<ol style='margin:.3rem 0 0;padding-left:1.1rem'><li>Whether each existing MPS IIIC study is "
                       "still enrolling and open to this family.</li><li>Whether sister-disease protocols and "
                       "registries can be shared (ask the sponsors).</li><li>Expert review of how well outcome measures "
                       "transfer between subtypes.</li></ol>"))
