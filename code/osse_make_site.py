"""Site-generic OSSE: pseudo-observations from a method-independent truth.

Generalises scripts/osse_make.py (NL-Loo, ADEMCMC-draw truth) to any of the
FluxVal sites, for the autoresearch protocol (autoresearch/autoresearch.md):

  truth   a plausible EDC-feasible point NEAR (not at) one of the real-data
          L-BFGS modes (the pilot's points re-optimised for 300 iterations) (runs/fluxval_pilot/proxy_results/
          site_<n>_results.npz, key z_modes): a random plausible mode plus
          N(0, (JITTER * prior sd)^2) noise in z, redrawn until the point is
          hard-gate feasible and plausible. Plausible = finite trajectory and
          mean GPP over the observed steps within [0.3x, 3x] of the site's
          observed mean GPP. The jitter (0.3 prior sd per dimension, ~2.8 sd
          in total) keeps the truth off the seed set the fitter starts from.
          Iid EDC-feasible PRIOR draws (z_hits) were the first choice and
          were rejected on 2026-09-01: at all five sites checked they are
          near-dead ecosystems (GPP < 5% of observed), which would make the
          pseudo-data uninformative.
  noise   the CBF's own declared error model per stream (osse_make.corrupt),
          plus ABGB regenerated from the truth with its factor-1.05
          uncertainty -- the NL-Loo OSSE had kept the REAL biomass value.
  design  all observations assimilated (times copied from the real site);
          every site is unobserved after step <=113 of 192, so steps after
          the last observation are the projection test.

usage: osse_make_site.py <site> [--tag A|B] [--truth-seed N] [--noise-seed N]
                         [--out-root runs/osse_sites]
writes  <out-root>/<site><tag>/{osse.cbf.nc, truth.npz, seeds.npz}
"""
import argparse
import os
import shutil
import sys

import numpy as np
import netCDF4

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jax  # noqa: E402  (import order: path first)
from sarla_forward import make_forward, make_lp, STREAMS, SCALE  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CBF_DIR = os.path.join(ROOT, "runs", "fluxval_pilot", "cbf")
HITS_DIR = os.path.join(ROOT, "runs", "fluxval_pilot", "proxy_results")
OBS_STREAMS = ("GPP", "NBE", "ET", "LAI")
GPP_RANGE = (0.3, 3.0)
JITTER = 0.3            # prior sd per dimension


def corrupt(truth, stream, rng, unc):
    """Noise matching the CBF's declared error model for that stream."""
    if stream == "NBE":                          # additive
        return truth + rng.normal(0.0, unc, truth.shape)
    out = truth * np.exp(rng.normal(0.0, np.log(unc), truth.shape))
    return np.maximum(out, 0.1) if stream in ("GPP", "ET") else out


def wood_budget(fwd, z):
    """Allocation and realised wood residence time of one parameter vector
    (flux indices as in the 2026-09-01 wood-budget audit: 0 gpp, 2 resp_auto,
    6 NPP->wood, 9 base wood mortality, 25 hydraulic wood mortality)."""
    from sarla_forward import z_to_p, run_dalec_1100, prederive_vegk
    import jax
    cbf = fwd["cbf"]
    VegK = prederive_vegk(cbf.met["DOY"], cbf.LAT)
    pools, fluxes = run_dalec_1100(z_to_p(np.asarray(z, float)), cbf.met,
                                   cbf.LAT, cbf.deltat, VegK)
    pools, fluxes = np.asarray(pools), np.asarray(fluxes)
    dpy = 365.25
    gpp, npp = fluxes[:, 0].mean(), (fluxes[:, 0] - fluxes[:, 2]).mean()
    woop = fluxes[:, 6].mean()
    wout = (fluxes[:, 9] + fluxes[:, 25]).mean()
    cwoo = ((pools[:-1, 3] + pools[1:, 3]) * 0.5).mean()
    with np.errstate(all="ignore"):
        return dict(GPP_yr=gpp * dpy, NPP_yr=npp * dpy, f_wood=woop / npp,
                    C_woo=cwoo, tau_wood_realised_yr=cwoo / wout / dpy,
                    drought_share=fluxes[:, 25].mean() / wout)


