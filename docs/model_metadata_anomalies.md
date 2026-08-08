# Model Metadata Anomalies

This audit does not ask models to identify themselves. Findings come only from Modelfile/template/system metadata. `IDENTITY_CLAIM_PRESENT` is an inspection flag, not proof of contamination.

| Model | Flags | Interpretation |
| --- | --- | --- |
| `rnj-1:latest` | IDENTITY_CLAIM_PRESENT | Inspect metadata provenance; no model self-report was used. |
| `ministral-3:8b` | IDENTITY_CLAIM_PRESENT | Inspect metadata provenance; no model self-report was used. |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | IDENTITY_CLAIM_PRESENT | Inspect metadata provenance; no model self-report was used. |
| `phi4-mini-reasoning:latest` | SYSTEM_PRESENT;IDENTITY_CLAIM_PRESENT | Inspect metadata provenance; no model self-report was used. |
| `smollm2:1.7b` | SYSTEM_PRESENT;IDENTITY_CLAIM_PRESENT | Inspect metadata provenance; no model self-report was used. |
| `ornith:9b` | SYSTEM_PRESENT | Inspect metadata provenance; no model self-report was used. |
