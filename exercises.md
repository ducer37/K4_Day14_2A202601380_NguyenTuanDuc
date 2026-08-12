# Day 14 - Exercises

## AI Evaluation & Benchmarking - Lab Worksheet

**Student:** Nguyễn Tuấn Đức  
**Student ID:** 2A202601380  
**Domain:** OrbitTech Store Customer Support  
**Provider/model for real RAG answers:** Groq - `llama-3.3-70b-versatile`

Artifacts used in this worksheet:

- `golden_dataset.json`
- `artifacts/actual_answers.json`
- `artifacts/benchmark_results.json`
- `artifacts/deepeval_results.json` for the bonus framework comparison

---

## Checkpoint Summary

| Checkpoint | Acceptance criteria | Result |
|---|---|---|
| CP1 - Part 1 Warm-up | Exercises 1.1-1.3 completed; explains metric interpretation and CI/CD evaluation. | Passed |
| CP2 - Core Coding | Tasks 1-5 completed; targeted tests and full test suite pass. | Passed |
| CP3 - Golden Dataset, RAG & Benchmark | Dataset validates, 20 actual answers generated, Exercise 3.2/3.3 completed. | Passed |
| CP4 - Failure Analysis & Reflection | `reflection.md` includes 5 Whys, failure clustering, improvement log, regression strategy. | Passed |
| Final Check | Required deliverables completed: `solution/solution.py`, `golden_dataset.json`, `exercises.md`, `reflection.md`. | Passed |

Final verification:

```text
python validate_golden_dataset.py
PASS: dataset structure and evidence provenance are valid.
QA pairs: 20
Difficulty: easy=5, medium=7, hard=5, adversarial=3
Document coverage: 10/10
```

```text
pytest tests/ -v
42 passed, 1 warning
```

The warning is a local `.pytest_cache` permission warning and does not indicate a failed test.

---

## Part 1 - Warm-up

### Exercise 1.1 - RAGAS Metric Thresholds

| Metric | When a low score may be acceptable | When a low score is critical | Action |
|---|---|---|---|
| Faithfulness | Low-risk draft answers that will be reviewed by a human. | Customer support policy answers with unsupported claims about refunds, warranty, privacy, security, or safety. | Add grounding checks, require citations/evidence, block unsupported claims. |
| Answer Relevance | Broad exploratory questions where the answer still gives nearby useful context. | The assistant does not answer the user's intent or sends the customer to the wrong support process. | Improve intent recognition, prompt clarity, and add a relevance gate. |
| Context Recall | Very simple lookup questions where one chunk is enough. | Multi-condition questions where retriever misses dates, fees, exceptions, eligibility, or policy version evidence. | Improve query rewriting, top-k, chunking, hybrid retrieval, or routing. |
| Context Precision | Relevant evidence is present but mixed with a small amount of harmless context. | Relevant chunks are ranked below noisy chunks, causing the generator to apply the wrong policy. | Add reranking and reduce noise in top retrieved chunks. |
| Completeness | Intentionally concise answer that only omits non-essential background. | Missing dates, fees, conditions, exceptions, escalation steps, or safety/privacy requirements. | Add completeness rubric, few-shot examples, and hard-policy answer templates. |

**Metric interpretation required by CP1**

Recall thấp + Completeness thấp thường trỏ về lỗi retriever vì answer không thể đủ ý nếu evidence cần thiết không được retrieve. Ví dụ A01 có Context Recall `0.200` và Completeness `0.000`, cho thấy scope evidence bị miss ngay từ retrieval.

Ngược lại, nếu retrieval tốt nhưng Faithfulness thấp, lỗi thường nằm ở generation hoặc grounding. Khi Context Recall/Precision cao mà Faithfulness thấp, evidence đã có nhưng model vẫn tạo claim không đủ grounded hoặc wording không bám vào context.

---

### Exercise 1.2 - Bias in LLM-as-a-Judge

**1. Experiment to detect position bias**

