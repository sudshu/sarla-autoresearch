# Codex advisor, iteration 027

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

This is encouraging but incomplete: only NL-Loo and DK-Sor were scored, with one kernel seed, so `G_dev=1.02` is not a protocol-valid development aggregate.

Relative to 16-rung likelihood-only tempering, full-posterior tempering improved both tested sites: NL-Loo 0.960→0.748 (−0.211) and DK-Sor 1.456→1.295 (−0.161). Relative to baseline, the reductions are much larger: −0.668 and −2.228, respectively. Thus the benefit is not confined to one site.

At NL-Loo, parameter coverage is good (`c90=0.888`, `c50=0.539`, `rms_z=0.948`) and no chains are stuck. However, density rank remains 0.946, contributing 0.495 of the total 0.748 gap, while all four projections have 100% coverage and therefore contribute another 0.167 through overcoverage. The sampler reaches the truth’s density but still underweights its high-allocation mode (0.39 versus truth-associated 0.64).

DK-Sor remains less calibrated: `c90=0.787`, `c50=0.393`, `rms_z=1.387`, and rank 0.960. Rank contributes 0.511 to G, projection miscalibration 0.288, and parameter undercoverage another 0.367; projection coverage is especially weak for two streams (0.524 and 0.786). Its high-mode mass is also low (0.09 versus 0.29).

Wall time is 2,040 s, 0.67× baseline: comfortably within the promotion guard but not the ≤0.5× speed path. There is substantial risk of development-site and single-truth optimization because these are precisely the two sites that motivated tempering; no BE-Vie, DE-Gri, B-truth, real-data, or holdout result is available.

## 2. RISKS

The uncapped two-site mean and absent `sd_dev`/`delta` can look promotion-ready despite being only a screen. G also obscures opposing errors: NL-Loo’s excellent marginal coverage coexists with a severely biased mode weight, while its projections are uniformly too wide. Good adjacent-swap acceptance does not establish temperature round trips or correct cold-chain occupancy. Finally, flattening soft EDC penalties is valid only if the cold rung exactly retains the intended posterior; that implementation should be numerically audited.

## 3. NEXT STEPS

1. Complete the preregistered four-site, three-seed confirmation and mode-weight gate before tuning further; vary only `kernel_seed`, then run dev-B, holdouts, and real NL-Loo if it qualifies.

2. Test full-posterior tempering with `de_gamma=0.12` and `de_gamma=0.25`, holding `kernel=chart_de`, `n_chains`, and `n_steps` fixed, because the remaining failure is mode weighting rather than failure to reach truth-level density.

3. Test stronger burn-in redistribution with `restart_gap=50`, `restart_every=250`, and `restart_until=0.5`, retaining `start_policy=balanced`, and judge primarily by NL-Loo/DK-Sor mode-fraction SD rather than mean G.

4. **[NEW CODE]** Record replica round trips and high/low-mode transitions by temperature for the unchanged `kernel=chart_de` variant, since swap acceptance alone cannot distinguish genuine mode transport from local exchanges.

## 4. STOP/CONTINUE

Abandon likelihood-only tempering T1: working ladders and 2× budget failed to equilibrate modes. Continue T2 full-posterior tempering through confirmation, but abandon it if three-seed mode-weight SD exceeds 0.10 or the full four-site result loses the current two-site advantage.
