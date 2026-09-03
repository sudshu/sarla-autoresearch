"""SARLA v2 engine: topology-aware, rank-adaptive Laplace atlas with real surgery.

Same pipeline as sarla.py (optimization -> Laplace atlas -> importance audit
-> normal projection -> rank/topology diagnosis -> surgery -> re-audit ->
freeze -> exact MCMC), but the surgery operations are structurally different
from one another instead of all ending in "append another Gaussian":

  extend       grow chart k's tangent extent along the direction the flagged
               point lies in (no new chart): the ridge continues straight and
               k's quadratic model is still accurate there
  refine       the ridge bends: k's extent is capped where its model fails and
               a new chart is tiled at the corrected point, linked to k
  split        k's quadratic model is wrong INSIDE its own domain: k is
               replaced by two charts at k +/- offset along the offending
               tangent direction (fresh Hessians, halved extents), linked
  rank-change  the corrected point has a different local rank: a new chart of
               that rank is linked to k by a 'rank' edge (a stratum boundary)
  branch       the corrected point is not density-connected to k (the segment
               dips more than branch_tau below its endpoints): a new stratum
               (branch id), no link
  merge        neighbouring charts of the same rank and branch that explain
               each other's centres are fused (extents unioned)

Charts carry rank, tangent/normal bases, per-tangent extent (via the proposal
variance), neighbours (metric overlap), branch id (connected component of the
neighbour graph including rank edges) and typed links. The proposal density
is still a mixture with exactly known weights (uniform or tangent-volume),
so the final independence-MH / chart-RWM stages remain exact.

Every audit round is logged with chart count, rank histogram, IS-ESS, number
and severity of uncovered draws, quadratic-model error of the flagged points,
counts of each operation, cumulative target evaluations and wall-clock.

Chart2 exposes the same fields the fast-path kernel reads from sarla.Chart
(center, eigvecs, var, maha2), so sarla_fit's sampling stage is unchanged.
"""
import time
from dataclasses import dataclass, field, asdict

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln, logsumexp


@dataclass
class SurgeryConfig:
    # rank detection
    rank_tau: float = 1.0
    gap_min: float = 10.0
    gap_cap: float = 100.0
    var_cap: float = 1.0
    # audit
    n_audit: int = 4096
    flag_topk: int = 8
    flag_thresh: float = 5.0        # nats above the median importance log-weight
    eta: float = 0.05               # defensive Student-t weight
    t_df: float = 4.0
    weight_rule: str = "uniform"    # uniform | volume
    # diagnosis
    normal_projection: bool = True
    extend_sigma: float = 2.0       # tangent extent = extend_sigma * sqrt(var_t)
    model_tol: float = 2.0          # nats of quadratic-model error still "accurate"
    merge_tol: float = 1.0          # Mahalanobis distance for duplicate/merge
    overlap_tol: float = 2.0        # Mahalanobis distance defining neighbours
    branch_tau: float = 10.0        # density dip that defines a separate stratum
    n_mid: int = 5
    split_offset: float = 0.5       # split children at +/- offset * s_z
    refine_shrink: float = 1.0      # cap factor on k's extent at a bend
    rank_hysteresis: float = 2.0    # a rank change must survive rank_tau / and * this factor
    bend_tol: float = 1.0           # normal displacement (in normal sigmas) beyond which the ridge "bends"
    fallback_patch: bool = True     # if a round has flags but no structural op, add a chart (v1 behaviour)
    branch_on_infeasible: bool = True  # False: a segment through the hard gate is "unknown", not a new stratum
    # which operations are enabled (for ablations)
    do_extend: bool = True
    do_refine: bool = True
    do_split: bool = True
    do_rank: bool = True
    do_branch: bool = True
    do_merge: bool = True
    # loop
    rounds: int = 6
    clean_stop: int = 2
    stop_ess: float = None          # freeze when IS-ESS fraction exceeds this


def rank_split(lam, cfg, tau=None):
    r_abs = int(np.sum(lam < (tau if tau is not None else cfg.rank_tau)))
    best_r, best_ratio = r_abs, 1.0
    for i in range(lam.size - 1):
        if lam[i] >= cfg.gap_cap:
            break
        lo = max(lam[i], 1e-9)
        if lam[i + 1] / lo > best_ratio:
            best_ratio, best_r = lam[i + 1] / lo, i + 1
    return max(r_abs, best_r) if best_ratio >= cfg.gap_min else r_abs


