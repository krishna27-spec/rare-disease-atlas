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
| Gene | 23 |
| Disease | 22 |
| Paper | 18 |

## Edges by evidence type

| evidence type | count |
|---|---|
| curated | 3204 |
| inferred | 44 |
| text_mined | 21 |

## Edges by predicate

| predicate | count |
|---|---|
| has_phenotype | 1405 |
| studied_in_trial | 543 |
| investigator_of | 434 |
| funded_by | 358 |
| has_asset | 232 |
| participates_in_pathway | 214 |
| similar_to | 44 |
| gene_associated_with_disease | 39 |

## Text-mined facts

- 774 abstracts collected; 712 mention one of our diseases or genes (62 off-topic removed before reading).
- 42 abstracts read by the LLM; 34 gave at least one fact.
- 98 facts kept after the quote check; 4 more were dropped because the quoted sentence was not in the abstract.
- 21 became graph edges. Dropped while resolving to stable IDs: 24 unresolved (name not in graph), 37 out of scope (disease not one of ours / not this paper's), 16 pathway predicate has no disease->pathway home.

## Connections

- 0 contradictions found among 21 text-mined facts (extraction has no negation field)
- 47 investigators work across 2+ diseases (11 across clusters).
- 543 asset/trial rows linked to diseases.
