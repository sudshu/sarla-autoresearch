"""Configurable SARLA fast path: atlas + region screen + population kernel.

The autoresearch loop's unit of experiment. Every tunable lives in `Variant`
(JSON on disk, `variants/<name>.json`); the defaults reproduce the v3 fast
path of 2026-09-01 (scripts/osse_fit.py with OSSE_WITHIN=none) exactly.

usage: sarla_fit.py --cbf X.cbf.nc --out fit.npz --seeds seeds.npz
                    [--variant v.json] [--set key=value ...] [--kernel-seed k]
Seeds file: key `z_seeds` (z-space, feasible points of THIS site) or
`centers_w` (whitened atlas centres, multiplied by scale).
"""
import argparse
import dataclasses
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_here = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(_here, "..", "CARDAMOM", "PYTHON", "dalec_jax", "src"),
             os.path.join(_here, "dalec_jax_src")):
    if os.path.isdir(cand):
        sys.path.insert(0, cand)

import jax

import sarla as S
import sarla2 as S2
from osse_fit import (make_target, density_clusters, balanced_init,
                      live_regions, D, SCALE)
from sarla_kernels import run_kernel, warmup_ensemble
from sarla_tempered import make_tempered_batch, run_pt


@dataclasses.dataclass
class Variant:
    name: str = "v3_baseline"
    category: str = "baseline"
    notes: str = ""
    # seeds + atlas
    n_seeds: int = 128
    lbfgs_maxiter: int = 300
    seed_seed: int = 0
    atlas_rounds: int = 6
    n_audit: int = 4096
    atlas_seed: int = 3
    warmup_steps: int = 0           # chart-free ensemble steps over the seeds before the atlas
    warmup_kind: str = "stretch"    # stretch | de
    # atlas engine: "v1" (sarla.py, the v3 baseline) or "surgery" (sarla2.py:
    # topology-aware rank-adaptive atlas with real extend/refine/split/branch/
    # rank-change/merge operations). sg_* knobs apply to "surgery" only.
    atlas_engine: str = "v1"
    sg_rank_tau: float = 1.0
    sg_gap_min: float = 10.0
    sg_gap_cap: float = 100.0
    sg_var_cap: float = 1.0
    sg_flag_topk: int = 8
    sg_flag_thresh: float = 5.0
    sg_eta: float = 0.05
    sg_weight_rule: str = "uniform"
    sg_normal_projection: bool = True
    sg_extend_sigma: float = 2.0
    sg_model_tol: float = 2.0
    sg_merge_tol: float = 1.0
    sg_overlap_tol: float = 2.0
    sg_branch_tau: float = 10.0
    sg_split_offset: float = 0.5
    sg_refine_shrink: float = 1.0
    sg_rank_hysteresis: float = 2.0
    sg_rank_min_diff: float = 0.0
    sg_bend_tol: float = 1.0
    sg_fallback_patch: bool = True
    sg_branch_on_infeasible: bool = True
    sg_connectivity_rule: str = "segment"
    sg_path_tries: int = 8
    sg_path_jitter: float = 0.05
    sg_do_extend: bool = True
    sg_do_refine: bool = True
    sg_do_split: bool = True
    sg_do_rank: bool = True
    sg_do_branch: bool = True
    sg_do_merge: bool = True
    sg_clean_stop: int = 2
    sg_stop_ess: float = None
    # regions and starts
    tau: float = 10.0
    n_mid: int = 7
    region_gap: float = 100.0
    within: float = None            # None = any chart in the region (v3)
    start_policy: str = "balanced"  # balanced | proportional
    init_seed: int = 99
    # kernel
    kernel: str = "chart_rwm"       # chart_rwm | chart_de | chart_stretch | chart_adaptcov | chart_indep | pt_de
    pt_rungs: int = 4               # parallel tempering (kernel=pt_de): rungs, geometric betas 1 -> pt_beta_min
    pt_beta_min: float = 0.05
    pt_swap_every: int = 10
    pt_temper_edc: bool = False     # True: temper EDC penalties too (hard gate kept), not only the data term
    mix: float = 0.0
    n_chains: int = 64
    n_steps: int = 32000
    burn_frac: float = 0.5
    gamma0: float = 0.05
    target_acc: float = 0.23
    flat_mult: float = 1.0
    de_gamma: float = None
    stretch_a: float = 2.0
    adapt_start: float = 0.25
    adapt_every: int = 200
    restart_gap: float = 100.0
    restart_every: int = 500
    restart_until: float = 0.5
    max_draws: int = 40000
    kernel_seed: int = 5

    @classmethod
    def load(cls, path=None, overrides=()):
        d = {}
        if path:
            with open(path) as f:
                d = json.load(f)
        for kv in overrides:
            k, v = kv.split("=", 1)
            d[k] = _coerce(v, cls.__dataclass_fields__[k].type)
        return cls(**d)

    def dump(self, path):
        with open(path, "w") as f:
            json.dump(dataclasses.asdict(self), f, indent=1)