@dataclass
class Chart2:
    id: int
    center: np.ndarray
    eigvals: np.ndarray
    eigvecs: np.ndarray
    rank: int
    var: np.ndarray            # per-eigendirection proposal variance
    logpi: float
    branch: int = 0
    neighbors: set = field(default_factory=set)
    links: list = field(default_factory=list)   # (other_id, kind)
    born: str = "seed"
    round_born: int = -1

    @property
    def tangent(self):
        return self.eigvecs[:, :self.rank]

    @property
    def normal(self):
        return self.eigvecs[:, self.rank:]

    def extent(self, cfg):
        return cfg.extend_sigma * np.sqrt(self.var[:self.rank])

    def coords(self, w):
        return self.eigvecs.T @ (w - self.center)

    def model_err(self, w, logpi_w):
        y = self.coords(w)
        return abs(logpi_w - (self.logpi - 0.5 * float(self.eigvals @ (y * y))))

    def maha2(self, W):
        y = (W - self.center) @ self.eigvecs / np.sqrt(self.var)
        return np.sum(y * y, axis=-1)

    def logpdf(self, W):
        d = self.center.size
        return -0.5 * (self.maha2(W) + np.sum(np.log(self.var)) + d * np.log(2 * np.pi))

    def draw(self, rng, n):
        xi = rng.standard_normal((n, self.center.size))
        return self.center + (xi * np.sqrt(self.var)) @ self.eigvecs.T

    def log_volume(self):
        return float(np.sum(0.5 * np.log(self.var[:self.rank]))) if self.rank else 0.0


