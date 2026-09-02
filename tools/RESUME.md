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
