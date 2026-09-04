"""Likelihood-only parallel tempering for the SARLA sampling stage (idea T1).

Tempered target at inverse temperature beta:
    V_beta(z) = P(z) - (1 - beta) * Plik(z) + logit_jacobian(z)
where P is the full log-posterior of dalec_jax.likelihood.mlf2 (EDC terms +
data likelihood, -inf outside the hard gate) and Plik the data-likelihood
part alone. Every rung keeps the EDC gate and the EDC penalties at full
strength; only the data term is flattened, so hot rungs cannot leak into
infeasible space.

Kernel: K rungs with geometric betas from 1 down to beta_min, n_per_rung
walkers each; within a rung the move is the chart-shaped random walk or a
differential-evolution move (complementary halves, gamma = 2.38/sqrt(2D) 90%
of the time, 1.0 otherwise), chosen per step with probability `mix`; every
`swap_every` steps adjacent rungs propose walker swaps with
    log alpha = (beta_k - beta_{k+1}) * (Plik_{k+1} - Plik_k).
Only the cold rung (beta = 1) is recorded, after burn-in, so the output is an
exact sample of the target. Evaluation cost per step = K * n_per_rung.
"""
import os
import sys
import time

import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(_here, "..", "CARDAMOM", "PYTHON", "dalec_jax", "src"),
             os.path.join(_here, "dalec_jax_src")):
    if os.path.isdir(cand):
        sys.path.insert(0, cand)

import jax
import jax.numpy as jnp

D = 89


def make_tempered_batch(cbf_path, temper_edc=False, edc_terms=()):
    """Return batch(Z) -> (P_full, L): P_full = mlf2 total + logit Jacobian; L is the
    part that gets tempered: the data likelihood alone (default) or, with
    temper_edc=True, the whole finite posterior except the Jacobian (EDC
    penalties included; the hard gate stays -inf at every temperature)."""
    from dalec_jax.likelihood import data_prep, mlf2
    from dalec_jax import edcs
    from dalec_jax.model.dalec_1100 import run_dalec_1100, prederive_vegk
    from dalec_jax.indices import PARMIN, PARMAX, E
    from dalec_jax.inference.target import logit_jacobian
    sel = [getattr(E, name) for name in edc_terms if name]   # selective EDC tempering
    cbf = data_prep.load_cbf(cbf_path)
    ecfg = {"n_timesteps": cbf.n_timesteps, "dint": edcs.compute_dint(cbf.time),
            "edc_eqf": cbf.edc_eqf, "skt_ref_mean": cbf.skt_ref_mean}
    VegK = prederive_vegk(cbf.met["DOY"], cbf.LAT)
    pmin, lr = jnp.asarray(PARMIN), jnp.log(jnp.asarray(PARMAX) / jnp.asarray(PARMIN))

    def one(z):
        p = pmin * jnp.exp(jax.nn.sigmoid(z) * lr)
        pools, fluxes = run_dalec_1100(p, cbf.met, cbf.LAT, cbf.deltat, VegK)
        rec, ML, P = mlf2(cbf, ecfg, p, pools, fluxes)
        if temper_edc:
            L = P                                    # everything finite except the Jacobian
        elif sel:
            L = jnp.sum(ML) + jnp.sum(jnp.asarray([rec[i] for i in sel]))   # data + chosen EDC penalties
        else:
            L = jnp.sum(ML)
        return P + logit_jacobian(z), L
    f = jax.jit(jax.vmap(one))

    def batch(Z, chunk=4096):
        Z = np.atleast_2d(np.asarray(Z, float))
        Ps, Ls = [], []
        for i in range(0, len(Z), chunk):
            P, L = f(jnp.asarray(Z[i:i + chunk]))
            Ps.append(np.asarray(P, float)); Ls.append(np.asarray(L, float))
        return np.concatenate(Ps), np.concatenate(Ls)
    return batch