class Atlas2:
    def __init__(self, target, cfg, rng):
        self.target, self.cfg, self.rng = target, cfg, rng
        self.scale = np.asarray(target["scale"], float)
        self.charts, self.next_id = [], 0
        self.history, self.ops_log = [], []
        self.n_eval = 0
        self.t_loc = self.t_scale = None
        self.logw_k = None

    # ---- target access with evaluation accounting
    def lp(self, W):
        W = np.atleast_2d(W)
        self.n_eval += len(W)
        return np.asarray(self.target["logpost_batch"](W * self.scale), float)

    def make_chart(self, w, born, round_no):
        z = w * self.scale
        H = np.asarray(self.target["hess"](z), dtype=float)
        Hw = self.scale[:, None] * H * self.scale[None, :]
        Hw = 0.5 * (Hw + Hw.T)
        if np.all(np.isfinite(Hw)):
            lam, V = np.linalg.eigh(Hw)
        else:
            lam, V = np.zeros(w.size), np.eye(w.size)
        lam = np.where(np.isfinite(lam), lam, 0.0)
        var = np.where(lam > 1.0 / self.cfg.var_cap, 1.0 / np.maximum(lam, 1e-12), self.cfg.var_cap)
        c = Chart2(id=self.next_id, center=np.array(w, float), eigvals=lam, eigvecs=V,
                   rank=rank_split(lam, self.cfg), var=var, logpi=float(self.lp(w[None])[0]),
                   born=born, round_born=round_no)
        self.next_id += 1
        return c

    def by_id(self, i):
        for c in self.charts:
            if c.id == i:
                return c
        return None

    # ---- geometry / topology bookkeeping
    def refresh(self):
        cfg = self.cfg
        C = np.stack([c.center for c in self.charts])
        for c in self.charts:
            c.neighbors = set()
        for i, ci in enumerate(self.charts):
            m = ci.maha2(C)
            for j, cj in enumerate(self.charts):
                if j != i and m[j] < cfg.overlap_tol ** 2:
                    ci.neighbors.add(cj.id); cj.neighbors.add(ci.id)
        # branches: connected components of neighbour graph + rank links
        ids = [c.id for c in self.charts]
        parent = {i: i for i in ids}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for c in self.charts:
            for j in c.neighbors:
                if j in parent:
                    parent[find(c.id)] = find(j)
            for j, kind in c.links:
                if j in parent and kind in ("rank", "split", "refine"):
                    parent[find(c.id)] = find(j)
        roots = sorted({find(i) for i in ids})
        for c in self.charts:
            c.branch = roots.index(find(c.id))
        # mixture weights
        if cfg.weight_rule == "volume":
            lv = np.array([c.log_volume() for c in self.charts])
            self.logw_k = lv - logsumexp(lv)
        else:
            self.logw_k = np.full(len(self.charts), -np.log(len(self.charts)))
        self.t_loc = np.zeros(C.shape[1])
        self.t_scale = max(2.0, 1.3 * float(np.abs(C).max()))

    # ---- proposal density (exact)
    def _t_logpdf(self, W):
        d, df = W.shape[-1], self.cfg.t_df
        r2 = np.sum(((W - self.t_loc) / self.t_scale) ** 2, axis=-1)
        return (gammaln((df + d) / 2) - gammaln(df / 2) - 0.5 * d * np.log(df * np.pi)
                - d * np.log(self.t_scale) - 0.5 * (df + d) * np.log1p(r2 / df))

    def logq(self, W):
        comp = np.stack([c.logpdf(W) for c in self.charts], axis=-1) + self.logw_k
        return np.logaddexp(np.log1p(-self.cfg.eta) + logsumexp(comp, axis=-1),
                            np.log(self.cfg.eta) + self._t_logpdf(W))

    def draw(self, rng, n):
        n_t = rng.binomial(n, self.cfg.eta)
        xi = rng.standard_normal((n_t, self.t_loc.size))
        u = rng.chisquare(self.cfg.t_df, size=n_t)
        Wt = self.t_loc + self.t_scale * xi * np.sqrt(self.cfg.t_df / u)[:, None]
        ks = rng.choice(len(self.charts), size=n - n_t, p=np.exp(self.logw_k))
        Wa = np.concatenate([self.charts[k].draw(rng, 1) for k in ks]) \
            if n - n_t else np.empty((0, self.t_loc.size))
        W = np.concatenate([Wa, Wt])
        return W[rng.permutation(n)]

    # ---- coverage test
    def covered(self, w, logpi_w):
        return any(c.maha2(w[None])[0] < self.cfg.merge_tol ** 2
                   and c.model_err(w, logpi_w) < self.cfg.model_tol for c in self.charts)

    def density_connected(self, wa, wb, lpa, lpb):
        """Straight-segment connectivity. At 89-D the feasible set is thin, so
        the segment between two feasible points usually crosses the hard
        gate; with branch_on_infeasible=False such a segment is treated as
        'unknown' (connected) rather than as evidence of a new stratum."""
        ts = np.linspace(0, 1, self.cfg.n_mid + 2)[1:-1]
        mids = wa[None] + ts[:, None] * (wb - wa)[None]
        lpm = self.lp(mids)
        fin = np.isfinite(lpm)
        if not fin.all():
            return not self.cfg.branch_on_infeasible
        return bool(lpm.min() > min(lpa, lpb) - self.cfg.branch_tau)

    def nearest(self, w):
        return int(np.argmin([c.maha2(w[None])[0] for c in self.charts]))

    def normal_correct(self, w_pred, Nk, n0):
        s = self.scale

        def f(n):
            z = (w_pred + Nk @ n) * s
            self.n_eval += 1
            J = -float(self.target["logpost_batch"](z[None])[0])
            g = np.asarray(self.target["grad"](z), float)
            return (J, Nk.T @ (g * s)) if np.isfinite(J) else (1e30, 0 * n)
        res = minimize(f, n0, jac=True, method="L-BFGS-B", options=dict(maxiter=100))
        return w_pred + Nk @ res.x


def build(target, seeds_z, cfg, rng):
    atlas = Atlas2(target, cfg, rng)
    for z in np.atleast_2d(seeds_z):
        w = np.asarray(z, float) / atlas.scale
        if atlas.charts and any(c.maha2(w[None])[0] < cfg.merge_tol ** 2 for c in atlas.charts):
            continue
        c = atlas.make_chart(w, "seed", -1)
        if np.isfinite(c.logpi):
            atlas.charts.append(c)
    if not atlas.charts:
        raise RuntimeError("no feasible seed chart")
    atlas.refresh()
    return atlas


