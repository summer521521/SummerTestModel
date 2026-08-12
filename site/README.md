# SummerTestModel report site

This directory contains the bilingual interactive site for the current **SummerTestModel Benchmark 1.0-rc1** snapshot.

- Production: <https://summertestmodel-benchmark.walker-ethan.chatgpt.site>
- Source data: `data/rc1_model_assessments.json`
- Public only: no private tasks, raw model responses, or run state are included.
- Languages: Simplified Chinese and English share the same structured dataset.

## Local validation

Requires Node.js `>=22.13.0`.

```bash
npm ci
npm run lint
npm test
```

`npm test` builds the vinext/Cloudflare worker output and verifies the server-rendered RC1 shell. The website is a static report and does not use a database, external model API, or runtime secret.

## Data update rule

Regenerate `public_results/rc1_model_assessments.json` from the repository root, copy the validated output to `site/data/`, then rebuild and deploy a new Sites version. Never copy `private_benchmark/` or `private_runs/` into this directory.
