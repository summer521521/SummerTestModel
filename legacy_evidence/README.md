# Pre-RC1 local evidence archive

This directory preserves files that existed beside the canonical Git repository but were not yet represented in Git history. They are retained as historical evidence only; none of their scores are comparable with SummerTestModel Benchmark 1.0-rc1.

## Archived snapshot

`pre_rc1_local_workspace/` contains 39 byte-for-byte copies of locally unique files recovered during the 2026-08-12 repository consolidation:

- 13 files from the early `20260324` Test1 experiment, including its task, model answers, Markdown score report, and workbook;
- 25 unique files from the pre-RC1 `benchmark_20260629` workspace: historical reports, score tables, task snapshots, and one raw response revision;
- the 2026-07-18 model recommendation memo, retained for decision-history context rather than as current project guidance.

The source workspace contained another 270 files whose SHA-256 content already matched tracked files in this repository. Those duplicates were not committed a second time.

## Interpretation rules

- Treat all contents here as **Legacy Experimental Evidence**.
- Do not combine these scores with RC1 track scores or use them as current retention decisions.
- Original filenames and bytes are preserved, including historical naming quirks.
- Current results and reproducible workflows live in [`public_results/`](../public_results/), [`docs/rc1_results.md`](../docs/rc1_results.md), and [`docs/INCREMENTAL_MODELS.md`](../docs/INCREMENTAL_MODELS.md).
