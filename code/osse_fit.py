"""Fit the fast path (SARLA atlas + balanced chart-RWM) to any CBF.

Self-contained on purpose: it imports only `sarla` and `dalec_jax`, so it can
be rsynced to a remote GPU without dragging in the toy-model harness.

The atlas is built FROM SCRATCH for whichever CBF is passed: the cached
81-chart atlas belongs to the real NL-Loo posterior, and an OSSE target is a
different posterior, so reusing it as the atlas would be wrong. Those centres
ARE reused as optimizer STARTING POINTS, which is legitimate and necessary --
EDC feasibility is a property of the parameters alone and never of the
observations, and without feasible starts the atlas comes back with no
curvature at all (see find_seeds).

Pipeline, as validated on the 89-D transfer test:
  1. L-BFGS from known-feasible starts   (the EDC-search analogue)
  2. SARLA audit-and-surgery atlas
  3. density-connectivity clustering into regions
  4. equal chains per region             (fixes the width compression)
  5. chart-shaped local RWM at N x budget

usage: osse_fit.py <cbf> <out.npz> [budget_mult] [n_chains] [n_seeds] [seeds.npz]
"""
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_here = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(_here, "..", "CARDAMOM", "PYTHON", "dalec_jax",
                          "src"),
             os.path.join(_here, "dalec_jax_src")):
    if os.path.isdir(cand):
        sys.path.insert(0, cand)

import jax
import jax.numpy as jnp

from dalec_jax.inference.target import build_logpost
import sarla as S

D = 89
SCALE = np.full(D, np.pi / np.sqrt(3.0))
BASE_STEPS = 2000
TAU, N_MID = 10.0, 7          # density-connectivity clustering

# Two guards added after the 2026-09-01 OSSE (docs/OSSE_SARLA.md): 26 of 64
# chains sat 100-650,000 nats below the mode, all in one- to five-chart
# regions that balanced allocation had given as many chains as the 144-chart
# main region, and a chart-shaped local walk never leaves such a pit.
#   REGION_GAP   a region whose best chart centre is this far below the
#                global best gets no chains. 100 nats is a heuristic: the
#                typical set sits ~D/2 = 45 below the mode, and volume
#                cannot make up e^100 within the prior box for anything
#                seen so far (observed junk gaps: 10^3-10^5).
#   RESTART_GAP  during burn-in, a chain this far below the population's
#                best is moved onto a healthy chain's position. Standard
#                population-MCMC practice; stops at the end of burn-in so
#                the sampling phase is plain MCMC from wherever chains are.
# Set either to None to recover the 2026-08-31 behaviour.
REGION_GAP = 100.0
RESTART_GAP, RESTART_EVERY = 100.0, 500


def make_target(cbf_path):
    logpost, _ = build_logpost(cbf_path)
    logpost_curv, _ = build_logpost(cbf_path, gate="none")
    lp = jax.jit(jax.vmap(logpost))
    g = jax.jit(jax.grad(lambda z: -logpost(z)))
    H = jax.jit(jax.jacfwd(jax.grad(lambda z: -logpost_curv(z))))

    def batch(Z, chunk=4096):
        Z = np.atleast_2d(np.asarray(Z, float))
        return np.concatenate([np.asarray(lp(jnp.asarray(Z[i:i + chunk])))
                               for i in range(0, len(Z), chunk)])

    return dict(logpost_batch=batch,
                grad=lambda z: np.asarray(g(jnp.asarray(z))),
                hess=lambda z: np.asarray(H(jnp.asarray(z))),
                scale=SCALE)


def find_seeds(target, n_starts, seed=0, seed_file=None):
    """Feasible starting points, then L-BFGS polish.

    A random start is USELESS here: the hard EDC gate makes logpost -inf with
    no gradient almost everywhere, so L-BFGS cannot move off an infeasible
    point. Measured on this target: 0 of 1024 draws feasible, from N(0,
    0.6*scale) AND from the true prior. An earlier version of this script
    seeded randomly and produced 128 charts every one of which had a NaN
    Hessian -- an atlas with no curvature at all.

    So starts come from a file of known-feasible points (EDC feasibility
    depends only on parameters, never on the observations, so centres found
    for one dataset are valid starts for any other dataset of the same site).
    """
    rng = np.random.default_rng(seed)
    if seed_file:
        z0s = np.load(seed_file)
        z0s = z0s["centers_w"] * SCALE if "centers_w" in getattr(
            z0s, "files", []) else np.asarray(z0s)
        lp = target["logpost_batch"](z0s)
        z0s = z0s[np.isfinite(lp)]
        print(f"    {len(z0s)} feasible seed points from {seed_file}",
              flush=True)
        if len(z0s) == 0:
            raise SystemExit("no feasible seed points -- refusing to build "
                             "an atlas with no curvature")
        idx = rng.choice(len(z0s), n_starts, replace=len(z0s) < n_starts)
        z0s = z0s[idx] + 0.02 * rng.standard_normal((n_starts, D))
    else:
        z0s = rng.standard_normal((n_starts, D)) * SCALE * 0.6

    f = lambda z: -float(target["logpost_batch"](z[None])[0])
    out, t0 = [], time.time()
    for i, z0 in enumerate(z0s):
        r = minimize(f, z0, jac=lambda z: target["grad"](z),
                     method="L-BFGS-B", options=dict(maxiter=300))
        out.append(r.x)
        if (i + 1) % 16 == 0:
            print(f"    seeds {i+1}/{n_starts}  {time.time()-t0:.0f}s",
                  flush=True)
    out = np.array(out)
    ok = np.isfinite(target["logpost_batch"](out))
    print(f"    {ok.sum()}/{len(out)} polished seeds feasible", flush=True)
    if ok.sum() < 4:
        raise SystemExit("fewer than 4 feasible seeds -- aborting rather "
                         "than building a curvature-free atlas")
    return out[ok]


