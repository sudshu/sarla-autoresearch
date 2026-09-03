# Codex advisor, iteration 012

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

The strongest confirmed result is `s3_surgery_volume`: \(G_{\rm dev}=1.131\pm0.043\), 0.587 below the 1.717 baseline, with a counterfactual v4 threshold of \(2SE=0.498\) (`v4_t=2.35`). Runtime is effectively unchanged (3,030 versus 3,060 s), and no site violates the +0.25 guard: changes versus baseline are +0.069 NL-Loo, +0.157 BE-Vie, −0.029 DE-Gri, and −2.544 DK-Sor. Thus most aggregate improvement comes from rescuing DK-Sor, not uniform gains.

Volume weighting is seed-stable in aggregate, but less so per site: BE-Vie spans 1.15–1.47 and DK-Sor 0.81–1.13. All chains avoid junk regions (`stuck_frac=0`), yet density rank remains near 1 at every site (rank penalties 3.14–3.33), showing persistent typical-set or mode-weight failure. NL-Loo remains under-dispersed (`c90=0.708`, `c50=0.337`); projection failures are concentrated in BE-Vie LAI (coverage 0.116) and DK-Sor GPP (0.512).

Adding DE to volume-weighted surgery (`s7`) improves NL-Loo to 0.852 and moves its rank to 0.420, but it is only one seed and worsens DK-Sor to 1.336. The earlier uniform-weight surgery+DE result remains the best screen at 0.919.

## 2. RISKS

Iteration 12 was governed by v3, so the displayed v4 pass cannot retroactively promote `s3`. More importantly, neither holdouts, development-B truths, nor the required high-mode-fraction statistics are reported; apparent success could be specific to four A truths or incorrect mode weights. The low aggregate SD masks compensating site-level variability, while capped aggregation conceals how catastrophic DK-Sor originally was. Baseline term-level scores are unavailable, preventing a clean attribution of improvement by metric component.

## 3. NEXT STEPS

1. Confirm S4 on three fresh seeds with `atlas_engine=surgery`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `sg_flag_topk=16`, and `atlas_rounds=10`, because its 0.919 screen is the best balanced four-site result; report both mode-weight gates and real-data NL-Loo.

2. Re-test the simpler DE candidate under v4 using `kernel=chart_de`, `mix=0.5`, `n_chains=128`, and `n_steps=16000`, because its prior \(1.05\pm0.09\) result may deliver most of the gain without fragile surgery geometry.

3. Tune S4 with `de_gamma=0.12` and `de_gamma=0.25` in paired single-seed screens, because the remaining near-one ranks indicate that cross-mode transition scale—not marginal coverage—is now the dominant defect.

4. Test greater ensemble diversity with `n_chains=256`, `n_steps=8000`, `kernel=chart_de`, and `mix=0.5`, because mode-weight stability may benefit even though the more extreme 512-chain variants failed.

5. **[NEW CODE]** Implement likelihood tempering around `kernel=chart_de`, retaining balanced starts, because ordinary surgery repeatedly leaves NL-Loo/DK-Sor ranks near one and may be unable to cross the allocation-mode barrier.

## 4. STOP/CONTINUE

Abandon standalone surgery and further rank/branch-threshold micro-tuning: its diagnostics remain pathological and its gains are DK-Sor-dominated. Continue only the surgery+DE combination through its preregistered confirmation; abandon it too if S4 fails the mode-weight or holdout gates.
