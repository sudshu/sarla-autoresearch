"""Mode-weight check on REAL NL-Loo data: fraction of posterior draws with
wood-allocation fraction f_wood > 0.5, against the converged 64-chain ADEMCMC
reference (0.815, 90% CI 0.794-0.834; sibling session's alloc_occupancy.npz).

usage: realdata_mode_check.py --fit NAME=fit.npz [...] --out JSON
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarla_forward import make_forward, make_lp

REF = dict(high_frac=0.815, lo=0.794, hi=0.834, floor=0.03)
CBF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs", "fluxval_pilot", "cbf", "fluxval_183_1100.cbf.nc")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ndraw", type=int, default=2000)
    a = ap.parse_args()
    fwd = make_forward(CBF); LP = make_lp(CBF, "none")
    rng = np.random.default_rng(11)
    res = dict(reference=REF, fits={})
    for spec in a.fit:
        name, path = spec.split("=", 1)
        d = np.load(path); Z = d["draws"].astype(float); nc = int(d["n_chains"])
        sel = rng.choice(len(Z), min(a.ndraw, len(Z)), replace=False)
        fw = fwd["predict"](Z[sel])["f_wood"]; fw = np.where((fw >= 0) & (fw <= 1.5), fw, np.nan)
        lp = LP(Z[sel])
        # per-chain high fraction (chain = row index % n_chains) for a between-chain spread
        chain = sel % nc
        per_chain = [np.nanmean(fw[chain == c] > 0.5) for c in range(nc) if np.sum(chain == c) >= 5]
        r = dict(high_frac=float(np.nanmean(fw > 0.5)), n=int(len(sel)), n_chains=nc,
                 per_chain_sd=float(np.nanstd(per_chain)) if per_chain else None,
                 lp_best=float(np.nanmax(lp)), lp_median=float(np.nanmedian(lp)),
                 f_wood_q05=float(np.nanpercentile(fw, 5)), f_wood_q95=float(np.nanpercentile(fw, 95)),
                 inside_ref_ci=bool(REF["lo"] <= np.nanmean(fw > 0.5) <= REF["hi"]))
        res["fits"][name] = r
        print(f"{name:28s} high-mode fraction {r['high_frac']:.3f} (ref 0.815 [0.794,0.834]) per-chain sd {r['per_chain_sd']}  lp best {r['lp_best']:.1f} median {r['lp_median']:.1f}")
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