def density_clusters(atlas, target, tau=TAU, n_mid=N_MID, return_lp=False):
    C = np.stack([c.center for c in atlas.charts])
    K = len(C)
    lp0 = np.asarray(target["logpost_batch"](C * atlas.scale), float)
    ts = np.linspace(0, 1, n_mid + 2)[1:-1]
    parent = list(range(K))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    pairs = [(i, j) for i in range(K) for j in range(i + 1, K)]
    mids = np.concatenate([C[i][None] + ts[:, None] * (C[j] - C[i])[None]
                           for i, j in pairs])
    lpm = np.asarray(target["logpost_batch"](mids * atlas.scale),
                     float).reshape(len(pairs), n_mid)
    for (i, j), row in zip(pairs, lpm):
        if row.min() > min(lp0[i], lp0[j]) - tau:
            a, b = find(i), find(j)
            if a != b:
                parent[a] = b
    _, lab = np.unique(np.array([find(i) for i in range(K)]),
                       return_inverse=True)
    return (lab, lp0) if return_lp else lab


def balanced_init(lab, n_chains, rng, keep=None, lp0=None, within=45.0):
    """Equal chains per region, over the regions in `keep` (default all).

    Within a region, start only from charts whose centre is within `within`
    nats of that region's best. The audit rounds add charts far down the
    density (smoke test: seed charts at -324..-627, audit-added charts at
    -700..-1491), and the connectivity test is relative to the LOWER
    endpoint, so those charts are merged into the main region; a chain
    started there spends its burn-in climbing out.
    """
    regs = np.unique(lab) if keep is None else np.asarray(keep)
    out = []
    for i in range(n_chains):
        cand = np.flatnonzero(lab == regs[i % len(regs)])
        if lp0 is not None:
            good = cand[lp0[cand] >= lp0[cand].max() - within]
            cand = good if len(good) else cand
        out.append(rng.choice(cand))
    return np.array(out)


def live_regions(lab, lp0, gap=REGION_GAP):
    """Regions whose best chart centre is within `gap` of the global best."""
    regs = np.unique(lab)
    best = np.array([lp0[lab == r].max() for r in regs])
    if gap is None:
        return regs, best
    return regs[best >= best.max() - gap], best


