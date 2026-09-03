# Codex advisor, iteration 019

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

`t1_pt6_de` reduced development G from 1.717 to 0.977, a 0.741-point/43% improvement, while taking 2,760 s versus 3,060 s (10% faster). Site changes were NL-Loo −0.502, BE-Vie −0.437, DE-Gri −0.004, and DK-Sor −2.020; thus the gain is broad enough to avoid a site-worsening concern, but 68% of the summed improvement comes from DK-Sor.

The mean term contributions were: rank 2.57, projection 1.02, cover90 0.83, cover50 0.76, rms-z 0.48, and stuck 0.21. Rank therefore contributes 44% of G’s numerator and remains the central failure: ranks are 0.994 at NL-Loo and 1.000 at DK-Sor. DK-Sor is consistently weakest, with poor 90%/50% coverage (0.775/0.371), rms-z 1.50, and one projection stream covering only 0.50. DE-Gri is essentially unchanged from baseline and still has rank 0.888 plus 4.2% stuck chains.

This is not better than the simpler four-rung result (G 0.978), and the working 16-rung ladder was worse on the two tested sites. High-mode mass remains deficient at NL-Loo (0.30) and BE-Vie (0.23). Exact term-by-term movement versus baseline cannot be determined because baseline term vectors were not supplied.

There is no evidence yet about holdout or truth-B generalization; one kernel seed also prevents evaluating the mode-weight gate. Repeated development-site selection makes dev overfitting plausible, while good interval coverage for one truth can coexist with badly wrong posterior mode weights.

## 2. RISKS

Only 24 walkers occupy each rung, making stuck fractions coarse in increments of 0.0417 and leaving relatively few cold-posterior trajectories. Most of the fixed evaluation budget is spent away from the target distribution, so acceptable aggregate G can mask low cold-rung effective sample size. The one-sided rms-z term gives NL-Loo zero penalty at 0.965, while its near-unit density rank clearly says the sampled posterior is too low-density. The 3–18% swap range also implies a ladder bottleneck despite a reasonable average-looking G. Wall time passes the ordinary guard but is far from the speed path’s ≤1,530 s threshold.

## 3. NEXT STEPS

1. Test the corrected surgery topology with the strongest kernel over three seeds, because it directly targets false branches while S4 already achieved G 0.964: `atlas_engine="surgery"`, `sg_connectivity_rule="feasible_path"`, `sg_path_tries=8`, `sg_path_jitter=0.05`, `atlas_rounds=10`, `sg_flag_topk=16`, `kernel="chart_de"`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, varied `kernel_seed`.

2. **[NEW CODE]** Temper the finite full posterior—including soft EDC penalties but retaining the hard feasibility gate—because likelihood-only tempering leaves the dominant barrier intact: `kernel="pt_de_full"`, `pt_rungs=8`, `pt_beta_min=0.05`, `pt_swap_every=5`, `start_policy="balanced"`, `n_chains=128`, `n_steps=16000`.

3. Combine feasible-path surgery with pooled-covariance moves to test mode-weight stability without DE’s seed-sensitive cross-mode jumps: `atlas_engine="surgery"`, `sg_connectivity_rule="feasible_path"`, `kernel="chart_adaptcov"`, `mix=0.5`, `adapt_start=0.25`, `adapt_every=200`, `n_chains=128`, `n_steps=16000`.

4. Apply tighter burn-in rescue to the best configuration, targeting the observed stuck chains cheaply: `restart_gap=50`, `restart_every=250`, `restart_until=0.5`.

## 4. STOP/CONTINUE

Abandon the T1 likelihood-only tempering family: four and six rungs fail to exchange adequately, while 16 rungs exchange but starve each walker and do not improve G or mode recovery. Treat full-posterior tempering as a distinct, single falsification test; continue feasible-path surgery.
