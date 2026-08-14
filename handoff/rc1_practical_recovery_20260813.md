# SummerTestModel RC1 Practical Recovery Handoff

Status: PRACTICAL_RECOVERY_COMPLETE

Benchmark: 1.0-rc1

Purpose: targeted practical regrade and recovery only; the completed formal
39-model baseline was not restarted or re-finalized.

Branch: `main`

Execution-start HEAD: `066cf32d26ecdcd3142ac85901f6e60621718274`

At executor handoff, execution changes were intentionally left uncommitted and
unpushed for audit. Their later publication state is recorded by repository
history. No history rewrite, reset, merge, or branch change was performed by
the recovery executor.

## Integrity and environment

- Formal doctor: READY
- All byte-level manifest/config/scorer/runtime checks: PASS
- Logical task identity hashes were preserved separately from file-byte hashes
- Negative tamper check for the byte-hash gate: PASS
- Actual Ollama: 0.32.9
- Ollama API: HTTP 200
- Ollama patch-version difference was recorded as a practical environment
  warning only; no update, download, deletion, or configuration change was
  performed
- Targeted model digest revisions: 0
- Model plan revisions: 0
- Recovery execution suite at handoff: 84 tests passed
- Final publication validation: 89 tests passed; Phase 3S golden validation
  checked 116/116 tasks; Phase 3R validator passed

The repair separated file-integrity verification from logical benchmark
identity. It also made recovery evidence atomic, retained final raw-file
hashes in terminal events, used the frozen executor/circuit-breaker path, and
validated live model digests before execution. Benchmark tasks, scoring
semantics, assignments, generation policy, and runtime limits were not
changed.

## Targeted recovery

- Recovery directory: `private_runs/rc1_relaxed_recovery_20260813`
- Planned/accounted: 50 / 50
- Models touched: 8
- Recovery wall time: 10,851.913 seconds (about 3 h 00 m 52 s)
- Raw records saved: 50
- Score records saved: 50
- Raw files present: 50
- Score files present: 50
- Recovery comparison rows: 50
- Practical recovery selections after flat/private scorer payload normalization: 39
- Recovery review-required capability items: 6, all retained with their recorded runtime status
  status
- Missing raw: 0
- Raw/event hash mismatches: 0
- Duplicate inference keys: 0
- Runner exceptions: 0
- Scoring errors: 0
- Infrastructure failures: 0
- Model plan revisions: 0

Recovery inference statuses:

- completed: 38
- truncated: 3
- truncated_before_final: 5
- absolute_timeout: 2
- tool_loop_limit: 1
- tool_not_found: 1

The `nemotron-3-nano:4b / TOOL_07` replay remained `tool_not_found`; it was
recorded once without a capability retry.

## Baseline preservation and derived results

- Original formal baseline records retained: 1,938
- Original raw hash records checked: 1,938; mismatches: 0
- Original strict public result was not modified
- Current strict public result path:
  `public_results/rc1_baseline_20260809.scorer-1.0-rc1.1.jsonl`
- Private practical derivation remains under:
  `private_runs/rc1_relaxed_recovery_20260813/derived/`
- A separate sanitized practical snapshot was exported under `public_results/`;
  it does not replace the strict public baseline

The practical merge used recovery evidence only where the authorized
selection rule allowed it; the original strict evidence remains the source of
the formal baseline public result.

## Privacy and publication state

- `git ls-files private_benchmark`: empty
- `git ls-files private_runs`: empty
- Private evidence remains outside tracked and public files
- `git diff --check`: PASS
- Public result privacy audit: original strict public file unchanged; practical
  export contains derived fields only
- No commit or push was performed for this recovery task
- No cloud benchmark was run
- No model was downloaded, updated, deleted, or replaced
- Retention: UNASSESSED

This handoff contains sanitized execution metadata only. It does not contain
private task content or model-generated payloads.
