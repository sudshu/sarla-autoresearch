# SARLA autoresearch

An autonomous research loop that tries to make CARDAMOM's Bayesian calibration
of the DALEC land model fast (minutes on a GPU instead of ~33 h) without making
it wrong. Live page: https://sudshu.github.io/sarla-autoresearch/

- `autoresearch.md` — program and the frozen evaluation protocol
- `autoresearch.ideas.md` — hypothesis bank with status
- `autoresearch.jsonl` — machine-readable run log (one line per experiment)
- `LOG.md` — plain-language log, one entry per iteration
- `experiments/NNN/` — per-iteration scores (JSON), figures, advisor notes
- `variants/` — sampler configurations tested
- `code/` — snapshot of the sampler code at each iteration
- `tools/` — dispatcher, workers, scoring, page builder
- `docs/` — the generated page

Sampler and model code: fork `sudshu/CARDAMOM`, branch `jax-port`
(`PYTHON/dalec_jax`). Data: FLUXNET2015 via CARDAMOM-FluxVal v1.0
(CC-BY-4.0); this repository holds aggregate metrics only.