def audit(atlas, rng):
    cfg = atlas.cfg
    W = atlas.draw(rng, cfg.n_audit)
    logpi = atlas.lp(W)
    logq = atlas.logq(W)
    logw = np.where(np.isfinite(logpi), logpi - logq, -np.inf)
    fin = np.isfinite(logw)
    lw = logw - logw[fin].max()
    wgt = np.where(fin, np.exp(lw), 0.0)
    ess = float(wgt.sum() ** 2 / (wgt ** 2).sum()) / cfg.n_audit
    med = np.median(logw[fin])
    thresh = med + cfg.flag_thresh
    uncovered = np.flatnonzero(fin & (logw > thresh))
    order = uncovered[np.argsort(logw[uncovered])[::-1]]
    flags = []
    for i in order:
        if len(flags) >= cfg.flag_topk:
            break
        if all(np.linalg.norm(W[i] - W[j]) > cfg.merge_tol for j in flags):
            flags.append(i)
    return dict(W=W, logpi=logpi, logq=logq, logw=logw, ess=ess,
                flags=np.asarray(flags, int), n_uncovered=int(len(uncovered)),
                logw_max=float(logw[fin].max() - med), logw_q95=float(np.percentile(logw[fin], 95) - med),
                logw_q99=float(np.percentile(logw[fin], 99) - med), median=float(med))


OPS = ("extend", "refine", "split", "rank-change", "branch", "merge", "patch", "duplicate", "infeasible")


