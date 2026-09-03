"""Move set for the SARLA sampling phase, vectorised over chains.

The default configuration (kernel="chart_rwm", mix=0) issues exactly the
same RNG calls in the same order as scripts/osse_fit.py:run_kernel (the v3
fast path of 2026-09-01), so the baseline of the autoresearch loop IS v3.

Population moves (used when cfg.mix > 0) update the two halves of the
ensemble alternately, each half proposing from the other (the complementary-
ensemble scheme of Goodman & Weare / emcee), which keeps detailed balance
when all chains of a half move simultaneously:

  chart_de        y = x + g (x_a - x_b) + 1e-6 N(0,1);  g = 2.38/sqrt(2D)
                  (90%) or 1 (10%): CARDAMOM's STEP_DEMCMC move
  chart_stretch   y = x_j + z (x - x_j), z ~ g(z) on [1/a, a] ~ 1/sqrt(z);
                  MH ratio gets (D-1) log z: CARDAMOM's AFDEMCMC (mode 4) move
  chart_adaptcov  y = x + s L N(0,1), L L^T = pooled covariance of the whole
                  ensemble, refreshed every cfg.adapt_every steps during
                  burn-in only (fixed afterwards, so the sampling phase is a
                  valid fixed-kernel chain); s adapted to cfg.target_acc

All moves work in the atlas's whitened coordinates (x = z / scale).
"""
import time

import numpy as np

D = 89