def run_kernel(atlas, target, n_steps, n_chains, seed=5, init_ks=None,
               report=None, restart_gap=RESTART_GAP,
               restart_every=RESTART_EVERY):
    rng = np.random.default_rng(seed)
    charts, scale = atlas.charts, atlas.scale
    K = len(charts)
    C = np.stack([c.center for c in charts])
    E = np.stack([c.eigvecs for c in charts])
    Vs = np.stack([np.sqrt(c.var) for c in charts])
    thin = max(5, n_steps // 600)
    batch = target["logpost_batch"]

    ks0 = rng.integers(0, K, n_chains) if init_ks is None else \
        np.asarray(init_ks, int)
    X = C[ks0] + 0.01 * rng.standard_normal((n_chains, D))
    lpi = np.array(batch(X * scale), dtype=float)
    bad = ~np.isfinite(lpi)
    while bad.any():
        idx = rng.integers(0, K, int(bad.sum()))
        X[bad] = C[idx] + 0.01 * rng.standard_normal((int(bad.sum()), D))
        lpi[bad] = batch(X[bad] * scale)
        bad = ~np.isfinite(lpi)

    def nearest(W):
        return np.argmin(np.stack([c.maha2(W) for c in charts], axis=1), 1)

    def loc_lq(kk, A, B):
        s = Vs[kk] * gamma
        y = np.einsum("nd,ndk->nk", B - A, E[kk]) / s
        return -0.5 * np.sum(y * y, 1) - np.sum(np.log(s), 1)

    gamma, recent, acc = 0.05, [], [0, 0]
    keep, t0, n_restart = [], time.time(), 0
    for t in range(n_steps):
        if (restart_gap is not None and 0 < t < n_steps // 2
                and t % restart_every == 0):
            stuck = lpi < lpi.max() - restart_gap
            if stuck.any() and (~stuck).any():
                src = rng.choice(np.flatnonzero(~stuck), int(stuck.sum()))
                X[stuck] = X[src] + 1e-3 * rng.standard_normal(
                    (int(stuck.sum()), D))
                lpi[stuck] = batch(X[stuck] * scale)
                # a restart that lands infeasible just re-copies exactly
                bad = stuck.copy(); bad[stuck] = ~np.isfinite(lpi[stuck])
                X[bad] = X[src[~np.isfinite(lpi[stuck])]]
                lpi[bad] = batch(X[bad] * scale) if bad.any() else lpi[bad]
                n_restart += int(stuck.sum())
        kx = nearest(X)
        xi = rng.standard_normal((n_chains, D)) * (gamma * Vs[kx])
        Y = X + np.einsum("nk,ndk->nd", xi, E[kx])
        lpy = np.array(batch(Y * scale), dtype=float)
        ky = nearest(Y)
        loga = np.where(np.isfinite(lpy),
                        (lpy - lpi) + (loc_lq(ky, Y, X) - loc_lq(kx, X, Y)),
                        -np.inf)
        take = np.log(rng.random(n_chains)) < loga
        acc[0] += int(take.sum()); acc[1] += n_chains
        recent.append(take.mean())
        if t < n_steps // 2 and len(recent) >= 25:
            gamma *= float(np.exp(np.mean(recent) - 0.23))
            recent = []
        X[take], lpi[take] = Y[take], lpy[take]
        if t >= n_steps // 2 and t % thin == 0:
            keep.append((X * scale).copy())
        if report and t % report == 0:
            print(f"    step {t:6d}/{n_steps} acc {acc[0]/max(acc[1],1):.3f} "
                  f"gamma {gamma:.4f} best {lpi.max():.2f} "
                  f"chains>best-100: {int(np.sum(lpi > lpi.max()-100))}/"
                  f"{n_chains} restarts {n_restart} "
                  f"{time.time()-t0:.0f}s", flush=True)
    return np.concatenate(keep), acc[0] / acc[1], float(lpi.max())


if __name__ == "__main__":
    cbf, out = sys.argv[1], sys.argv[2]
    mult = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    n_chains = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    n_seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 128
    seed_file = sys.argv[6] if len(sys.argv) > 6 else None
    print(f"backend {jax.default_backend()}  cbf {cbf}  x{mult}", flush=True)

    target = make_target(cbf)
    t0 = time.time()
    seeds = find_seeds(target, n_seeds, seed_file=seed_file)
    print(f"  {n_seeds} seeds in {time.time()-t0:.0f}s", flush=True)

    t0 = time.time()
    atlas = S.sarla(target, seeds, rounds=6, n_audit=4096, seed=3)
    degraded = sum(1 for c in atlas.charts if np.all(c.eigvals == 0))
    print(f"  atlas {len(atlas.charts)} charts in {time.time()-t0:.0f}s "
          f"({degraded} degraded)", flush=True)
    if degraded == len(atlas.charts):
        raise SystemExit("every chart degraded -- the atlas has no curvature; "
                         "check that the seeds are EDC-feasible")

    lab, lp0 = density_clusters(atlas, target, return_lp=True)
    keep_regs, best = live_regions(lab, lp0)
    print(f"  {lab.max()+1} regions, sizes {np.bincount(lab)}", flush=True)
    print(f"  region best logpost {np.round(best, 1)}; keeping "
          f"{len(keep_regs)}/{lab.max()+1} within {REGION_GAP} of the best",
          flush=True)
    # OSSE_WITHIN: nats below the region's best a start chart may be
    # (default 45); "none" = any chart in the region, the 2026-08-31 way.
    _w = os.environ.get("OSSE_WITHIN", "45")
    within = None if _w.lower() == "none" else float(_w)
    print(f"  start charts within {within} nats of region best", flush=True)
    ks = balanced_init(lab, n_chains, np.random.default_rng(99),
                       keep=keep_regs, lp0=lp0 if within is not None else None,
                       within=within if within is not None else 45.0)
    print(f"  init charts: {len(np.unique(ks))} distinct, centre logpost "
          f"{lp0[ks].min():.1f}..{lp0[ks].max():.1f}", flush=True)

    ns = BASE_STEPS * mult
    t0 = time.time()
    draws, acc, best = run_kernel(atlas, target, ns, n_chains, init_ks=ks,
                                  report=max(ns // 8, 500))
    print(f"  sampled {draws.shape} acc {acc:.3f} best {best:.2f} in "
          f"{time.time()-t0:.0f}s", flush=True)

    # float64 on purpose: the hard gate's state_ranges EDC is a rounding
    # knife-edge at topsoil saturation, and float32-rounded draws come back
    # -inf under it ~14% of the time (2026-09-01).
    np.savez(out, draws=draws, lab=lab, acc=acc, best=best,
             centers=np.stack([c.center for c in atlas.charts]),
             center_lp=lp0, kept_regions=keep_regs, region_gap=REGION_GAP,
             restart_gap=RESTART_GAP if RESTART_GAP is not None else np.nan,
             n_steps=ns, n_chains=n_chains)
    print(f"wrote {out}", flush=True)