def run_pt(atlas, tbatch, cfg, n_steps, n_chains, seed=5, init_ks=None, report=None,
           init_X=None):
    """Parallel tempering over the atlas charts. Returns (draws, acc, best, diag)."""
    rng = np.random.default_rng(seed)
    K = int(cfg.pt_rungs)
    n = n_chains // K
    betas = np.geomspace(1.0, cfg.pt_beta_min, K)
    charts, scale = atlas.charts, atlas.scale
    C = np.stack([c.center for c in charts])
    E = np.stack([c.eigvecs for c in charts])
    Vs = np.stack([np.sqrt(c.var) for c in charts])
    D = C.shape[1]                                  # dimension from the atlas, not a constant
    burn_end = int(round(n_steps * cfg.burn_frac))
    thin = max(5, n_steps // 600)
    if cfg.max_draws:
        thin = max(thin, int(np.ceil((n_steps - burn_end) * n / cfg.max_draws)))
    de_gamma = cfg.de_gamma if cfg.de_gamma else 2.38 / np.sqrt(2 * D)

    def V(P, L, k):
        return P - (1.0 - betas[k]) * L

    # initial states: same for every rung (chart centres or explicit points)
    ks0 = rng.integers(0, len(charts), n_chains) if init_ks is None else np.asarray(init_ks, int)
    X0 = C[ks0[:n_chains]] + 0.01 * rng.standard_normal((n_chains, D))
    if init_X is not None:
        X0 = np.asarray(init_X, float)[:n_chains] + 0.01 * rng.standard_normal((n_chains, D))
    X = X0.reshape(K, n, D).copy()
    P, L = tbatch(X.reshape(-1, D) * scale)
    P, L = np.array(P, float).reshape(K, n), np.array(L, float).reshape(K, n)   # writable copies
    bad = ~np.isfinite(P)
    while bad.any():
        idx = rng.integers(0, len(charts), int(bad.sum()))
        X[bad] = C[idx] + 0.01 * rng.standard_normal((int(bad.sum()), D))
        p2, l2 = tbatch(X[bad] * scale)
        P[bad], L[bad] = np.array(p2, float), np.array(l2, float)
        bad = ~np.isfinite(P)

    def nearest(W):
        return np.argmin(np.stack([c.maha2(W) for c in charts], axis=1), 1)

    gamma = np.full(K, cfg.gamma0)
    recent = [[] for _ in range(K)]
    acc = np.zeros((K, 2)); pacc = np.zeros((K, 2)); swaps = np.zeros((K - 1, 2))
    half = n // 2
    halves = (np.arange(half), np.arange(half, n))
    keep, t0 = [], time.time()
    keep_hot = []                                    # thinned hottest-rung trace (chain identity kept) for diagnostics
    ident = np.arange(K * n).reshape(K, n)          # replica identity travels with swaps
    seen_hot = np.zeros(K * n, bool); seen_cold_after_hot = np.zeros(K * n, bool)
    round_trips = np.zeros(K * n, int); hot_visits = 0

    def loc_lq(kk, A, B, g):
        s = Vs[kk] * g
        y = np.einsum("nd,ndk->nk", B - A, E[kk]) / s
        return -0.5 * np.sum(y * y, 1) - np.sum(np.log(s), 1)

    # hot-rung independence moves from the (inflated) atlas mixture: re-randomise the basin
    # of the hottest rungs every step so replicas do not merely get sorted by density
    hot_p = float(getattr(cfg, "pt_hot_indep", 0.0) or 0.0)
    hot_rungs = int(getattr(cfg, "pt_hot_rungs", 1) or 1)
    infl = float(getattr(cfg, "pt_hot_inflate", 0.0) or 0.0) or 1.0 / np.sqrt(betas[-1])
    nC = len(charts)
    def mix_logq(W):
        comp = np.stack([-0.5 * c.maha2(W) / infl**2 - np.sum(np.log(np.sqrt(c.var) * infl)) for c in charts], 1)
        m = comp.max(1, keepdims=True)
        return (m[:, 0] + np.log(np.exp(comp - m).sum(1))) - np.log(nC)
    def mix_sample(m):
        j = rng.integers(0, nC, m)
        return C[j] + np.einsum("nj,ndj->nd", rng.standard_normal((m, D)) * Vs[j] * infl, E[j])
    iacc = np.zeros(2)
    hot_prev = None; hot_changes = np.zeros(2)          # nearest-chart changes at the hottest rung (basin-hopping proxy)

    for t in range(n_steps):
        use_de = cfg.mix > 0 and rng.random() < cfg.mix
        if not use_de:
            # chart move on all rungs at once (one batched evaluation)
            kx = nearest(X.reshape(-1, D)).reshape(K, n)
            if hot_prev is not None:
                hot_changes += ((kx[-1] != hot_prev).sum(), n)
            hot_prev = kx[-1].copy()
            xi = rng.standard_normal((K, n, D)) * (gamma[:, None, None] * Vs[kx])
            Y = X + np.einsum("knk2,knd2->knd", xi[..., None, :][..., 0, :], E[kx]) if False else \
                X + np.einsum("knj,kndj->knd", xi, E[kx])
            Py, Ly = tbatch(Y.reshape(-1, D) * scale)
            Py, Ly = np.array(Py, float).reshape(K, n), np.array(Ly, float).reshape(K, n)
            ky = nearest(Y.reshape(-1, D)).reshape(K, n)
            for k in range(K):
                lq_fwd = loc_lq(kx[k], X[k], Y[k], gamma[k]); lq_bwd = loc_lq(ky[k], Y[k], X[k], gamma[k])
                loga = np.where(np.isfinite(Py[k]), V(Py[k], Ly[k], k) - V(P[k], L[k], k) + (lq_bwd - lq_fwd), -np.inf)
                take = np.log(rng.random(n)) < loga
                acc[k] += (take.sum(), n); recent[k].append(take.mean())
                X[k][take], P[k][take], L[k][take] = Y[k][take], Py[k][take], Ly[k][take]
                if t < burn_end and len(recent[k]) >= 25:
                    gamma[k] *= float(np.exp(np.mean(recent[k]) - cfg.target_acc)); recent[k] = []
        else:
            for S1, S2 in (halves, halves[::-1]):
                n1 = len(S1)
                a = S2[rng.integers(0, len(S2), (K, n1))]
                b = S2[rng.integers(0, len(S2), (K, n1))]
                same = a == b
                while same.any():
                    b[same] = S2[rng.integers(0, len(S2), int(same.sum()))]; same = a == b
                g = np.where(rng.random((K, n1)) < 0.9, de_gamma, 1.0)
                rows = np.arange(K)[:, None]
                Xa, Xb = X[rows, a], X[rows, b]            # (K, n1, D) partner states
                Y = X[:, S1] + g[..., None] * (Xa - Xb) + 1e-6 * rng.standard_normal((K, n1, D))
                Py, Ly = tbatch(Y.reshape(-1, D) * scale)
                Py, Ly = np.array(Py, float).reshape(K, n1), np.array(Ly, float).reshape(K, n1)
                for k in range(K):
                    loga = np.where(np.isfinite(Py[k]), V(Py[k], Ly[k], k) - V(P[k][S1], L[k][S1], k), -np.inf)
                    take = np.log(rng.random(n1)) < loga
                    pacc[k] += (take.sum(), n1)
                    idx = S1[take]
                    X[k][idx], P[k][idx], L[k][idx] = Y[k][take], Py[k][take], Ly[k][take]
        if hot_p > 0 and rng.random() < hot_p:
            ks = list(range(K - hot_rungs, K))
            Yh = mix_sample(n * len(ks)).reshape(len(ks), n, D)
            Ph, Lh = tbatch(Yh.reshape(-1, D) * scale)
            Ph, Lh = np.array(Ph, float).reshape(len(ks), n), np.array(Lh, float).reshape(len(ks), n)
            for i, k in enumerate(ks):
                lq_new = mix_logq(Yh[i]); lq_old = mix_logq(X[k])
                loga = np.where(np.isfinite(Ph[i]), V(Ph[i], Lh[i], k) - V(P[k], L[k], k) + (lq_old - lq_new), -np.inf)
                take = np.log(rng.random(n)) < loga
                iacc += (take.sum(), n)
                X[k][take], P[k][take], L[k][take] = Yh[i][take], Ph[i][take], Lh[i][take]
        if cfg.pt_swap_every and t % cfg.pt_swap_every == 0 and K > 1:
            for k in range(K - 1):
                loga = (betas[k] - betas[k + 1]) * (L[k + 1] - L[k])
                take = np.log(rng.random(n)) < loga
                swaps[k] += (take.sum(), n)
                for arr in (X, P, L, ident):
                    tmp = arr[k][take].copy(); arr[k][take] = arr[k + 1][take]; arr[k + 1][take] = tmp
            # round trips: a replica that reaches the hottest rung and later returns to the cold rung
            hot_ids = ident[-1]; seen_hot[hot_ids] = True
            cold_ids = ident[0]
            back = seen_hot[cold_ids]
            round_trips[cold_ids[back]] += 1; seen_hot[cold_ids[back]] = False
        if t >= burn_end and t % thin == 0:
            keep.append((X[0] * scale).copy())
            if getattr(cfg, "pt_keep_hot", False):
                keep_hot.append((X[-1] * scale).copy())
        if report and t % report == 0:
            print(f"    pt step {t:6d}/{n_steps} cold acc {acc[0,0]/max(acc[0,1],1):.3f} "
                  f"de-acc {pacc[0,0]/max(pacc[0,1],1):.3f} swaps "
                  + "/".join(f"{swaps[k,0]/max(swaps[k,1],1):.2f}" for k in range(K - 1))
                  + f" best {P[0].max():.2f} hot-best {P[-1].max():.2f} {time.time()-t0:.0f}s", flush=True)
    diag = dict(acc_chart=float(acc[0, 0] / max(acc[0, 1], 1)), acc_pop=float(pacc[0, 0] / max(pacc[0, 1], 1)),
                swap_acc=[float(swaps[k, 0] / max(swaps[k, 1], 1)) for k in range(K - 1)],
                round_trips_total=int(round_trips.sum()), acc_hot_indep=float(iacc[0] / max(iacc[1], 1)),
                hot_chart_change_rate=float(hot_changes[0] / max(hot_changes[1], 1)),
                hot_draws=(np.stack(keep_hot) if keep_hot else None), replicas_with_round_trip=int((round_trips > 0).sum()),
                n_replicas=int(K * n),
                betas=betas.tolist(), n_pop_steps=int(pacc[0, 1] // max(n, 1)), n_restart=0,
                gamma_final=float(gamma[0]), s_ad_final=0.0, thin=thin, final_lp=P[0].copy())
    return np.concatenate(keep), diag["acc_chart"], float(P[0].max()), diag