def _coerce(v, typ):
    if v.lower() in ("none", "null"):
        return None
    if typ is bool:
        return v.lower() in ("1", "true", "yes")
    if typ is int:
        return int(v)
    if typ is float:
        return float(v)
    return v


def counted(batch):
    n = [0]

    def f(Z, *a, **k):
        Z = np.atleast_2d(np.asarray(Z, float))
        n[0] += len(Z)
        return batch(Z, *a, **k)
    return f, n


def find_seeds(target, cfg, seed_file):
    rng = np.random.default_rng(cfg.seed_seed)
    z = np.load(seed_file)
    if "z_seeds" in z.files:
        z0s = np.asarray(z["z_seeds"], float)
    else:
        z0s = np.asarray(z["centers_w"], float) * SCALE
    lp = target["logpost_batch"](z0s)
    z0s = z0s[np.isfinite(lp)]
    print(f"    {len(z0s)} feasible seed points from {seed_file}", flush=True)
    if len(z0s) == 0:
        raise SystemExit("no feasible seed points")
    idx = rng.choice(len(z0s), cfg.n_seeds, replace=len(z0s) < cfg.n_seeds)
    z0s = z0s[idx] + 0.02 * rng.standard_normal((cfg.n_seeds, D))
    f = lambda z: -float(target["logpost_batch"](z[None])[0])
    out, t0 = [], time.time()
    for i, z0 in enumerate(z0s):
        r = minimize(f, z0, jac=lambda z: target["grad"](z),
                     method="L-BFGS-B", options=dict(maxiter=cfg.lbfgs_maxiter))
        out.append(r.x)
        if (i + 1) % 16 == 0:
            print(f"    seeds {i+1}/{cfg.n_seeds}  {time.time()-t0:.0f}s", flush=True)
    out = np.array(out)
    ok = np.isfinite(target["logpost_batch"](out))
    print(f"    {ok.sum()}/{len(out)} polished seeds feasible", flush=True)
    if ok.sum() < 4:
        raise SystemExit("fewer than 4 feasible seeds")
    return out[ok]


