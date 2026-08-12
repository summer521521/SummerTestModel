# Ollama runtime policy and prior local changes

## Current policy

SummerTestModel is a practical-local benchmark. The current Ollama client/server version is recorded for every published run, but patch-version drift alone is not a fail-closed condition. A run stops when Ollama is unreachable, a required API/capability is unavailable, model digests or frozen manifests do not match, private payload integrity fails, or raw/checkpoint persistence is unsafe.

Windows maintenance flags, background-load variation, and Ollama version differences are publication metadata and limitations. They are not automatically capability failures or reasons to discard an otherwise complete run.

The post-run snapshot on 2026-08-12 records Ollama client/server `0.32.6`, 44 inventory entries, HTTP API available, and zero loaded models. See `environment/runtime_snapshot_20260812.json`.

## What was changed before the baseline

Before the completed RC1 baseline, a previous fail-closed night task treated the expected Ollama patch as a hard gate. To restore that expected environment, the local installation was changed from `0.32.7` to the official `0.32.6` Windows build after these safeguards. The external recovery package is retained under `F:\Codex_File\summer_test_model_ollama_restore_20260811` (local-only; never published):

- The existing Ollama installation, updater, application settings, startup shortcut, API tag inventory, and version evidence were copied to an external backup directory outside this repository.
- The downloaded official installer SHA-256 was `526e47db7c295d017e9514df5bb20c6f32b3d1170f2c8bb9c59b53185f5bd6ff`; its Ollama, Inc. Authenticode signature was valid.
- Login autostart was disabled by moving the startup shortcut into the external backup.
- Ollama automatic update was disabled in the local application settings after backing up the database.
- The cached updater was moved to the external backup rather than permanently deleted.
- The application was subsequently run hidden with its normal local `serve` child.

No Ollama model was downloaded, deleted, re-quantized, renamed, or given a different digest by that operation. The before/after evidence recorded an exact 44/44 name-and-digest match; the model store was preserved.

## What is not being changed now

This repository update changes the benchmark policy and documentation only: future runs record the current patch version instead of requiring `0.32.6`. It does not restore autostart, re-enable automatic updates, install another Ollama version, or alter any system setting. Those are machine-level choices and require a separate explicit user instruction with backup and rollback steps.
