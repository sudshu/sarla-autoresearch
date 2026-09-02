"""Site-generic forward model for OSSE generation and scoring.

`nlloo_science_compare` binds its forward run to the NL-Loo CBF at import
time; anything multi-site must build the forward closure per CBF. This module
does only that: parameters (z-space, the sampler's coordinates) -> the
observation-operator series the likelihood compares against.
"""
import os
import sys

import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(_here, "..", "CARDAMOM", "PYTHON", "dalec_jax", "src"),
             os.path.join(_here, "dalec_jax_src")):
    if os.path.isdir(cand):
        sys.path.insert(0, cand)

import jax
import jax.numpy as jnp

from dalec_jax.inference.target import build_logpost
from dalec_jax.model.dalec_1100 import run_dalec_1100, prederive_vegk
from dalec_jax.indices import F, S, PARMIN, PARMAX

STREAMS = ("GPP", "NBE", "ET", "LAI", "ABGB")
D = 89
SCALE = np.full(D, np.pi / np.sqrt(3.0))


def z_to_p(Z):
    u = jax.nn.sigmoid(jnp.asarray(Z))
    return jnp.asarray(PARMIN) * jnp.exp(u * jnp.log(jnp.asarray(PARMAX) / jnp.asarray(PARMIN)))


def make_forward(cbf_path):
    """Return dict(cbf, T, predict(Z, chunk) -> {stream: (n, T)})."""
    _, cbf = build_logpost(cbf_path, gate="none")
    VegK = prederive_vegk(cbf.met["DOY"], cbf.LAT)
    runb = jax.jit(jax.vmap(lambda p: run_dalec_1100(p, cbf.met, cbf.LAT,
                                                     cbf.deltat, VegK)))

    def predict(Z, chunk=100):
        out = []
        for i in range(0, len(Z), chunk):
            pools, fluxes = runb(z_to_p(np.asarray(Z[i:i + chunk], float)))
            pools, fluxes = np.asarray(pools), np.asarray(fluxes)
            mid = lambda k: (pools[:, :-1, k] + pools[:, 1:, k]) * 0.5
            out.append(dict(
                GPP=fluxes[:, :, F.gpp],
                NBE=(-fluxes[:, :, F.gpp] + fluxes[:, :, F.resp_auto]
                     + fluxes[:, :, F.rh_co2] + fluxes[:, :, F.f_total]),
                ET=fluxes[:, :, F.ets],
                LAI=mid(S.D_LAI),
                ABGB=mid(S.C_lab) + mid(S.C_fol) + mid(S.C_roo) + mid(S.C_woo),
                # per-draw scalars for mode bookkeeping (2026-09-01: NL-Loo's
                # real posterior has an 82% high-wood-allocation mode the
                # fast path misses): allocation fraction to wood = flux 6 / NPP
                f_wood=(fluxes[:, :, 6].mean(1)
                        / np.maximum((fluxes[:, :, F.gpp] - fluxes[:, :, F.resp_auto]).mean(1), 1e-9))))
        return {k: np.concatenate([o[k] for o in out]) for k in out[0]}

    return dict(cbf=cbf, T=int(cbf.n_timesteps), predict=predict)


def make_lp(cbf_path, gate):
    lp, _ = build_logpost(cbf_path, gate=gate)
    vl = jax.jit(jax.vmap(lp))

    def batch(Z, chunk=1024):
        Z = np.atleast_2d(np.asarray(Z, float))
        return np.concatenate([np.asarray(vl(jnp.asarray(Z[i:i + chunk])))
                               for i in range(0, len(Z), chunk)])
    return batch
