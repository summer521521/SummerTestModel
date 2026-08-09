# Model reference policy

This scaffold separates public model-reference claims from SummerTestModel measurements. It contains no benchmark prompt, ground truth, raw response, private path, or fabricated model metadata.

Reference entries must label each claim as one of:

- `official_model_card`: official model card or repository.
- `official_technical_paper`: official technical paper.
- `official_release_notes`: official release or platform notes.
- `ollama_official`: Ollama's official model page or API documentation.
- `packager_or_quantizer`: the packager or quantizer's own artifact metadata.
- `summer_testmodel_measurement`: a measurement produced by the frozen benchmark runner.

Source priority is the official model card/repository, official technical paper or release notes, the Ollama official page, and then packager/quantizer metadata. Third-party commentary is not an official source and must not be presented as one.

Official claims and local measurements are separate fields. A missing fact remains `null` or `unconfirmed`; it is not inferred from parameter count, tag name, or benchmark score. Runtime defaults are referenced by digest and modelfile hash from `inventory/model_runtime_defaults.rc1.json`.
