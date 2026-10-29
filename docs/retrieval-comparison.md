# Retrieval and answer comparison

All values below come from saved real API runs. Historical baseline files and the original 16-question dataset are byte-for-byte preserved.

| Run | Recall | Precision | MRR | Citation validity | Lexical F1 | Faithfulness proxy | Mean seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical dense (embedding included) | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8468 | 0.8960 | 1.5719 |
| dense | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8529 | 0.8942 | 1.3387 |
| hybrid | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8463 | 0.8913 | 1.2679 |
| hybrid_rerank | 1.0000 | 0.9479 | 1.0000 | 1.0000 | 0.8149 | 0.8786 | 1.4366 |

The three current runs reuse the same real query vectors; their latency excludes the shared embedding batch and optional judges. They run in A/B/C order, not a randomized repeated timing experiment. Historical latency includes per-question embedding and must not be treated as directly comparable.

All three configurations retained 100% expected-evidence token coverage in retrieval-only evaluation. Mean selected evidence fell from 5 to 1.5625 chunks with reranking/filtering. Generation input tokens fell from 8,657 to 5,101 (41.08%). These are measured token counts, not a dollar savings estimate.

The dense top-1 control reached 100% source recall and 100% filename precision but only 94.49% expected-evidence token coverage. This exposes the coarseness of filename labels and guards against attributing every gain to hybrid search. Hybrid search without filtering did not improve precision.

After the recorded targeted recheck, correctness, faithfulness, and citation-support judge averages were 1.0 for all three configurations, with zero missing scores. The initial reranked report had a citation-support judge average of .9375 because a valid cited partial answer was discarded by refusal validation. That original report and its raw model output remain preserved. The validator was fixed and only the affected example was regenerated/rejudged.

The calibrated threshold is .2 for the tested lightweight reranker. Threshold trials required every question to preserve source recall AND expected-evidence token coverage relative to dense. Calibration used the same sample set: this is an in-sample selection, not a held-out improvement claim.

Lexical F1 and faithfulness proxy fell under the optimized configuration. Model judges stayed high, but they are not independent human labels and may be biased. Retrieval precision improved without an observed source-recall or citation-validity loss on this corpus; generalization remains unverified. No speed improvement is claimed.

Raw retrieval studies, threshold trials, full answers, original/rechecked reports, and conditions are in docs/ablation. The calibration-stage default was hybrid_rerank with K=5, 20 candidates, and .2 threshold. Following the separate held-out study, the operational default is hybrid; dense is also recommended and aggressive reranking is experimental. Historical measurements are unchanged.