def polish(cbf_path, Z, maxiter):
    """L-BFGS every feasible point against the real data: the pilot's stored
    modes were under-optimised (GPP 0.15-0.5x observed at several sites)."""
    from scipy.optimize import minimize
    from osse_fit import make_target
    target = make_target(cbf_path)
    lp = target["logpost_batch"](Z)
    Z = Z[np.isfinite(lp)]
    f = lambda z: -float(target["logpost_batch"](z[None])[0])
    out = []
    for z0 in Z:
        r = minimize(f, z0, jac=lambda z: target["grad"](z), method="L-BFGS-B",
                     options=dict(maxiter=maxiter))
        out.append(r.x)
    out = np.array(out)
    lp2 = target["logpost_batch"](out)
    print(f"  polished {len(out)} points: logpost {np.round(np.sort(lp2)[::-1][:6], 1)} ...",
          flush=True)
    return out[np.isfinite(lp2)]


def stream_unc(var):
    a = {k: float(getattr(var, k)) for k in var.ncattrs()}
    if a.get("opt_unc_type", 1.0) == 0.0:
        return a.get("single_unc", 1.0)
    return a.get("single_unc", a.get("single_annual_unc", 3.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=int)
    ap.add_argument("--tag", default="")
    ap.add_argument("--truth-seed", type=int, default=None)
    ap.add_argument("--noise-seed", type=int, default=None)
    ap.add_argument("--out-root", default=os.path.join(ROOT, "runs", "osse_sites"))
    ap.add_argument("--gpp-range", default="0.3,3.0",
                    help="plausibility window for mean GPP and biomass as "
                         "multiples of the observed values")
    ap.add_argument("--polish", type=int, default=300,
                    help="L-BFGS iterations to re-optimise the pilot's points "
                         "against the REAL data before choosing a mode (0 = off)")
    a = ap.parse_args()
    global GPP_RANGE
    GPP_RANGE = tuple(float(x) for x in a.gpp_range.split(","))
    site = a.site
    tseed = a.truth_seed if a.truth_seed is not None else 20260901 + site
    nseed = a.noise_seed if a.noise_seed is not None else 30260901 + site
    if a.tag == "B":
        tseed += 1000; nseed += 1000
    out_dir = os.path.join(a.out_root, f"{site}{a.tag}")
    os.makedirs(out_dir, exist_ok=True)
    src_cbf = os.path.join(CBF_DIR, f"fluxval_{site}_1100.cbf.nc")
    print(f"site {site}{a.tag}: cbf {src_cbf}  truth seed {tseed}  noise seed {nseed}",
          flush=True)

    ds = netCDF4.Dataset(src_cbf)
    T = len(ds.variables["GPP"][:])
    real = {k: np.array(ds.variables[k][:], float) for k in STREAMS}
    unc = {k: stream_unc(ds.variables[k]) for k in STREAMS}
    ds.close()
    valid = {k: (v > -9990) & np.isfinite(v) for k, v in real.items()}
    print("  declared unc:", unc)

    fwd = make_forward(src_cbf)
    lp_hard = make_lp(src_cbf, "hard")
    hits = np.load(os.path.join(HITS_DIR, f"site_{site}_results.npz"))
    rng_t = np.random.default_rng(tseed)
    gpp_obs = real["GPP"][valid["GPP"]].mean()

    def candidates(Z, label, quiet=False):
        lp = lp_hard(Z)
        pred = fwd["predict"](Z)
        ok = np.isfinite(lp)
        ok &= np.all(np.isfinite(pred["GPP"]), 1) & np.all(np.isfinite(pred["LAI"]), 1)
        g = pred["GPP"][:, valid["GPP"]].mean(1)
        ok &= (g >= GPP_RANGE[0] * gpp_obs) & (g <= GPP_RANGE[1] * gpp_obs)
        if valid["ABGB"].any():
            ab = pred["ABGB"][:, valid["ABGB"]].mean(1)
            ab_obs = real["ABGB"][valid["ABGB"]].mean()
            ok &= (ab >= GPP_RANGE[0] * ab_obs) & (ab <= GPP_RANGE[1] * ab_obs)
        if not quiet:
            print(f"  {label}: {len(Z)} points, {np.isfinite(lp).sum()} feasible, "
                  f"{ok.sum()} plausible (obs mean GPP {gpp_obs:.2f}; "
                  f"candidate GPP {np.round(g[ok], 2)})", flush=True)
        return np.flatnonzero(ok), lp

    Zm = hits["z_modes"].astype(float)
    if a.polish:
        Zm = polish(src_cbf, np.concatenate([Zm, hits["z_hits"].astype(float)]),
                    a.polish)
    idx, lp = candidates(Zm, "real-data L-BFGS modes")
    if len(idx) == 0:
        raise SystemExit("no plausible mode")
    j = int(rng_t.choice(idx))
    z_true = None
    for attempt in range(60):
        Zj = Zm[j] + JITTER * SCALE * rng_t.standard_normal((32, len(SCALE)))
        idx_j, _ = candidates(Zj, f"jitter batch {attempt}", quiet=True)
        if len(idx_j):
            z_true = Zj[int(rng_t.choice(idx_j))]
            break
    if z_true is None:
        raise SystemExit("no feasible plausible jittered point")
    dist = np.sqrt(np.mean(((z_true - Zm[j]) / SCALE) ** 2))
    print(f"  truth: jittered mode {j} (mode logpost on real data {lp[j]:.1f}); "
          f"rms offset {dist:.3f} prior sd, feasible after {attempt+1} batches",
          flush=True)
    source, j = "z_modes+jitter", j

    truth = {k: v[0] for k, v in fwd["predict"](z_true[None]).items()}
    budget = wood_budget(fwd, z_true)
    print("  truth carbon budget: " + ", ".join(f"{k} {v:.3g}" for k, v in budget.items()),
          flush=True)
    rng_n = np.random.default_rng(nseed)
    pseudo, keep_idx = {}, {}
    for k in STREAMS:
        obs = np.full(T, -9999.0)
        m = valid[k]
        obs[m] = corrupt(truth[k][m], k, rng_n, unc[k])
        pseudo[k] = obs
        keep_idx[k] = np.flatnonzero(m)
        print(f"  {k:4s}: {m.sum():3d} pseudo-obs at steps "
              f"{keep_idx[k].min() if m.any() else '-'}-"
              f"{keep_idx[k].max() if m.any() else '-'}, truth mean "
              f"{truth[k][m].mean() if m.any() else np.nan:9.3f}, pseudo mean "
              f"{obs[m].mean() if m.any() else np.nan:9.3f}", flush=True)
    last_obs = max(keep_idx[k].max() for k in OBS_STREAMS if len(keep_idx[k]))
    cut = int(last_obs + 1)
    print(f"  record {T} steps; projection window {cut}..{T-1}")

    path = os.path.join(out_dir, "osse.cbf.nc")
    shutil.copy(src_cbf, path)
    ds = netCDF4.Dataset(path, "a")
    for k in STREAMS:
        ds[k][:] = pseudo[k]
    ds.close()

    np.savez(os.path.join(out_dir, "truth.npz"), z_true=z_true, cut=cut,
             site=site, tag=a.tag, truth_seed=tseed, noise_seed=nseed,
             source=source, source_index=j, real_gpp_mean=gpp_obs,
             gpp_range=np.array(GPP_RANGE),
             **{f"keep_{k}": v for k, v in keep_idx.items()},
             **{f"truth_{k}": v for k, v in truth.items()},
             **{f"pseudo_{k}": v for k, v in pseudo.items()})
    # starting points for the fitter: every known-feasible point of this site
    # (feasibility depends on parameters only, never on the observations)
    Zs = np.concatenate([hits["z_modes"].astype(float), hits["z_hits"].astype(float)])
    np.savez(os.path.join(out_dir, "seeds.npz"), z_seeds=Zs)
    print(f"wrote {out_dir}/{{osse.cbf.nc, truth.npz, seeds.npz}}  "
          f"({len(Zs)} seed points)")


if __name__ == "__main__":
    main()