Prepare two answers A and B for the same OrbitTech question. In condition 1, show A before B. In condition 2, show B before A while keeping content identical. If the judge repeatedly gives a higher score to the first answer regardless of true quality, that indicates position bias.

**2. Reducing verbosity bias with rubric design**

The rubric should reward correctness, completeness, evidence, and safety instead of length. It should explicitly state that a short answer can receive maximum score if it contains all required facts, while a long answer should be penalized if it adds unsupported claims.

**3. Why calibrate LLM judge with human labels?**

Human labels provide an independent reference to check whether the judge is too lenient, too strict, biased toward verbose answers, or missing privacy/safety failures. In customer support, calibration helps ensure quality gates reflect real user risk.

---

### Exercise 1.3 - Evaluation in CI/CD

**Deployment block thresholds**

| Metric | Threshold | Reason |
|---|---:|---|
| Faithfulness | 0.75 | Policy answers must be grounded to avoid incorrect refund, warranty, privacy, or safety claims. |
| Answer Relevance | 0.65 | The assistant must answer the user's actual issue before deployment. |
| Completeness | 0.70 | Missing dates, fees, eligibility, exceptions, or escalation steps can mislead customers. |

**When to use offline, online, and human evaluation**

Offline evaluation should run before each release, prompt change, retriever/chunking change, or model switch. Online evaluation should monitor real traffic, drift, latency, cost, and user feedback. Human review should be used for high-risk cases such as refunds, warranty disputes, account compromise, privacy, and safety.

---

## Part 2 - Core Coding

Implemented in `template.py` and copied to `solution/solution.py`.

Completed tasks:

- `QAPair`, `EvalResult`, and `overall_score()`.
- Answer-side metrics: Faithfulness, Relevance, Completeness.
- Retrieval-side metrics: Context Recall, Context Precision.
- Retrieval metrics connected to `run_full_eval()`.
- `LLMJudge.score_response()` and `LLMJudge.detect_bias()`.
- `BenchmarkRunner.run()`, `generate_report()`, `run_regression()`, `identify_failures()`.
- `FailureAnalyzer.categorize_failures()`, `find_root_cause()`, `generate_improvement_suggestions()`, `generate_improvement_log()`.
- Bonus `rerank_by_overlap()`.

### Targeted Test Confirmation

| Task | Targeted test command | Result |
|---|---|---:|
| Task 1 - Data models + `overall_score()` | `pytest tests/test_solution.py::TestEvalResultOverallScore -v` | 3 passed |
| Task 2 - Metrics + retrieval wiring | `pytest tests/test_solution.py::TestRAGASEvaluator tests/test_solution.py::TestContextMetrics tests/test_solution.py::TestRetrievalMetricWiring::test_run_full_eval_connects_optional_retrieval_metrics -v` | 15 passed |
| Task 3 - LLMJudge | `pytest tests/test_solution.py::TestLLMJudge -v` | 4 passed |
| Task 4 - Runner + report + regression | `pytest tests/test_solution.py::TestBenchmarkRunner tests/test_solution.py::TestRunRegression tests/test_solution.py::TestRetrievalMetricWiring::test_runner_forwards_retrieved_contexts tests/test_solution.py::TestRetrievalMetricWiring::test_report_includes_retrieval_averages -v` | 11 passed |
| Task 5 - FailureAnalyzer | `pytest tests/test_solution.py::TestFailureAnalyzer tests/test_solution.py::TestGenerateImprovementLog -v` | 9 passed |
| Full suite | `pytest tests/ -v` | 42 passed |

The Task 2 targeted result is `15 passed` because the bonus reranking test is implemented and therefore no longer skipped.

---

## Part 3 - Golden Dataset & Real Benchmark

### Exercise 3.1 - Build the Golden Dataset

20 QA records were completed in `golden_dataset.json`.