def diagnose_repair(atlas, aud, round_no):
    cfg = atlas.cfg
    ops = {k: 0 for k in OPS}
    model_errs = []
    for i in aud["flags"]:
        wz = aud["W"][i]
        if not atlas.charts:
            break
        k = atlas.nearest(wz)
        ck = atlas.charts[k]
        Tk, Nk = ck.tangent, ck.normal
        s_z = Tk.T @ (wz - ck.center)
        w_pred = ck.center + Tk @ s_z
        if cfg.normal_projection and Nk.shape[1]:
            w_star = atlas.normal_correct(w_pred, Nk, Nk.T @ (wz - w_pred))
        else:
            w_star = wz
        lp_star = float(atlas.lp(w_star[None])[0])
        if not np.isfinite(lp_star):
            ops["infeasible"] += 1
            atlas.ops_log.append((round_no, "infeasible", ck.id, None)); continue
        if atlas.covered(w_star, lp_star):
            ops["duplicate"] += 1
            atlas.ops_log.append((round_no, "duplicate", ck.id, None)); continue
        err_k = ck.model_err(w_star, lp_star)
        model_errs.append(err_k)
        ext = ck.extent(cfg)
        ratio = np.abs(s_z) / np.maximum(ext, 1e-12) if ck.rank else np.zeros(0)
        j = int(np.argmax(ratio)) if ck.rank else None
        outside = bool(ck.rank and ratio[j] > 1.0)
        connected = atlas.density_connected(ck.center, w_star, ck.logpi, lp_star)

        if cfg.do_branch and not connected:
            new = atlas.make_chart(w_star, "branch", round_no)
            if np.isfinite(new.logpi):
                atlas.charts.append(new); ops["branch"] += 1
                atlas.ops_log.append((round_no, "branch", ck.id, new.id))
            continue
        new = atlas.make_chart(w_star, "pending", round_no)
        if not np.isfinite(new.logpi):
            ops["infeasible"] += 1; continue
        robust_rank_change = (new.rank != ck.rank and cfg.do_rank
                              and ck.rank not in (rank_split(new.eigvals, cfg, cfg.rank_tau / cfg.rank_hysteresis),
                                                  rank_split(new.eigvals, cfg, cfg.rank_tau * cfg.rank_hysteresis)))
        # bend test: how far did the normal correction move the point, in the chart's normal sigmas
        if Nk.shape[1]:
            nrm = Nk.T @ (w_star - w_pred)
            bend = float(np.sqrt(np.sum(nrm ** 2 / ck.var[ck.rank:])))
        else:
            bend = 0.0
        if robust_rank_change:
            new.born = "rank-change"
            new.links.append((ck.id, "rank")); ck.links.append((new.id, "rank"))
            if outside:
                ck.var[j] = (abs(s_z[j]) / cfg.extend_sigma) ** 2   # cap k at the boundary
            atlas.charts.append(new); ops["rank-change"] += 1
            atlas.ops_log.append((round_no, "rank-change", ck.id, new.id))
        elif cfg.do_extend and outside and err_k < cfg.model_tol and bend < cfg.bend_tol:
            ck.var[j] = (1.1 * abs(s_z[j]) / cfg.extend_sigma) ** 2  # grow, no new chart
            ops["extend"] += 1
            atlas.ops_log.append((round_no, "extend", ck.id, None))
        elif cfg.do_refine and outside:
            new.born = "refine"
            new.links.append((ck.id, "refine")); ck.links.append((new.id, "refine"))
            ck.var[j] = min(ck.var[j], (cfg.refine_shrink * abs(s_z[j]) / cfg.extend_sigma) ** 2)
            atlas.charts.append(new); ops["refine"] += 1
            atlas.ops_log.append((round_no, "refine", ck.id, new.id))
        elif cfg.do_split and ck.rank:
            # k's model is wrong inside its own domain: replace k by two charts
            direction = Tk[:, j]
            off = cfg.split_offset * s_z[j]
            kids = []
            for sgn in (+1, -1):
                w_c = ck.center + sgn * off * direction
                kid = atlas.make_chart(w_c, "split", round_no)
                if np.isfinite(kid.logpi):
                    kid.var[:kid.rank] = np.minimum(kid.var[:kid.rank], ck.var[:ck.rank].max() * 0.25) \
                        if kid.rank else kid.var[:kid.rank]
                    kid.links = list(ck.links); kids.append(kid)
            if len(kids) == 2:
                kids[0].links.append((kids[1].id, "split")); kids[1].links.append((kids[0].id, "split"))
                atlas.charts = [c for c in atlas.charts if c.id != ck.id] + kids
                ops["split"] += 1
                atlas.ops_log.append((round_no, "split", ck.id, (kids[0].id, kids[1].id)))
            else:
                new.born = "refine"; atlas.charts.append(new); ops["refine"] += 1
        else:
            new.born = "refine"; atlas.charts.append(new); ops["refine"] += 1
            atlas.ops_log.append((round_no, "refine", ck.id, new.id))
    structural = sum(ops[k] for k in ("extend", "refine", "split", "rank-change", "branch"))
    if cfg.fallback_patch and structural == 0 and len(aud["flags"]):
        # every flag was 'duplicate'/'infeasible' yet the audit still flags them:
        # the mixture weight there is too low. Patch with a chart at the worst flag.
        wz = aud["W"][aud["flags"][0]]
        lpz = float(aud["logpi"][aud["flags"][0]])
        if np.isfinite(lpz):
            new = atlas.make_chart(wz, "patch", round_no)
            if np.isfinite(new.logpi):
                atlas.charts.append(new); ops["patch"] = ops.get("patch", 0) + 1
                atlas.ops_log.append((round_no, "patch", None, new.id))
    atlas.refresh()
    if cfg.do_merge:
        ops["merge"] += merge_pass(atlas, round_no)
        atlas.refresh()
    return ops, model_errs


def merge_pass(atlas, round_no):
    cfg = atlas.cfg
    n = 0
    changed = True
    while changed:
        changed = False
        for ci in sorted(atlas.charts, key=lambda c: -c.logpi):
            for jid in list(ci.neighbors):
                cj = atlas.by_id(jid)
                if cj is None or cj is ci or cj.rank != ci.rank or cj.branch != ci.branch:
                    continue
                if (ci.maha2(cj.center[None])[0] < cfg.merge_tol ** 2
                        and cj.maha2(ci.center[None])[0] < cfg.merge_tol ** 2
                        and ci.model_err(cj.center, cj.logpi) < cfg.model_tol
                        and cj.model_err(ci.center, ci.logpi) < cfg.model_tol):
                    keep, drop = (ci, cj) if ci.logpi >= cj.logpi else (cj, ci)
                    s = keep.tangent.T @ (drop.center - keep.center) if keep.rank else np.zeros(0)
                    for t in range(keep.rank):
                        keep.var[t] = max(keep.var[t], (abs(s[t]) / cfg.extend_sigma) ** 2)
                    keep.links += [l for l in drop.links if l[0] != keep.id]
                    atlas.charts = [c for c in atlas.charts if c.id != drop.id]
                    atlas.ops_log.append((round_no, "merge", keep.id, drop.id))
                    n += 1; changed = True
                    break
            if changed:
                atlas.refresh(); break
    return n


