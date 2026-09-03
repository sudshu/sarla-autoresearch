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


def make_tempered_batch(cbf_path, temper_edc=False):
    """Return batch(Z) -> (P_full, L): P_full = mlf2 total + logit Jacobian; L is the
    part that gets tempered: the data likelihood alone (default) or, with
    temper_edc=True, the whole finite posterior except the Jacobian (EDC
    penalties included; the hard gate stays -inf at every temperature)."""
    from dalec_jax.likelihood import data_prep, mlf2
    from dalec_jax import edcs
    from dalec_jax.model.dalec_1100 import run_dalec_1100, prederive_vegk
    from dalec_jax.indices import PARMIN, PARMAX
    from dalec_jax.inference.target import logit_jacobian
    cbf = data_prep.load_cbf(cbf_path)
    ecfg = {"n_timesteps": cbf.n_timesteps, "dint": edcs.compute_dint(cbf.time),
            "edc_eqf": cbf.edc_eqf, "skt_ref_mean": cbf.skt_ref_mean}
    VegK = prederive_vegk(cbf.met["DOY"], cbf.LAT)
    pmin, lr = jnp.asarray(PARMIN), jnp.log(jnp.asarray(PARMAX) / jnp.asarray(PARMIN))

    def one(z):
        p = pmin * jnp.exp(jax.nn.sigmoid(z) * lr)
        pools, fluxes = run_dalec_1100(p, cbf.met, cbf.LAT, cbf.deltat, VegK)
        rec, ML, P = mlf2(cbf, ecfg, p, pools, fluxes)
        L = P if temper_edc else jnp.sum(ML)
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
    P, L = P.reshape(K, n), L.reshape(K, n)
    bad = ~np.isfinite(P)
    while bad.any():
        idx = rng.integers(0, len(charts), int(bad.sum()))
        X[bad] = C[idx] + 0.01 * rng.standard_normal((int(bad.sum()), D))
        p2, l2 = tbatch(X[bad] * scale)
        P[bad], L[bad] = p2, l2
        bad = ~np.isfinite(P)

    def nearest(W):
        return np.argmin(np.stack([c.maha2(W) for c in charts], axis=1), 1)

    gamma = np.full(K, cfg.gamma0)
    recent = [[] for _ in range(K)]
    acc = np.zeros((K, 2)); pacc = np.zeros((K, 2)); swaps = np.zeros((K - 1, 2))
    half = n // 2
    halves = (np.arange(half), np.arange(half, n))
    keep, t0 = [], time.time()

    def loc_lq(kk, A, B, g):
        s = Vs[kk] * g
        y = np.einsum("nd,ndk->nk", B - A, E[kk]) / s
        return -0.5 * np.sum(y * y, 1) - np.sum(np.log(s), 1)

    for t in range(n_steps):
        use_de = cfg.mix > 0 and rng.random() < cfg.mix
        if not use_de:
            # chart move on all rungs at once (one batched evaluation)
            kx = nearest(X.reshape(-1, D)).reshape(K, n)
            xi = rng.standard_normal((K, n, D)) * (gamma[:, None, None] * Vs[kx])
            Y = X + np.einsum("knk2,knd2->knd", xi[..., None, :][..., 0, :], E[kx]) if False else \
                X + np.einsum("knj,kndj->knd", xi, E[kx])
            Py, Ly = tbatch(Y.reshape(-1, D) * scale)
            Py, Ly = Py.reshape(K, n), Ly.reshape(K, n)
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
                Xa = np.take_along_axis(X, a[..., None], 1); Xb = np.take_along_axis(X, b[..., None], 1)
                Y = X[:, S1] + g[..., None] * (Xa - Xb) + 1e-6 * rng.standard_normal((K, n1, D))
                Py, Ly = tbatch(Y.reshape(-1, D) * scale)
                Py, Ly = Py.reshape(K, n1), Ly.reshape(K, n1)
                for k in range(K):
                    loga = np.where(np.isfinite(Py[k]), V(Py[k], Ly[k], k) - V(P[k][S1], L[k][S1], k), -np.inf)
                    take = np.log(rng.random(n1)) < loga
                    pacc[k] += (take.sum(), n1)
                    idx = S1[take]
                    X[k][idx], P[k][idx], L[k][idx] = Y[k][take], Py[k][take], Ly[k][take]
        if cfg.pt_swap_every and t % cfg.pt_swap_every == 0 and K > 1:
            for k in range(K - 1):
                loga = (betas[k] - betas[k + 1]) * (L[k + 1] - L[k])
                take = np.log(rng.random(n)) < loga
                swaps[k] += (take.sum(), n)
                for arr in (X, P, L):
                    tmp = arr[k][take].copy(); arr[k][take] = arr[k + 1][take]; arr[k + 1][take] = tmp
        if t >= burn_end and t % thin == 0:
            keep.append((X[0] * scale).copy())
        if report and t % report == 0:
            print(f"    pt step {t:6d}/{n_steps} cold acc {acc[0,0]/max(acc[0,1],1):.3f} "
                  f"de-acc {pacc[0,0]/max(pacc[0,1],1):.3f} swaps "
                  + "/".join(f"{swaps[k,0]/max(swaps[k,1],1):.2f}" for k in range(K - 1))
                  + f" best {P[0].max():.2f} hot-best {P[-1].max():.2f} {time.time()-t0:.0f}s", flush=True)
    diag = dict(acc_chart=float(acc[0, 0] / max(acc[0, 1], 1)), acc_pop=float(pacc[0, 0] / max(pacc[0, 1], 1)),
                swap_acc=[float(swaps[k, 0] / max(swaps[k, 1], 1)) for k in range(K - 1)],
                betas=betas.tolist(), n_pop_steps=int(pacc[0, 1] // max(n, 1)), n_restart=0,
                gamma_final=float(gamma[0]), s_ad_final=0.0, thin=thin, final_lp=P[0].copy())
    return np.concatenate(keep), diag["acc_chart"], float(P[0].max()), diag