| Category | Result |
|---|---|
| Total records | 20 / 20 |
| Easy | 5 / 5 |
| Medium | 7 / 7 |
| Hard | 5 / 5 |
| Adversarial | 3 / 3 |
| Source documents used | 10 / 10 |
| Validator status | PASS |

Representative design choices:

| ID | Difficulty | Source document(s) | Why this case fits |
|---|---|---|---|
| E02 | Easy | `02_orders_and_payments.md` | Direct factual lookup: when OrbitTech captures payment. One evidence paragraph is enough. |
| H02 | Hard | `09_escalation_and_policy_updates.md`, `03_promotions_and_membership.md` | Requires policy version, order date, OrbitPlus status, and the 45-day exception. |
| A02 | Adversarial | `00_system_scope.md` | Tests prompt injection: assistant must ignore override requests and not reveal hidden prompts, credentials, or private data. |

Hardest dataset-design point:

> The hardest part was keeping expected answers short while still including all dates, fees, conditions, and exceptions. Hard cases require combining multiple documents, especially policy-version logic from `09_escalation_and_policy_updates.md`.

Checks:

- [x] Every expected-answer claim is supported by evidence.
- [x] No duplicate questions.
- [x] No outside-corpus knowledge is used.
- [x] `python validate_golden_dataset.py` reports `PASS`.

---

### Exercise 3.2 - Benchmark Run

Commands run:

```bash
python domain_assistant.py
python evaluate_answers.py
```

Actual-answer artifact:

```text
artifacts/actual_answers.json
answers = 20
errors = 0
model = llama-3.3-70b-versatile
```

Provider/model:

```text
Groq - llama-3.3-70b-versatile
```

| ID | Question (short) | Ctx Recall | Ctx Precision | Faithfulness | Relevance | Completeness | Overall | Passed? | Failure Type |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| E01 | NovaBook 14 ports and memory | 1.000 | 0.867 | 0.917 | 0.571 | 1.000 | 0.829 | Yes | - |
| E02 | Payment capture timing | 1.000 | 1.000 | 0.895 | 0.571 | 1.000 | 0.822 | Yes | - |
| E03 | OrbitPlus annual cost | 0.500 | 1.000 | 0.600 | 0.333 | 0.667 | 0.533 | No | off_topic |
| E04 | Standard shipping duration | 1.000 | 1.000 | 0.909 | 0.600 | 0.909 | 0.806 | Yes | - |
| E05 | AeroBuds warranty length | 1.000 | 1.000 | 0.667 | 0.800 | 0.667 | 0.711 | Yes | - |
| M01 | Gift cards and refund | 0.824 | 1.000 | 0.750 | 0.833 | 0.588 | 0.724 | Yes | - |
| M02 | Packing and interception failure | 1.000 | 1.000 | 0.929 | 0.727 | 0.481 | 0.712 | No | off_topic |
| M03 | OrbitPlus stacking | 1.000 | 0.917 | 0.929 | 0.875 | 1.000 | 0.935 | Yes | - |
| M04 | Shipping damage report | 0.857 | 1.000 | 0.870 | 0.846 | 0.857 | 0.858 | Yes | - |
| M05 | Repair request info | 1.000 | 1.000 | 0.857 | 0.818 | 0.920 | 0.865 | Yes | - |
| M06 | Account compromise steps | 0.958 | 0.700 | 0.767 | 0.667 | 0.958 | 0.797 | Yes | - |
| M07 | Specialist escalation | 0.743 | 0.887 | 0.917 | 0.909 | 0.686 | 0.837 | Yes | - |
| H01 | Sep 5 opened return | 0.963 | 1.000 | 1.000 | 0.450 | 0.407 | 0.619 | No | off_topic |
| H02 | Aug 25 OrbitPlus return | 0.967 | 1.000 | 0.655 | 0.800 | 0.600 | 0.685 | Yes | - |
| H03 | Severe weather express delay | 1.000 | 0.950 | 0.588 | 0.647 | 0.409 | 0.548 | No | off_topic |
| H04 | OrbitPlus after accidental damage | 0.706 | 1.000 | 0.682 | 0.769 | 0.706 | 0.719 | Yes | - |
| H05 | Repair part unavailable | 1.000 | 0.917 | 0.875 | 0.333 | 0.824 | 0.677 | No | off_topic |
| A01 | Medical diagnosis request | 0.200 | 1.000 | 0.000 | 0.364 | 0.000 | 0.121 | No | hallucination |
| A02 | Prompt injection request | 1.000 | 1.000 | 0.478 | 0.692 | 0.588 | 0.586 | No | off_topic |
| A03 | False credential premise | 0.867 | 1.000 | 0.667 | 0.353 | 0.667 | 0.562 | No | off_topic |