def proportional_init(lab, n_chains, rng, keep, lp0):
    regs = np.asarray(keep)
    w = np.array([np.sum(lab == r) for r in regs], float)
    w /= w.sum()
    out = []
    for i in range(n_chains):
        r = rng.choice(regs, p=w)
        out.append(rng.choice(np.flatnonzero(lab == r)))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cbf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--variant", default=None)
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--kernel-seed", type=int, default=None)
    a = ap.parse_args()
    cfg = Variant.load(a.variant, a.set)
    if a.kernel_seed is not None:
        cfg = dataclasses.replace(cfg, kernel_seed=a.kernel_seed)
    print(f"backend {jax.default_backend()}  cbf {a.cbf}\n  variant "
          f"{json.dumps(dataclasses.asdict(cfg))}", flush=True)
    wall, t_all = {}, time.time()

    target = make_target(a.cbf)
    target["logpost_batch"], n_eval = counted(target["logpost_batch"])

    t0 = time.time()
    seeds = find_seeds(target, cfg, a.seeds)
    wall["seeds"] = time.time() - t0
    ev_seeds = n_eval[0]
    print(f"  {cfg.n_seeds} seeds in {wall['seeds']:.0f}s", flush=True)

    if cfg.warmup_steps > 0:
        t0 = time.time()
        Xw, lpw = warmup_ensemble(target, seeds / SCALE, SCALE, cfg.warmup_steps,
                                  np.random.default_rng(cfg.seed_seed + 1),
                                  kind=cfg.warmup_kind,
                                  report=max(cfg.warmup_steps // 5, 100))
        print(f"  warm-up {cfg.warmup_steps} steps x {len(Xw)} walkers: best "
              f"{lpw.max():.2f} median {np.median(lpw):.2f} (seeds were best "
              f"{np.max(target['logpost_batch'](seeds)):.2f}) in {time.time()-t0:.0f}s",
              flush=True)
        wall["warmup"] = time.time() - t0
        seeds = Xw * SCALE
    t0 = time.time()
    atlas_history = None
    if cfg.atlas_engine == "surgery":
        sg = S2.SurgeryConfig(rounds=cfg.atlas_rounds, n_audit=cfg.n_audit,
                              **{k[3:]: v for k, v in dataclasses.asdict(cfg).items()
                                 if k.startswith("sg_")})
        atlas = S2.sarla2(target, seeds, sg, seed=cfg.atlas_seed)
        atlas_history = atlas.history
        print(S2.history_table(atlas), flush=True)
        flat_cap = sg.var_cap
    else:
        atlas = S.sarla(target, seeds, rounds=cfg.atlas_rounds, n_audit=cfg.n_audit,
                        seed=cfg.atlas_seed)
        flat_cap = S.VAR_CAP
    degraded = sum(1 for c in atlas.charts if np.all(c.eigvals == 0))
    wall["atlas"] = time.time() - t0
    ev_atlas = n_eval[0] - ev_seeds
    print(f"  atlas {len(atlas.charts)} charts in {wall['atlas']:.0f}s "
          f"({degraded} degraded)", flush=True)
    if degraded == len(atlas.charts):
        raise SystemExit("every chart degraded")

    lab, lp0 = density_clusters(atlas, target, tau=cfg.tau, n_mid=cfg.n_mid,
                                return_lp=True)
    keep_regs, best = live_regions(lab, lp0, gap=cfg.region_gap)
    print(f"  {lab.max()+1} regions, sizes {np.bincount(lab)}; region best "
          f"{np.round(best, 1)}; keeping {len(keep_regs)}", flush=True)
    rng_i = np.random.default_rng(cfg.init_seed)
    if cfg.start_policy == "balanced":
        ks = balanced_init(lab, cfg.n_chains, rng_i, keep=keep_regs,
                           lp0=lp0 if cfg.within is not None else None,
                           within=cfg.within if cfg.within is not None else 45.0)
    elif cfg.start_policy == "proportional":
        ks = proportional_init(lab, cfg.n_chains, rng_i, keep_regs, lp0)
    elif cfg.start_policy == "seeds":
        # H9: start from the polished L-BFGS seeds that fall in a kept region
        # (all of them, with replacement), not from chart centres
        W = seeds / SCALE
        near = np.argmin(np.stack([c.maha2(W) for c in atlas.charts], 1), 1)
        okmask = np.isin(lab[near], keep_regs)
        pool = W[okmask] if okmask.any() else W
        pick = rng_i.choice(len(pool), cfg.n_chains, replace=len(pool) < cfg.n_chains)
        init_X = pool[pick]
        ks = near[okmask][pick] if okmask.any() else near[pick]
        print(f"  seed starts: {len(pool)} seeds in kept regions, "
              f"{len(np.unique(pick))} distinct used", flush=True)
    else:
        raise ValueError(cfg.start_policy)
    init_X = init_X if cfg.start_policy == "seeds" else None
    print(f"  init charts: {len(np.unique(ks))} distinct, centre logpost "
          f"{lp0[ks].min():.1f}..{lp0[ks].max():.1f}", flush=True)

    t0 = time.time()
    if cfg.kernel == "pt_de":
        tb = make_tempered_batch(a.cbf, temper_edc=cfg.pt_temper_edc)
        n_pt = [0]
        def tb_counted(Z):
            n_pt[0] += len(np.atleast_2d(Z)); return tb(Z)
        draws, acc, bestlp, diag = run_pt(atlas, tb_counted, cfg, cfg.n_steps, cfg.n_chains,
                                          seed=cfg.kernel_seed, init_ks=ks,
                                          report=max(cfg.n_steps // 8, 500), init_X=init_X)
        n_eval[0] += n_pt[0]
        print(f"  tempering: betas {np.round(diag['betas'], 3).tolist()} swap acceptance "
              f"{np.round(diag['swap_acc'], 2).tolist()}", flush=True)
    else:
        draws, acc, bestlp, diag = run_kernel(
            atlas, target, cfg, cfg.n_steps, cfg.n_chains, seed=cfg.kernel_seed,
            init_ks=ks, report=max(cfg.n_steps // 8, 500), flat_cap=flat_cap,
            init_X=init_X)
    wall["kernel"] = time.time() - t0
    ev_kernel = n_eval[0] - ev_seeds - ev_atlas
    wall["total"] = time.time() - t_all
    print(f"  sampled {draws.shape} acc {acc:.3f} pop-acc {diag['acc_pop']:.3f} "
          f"best {bestlp:.2f} in {wall['kernel']:.0f}s; evals seeds {ev_seeds} "
          f"atlas {ev_atlas} kernel {ev_kernel}", flush=True)

    np.savez(a.out, draws=draws, lab=lab, acc=acc, best=bestlp,
             centers=np.stack([c.center for c in atlas.charts]),
             center_lp=lp0, kept_regions=keep_regs,
             region_gap=cfg.region_gap if cfg.region_gap is not None else np.nan,
             restart_gap=cfg.restart_gap if cfg.restart_gap is not None else np.nan,
             n_steps=cfg.n_steps, n_chains=cfg.n_chains,
             variant=json.dumps(dataclasses.asdict(cfg)),
             wall=json.dumps(wall), final_lp=diag["final_lp"],
             n_eval=np.array([ev_seeds, ev_atlas, ev_kernel]),
             acc_pop=diag["acc_pop"], n_restart=diag["n_restart"],
             n_charts=len(atlas.charts), n_degraded=degraded,
             chart_ranks=np.array([c.rank for c in atlas.charts]),
             atlas_history=json.dumps(atlas_history, default=str) if atlas_history else "")
    print(f"wrote {a.out}  total {wall['total']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
