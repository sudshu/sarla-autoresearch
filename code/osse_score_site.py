"""Score fast-path fits against a site OSSE truth (autoresearch protocol).

usage: osse_score_site.py --site-dir runs/osse_sites/183 --fit NAME=fit.npz
                          [--fit ...] --out score.json [--ndraw 500]
                          [--chain-gap 100] [--fig-dir DIR]

Per fit: parameter recovery (cover90/50, rms_z, PIT KS), joint calibration
(density rank r = P(lp(draw) < lp(truth)), gate-free target), typical-set
gap (best - median lp, Gaussian expectation D/2), stuck-chain fraction
(chain median lp < best chain median - gap; draws are chain-interleaved), hard-gate
-inf fraction (knife-edge artifact), trajectory skill on assimilated steps
and on the unobserved projection window, and the protocol's calibration gap
G with its terms. All draws are scored as the sampler delivered them (no
chain screening) -- coping with stuck chains is the sampler's job.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarla_forward import make_forward, make_lp, STREAMS, D  # noqa: E402
from sarla_metrics import param_scores, traj_scores, calibration_gap  # noqa: E402

OBS_STREAMS = ("GPP", "NBE", "ET", "LAI")


def load_fit(path):
    d = np.load(path)
    Z = d["draws"].astype(float)
    meta = dict(n_total=int(len(Z)), acc=float(d["acc"]), best=float(d["best"]),
                n_steps=int(d["n_steps"]), n_chains=int(d["n_chains"]),
                regions=np.bincount(d["lab"]).tolist())
    for k in ("wall", "variant"):
        if k in d.files:
            meta[k] = json.loads(str(d[k]))
    # parallel tempering records only the cold rung: chain interleaving is per rung
    v = meta.get("variant") or {}
    if v.get("kernel") == "pt_de" and v.get("pt_rungs"):
        meta["n_chains"] = int(d["n_chains"]) // int(v["pt_rungs"])
    for k in ("n_eval", "acc_pop", "n_restart", "n_charts", "n_degraded", "chart_ranks"):
        if k in d.files:
            meta[k] = np.asarray(d[k]).tolist()
    if "atlas_history" in d.files and str(d["atlas_history"]):
        h = json.loads(str(d["atlas_history"]))
        meta["atlas_history"] = h
        tot = {}
        for row in h:
            for kk, vv in (row.get("ops") or {}).items():
                tot[kk] = tot.get(kk, 0) + vv
        meta["atlas_summary"] = dict(rounds=len(h), K_final=h[-1]["K_after"], ess_final=h[-1]["ess"],
                                     uncovered_final=h[-1]["n_uncovered"], ops_total=tot,
                                     n_eval_atlas=h[-1]["n_eval"], ranks_final=h[-1]["ranks"])
    return Z, meta


def score_one(Z, meta, truth, LP, LPH, fwd, ndraw, chain_gap, rng):
    zt = truth["z_true"]
    cut = int(truth["cut"])
    T = len(truth["truth_GPP"])
    proj = np.arange(cut, T)
    out = dict(meta=meta)
    out["param"] = {k: v for k, v in param_scores(Z, zt).items()
                    if k not in ("zscore", "pit")}
    zs = param_scores(Z, zt)["zscore"]
    out["param"]["worst"] = [(int(i), float(zs[i])) for i in np.argsort(-np.abs(zs))[:8]]

    lp_all = LP(Z)
    lp_true = float(LP(zt[None])[0])
    fin = np.isfinite(lp_all)
    out["lp_true"] = lp_true
    out["lp_best"] = float(np.nanmax(lp_all[fin])) if fin.any() else np.nan
    out["lp_median"] = float(np.nanmedian(lp_all[fin])) if fin.any() else np.nan
    out["typical_gap"] = out["lp_best"] - out["lp_median"]
    out["rank"] = float(np.mean(lp_all[fin] < lp_true)) if fin.any() else np.nan
    out["nonfinite_frac"] = float(np.mean(~fin))
    nc = meta["n_chains"]
    chain = np.arange(len(Z)) % nc
    med = np.array([np.nanmedian(lp_all[chain == c]) for c in range(nc)])
    # stuck: relative to the best CHAIN (median), not the single best draw
    stuck = med < np.nanmax(med) - chain_gap
    out["stuck_frac"] = float(stuck.mean())
    out["n_stuck"] = int(stuck.sum())

    sel = rng.choice(len(Z), min(ndraw, len(Z)), replace=False)
    Zs = Z[sel]
    out["hard_infeasible"] = float(np.mean(~np.isfinite(LPH(Zs))))
    pred = fwd["predict"](Zs)
    fw = pred.pop("f_wood")
    fw = np.where((fw >= 0) & (fw <= 1.5), fw, np.nan)   # degenerate NPP -> nan
    tw = fwd["predict"](zt[None]).pop("f_wood")[0]
    out["mode"] = dict(truth_f_wood=float(tw), high_frac=float(np.nanmean(fw > 0.5)),
                       n_degenerate=int(np.isnan(fw).sum()),
                       f_wood_median=float(np.nanmedian(fw)),
                       f_wood_q05=float(np.nanpercentile(fw, 5)),
                       f_wood_q95=float(np.nanpercentile(fw, 95)))
    out["traj"] = {}
    for k in STREAMS:
        obs_idx = truth[f"keep_{k}"]
        out["traj"][k] = dict(
            assimilated=traj_scores(pred[k], truth[f"truth_{k}"], obs_idx),
            projection=traj_scores(pred[k], truth[f"truth_{k}"], proj))
    p90 = {k: out["traj"][k]["projection"]["cover90"] for k in OBS_STREAMS}
    G, terms = calibration_gap(out["param"]["cover90"], out["param"]["cover50"],
                               out["rank"], out["param"]["rms_z"], p90,
                               out["stuck_frac"])
    out["G"] = G
    out["G_terms"] = terms
    out["pred_bands"] = {k: dict(lo=np.percentile(pred[k], 5, 0).tolist(),
                                 med=np.median(pred[k], 0).tolist(),
                                 hi=np.percentile(pred[k], 95, 0).tolist())
                         for k in OBS_STREAMS} if False else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", required=True)
    ap.add_argument("--fit", action="append", default=[], help="NAME=path.npz")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ndraw", type=int, default=500)
    ap.add_argument("--chain-gap", type=float, default=100.0)
    ap.add_argument("--fig-dir", default=None)
    a = ap.parse_args()
    rng = np.random.default_rng(7)
    cbf = os.path.join(a.site_dir, "osse.cbf.nc")
    truth = dict(np.load(os.path.join(a.site_dir, "truth.npz")))
    t0 = time.time()
    fwd = make_forward(cbf)
    LP, LPH = make_lp(cbf, "none"), make_lp(cbf, "hard")
    res = dict(site_dir=a.site_dir, site=int(truth["site"]), tag=str(truth["tag"]),
               cut=int(truth["cut"]), fits={})
    for spec in a.fit:
        name, path = spec.split("=", 1)
        if not os.path.exists(path):
            res["fits"][name] = dict(error="missing")
            continue
        Z, meta = load_fit(path)
        r = score_one(Z, meta, truth, LP, LPH, fwd, a.ndraw, a.chain_gap, rng)
        r["path"] = path
        res["fits"][name] = r
        p = r["param"]
        print(f"{name:24s} G {r['G']:.3f}  c90 {p['cover90']:.2f} c50 {p['cover50']:.2f} "
              f"rank {r['rank']:.2f} rms_z {p['rms_z']:.2f} |z|>2 {p['n_gt2']:2d} "
              f"stuck {r['n_stuck']}/{meta['n_chains']} typ-gap {r['typical_gap']:.1f} "
              f"(D/2={D/2}) proj c90 "
              + " ".join(f"{k}:{r['traj'][k]['projection']['cover90']:.2f}" for k in OBS_STREAMS)
              + f"  hard-inf {r['hard_infeasible']:.2f}  f_wood truth {r['mode']['truth_f_wood']:.2f} "
              f"post [{r['mode']['f_wood_q05']:.2f},{r['mode']['f_wood_q95']:.2f}] high-mode {r['mode']['high_frac']:.2f}",
              flush=True)
        if a.fig_dir:
            plot_fit(a.fig_dir, name, truth, fwd, Z, rng, r)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    print(f"wrote {a.out} ({time.time()-t0:.0f}s)")


def plot_fit(fig_dir, name, truth, fwd, Z, rng, r):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(fig_dir, exist_ok=True)
    Zs = Z[rng.choice(len(Z), min(300, len(Z)), replace=False)]
    pred = fwd["predict"](Zs)
    T = len(truth["truth_GPP"]); t = np.arange(T); cut = int(truth["cut"])
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for ax, k in zip(axes, OBS_STREAMS):
        P = pred[k]; P = P[np.all(np.isfinite(P), 1)]
        lo, hi = np.percentile(P, [5, 95], 0)
        ax.fill_between(t, lo, hi, color="#d62728", alpha=0.2, lw=0, label="posterior 90% band")
        ax.plot(t, np.median(P, 0), color="#d62728", lw=1, label="posterior median")
        ax.plot(t, truth[f"truth_{k}"], "k-", lw=1.3, label="truth")
        oi = truth[f"keep_{k}"]
        ax.plot(oi, truth[f"pseudo_{k}"][oi], ".", color="0.4", ms=3, label="pseudo-obs")
        ax.axvline(cut - 0.5, color="0.6", ls="--", lw=0.8)
        c = r["traj"][k]["projection"]["cover90"]
        ax.set_title(f"{k}: projection cover90 {c:.2f} (target 0.90)", fontsize=9, loc="left")
        if k == "GPP":
            ax.legend(fontsize=7, ncol=4)
    axes[-1].set_xlabel("month (dashed: start of the unobserved projection window)")
    fig.suptitle(f"site {int(truth['site'])}{str(truth['tag'])}  {name}   G = {r['G']:.2f}", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, f"traj_{int(truth['site'])}{str(truth['tag'])}_{name}.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
