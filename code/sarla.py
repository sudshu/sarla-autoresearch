"""SARLA — Sampling-Audited, Rank-adaptive Laplace Atlas.

Implementation of the Notion spec (SARLA page, 2026-08): build a Laplace
atlas of charts (tangent/normal rank split via a whitened-metric eigen
threshold), audit it with importance draws from a frozen defensive proposal,
project each discrepancy onto the near-optimal set (tangent-preserving
normal-space re-optimization), diagnose the geometric defect, perform atlas
surgery, iterate to stability, then freeze and run exact independence
Metropolis-Hastings.

Target-agnostic: the caller supplies
    logpost_batch : (N, d) -> (N,)   log unnormalized posterior (finite or -inf)
    hess          : (d,)   -> (d, d) Hessian of -logpost (any symmetry noise ok)
    grad          : (d,)   -> (d,)   gradient of -logpost
    scale         : (d,)   prior stds; the atlas works in whitened w = z/scale.

All atlas math is numpy in whitened coordinates; only target calls hit JAX.
Weights across charts are uniform (arc-length tiling; density-derived weights
collapse on flat ridges — established in the ridge-atlas experiments).
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln, logsumexp

RANK_TAU = 1.0          # whitened curvature below prior curvature => tangent
VAR_CAP = 1.0           # cap chart variance at whitened prior variance
VAR_FLOOR = 1e-12
T_DF = 4.0              # defensive Student-t degrees of freedom
ETA = 0.05              # defensive mixture weight
FLAG_TOPK = 8           # discrepancies repaired per audit round
MERGE_TOL = 1.0         # whitened Mahalanobis distance for duplicate charts
EXTEND_SIGMA = 2.0      # tangential extent beyond which a flag means "extend"
MODEL_TOL = 2.0         # log-units of quadratic-model error still "covered"
GAP_MIN = 10.0          # spectral gap ratio that defines a tangent subspace
GAP_CAP = 100.0         # only eigvals below this can sit on the tangent side


def rank_split(lam):
    """Scale-aware local rank (spec: 'stability rule, not a raw cutoff').

    Prefer a clear spectral gap: the largest consecutive eigenvalue ratio
    among candidates below GAP_CAP; if it exceeds GAP_MIN, everything below
    the gap is tangent. Otherwise fall back to the absolute prior-curvature
    rule (lam < RANK_TAU). A fixed cutoff alone misclassifies ridges whose
    soft direction is only ~1.5x stiffer than the prior (rank 0 there makes
    every audit repair collapse back to the mode)."""
    r_abs = int(np.sum(lam < RANK_TAU))
    best_r, best_ratio = r_abs, 1.0
    for i in range(lam.size - 1):
        if lam[i] >= GAP_CAP:
            break
        lo = max(lam[i], 1e-9)
        if lam[i + 1] / lo > best_ratio:
            best_ratio, best_r = lam[i + 1] / lo, i + 1
    return max(r_abs, best_r) if best_ratio >= GAP_MIN else r_abs


def _covered(charts, w, logpi_w):
    """A point is a duplicate only if a nearby chart's quadratic model is
    also ACCURATE there — Mahalanobis proximity alone is not coverage (a
    variance-capped flat chart is 'near' the whole ridge it fails on)."""
    return any(c.maha2(w[None])[0] < MERGE_TOL ** 2
               and c.model_err(w, logpi_w) < MODEL_TOL
               for c in charts)


# ---------------------------------------------------------------- charts

@dataclass
class Chart:
    center: np.ndarray        # whitened
    eigvals: np.ndarray       # of whitened Hessian of -logpost, ascending
    eigvecs: np.ndarray       # columns
    rank: int                 # tangent dimensionality (# eigvals < RANK_TAU)
    var: np.ndarray           # per-eigendirection proposal variance (capped)
    logpi: float              # log target at center (z-space value, bookkeeping)

    @property
    def tangent(self):
        return self.eigvecs[:, :self.rank]      # eigvals ascending

    @property
    def normal(self):
        return self.eigvecs[:, self.rank:]

    def model_err(self, w, logpi_w):
        """|true logpi - this chart's local quadratic prediction| at w."""
        y = self.eigvecs.T @ (w - self.center)
        pred = self.logpi - 0.5 * float(self.eigvals @ (y * y))
        return abs(logpi_w - pred)

    def maha2(self, W):
        y = (W - self.center) @ self.eigvecs / np.sqrt(self.var)
        return np.sum(y * y, axis=-1)

    def logpdf(self, W):
        d = self.center.size
        return -0.5 * (self.maha2(W) + np.sum(np.log(self.var))
                       + d * np.log(2 * np.pi))

    def draw(self, rng, n):
        xi = rng.standard_normal((n, self.center.size))
        return self.center + (xi * np.sqrt(self.var)) @ self.eigvecs.T