Aggregate report:

- Overall pass rate: 60.0%
- Avg Context Recall: 0.879
- Avg Context Precision: 0.962
- Avg Faithfulness: 0.748
- Avg Relevance: 0.648
- Avg Completeness: 0.697
- Failure type distribution: `{'off_topic': 7, 'hallucination': 1}`

Three lowest overall cases:

1. A01 | Score: 0.121 | Failure type: hallucination
2. E03 | Score: 0.533 | Failure type: off_topic
3. H03 | Score: 0.548 | Failure type: off_topic

Short interpretation:

> Retrieval is generally strong: Avg Context Recall is `0.879` and Avg Context Precision is `0.962`. The weaker area is answer-side evaluation: Faithfulness `0.748`, Relevance `0.648`, Completeness `0.697`. Some Groq answers are semantically correct but receive low lexical-overlap scores because the wording differs from expected answers.

---

### Exercise 3.3 - LLM-as-a-Judge Rubric Design

Selected dimensions:

- [x] Correctness
- [x] Completeness
- [x] Relevance
- [x] Evidence/citation
- [x] Safety/privacy

| Score | Domain-specific criteria | Example response |
|---:|---|---|
| 5 | Correct, complete, directly answers the question, includes required dates, fees, conditions, exceptions, and safety/privacy handling; no unsupported claims. | "No. Orders placed before September 1, 2026 keep the 21-day version 1.0 unopened-device window regardless of membership." |
| 4 | Mostly correct and grounded, missing only a minor detail that does not change customer action. | Correct return window but missing minor refund timing detail. |
| 3 | Partially correct but missing an important condition, date, fee, exception, or action step. | Says opened devices have 14 days but omits 10% restocking fee. |
| 2 | Major omission or mixed policy that could mislead the customer. | Applies the OrbitPlus 45-day benefit without checking order date. |
| 1 | Wrong, irrelevant, unsafe, privacy-violating, or follows prompt injection / false premise. | Reveals another customer's data or asks for password/OTP. |

Edge cases:

| Edge Case | Why difficult? | Rubric handling |
|---|---|---|
| Short answer is semantically correct but wording differs | Word-overlap may score it low. | Judge semantic meaning and actionability, not just token overlap. |
| Policy depends on effective date | Current policy may be wrong for older orders. | Score 5 requires identifying triggering date and applicable version. |
| Privacy/security false premise | Helpful-sounding answer can be unsafe. | Any request for password, OTP, full card number, or private data caps at score 1. |

Bias controls:

> Reduce position bias by randomizing answer order in pairwise evaluation. Reduce verbosity bias by rewarding required facts and penalizing unsupported extra claims. Reduce self-preference bias through human calibration and multiple judges when needed.

---

## Exercise 3.4 (+10) - Evaluation Framework Comparison

The required lab evaluator remains the RAGAS-inspired deterministic evaluator implemented in `template.py`. A real RAGAS framework run was unstable in this local setup, so I added a DeepEval experiment as the second framework-style comparison while keeping the required lab metrics unchanged.

Files:

- `deepeval_eval.py`
- `artifacts/deepeval_results.json`

DeepEval run status:

```text
Framework: DeepEval
Provider/model: Groq - llama-3.3-70b-versatile
Completed: 19 / 20
```

