# Graph statistics

Built from `data/graph/` on 2026-10-04.

## Nodes

| node type | count |
|---|---|
| Phenotype | 674 |
| Trial | 342 |
| Investigator | 306 |
| Grant | 233 |
| Asset | 126 |
| Pathway | 79 |
| Paper | 24 |
| Gene | 23 |
| Disease | 22 |

## Edges by evidence type

| evidence type | count |
|---|---|
| curated | 3204 |
| text_mined | 46 |
| inferred | 44 |

## Edges by predicate

| predicate | count |
|---|---|
| has_phenotype | 1425 |
| studied_in_trial | 543 |
| investigator_of | 434 |
| funded_by | 358 |
| has_asset | 232 |
| participates_in_pathway | 214 |
| gene_associated_with_disease | 44 |
| similar_to | 44 |

## Text-mined facts

- 774 abstracts collected; 712 mention one of our diseases or genes (62 off-topic removed before reading).
- 52 abstracts read by the LLM; 43 gave at least one fact.
- 147 facts kept after the quote check; 4 more were dropped because the quoted sentence was not in the abstract.
- 46 became graph edges. Dropped while resolving to stable IDs: 31 unresolved (name not in graph), 49 out of scope (disease not one of ours / not this paper's), 21 pathway predicate has no disease->pathway home.

## Connections

- 0 contradictions found among 46 text-mined facts (extraction has no negation field)
- 47 investigators work across 2+ diseases (11 across clusters).
- 543 asset/trial rows linked to diseases.