def make_chart(target, w):
    z = w * target["scale"]
    H = np.asarray(target["hess"](z), dtype=float)
    Hw = target["scale"][:, None] * H * target["scale"][None, :]
    Hw = 0.5 * (Hw + Hw.T)
    if np.all(np.isfinite(Hw)):
        lam, V = np.linalg.eigh(Hw)
    else:
        # NaN curvature (e.g. the known KNORR second-order leak): degrade to
        # a rank-open prior-width chart instead of crashing the atlas.
        d = w.size
        lam, V = np.zeros(d), np.eye(d)
    lam = np.where(np.isfinite(lam), lam, 0.0)
    # capped inverse curvature: indefinite/flat directions get prior variance
    var = np.where(lam > 1.0 / VAR_CAP, 1.0 / np.maximum(lam, VAR_FLOOR), VAR_CAP)
    rank = rank_split(lam)
    logpi = float(target["logpost_batch"](z[None, :])[0])
    return Chart(center=w.copy(), eigvals=lam, eigvecs=V, rank=rank,
                 var=var, logpi=logpi)


# ---------------------------------------------------------------- atlas

@dataclass
class Atlas:
    charts: list
    scale: np.ndarray
    eta: float = ETA
    t_loc: np.ndarray = None
    t_scale: float = None
    history: list = field(default_factory=list)   # audit-round records
    diagnoses: list = field(default_factory=list)  # (round, label, w*) log

    def refresh_defense(self):
        # Defense is PRIOR-wide (whitened prior is ~unit scale about 0), not
        # atlas-wide: it must reach mass the atlas knows nothing about.
        C = np.stack([c.center for c in self.charts])
        self.t_loc = np.zeros(C.shape[1])
        self.t_scale = max(2.0, 1.3 * float(np.abs(C).max()))

    def _t_logpdf(self, W):
        d = W.shape[-1]
        r2 = np.sum(((W - self.t_loc) / self.t_scale) ** 2, axis=-1)
        return (gammaln((T_DF + d) / 2) - gammaln(T_DF / 2)
                - 0.5 * d * np.log(T_DF * np.pi) - d * np.log(self.t_scale)
                - 0.5 * (T_DF + d) * np.log1p(r2 / T_DF))

    def logq(self, W):
        K = len(self.charts)
        comp = np.stack([c.logpdf(W) for c in self.charts], axis=-1)
        log_atlas = logsumexp(comp, axis=-1) - np.log(K)
        return np.logaddexp(np.log1p(-self.eta) + log_atlas,
                            np.log(self.eta) + self._t_logpdf(W))

    def draw(self, rng, n):
        n_t = rng.binomial(n, self.eta)
        xi = rng.standard_normal((n_t, self.t_loc.size))
        u = rng.chisquare(T_DF, size=n_t)
        Wt = self.t_loc + self.t_scale * xi * np.sqrt(T_DF / u)[:, None]
        ks = rng.integers(0, len(self.charts), size=n - n_t)
        Wa = np.concatenate([self.charts[k].draw(rng, 1) for k in ks]) \
            if n - n_t else np.empty((0, self.t_loc.size))
        W = np.concatenate([Wa, Wt])
        return W[rng.permutation(n)]


def build_atlas(target, seeds_z):
    """Phase A: charts at optimizer seeds (deduplicated)."""
    atlas = Atlas(charts=[], scale=np.asarray(target["scale"], float))
    for z in np.atleast_2d(seeds_z):
        w = np.asarray(z, float) / atlas.scale
        if any(c.maha2(w[None])[0] < MERGE_TOL**2 for c in atlas.charts):
            continue
        atlas.charts.append(make_chart(target, w))
    atlas.refresh_defense()
    return atlas


# ---------------------------------------------------------------- audit

def audit(atlas, target, n=4096, rng=None):
    """Phase B: frozen-proposal importance audit."""
    rng = rng or np.random.default_rng(0)
    W = atlas.draw(rng, n)
    logpi = np.asarray(target["logpost_batch"](W * atlas.scale), float)
    logq = atlas.logq(W)
    logw = np.where(np.isfinite(logpi), logpi - logq, -np.inf)
    lw = logw - logw.max()
    wgt = np.exp(lw)
    ess = float(wgt.sum() ** 2 / (wgt ** 2).sum()) / n
    # flag under-covered mass: largest importance ratios, deduplicated
    order = np.argsort(logw)[::-1]
    flags, thresh = [], np.median(logw[np.isfinite(logw)]) + 5.0
    for i in order:
        if logw[i] < thresh or len(flags) >= FLAG_TOPK:
            break
        if all(np.linalg.norm(W[i] - W[j]) > MERGE_TOL for j in flags):
            flags.append(i)
    return dict(W=W, logpi=logpi, logq=logq, logw=logw, ess=ess,
                flags=np.asarray(flags, int))


# ------------------------------------------------- diagnosis + surgery

def _normal_correct(target, atlas, w_pred, Nk, n0):
    """Minimize J along the normal subspace only (tangent frozen).

    Starts from the flagged point's own normal offset n0, so the corrector
    descends into the basin the discrepancy lives in — starting from 0
    (the chart center) would collapse every diagnosis back onto the chart.
    """
    s = atlas.scale

    def f(n):
        z = (w_pred + Nk @ n) * s
        J = -float(target["logpost_batch"](z[None])[0])
        g = np.asarray(target["grad"](z), float)          # grad of -logpost
        return (J, Nk.T @ (g * s)) if np.isfinite(J) else (1e30, 0 * n)

    res = minimize(f, n0, jac=True, method="L-BFGS-B",
                   options=dict(maxiter=100))
    return w_pred + Nk @ res.x


