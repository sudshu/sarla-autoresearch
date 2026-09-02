"""Box problems for the topology-aware atlas (sarla2) vs the v1 engine.

  A  curved ridge (banana), one seed at the mode      -> extend / refine
  B  hidden second mode, one seed at the left mode    -> branch
  C  flat ridge turning into a tight bump, one seed
     on the ridge                                     -> rank-change
  D  8-D Gaussian with 20 jittered seeds              -> merge

For each: grid KL(pi || q) before/after, round-by-round surgery trace, target
evaluations, and exactness of the final independence-MH draws (posterior
means/sds against the grid truth in 2-D, against the analytic values in D).
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jax
import jax.numpy as jnp
jax.config.update("jax_enable_x64", True)

import sarla as S1
import sarla2 as S2

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "sarla")
os.makedirs(OUT, exist_ok=True)


def make_target(logpi_jax, d):
    lp_b = jax.jit(jax.vmap(logpi_jax))
    g = jax.jit(jax.grad(lambda z: -logpi_jax(z)))
    H = jax.jit(jax.hessian(lambda z: -logpi_jax(z)))
    n = [0]

    def batch(Z):
        Z = np.atleast_2d(Z); n[0] += len(Z)
        return np.asarray(lp_b(jnp.asarray(Z)))
    return dict(logpost_batch=batch, grad=lambda z: np.asarray(g(jnp.asarray(z))),
                hess=lambda z: np.asarray(H(jnp.asarray(z))), scale=np.ones(d)), n


def grid_stats(logpi, lim=8.0, n=401, atlas=None):
    xs = np.linspace(-lim, lim, n)
    X, Y = np.meshgrid(xs, xs)
    P = np.stack([X.ravel(), Y.ravel()], 1)
    lp = np.asarray(jax.vmap(logpi)(jnp.asarray(P)))
    p = np.exp(lp - lp.max()); p /= p.sum()
    mean = (p[:, None] * P).sum(0); sd = np.sqrt((p[:, None] * (P - mean) ** 2).sum(0))
    kl = None
    if atlas is not None:
        lq = atlas.logq(P / atlas.scale)
        q = np.exp(lq - lq.max()); q /= q.sum()
        m = p > 1e-300
        kl = float(np.sum(p[m] * (np.log(p[m]) - np.log(np.maximum(q[m], 1e-300)))))
    return dict(mean=mean, sd=sd, kl=kl)


def run_case(name, logpi, d, seeds, cfg2, rounds=8, n_audit=4096, lim=8.0):
    res = {}
    for eng in ("v1", "v2"):
        t, n = make_target(logpi, d)
        t0 = time.time()
        if eng == "v1":
            atlas = S1.sarla(t, seeds, rounds=rounds, n_audit=n_audit, seed=3, verbose=False)
            labels = [x[1] for x in atlas.diagnoses]
            trace = [f"round {h['round']}: K={h['K']} ESS={h['ess']:.3f} flags={h['nflags']}" for h in atlas.history]
            prod = S1.production_imh(atlas, t, n_steps=3000, n_chains=32, seed=7)
        else:
            cfg2.rounds, cfg2.n_audit = rounds, n_audit
            atlas = S2.sarla2(t, seeds, cfg2, seed=3, verbose=False)
            labels = [x[1] for x in atlas.ops_log if x[1] not in ("duplicate", "infeasible")]
            trace = S2.history_table(atlas).splitlines()
            prod = S2.production_imh(atlas, t, n_steps=3000, n_chains=32, seed=7)
        n_atlas = n[0]
        draws = prod["draws_z"][1000:].reshape(-1, d)
        if d == 2:
            gs = grid_stats(logpi, lim=lim, atlas=atlas)
            err_mean = float(np.max(np.abs(draws.mean(0) - gs["mean"]) / gs["sd"]))
            err_sd = float(np.max(np.abs(draws.std(0) / gs["sd"] - 1)))
            kl = gs["kl"]
        else:
            err_mean = float(np.max(np.abs(draws.mean(0)) / 1.0)); err_sd = float(np.max(np.abs(draws.std(0) - 1.0)))
            kl = None
        extra = {}
        if name == "B":
            extra["right_mass"] = float(np.mean(draws[:, 0] > 0))
        res[eng] = dict(K=len(atlas.charts), ranks=sorted(c.rank for c in atlas.charts), kl=kl,
                        n_eval_atlas=n_atlas, acc=prod["accept"], err_mean_sd=err_mean, err_sd_rel=err_sd,
                        labels=labels, trace=trace, wall=time.time() - t0, **extra)
        if eng == "v2":
            res[eng]["branches"] = len({c.branch for c in atlas.charts})
    print(f"\n=== {name} ===")
    for eng, r in res.items():
        print(f"{eng}: K={r['K']} ranks={r['ranks']} KL={r['kl'] if r['kl'] is None else round(r['kl'],3)} "
              f"atlas evals={r['n_eval_atlas']} IMH acc={r['acc']:.2f} max|mean err|/sd={r['err_mean_sd']:.2f} "
              f"max sd rel err={r['err_sd_rel']:.2f} {('right-mode mass %.2f' % r['right_mass']) if 'right_mass' in r else ''} "
              f"{('branches=%d' % r['branches']) if 'branches' in r else ''} ({r['wall']:.0f}s)")
        print("   ops:", labels_summary(r["labels"]))
        for l in r["trace"]:
            print("   ", l)
    return res


def labels_summary(labels):
    from collections import Counter
    return dict(Counter(labels))


B_, SX, SN = 0.35, 2.5, 0.35
def logpi_banana(z):
    return -0.5 * ((z[0] / SX) ** 2 + ((z[1] - B_ * z[0] ** 2 + 1.5) / SN) ** 2)

S2_ = 0.35
def logpi_bimodal(z):
    l1 = -0.5 * ((z[0] + 4) ** 2 + z[1] ** 2) / S2_ ** 2
    l2 = -0.5 * ((z[0] - 4) ** 2 + z[1] ** 2) / S2_ ** 2
    return jnp.logaddexp(l1, l2) - jnp.log(2.0) - jnp.log(2 * jnp.pi * S2_ ** 2)

def logpi_rankchange(z):
    # flat ridge along x for x<0 (sd 3), tight bump for x>0 (sd 0.3); y stiff
    sx = jnp.where(z[0] < 0, 3.0, 0.3)
    return -0.5 * (z[0] / sx) ** 2 - 0.5 * (z[1] / 0.3) ** 2

def logpi_gauss8(z):
    return -0.5 * jnp.sum(z ** 2)


if __name__ == "__main__":
    cfg = S2.SurgeryConfig()
    results = {}
    results["A"] = run_case("A", logpi_banana, 2, np.array([[0.0, -1.5]]), S2.SurgeryConfig())
    results["B"] = run_case("B", logpi_bimodal, 2, np.array([[-4.0, 0.0]]), S2.SurgeryConfig(), n_audit=16384)
    results["C"] = run_case("C", logpi_rankchange, 2, np.array([[-2.0, 0.0]]), S2.SurgeryConfig())
    results["C2"] = run_case("C2", logpi_rankchange, 2, np.array([[0.5, 0.0]]), S2.SurgeryConfig())
    rng = np.random.default_rng(0)
    results["D"] = run_case("D", logpi_gauss8, 8, 0.3 * rng.standard_normal((20, 8)), S2.SurgeryConfig())
    json.dump(results, open(os.path.join(OUT, "sarla2_toys.json"), "w"), indent=1, default=str)
    print(f"\nwrote {OUT}/sarla2_toys.json")