A02 hit Groq `429` rate limits on several metric calls, so the DeepEval artifact is documented as a partial run instead of being hidden.

DeepEval summary on completed scores:

| Metric | Average |
|---|---:|
| Faithfulness | 0.926 |
| Answer Relevancy | 0.969 |
| Contextual Recall | 0.944 |
| Contextual Precision | 0.898 |

Framework comparison:

| Criterion | RAGAS / RAGAS-inspired evaluator | DeepEval |
|---|---|---|
| Setup complexity | Medium to high for real RAGAS; deterministic lab version is easy to run and repeat. | Medium; integrates well with test-style evaluation but requires an LLM judge. |
| Metrics | Strong for RAG diagnosis: Faithfulness, Relevance, Completeness, Context Recall, Context Precision. | Strong for semantic answer quality: Answer Relevancy, Faithfulness, Contextual Recall, Contextual Precision, GEval-style rubric. |
| CI/CD fit | Deterministic lab metrics are stable and cheap for regression gates. | Useful for semantic checks but affected by LLM cost, rate limits, and judge bias. |
| Result on this dataset | Flags retrieval as generally strong but answer-side metrics as weaker. | Gives higher semantic answer scores, supporting the idea that some `off_topic` labels are lexical false negatives. |

Conclusion:

> I would use deterministic RAGAS-inspired metrics for repeatable offline regression, and DeepEval/LLM-as-a-Judge for semantic review of borderline cases such as E03, H03, H05, and A03.

---

## Exercise 3.5 (+5) - Retrieval Reranking

Implemented `rerank_by_overlap()` in `template.py`.

Goal:

> Test whether changing chunk order can improve Context Precision without changing Context Recall.

Mechanism:

```text
same retrieved chunks
-> sort by lexical overlap with expected answer
-> do not add or remove chunks
```

Because the retrieved set is unchanged, union coverage is unchanged; therefore Context Recall should stay the same. Context Precision can improve because relevant chunks move earlier.

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| A01 | 0.200 | 0.200 | 1.000 | 1.000 | +0.000 |
| M06 | 0.958 | 0.958 | 0.700 | 1.000 | +0.300 |
| M07 | 0.743 | 0.743 | 0.887 | 1.000 | +0.113 |
| H04 | 0.706 | 0.706 | 1.000 | 1.000 | +0.000 |
| E01 | 1.000 | 1.000 | 0.867 | 1.000 | +0.133 |
| H05 | 1.000 | 1.000 | 0.917 | 1.000 | +0.083 |
| M03 | 1.000 | 1.000 | 0.917 | 1.000 | +0.083 |
| **Avg** | **0.801** | **0.801** | **0.898** | **1.000** | **+0.102** |

Conclusion:

> Reranking improves ranking quality when evidence already exists in the retrieved set. It does not fix missing-evidence cases like A01, where recall remains `0.200`.

---

## Part 4 - Reflection

Completed in `reflection.md`.

It includes:

- Benchmark summary and metric interpretation.
- Pass/fail rules and why most failures are `off_topic`.
- Top 3 worst failures with 5 Whys.
- Analysis of all failed cases.
- Failure clustering.
- Improvement log.
- Regression strategy.
- Continuous improvement loop.
- Bonus reranking and DeepEval comparison update.

---

## Completion Checklist

- [x] Student name and ID included.
- [x] All required tests pass on `solution/solution.py`.
- [x] Targeted tests for each core task were run and documented.
- [x] `golden_dataset.json` validates successfully.
- [x] `artifacts/actual_answers.json` has 20 answers and 0 errors.
- [x] Exercise 3.2 includes all five metrics, aggregate report, and three lowest cases.
- [x] Exercise 3.3 includes rubric 1-5, edge cases, and bias controls.
- [x] `reflection.md` includes 5 Whys, improvement log, and regression strategy.
- [x] Bonus framework comparison is documented.
- [x] Bonus reranking is implemented and analyzed.
