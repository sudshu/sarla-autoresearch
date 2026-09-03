"""Two-cell bridge estimate of the relative mass of the wood-allocation modes.

Cells: high (f_wood > cut) and low (f_wood <= cut). For each cell a Gaussian
kernel-density mixture on the cell's own draws is the bridge proposal (a
moment-matched Gaussian is entirely EDC-infeasible at 89-D); the restricted
target is pi(z) * 1[cell]. Bridge sampling (Meng & Wong; sarla_evidence
._bridge_logr) gives log Z_cell; the implied high-mode weight
Z_high / (Z_high + Z_low) is compared with the pooled draw fraction.
Independent of how many walkers sat in each mode, so it reweights a DE
sample whose mode occupancy is seed-dependent (idea B1, 2026-09-02).

usage: mode_bridge.py --cbf X.cbf.nc --fit NAME=fit.npz [...] --out JSON
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarla_forward import make_forward, make_lp
from sarla_evidence import _bridge_logr


def kde_fit(Z, h=0.2):
    """Gaussian KDE in z-space: centres = the cell's draws, isotropic-per-dim
    bandwidth h * sd (whitened). A moment-matched Gaussian is useless here:
    at 89-D every one of its draws is EDC-infeasible."""
    sd = Z.std(0) + 1e-9
    return dict(C=Z, bw=h * sd)


def kde_logpdf(Q, k):
    C, bw = k["C"], k["bw"]
    d = Q.shape[1]
    out = np.empty(len(Q))
    for i in range(0, len(Q), 256):
        y = (Q[i:i + 256, None, :] - C[None, :, :]) / bw
        lg = -0.5 * np.sum(y * y, -1) - np.sum(np.log(bw)) - 0.5 * d * np.log(2 * np.pi)
        m = lg.max(1, keepdims=True)
        out[i:i + 256] = (m[:, 0] + np.log(np.exp(lg - m).sum(1))) - np.log(len(C))
    return out


def kde_draw(k, n, rng):
    C, bw = k["C"], k["bw"]
    idx = rng.integers(0, len(C), n)
    return C[idx] + rng.standard_normal((n, C.shape[1])) * bw


def bridge_weights(Z, fw, LP, fwd, cut, n_q, rng, bw_h=0.2):
    out = {}
    for name, mask in (("high", fw > cut), ("low", fw <= cut)):
        n = int(mask.sum())
        if n < 50:
            out[name] = dict(n=n, logZ=-np.inf); continue
        Zc = Z[mask]
        # leave-one-out KDE for the cell's own draws (otherwise l1 is biased by self-density)
        half = len(Zc) // 2
        kA, kB = kde_fit(Zc[:half], bw_h), kde_fit(Zc[half:], bw_h)
        lp1 = LP(Zc)
        lq1 = np.concatenate([kde_logpdf(Zc[:half], kB), kde_logpdf(Zc[half:], kA)])
        l1 = lp1 - lq1
        k_all = kde_fit(Zc, bw_h)
        Q = kde_draw(k_all, n_q, rng)
        fq = fwd["predict"](Q)["f_wood"]; fq = np.where((fq >= 0) & (fq <= 1.5), fq, np.nan)
        in_cell = (fq > cut) if name == "high" else (fq <= cut)
        lp2 = LP(Q); lp2 = np.where(in_cell & np.isfinite(lp2), lp2, -np.inf)
        l2 = lp2 - kde_logpdf(Q, k_all)
        fin1 = np.isfinite(l1)
        logZ = _bridge_logr(l1[fin1], l2)
        out[name] = dict(n=n, logZ=float(logZ), q_in_cell=float(np.mean(in_cell)),
                         q_feasible=float(np.mean(np.isfinite(lp2))))
    zh, zl = out["high"]["logZ"], out["low"]["logZ"]
    w = 1.0 / (1.0 + np.exp(zl - zh)) if np.isfinite(zh) and np.isfinite(zl) else (1.0 if np.isfinite(zh) else 0.0)
    return w, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cbf", required=True)
    ap.add_argument("--fit", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--cut", type=float, default=0.5)
    ap.add_argument("--ndraw", type=int, default=4000)
    ap.add_argument("--nq", type=int, default=2000)
    ap.add_argument("--bw", type=float, default=0.2, help="KDE bandwidth as a fraction of the cell's per-dimension sd")
    a = ap.parse_args()
    fwd = make_forward(a.cbf); LP = make_lp(a.cbf, "hard")
    rng = np.random.default_rng(5)
    res = dict(cbf=a.cbf, cut=a.cut, fits={})
    for spec in a.fit:
        name, path = spec.split("=", 1)
        d = np.load(path); Z = d["draws"].astype(float)
        sel = rng.choice(len(Z), min(a.ndraw, len(Z)), replace=False); Z = Z[sel]
        fw = fwd["predict"](Z)["f_wood"]; fw = np.where((fw >= 0) & (fw <= 1.5), fw, np.nan)
        ok = np.isfinite(fw); Z, fw = Z[ok], fw[ok]
        pooled = float(np.mean(fw > a.cut))
        w, cells = bridge_weights(Z, fw, LP, fwd, a.cut, a.nq, rng, a.bw)
        # split-half repeat for a rough uncertainty
        h = len(Z) // 2
        w1, _ = bridge_weights(Z[:h], fw[:h], LP, fwd, a.cut, a.nq // 2, rng, a.bw)
        w2, _ = bridge_weights(Z[h:], fw[h:], LP, fwd, a.cut, a.nq // 2, rng, a.bw)
        r = dict(pooled_high_frac=pooled, bridge_high_weight=float(w), halves=[float(w1), float(w2)], cells=cells)
        res["fits"][name] = r
        print(f"{name:28s} pooled high {pooled:.3f} -> bridge {w:.3f} (halves {w1:.3f}, {w2:.3f}); "
              f"cells high n={cells['high']['n']} logZ {cells['high']['logZ']:.1f} q-in-cell {cells['high'].get('q_in_cell', 0):.2f}; "
              f"low n={cells['low']['n']} logZ {cells['low']['logZ']:.1f} q-in-cell {cells['low'].get('q_in_cell', 0):.2f}", flush=True)
    json.dump(res, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
