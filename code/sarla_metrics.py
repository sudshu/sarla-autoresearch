"""OSSE recovery metrics and the pre-registered calibration gap.

Copied from scripts/osse_score.py (param_scores, traj_scores) so the
multi-site scorer does not import the NL-Loo-bound modules. The gap G is the
protocol's single number per site (autoresearch/autoresearch.md):

  G_s = mean( |c90-0.90|/0.10, |c50-0.50|/0.10, |r-0.5|/0.15,
              max(0, rms_z-1)/0.5, mean_streams |p90_s-0.90|/0.10,
              stuck_frac/0.10 )

Each term is a distance from its target in units of roughly its binomial
noise floor over 89 parameters (sd(cover90) = 0.032, sd(cover50) = 0.053).
"""
import numpy as np
from scipy.stats import kstest

D = 89
SCALE = np.full(D, np.pi / np.sqrt(3.0))
GAP_STREAMS = ("GPP", "NBE", "ET", "LAI")


def param_scores(Z, zt):
    mu, sd = Z.mean(0), Z.std(0)
    zs = (zt - mu) / sd
    pit = (Z < zt).mean(0)
    q = np.percentile(Z, [5, 25, 75, 95], axis=0)
    ks = kstest(pit, "uniform")
    return dict(zscore=zs, pit=pit,
                cover90=float(((zt >= q[0]) & (zt <= q[3])).mean()),
                cover50=float(((zt >= q[1]) & (zt <= q[2])).mean()),
                rms_z=float(np.sqrt(np.mean(zs ** 2))),
                n_gt2=int((np.abs(zs) > 2).sum()),
                n_gt3=int((np.abs(zs) > 3).sum()),
                med_err_prior_sd=float(np.sqrt(np.mean(
                    ((np.median(Z, 0) - zt) / SCALE) ** 2))),
                shrink=float(np.median(sd / SCALE)),
                ks_stat=float(ks.statistic), ks_p=float(ks.pvalue))


def traj_scores(pred, truth, idx):
    """Draws with a non-finite trajectory in the window are dropped (n_bad)."""
    if len(idx) == 0:
        return None
    P, t = pred[:, idx], truth[idx]
    good = np.all(np.isfinite(P), axis=1)
    n_bad = int((~good).sum())
    P = P[good]
    if len(P) < 10:
        return dict(n=int(len(idx)), n_bad=n_bad, rmse=np.nan, bias=np.nan,
                    r=np.nan, cover90=np.nan, width=np.nan, rms_stderr=np.nan)
    med, mu, sd = np.median(P, 0), P.mean(0), P.std(0)
    lo, hi = np.percentile(P, [5, 95], axis=0)
    r = np.corrcoef(med, t)[0, 1] if len(t) > 2 and np.std(t) > 0 else np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        se = (t - mu) / sd
    return dict(n=int(len(idx)), n_bad=n_bad,
                rmse=float(np.sqrt(np.mean((med - t) ** 2))),
                bias=float(np.mean(med - t)), r=float(r),
                cover90=float(np.mean((t >= lo) & (t <= hi))),
                width=float(np.mean(hi - lo)),
                rms_stderr=float(np.sqrt(np.nanmean(se ** 2))))


def calibration_gap(c90, c50, r, rms_z, proj_cover90, stuck_frac):
    """Protocol gap and its six terms. proj_cover90: dict stream -> cover90."""
    p = [proj_cover90[k] for k in GAP_STREAMS if k in proj_cover90
         and np.isfinite(proj_cover90[k])]
    terms = dict(
        cover90=abs(c90 - 0.90) / 0.10,
        cover50=abs(c50 - 0.50) / 0.10,
        rank=abs(r - 0.5) / 0.15,
        rms_z=max(0.0, rms_z - 1.0) / 0.5,
        proj=float(np.mean([abs(x - 0.90) / 0.10 for x in p])) if p else np.nan,
        stuck=stuck_frac / 0.10)
    vals = [v for v in terms.values() if np.isfinite(v)]
    return float(np.mean(vals)), {k: float(v) for k, v in terms.items()}