def sarla2(target, seeds_z, cfg=None, seed=0, verbose=True):
    cfg = cfg or SurgeryConfig()
    rng = np.random.default_rng(seed)
    t0 = time.time()
    atlas = build(target, seeds_z, cfg, rng)
    clean, prev_q95 = 0, None
    for r in range(cfg.rounds):
        aud = audit(atlas, rng)
        rk = np.array([c.rank for c in atlas.charts])
        ranks = dict(min=int(rk.min()), q25=float(np.percentile(rk, 25)), med=float(np.median(rk)),
                     q75=float(np.percentile(rk, 75)), max=int(rk.max()))
        rec = dict(round=r, K=len(atlas.charts), ranks=ranks, n_branches=len({c.branch for c in atlas.charts}),
                   ess=aud["ess"], n_flags=int(len(aud["flags"])), n_uncovered=aud["n_uncovered"],
                   logw_max=aud["logw_max"], logw_q95=aud["logw_q95"], logw_q99=aud["logw_q99"],
                   improved=(None if prev_q95 is None else bool(aud["logw_q95"] < prev_q95)),
                   n_eval=atlas.n_eval, wall=time.time() - t0)
        prev_q95 = aud["logw_q95"]
        stop = False
        if len(aud["flags"]) == 0:
            clean += 1; stop = clean >= cfg.clean_stop
        else:
            clean = 0
        if cfg.stop_ess is not None and aud["ess"] >= cfg.stop_ess:
            stop = True
        if not stop and len(aud["flags"]):
            ops, errs = diagnose_repair(atlas, aud, r)
            rec["ops"] = ops
            rec["model_err_med"] = float(np.median(errs)) if errs else None
            rec["model_err_max"] = float(np.max(errs)) if errs else None
        else:
            rec["ops"] = {k: 0 for k in OPS}
        rec["K_after"] = len(atlas.charts)
        atlas.history.append(rec)
        if verbose:
            o = rec["ops"]
            print(f"[sarla2] audit {r}: K={rec['K']} rank med {ranks['med']:.0f} [{ranks['min']}-{ranks['max']}] "
                  f"branches={rec['n_branches']} "
                  f"ESS={aud['ess']:.3f} uncovered={aud['n_uncovered']} (q95 {aud['logw_q95']:.1f}, "
                  f"max {aud['logw_max']:.1f}) -> "
                  + ", ".join(f"{v} {k}" for k, v in o.items() if v) + (" freeze" if stop else "")
                  + f"  [{atlas.n_eval} evals, {rec['wall']:.0f}s]", flush=True)
        if stop:
            break
    atlas.refresh()
    return atlas


def production_imh(atlas, target, n_steps=2000, n_chains=64, seed=1):
    """Exact independence Metropolis-Hastings from the frozen atlas."""
    rng = np.random.default_rng(seed)
    d = atlas.t_loc.size
    X = atlas.draw(rng, n_chains)
    lpi = np.array(target["logpost_batch"](X * atlas.scale), dtype=float)
    lq = atlas.logq(X)
    bad = ~np.isfinite(lpi)
    while bad.any():
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
    return dict(draws_z=out * atlas.scale, draws_w=out, accept=acc / (n_steps * n_chains))


def history_table(atlas):
    lines = []
    for h in atlas.history:
        o = h.get("ops", {})
        acts = ", ".join(f"{v} {k}" for k, v in o.items() if v and k not in ("duplicate", "infeasible"))
        acts += f"  ({o.get('duplicate', 0)} dup)" if o.get("duplicate") else ""
        rk = h["ranks"]
        lines.append(f"audit {h['round']}: {h['n_uncovered']} uncovered (q95 {h['logw_q95']:.1f}), "
                     f"K={h['K']} rank med {rk['med']:.0f} [{rk['min']}-{rk['max']}] ESS={h['ess']:.3f} "
                     f"-> {acts or 'nothing'}")
    return "\n".join(lines)
