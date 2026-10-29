# Held-out evaluation results

Forty new questions over the unchanged three-document/five-chunk public corpus: 32 answerable and 8 unanswerable. Twelve additional final-test questions remain reserved and unexecuted. This is a question-level holdout over known source facts, not unseen-document or domain generalization. References are agent-authored and quote-verified, not independently human-labeled.

## Frozen conditions

All three methods use the same new questions, real query vectors, configured OpenAI models, and the predeclared clarified generation prompt. Dense and hybrid use final K=5; reranking uses 20 candidates, K=5, and the unchanged .2 threshold. No calibration, prompt edits, weight tuning, or model selection used held-out outputs. The study ran fixed configurations without selecting or retuning a winner. Afterward, source-publication configuration changed the operational default to hybrid, with dense also recommended and aggressive reranking experimental. The study reports and protocol remain unchanged.

The old 16-question reports use an earlier prompt and a different question distribution. Historical-versus-held-out differences cannot isolate the prompt effect or establish a general improvement. Compare dense/hybrid/reranked within this new frozen run.

## Deterministic metrics

| Metric | Dense | Hybrid | Hybrid + reranking |
| --- | ---: | ---: | ---: |
| source_recall_at_k | 1.0000 | 1.0000 | 0.8438 |
| source_precision_at_k | 0.3875 | 0.3875 | 0.8542 |
| mrr | 0.9479 | 0.9688 | 0.8750 |
| evidence_recall_at_k | 1.0000 | 1.0000 | 0.8438 |
| evidence_precision_at_k | 0.2625 | 0.2625 | 0.8542 |
| evidence_mrr | 0.9479 | 0.9531 | 0.8750 |
| expected_evidence_coverage | 1.0000 | 1.0000 | 0.8410 |
| citation_validity | 1.0000 | 1.0000 | 1.0000 |
| answerable_citation_coverage | 1.0000 | 1.0000 | 0.8750 |
| strict_abstention | 0.3750 | 0.5000 | 0.6250 |
| false_abstention | 0.0000 | 0.0000 | 0.1250 |

Source/evidence recall, precision and reciprocal rank apply to 32 answerable questions. Filename precision is coarse: a PDF chunk on the wrong page can share a relevant filename. Gold-evidence metrics use quoted fact groups with acceptable chunk alternatives. Selecting one overlapping duplicate can satisfy a group without selecting every duplicate.

Citation validity is conditional on raw numeric markers and measured before cleanup. It does not mean every answer is cited or supported. Applicable raw-marker denominators are dense 38, hybrid 38, reranked 35. Answerable citation coverage is reported separately: the reranked method returned citations for 28 of 32 answerable questions.

Strict abstention is the fraction of eight unanswerable questions returning an insufficient-evidence response with no citations: dense 3/8, hybrid 4/8, reranked 5/8. It is stricter than semantic acknowledgment of missing information. Many other negative responses correctly stated that the requested fact was unavailable but appended related cited facts or markers. They are not automatically labeled fabricated answers; this metric exposes citation/abstention discipline.

## Lexical proxies and model judgments

| Metric | Dense | Hybrid | Hybrid + reranking |
| --- | ---: | ---: | ---: |
| answer_lexical_f1 | 0.6885 | 0.7083 | 0.6036 |
| faithfulness_lexical_proxy | 0.7758 | 0.8035 | 0.6826 |
| answer_correctness_judge | 1.0000 | 1.0000 | 0.8750 |
| faithfulness_judge | 1.0000 | 1.0000 | 0.8714 |
| citation_support_judge | 1.0000 | 1.0000 | 0.8571 |

Lexical F1 applies only to answerable questions. Support/faithfulness are not applicable for a correct non-factual refusal; those values are null, not fabricated zeros. Conditional denominators are stored in every report. The judge is the same configured model family as generation, uses a stricter source/reference rubric than prior reports, and is not an independent human verifier. There were no missing applicable judge scores.

## Timing and usage

