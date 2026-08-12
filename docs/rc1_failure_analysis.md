# RC1 Failure Analysis

## Executive finding

The completed baseline has no missing raw evidence, duplicate inference, runner exception, or unresolved infrastructure failure. The visible error population is dominated by bounded generation/truncation, non-terminal streams after meaningful output, tool-loop behavior, and one corrected scorer implementation defect.

## Scorer defect corrected offline

`CORE_PRACT_04` previously raised `TypeError: unhashable type: 'dict'` for three models because the scorer converted an object-containing array to a set. The scorer now validates every list element is a string before set comparison. Raw responses were not changed; all 1,938 records were regraded with scorer `1.0-rc1.1`, repairing all three scorer errors.

Affected models: `granite4:7b-a1b-h`, `olmo-3:7b-instruct`, and `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M`.

## Runtime and model-output findings

- 7 absolute timeouts occurred in reasoning tasks. They are practical-local boundary results, not network failures.
- 12 streams ended after meaningful output but before a terminal Ollama record. Their raw output remains scoreable and is tagged `stream_interrupted_after_output`.
- 104 records are truncation-related: 66 `truncated` plus 38 `truncated_before_final`.
- Tool-loop failures are bounded at three rounds. `nemotron-3-nano:4b` emitted a nonexistent tool name on `TOOL_07`; MiniCPM5 and SmolLM2 repeated or malformed calls on several tool tasks.
- Cloud comparison had five `truncated_before_final` records and no infrastructure failure. Three other cloud catalog entries returned provider HTTP 410 and were recorded as unavailable, never capability score zero.

## Resolution policy

- Scorer defect: fix and offline regrade existing immutable raw (completed).
- Wrong answer, malformed output, repetition, tool-name/argument error, timeout after generation, and truncation: preserve as model/runtime result; do not retry automatically.
- Transport failure before meaningful output: use the frozen bounded retry/circuit-breaker policy.
- Stream interruption after meaningful output: preserve and score available evidence, tag incomplete terminal metadata, and only targeted-rerun if a future explicitly approved study requires it.
- Ollama patch-version drift: record as environment metadata. It is only blocking when the API is unavailable, a required capability is broken, or evidence integrity cannot be guaranteed.

## Machine-readable counts

See `public_results/rc1_failure_counts.csv`.
