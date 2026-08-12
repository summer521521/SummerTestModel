# Historical Failure Modes

Parsed historical records: 1856.

| Status/symptom | Count | Layer | Model-related? | Recommended executor handling |
| --- | ---: | --- | --- | --- |
| `completed` | 1076 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `completed_with_score` | 244 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `network_error` | 235 | infrastructure/runtime | No, unless repeated after healthy runtime | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `syntax_error` | 95 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `truncated` | 94 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `truncated_before_final_answer` | 25 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `unsafe_to_execute` | 23 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `failed` | 21 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `timeout_absolute` | 19 | infrastructure/runtime | No, unless repeated after healthy runtime | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `runtime_error` | 12 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `server_error` | 9 | infrastructure/runtime | No, unless repeated after healthy runtime | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `unsafe_code_detected` | 2 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |
| `policy_rejected` | 1 | model/scorer/runtime | Depends on preserved response | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |

## Named historical incidents

| Symptom | Probable layer | Model-related? | Old evidence/workaround | Executor handling |
| --- | --- | --- | --- | --- |
| `WinError 10061` / connection refused cascade | Ollama service/infrastructure | No | V2 `stage3-recovery-2` log; repeated retries produced network errors | Open circuit, stop dispatch, healthcheck, bounded recovery, checkpoint |
| HTTP 410 for cloud entries | Cloud service/account routing | No capability conclusion | Incremental run classified entries unavailable | Preserve response/status; do not score zero; continue |
| Absolute timeout / truncation | Runtime/profile or model completion | Mixed | Historical status and wall-time fields | Preserve partial raw and termination reason; architect decides scoring |
| Repetition degeneration in OCR | Model output behavior | Yes, after healthy execution | Offline V2 regrade separated semantic overlap and completion | Record semantic text, repetition flag and completion independently |
| Legacy in-process `exec(model_output)` | Scorer safety defect | No | V1 scorer source | Never use; run validated code in isolated child process |
| Corrupt/partial state or duplicate key | Persistence/resume | No | No material historical corruption proven; risk identified from design | Quarantine state, rebuild from events, key by version+digest+profile+task |

## Timing Evidence

| Track | N | P50 s | P90 s | P95 s | Max s |
| --- | ---: | ---: | ---: | ---: | ---: |
| code | 167 | 6.926 | 149.046 | 172.178 | 7222.91 |
| core | 841 | 4.937 | 59.387 | 86.626 | 237.835 |
| core_text | 245 | 11.911 | 68.709 | 87.039 | 118.521 |
| embedding | 6 | 0.471 | 4.495 | 5.404 | 6.313 |
| ocr | 14 | 18.69 | 29.724 | 30.678 | 32.434 |
| reasoning | 131 | 48.236 | 900.023 | 900.067 | 900.13 |
| safety | 32 | 4.372 | 22.526 | 30.018 | 35.179 |
| tool | 3 | 4.09 | 34.694 | 38.519 | 42.345 |
| translation | 139 | 4.314 | 24.803 | 79.838 | 23374.043 |
| vision | 26 | 10.557 | 53.952 | 66.588 | 66.825 |