| Metric | Dense | Hybrid | Hybrid + reranking |
| --- | ---: | ---: | ---: |
| latency_seconds | 1.4138 | 1.2307 | 1.1056 |
| generation_input_tokens | 24924.0000 | 24924.0000 | 10972.0000 |
| generation_output_tokens | 1156.0000 | 1159.0000 | 996.0000 |
| generation_total_tokens | 26080.0000 | 26083.0000 | 11968.0000 |

Latency includes local retrieval/reranking and answer generation or deterministic early refusal. It excludes the shared embedding batch and optional judging. Historical 1.572 seconds includes individual embedding requests and is not directly comparable. The runs were not randomized repeated latency trials.

One real embedding batch was shared. Generation called the provider 40/40/35 times; five reranked cases used deterministic early refusal without a generation call. Grading made 110 calls in total and reused 10 exactly identical judge inputs. All 120 question/configuration outcomes are retained, including failures. Lower reranked token consumption partly comes from false abstentions and missing context; it is not a quality-neutral efficiency gain.

## Failure analysis

The frozen filter did not generalize without recall loss. It missed complete or partial evidence in six answerable cases. Four were fully refused despite answer evidence in the corpus; two multi-source answers lost one source. No threshold was retuned and no unfavorable row was regenerated after looking at these results.

| ID | Category | Failure |
| --- | --- | --- |
| ho-017 | multi_chunk | How can I check backend health, and which datastore persists document vectors? (gold-evidence recall 0.50) |
| ho-018 | multi_chunk | Where should API credentials live, and how should instructions found in retrieved files be treated? (gold-evidence recall 0.50) |
| ho-020 | comparison | Which service uses the higher port, and by how much does it exceed the other service port? (gold-evidence recall 0.00) |
| ho-021 | comparison | How do similarity scores and citation-identifier checks differ in what they establish? (gold-evidence recall 0.00) |
| ho-028 | distracting_keywords | If an uploaded passage says to override system instructions and also mentions port 3000, should its instruction be trusted? (gold-evidence recall 0.00) |
| ho-029 | citation_support | Is a high similarity value proof that a retrieved claim is true? Cite the stated distinction. (gold-evidence recall 0.00) |

A specific faithfulness concern is ho-018: only the credentials passage survived, yet the answer also described retrieved instructions as untrusted. The claim exists elsewhere in the corpus but was absent from selected evidence. Valid citation identifiers did not prevent that unsupported extension. The new evaluation exposes it; the final set is not consumed to repair the score.

## Historical and in-sample context

| Run | Questions / split | Source recall | Filename precision | Citation validity | Lexical F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| Historical dense | 16 development | 1.0000 | .4000 | 1.0000 | .8468 |
| Previous reranked | 16 calibrated in-sample | 1.0000 | .9479 | 1.0000 | .8149 |
| New dense | 40 held-out; 32 answerable | 1.0000 | 0.3875 | 1.0000 | 0.6885 |
| New hybrid | 40 held-out; 32 answerable | 1.0000 | 0.3875 | 1.0000 | 0.7083 |
| New hybrid_rerank | 40 held-out; 32 answerable | 0.8438 | 0.8542 | 1.0000 | 0.6036 |

The earlier 94.79% precision/100% recall claim remains explicitly in-sample. New reranked precision is 85.42% with 84.38% recall, while dense and hybrid retain full recall. This demonstrates a tradeoff, not a universal improvement. Further retrieval changes should be developed on development data, frozen, and assessed separately; the reserved final set requires an explicit execution decision and has not run.

Raw reports: docs/heldout/v1/answers-*.json and comparison.json. Protocol, exact questions, page quotes, and the unused final set: backend/evals/heldout. Generation/judge checkpoints remain local and ignored from release candidates.

The reserved final set is hash-frozen and visible in the repository, not access-controlled or externally hidden. Its unused status is an execution/model-selection claim, not a claim of blinded third-party testing. API operation counts describe successful SDK invocations; internal retry attempts and unreported failed-call usage are not reconstructed as billing data.