def diagnose_repair(atlas, target, aud, round_no):
    """Phase C+D: project each flagged draw onto the near-optimal set,
    classify the geometric defect, operate on the atlas."""
    for i in aud["flags"]:
        wz = aud["W"][i]
        k = int(np.argmin([c.maha2(wz[None])[0] for c in atlas.charts]))
        ck = atlas.charts[k]
        Tk, Nk = ck.tangent, ck.normal
        s_z = Tk.T @ (wz - ck.center)
        w_pred = ck.center + Tk @ s_z
        w_star = _normal_correct(target, atlas, w_pred, Nk,
                                 Nk.T @ (wz - w_pred)) \
            if Nk.shape[1] else w_pred
        lp_star = float(target["logpost_batch"]((w_star * atlas.scale)[None])[0])
        if not np.isfinite(lp_star):
            atlas.diagnoses.append((round_no, "infeasible", w_star))
            continue
        if _covered(atlas.charts, w_star, lp_star):
            atlas.diagnoses.append((round_no, "duplicate", w_star))
            continue
        new = make_chart(target, w_star)
        if not np.isfinite(new.logpi):
            atlas.diagnoses.append((round_no, "infeasible", w_star))
            continue
        tang_sigma = np.sqrt(ck.var[:ck.rank]) if ck.rank else 1.0
        if new.rank != ck.rank:
            label = "rank-change"
        elif ck.rank and np.any(np.abs(s_z) > EXTEND_SIGMA * tang_sigma):
            label = "extend"
        elif np.linalg.norm(w_star - w_pred) > MERGE_TOL:
            label = "split"           # corrector left the chart's basin
        else:
            label = "refine"          # quadratic model wrong nearby (bend)
        atlas.charts.append(new)
        atlas.diagnoses.append((round_no, label, w_star))
    # merge/prune pass: drop charts fully shadowed by a kept neighbor whose
    # quadratic model also explains them (proximity alone is not shadowing)
    kept = []
    for c in sorted(atlas.charts, key=lambda c: -c.logpi):
        if not any(k.maha2(c.center[None])[0] < MERGE_TOL**2 * 0.25
                   and k.model_err(c.center, c.logpi) < MODEL_TOL
                   for k in kept):
            kept.append(c)
    atlas.charts = kept
    atlas.refresh_defense()


def sarla(target, seeds_z, rounds=6, n_audit=4096, clean_stop=2, seed=0,
          verbose=True):
    """Full loop: build -> (audit -> diagnose -> surgery)* -> freeze.

    Freezes only after `clean_stop` consecutive flag-free audits — a single
    clean audit is evidence, not proof, of coverage (finite audits can miss
    mass the defense rarely reaches).
    """
    rng = np.random.default_rng(seed)
    atlas = build_atlas(target, seeds_z)
    clean = 0
    for r in range(rounds):
        aud = audit(atlas, target, n=n_audit, rng=rng)
        atlas.history.append(dict(round=r, K=len(atlas.charts),
                                  ess=aud["ess"], nflags=len(aud["flags"])))
        if verbose:
            print(f"[sarla] round {r}: K={len(atlas.charts)} charts, "
                  f"IS-ESS={aud['ess']:.3f}, flags={len(aud['flags'])}")
        if len(aud["flags"]) == 0:
            clean += 1
            if clean >= clean_stop:
                break
            continue
        clean = 0
        diagnose_repair(atlas, target, aud, r)
    return atlas


# --------------------------------------------------- production sampler

def production_imh(atlas, target, n_steps=2000, n_chains=64, seed=1):
    """Phase E: exact independence Metropolis-Hastings from the frozen atlas."""
    rng = np.random.default_rng(seed)
    d = atlas.t_loc.size
    X = atlas.draw(rng, n_chains)
    lpi = np.array(target["logpost_batch"](X * atlas.scale), dtype=float)
    lq = atlas.logq(X)
    bad = ~np.isfinite(lpi)
    while bad.any():                       # feasible initial states only
        X[bad] = atlas.draw(rng, int(bad.sum()))
        lpi[bad] = target["logpost_batch"](X[bad] * atlas.scale)
        lq[bad] = atlas.logq(X[bad])
        bad = ~np.isfinite(lpi)
    out = np.empty((n_steps, n_chains, d))
    acc = 0
    for t in range(n_steps):
        Y = atlas.draw(rng, n_chains)
        lpy = np.array(target["logpost_batch"](Y * atlas.scale), dtype=float)
        lqy = atlas.logq(Y)
        loga = np.where(np.isfinite(lpy), (lpy - lqy) - (lpi - lq), -np.inf)
        take = np.log(rng.random(n_chains)) < loga
        X[take], lpi[take], lq[take] = Y[take], lpy[take], lqy[take]
        acc += int(take.sum())
        out[t] = X
    return dict(draws_z=out * atlas.scale, draws_w=out,
                accept=acc / (n_steps * n_chains))
