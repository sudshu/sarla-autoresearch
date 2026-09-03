# Resuming the loop (any session)

All state is on disk. Python: `env -u LD_LIBRARY_PATH ~/rough/cardamom_research/.venv/bin/python`.
Run everything from `~/rough/cardamom_research` with absolute paths.

1. `tools/dispatch.py poll --pull` — host status, retrieves finished jobs into
   `runs/autoresearch/jobs/<id>/`. `tools/dispatch.py workers` restarts dead
   workers. `tools/dispatch.py sync` pushes code/sites/variants.
2. Read `LOG.md` (last entry) and `experiments/NNN/aggregate.json` for the
   current default and best G. `autoresearch.jsonl` is the ground truth.
3. One iteration:
   - `tools/loop.py jobs --iter N --variant NAME [--sites ...] [--seeds 5]` then
     `tools/dispatch.py submit <job files>`; `tools/dispatch.py wait <ids>`.
   - `tools/loop.py score --iter N` (CPU) -> `experiments/NNN/scores/*.json`
   - `tools/loop.py aggregate --iter N` -> `aggregate.json`, apply the accept
     rule from `autoresearch.md`.
   - `tools/loop.py record --iter N --variant NAME --status keep|discard|dev-only|crash
      --description "..." --hypothesis Hk --category cat --commit <research sha>`
   - `tools/advisor.py --iter N` (Codex, reasoning high) -> `advisor.md`; read it,
     update `autoresearch.ideas.md`, write the LOG entry.
   - copy `scripts/{sarla_fit,sarla_kernels,sarla_forward,sarla.py,osse_fit}.py`
     to `code/`; `tools/build_site.py`; commit research repo; commit + push here.
   - breakthrough (dev G improves >= 0.20 / speed path / holdout confirmation):
     `tools/notify.py "subject" "body"`.
4. Stop: `touch autoresearch/STOP` (dispatcher loop and workers exit after the
   current job). Never run two jobs on one slot; never touch runs/ademcmc_*.

## Disk quota (100 GB hard limit on /home/spandey)
Run `tools/loop.py prune --iter N` after an iteration is scored (deletes the
~28 MB fit.npz per job; scores live in experiments/). Never keep raw ADEMCMC
.cbr files around: thin them (last 30%, every 10th row) into
runs/ademcmc_truth/site_N/thinned_last30.npz and delete the .cbr. The 33-h
NL-Loo OSSE arm (runs/ademcmc_osse_full) grows to ~9 GB and must never be
starved.

## Storage (2026-09-02)
Bulky outputs live on the local data volume /export/data1/spandey/cardamom/
(no user quota): autoresearch_jobs/ (symlinked from runs/autoresearch/jobs),
ademcmc_truth/ and ademcmc_truth60k/ (thinned truth chains, symlinked from
runs/). The sibling session's reference arm restarts under
/export/data1/spandey/cardamom/ademcmc_osse_full. Never write large files
under /home/spandey (100 GB hard quota shared with everything else).

## GPUs (user rule, 2026-09-03)
Never use the local A100s unless the user explicitly asks. Local scoring and
tooling run with JAX_PLATFORMS=cpu. GPU fits only on the H100 (az-ms) and the
two Blackwell cards on aws_kyo, as in tools/hosts.json.