def run_kernel(atlas, target, cfg, n_steps, n_chains, seed=5, init_ks=None,
               report=None, flat_cap=1.0, init_X=None):
    rng = np.random.default_rng(seed)
    charts, scale = atlas.charts, atlas.scale
    K = len(charts)
    C = np.stack([c.center for c in charts])
    E = np.stack([c.eigvecs for c in charts])
    Vs = np.stack([np.sqrt(c.var) for c in charts])
    if cfg.flat_mult != 1.0:
        flat = np.stack([c.var for c in charts]) >= flat_cap * (1 - 1e-9)
        Vs = np.where(flat, Vs * np.sqrt(cfg.flat_mult), Vs)
    burn_end = int(round(n_steps * cfg.burn_frac))
    restart_end = int(round(n_steps * cfg.restart_until))
    thin = max(5, n_steps // 600)
    if cfg.max_draws:
        thin = max(thin, int(np.ceil((n_steps - burn_end) * n_chains / cfg.max_draws)))
    batch = target["logpost_batch"]

    ks0 = rng.integers(0, K, n_chains) if init_ks is None else \
        np.asarray(init_ks, int)
    X = C[ks0] + 0.01 * rng.standard_normal((n_chains, D))
    if init_X is not None:                 # explicit whitened start points
        X = np.asarray(init_X, float) + 0.01 * rng.standard_normal((n_chains, D))
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

    gamma, recent, acc = cfg.gamma0, [], [0, 0]
    pacc, precent = [0, 0], []
    de_gamma = cfg.de_gamma if cfg.de_gamma else 2.38 / np.sqrt(2 * D)
    s_ad, L_ad = 2.38 / np.sqrt(D), None
    half = n_chains // 2
    halves = (np.arange(half), np.arange(half, n_chains))
    keep, t0, n_restart, n_pop = [], time.time(), 0, 0

    for t in range(n_steps):
        if (cfg.restart_gap is not None and 0 < t < restart_end
                and t % cfg.restart_every == 0):
            stuck = lpi < lpi.max() - cfg.restart_gap
            if stuck.any() and (~stuck).any():
                src = rng.choice(np.flatnonzero(~stuck), int(stuck.sum()))
                X[stuck] = X[src] + 1e-3 * rng.standard_normal(
                    (int(stuck.sum()), D))
                lpi[stuck] = batch(X[stuck] * scale)
                bad = stuck.copy(); bad[stuck] = ~np.isfinite(lpi[stuck])
                X[bad] = X[src[~np.isfinite(lpi[stuck])]]
                lpi[bad] = batch(X[bad] * scale) if bad.any() else lpi[bad]
                n_restart += int(stuck.sum())

        if (cfg.kernel == "chart_adaptcov" and t < burn_end
                and t >= int(cfg.adapt_start * n_steps)
                and (L_ad is None or t % cfg.adapt_every == 0)):
            cov = np.cov(X.T) + 1e-8 * np.eye(D)
            L_ad = np.linalg.cholesky(cov)

        use_pop = (cfg.mix > 0 and (cfg.kernel != "chart_adaptcov" or L_ad is not None)
                   and rng.random() < cfg.mix)
        if use_pop and cfg.kernel == "chart_indep":
            # exact independence Metropolis from the frozen atlas mixture q:
            # global jumps wherever the atlas has coverage (mode weights follow q's coverage, corrected by MH)
            n_pop += 1
            Y = atlas.draw(rng, n_chains)
            lpy = np.array(batch(Y * scale), dtype=float)
            lqx, lqy = atlas.logq(X), atlas.logq(Y)
            loga = np.where(np.isfinite(lpy), (lpy - lqy) - (lpi - lqx), -np.inf)
            take = np.log(rng.random(n_chains)) < loga
            pacc[0] += int(take.sum()); pacc[1] += n_chains
            X[take], lpi[take] = Y[take], lpy[take]
            use_pop = False           # skip the half-ensemble block below
            did_indep = True
        else:
            did_indep = False
        if did_indep:
            pass
        elif not use_pop:
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
            if t < burn_end and len(recent) >= 25:
                gamma *= float(np.exp(np.mean(recent) - cfg.target_acc))
                recent = []
            X[take], lpi[take] = Y[take], lpy[take]
        else:
            n_pop += 1
            for S1, S2 in (halves, halves[::-1]):
                n1 = len(S1)
                if cfg.kernel == "chart_de":
                    a = S2[rng.integers(0, len(S2), n1)]
                    b = S2[rng.integers(0, len(S2), n1)]
                    same = a == b
                    while same.any():
                        b[same] = S2[rng.integers(0, len(S2), int(same.sum()))]
                        same = a == b
                    g = np.where(rng.random(n1) < 0.9, de_gamma, 1.0)
                    Y = X[S1] + g[:, None] * (X[a] - X[b]) \
                        + 1e-6 * rng.standard_normal((n1, D))
                    logq = 0.0
                elif cfg.kernel == "chart_stretch":
                    j = S2[rng.integers(0, len(S2), n1)]
                    u = rng.random(n1)
                    z = ((cfg.stretch_a - 1.0) * u + 1.0) ** 2 / cfg.stretch_a
                    Y = X[j] + z[:, None] * (X[S1] - X[j])
                    logq = (D - 1) * np.log(z)
                elif cfg.kernel == "chart_adaptcov":
                    Y = X[S1] + s_ad * (rng.standard_normal((n1, D)) @ L_ad.T)
                    logq = 0.0
                else:
                    raise ValueError(cfg.kernel)
                lpy = np.array(batch(Y * scale), dtype=float)
                loga = np.where(np.isfinite(lpy), lpy - lpi[S1] + logq, -np.inf)
                take = np.log(rng.random(n1)) < loga
                pacc[0] += int(take.sum()); pacc[1] += n1
                precent.append(take.mean())
                X[S1[take]], lpi[S1[take]] = Y[take], lpy[take]
            if cfg.kernel == "chart_adaptcov" and t < burn_end and len(precent) >= 25:
                s_ad *= float(np.exp(np.mean(precent) - cfg.target_acc))
                precent = []

        if t >= burn_end and t % thin == 0:
            keep.append((X * scale).copy())
        if report and t % report == 0:
            print(f"    step {t:6d}/{n_steps} acc {acc[0]/max(acc[1],1):.3f} "
                  f"pop-acc {pacc[0]/max(pacc[1],1):.3f} ({n_pop}) "
                  f"gamma {gamma:.4f} best {lpi.max():.2f} "
                  f"chains>best-100: {int(np.sum(lpi > lpi.max()-100))}/"
                  f"{n_chains} restarts {n_restart} "
                  f"{time.time()-t0:.0f}s", flush=True)
    diag = dict(acc_chart=acc[0] / max(acc[1], 1),
                acc_pop=pacc[0] / max(pacc[1], 1), n_pop_steps=n_pop,
                n_restart=n_restart, gamma_final=float(gamma),
                s_ad_final=float(s_ad), thin=thin,
                final_lp=lpi.copy())
    return np.concatenate(keep), acc[0] / max(acc[1], 1), float(lpi.max()), diag


def warmup_ensemble(target, X0, scale, n_steps, rng, kind="stretch", a=2.0,
                    report=None):
    """Chart-free population warm-up between the L-BFGS seeds and the atlas.

    2026-09-02, protocol-v2 baseline at NL-Loo: the truth's log-posterior was
    -284 while the atlas's best chart centre was -310..-340 and no draw of
    20,000 reached the truth's density. The seed stage (L-BFGS from pilot
    points, which carry soft-EDC penalties of ~500 nats) does not find the
    posterior's basin. This runs Goodman-Weare stretch (or DE) moves over the
    whole seed population so the atlas is built where the mass is.
    Returns (X, lp) of the final population, whitened coordinates.
    """
    X = np.array(X0, float)
    n, d = X.shape
    batch = target["logpost_batch"]
    lp = np.array(batch(X * scale), dtype=float)
    bad = ~np.isfinite(lp)
    X, lp = X[~bad], lp[~bad]
    n = len(X)
    half = n // 2
    halves = (np.arange(half), np.arange(half, n))
    acc = [0, 0]
    de_gamma = 2.38 / np.sqrt(2 * d)
    t0 = time.time()
    for t in range(n_steps):
        for S1, S2 in (halves, halves[::-1]):
            n1 = len(S1)
            if kind == "stretch":
                j = S2[rng.integers(0, len(S2), n1)]
                u = rng.random(n1)
                z = ((a - 1.0) * u + 1.0) ** 2 / a
                Y = X[j] + z[:, None] * (X[S1] - X[j])
                logq = (d - 1) * np.log(z)
            else:
                aa = S2[rng.integers(0, len(S2), n1)]
                bb = S2[rng.integers(0, len(S2), n1)]
                same = aa == bb
                while same.any():
                    bb[same] = S2[rng.integers(0, len(S2), int(same.sum()))]
                    same = aa == bb
                g = np.where(rng.random(n1) < 0.9, de_gamma, 1.0)
                Y = X[S1] + g[:, None] * (X[aa] - X[bb]) + 1e-6 * rng.standard_normal((n1, d))
                logq = 0.0
            lpy = np.array(batch(Y * scale), dtype=float)
            loga = np.where(np.isfinite(lpy), lpy - lp[S1] + logq, -np.inf)
            take = np.log(rng.random(n1)) < loga
            acc[0] += int(take.sum()); acc[1] += n1
            X[S1[take]], lp[S1[take]] = Y[take], lpy[take]
        if report and t % report == 0:
            print(f"    warmup {t:5d}/{n_steps} acc {acc[0]/max(acc[1],1):.3f} "
                  f"best {lp.max():.2f} median {np.median(lp):.2f} {time.time()-t0:.0f}s",
                  flush=True)
    return X, lp
