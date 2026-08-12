# Private Benchmark Policy

SummerTestModel Benchmark 1.0 uses a locally frozen evaluation set. Exact
prompts, ground truths, hidden code tests, tool fixtures, vision/OCR assets,
long-context payloads, embedding corpus/query answers, safety labels and
medical ground truth are private benchmark material.

The public repository may contain task IDs, categories, scorer IDs,
methodology, prompt/ground-truth/asset hashes, aggregate counts, frozen
manifest hashes and generic scorer implementations. It must not contain the
evaluation payload or embedded expected answers.

The local package is `private_benchmark/1.0-rc1/` and is ignored by Git. Its
`private_package_manifest.json` contains only relative identifiers and hashes.
The payload may be published only after the benchmark is retired and the user
explicitly authorizes publication.

Any public-leakage scan failure is a release blocker. A scorer must read
expected values from the local private package and must never call Ollama,
OpenAI, another LLM or the Internet.
