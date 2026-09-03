# Codex advisor, iteration 010

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S4 is the strongest screen so far: \(G_{\rm dev}=0.919\), improving 0.799 over the 1.717 baseline at only 1.07× wall-clock. Scores are unusually consistent across sites (0.80–1.06), and no site is currently near the cap. However, 77% of the aggregate improvement comes from DK-Sor (3.52→1.06); NL-Loo improves 1.42→0.97, BE-Vie 1.11→0.80, while DE-Gri is essentially unchanged/slightly worse (0.817→0.847).

Relative to S5, S4’s 0.089 advantage comes mainly from better mean rank error (1.90 versus 2.51) and 90% coverage error (0.80 versus 0.97), partly offset by worse projection error (1.29 versus 1.08) and RMS-z error (0.62 versus 0.54). Thus lowering the branch threshold from S5’s restrictive setting chiefly helps typical-set access, not predictive calibration.

Residual failures remain structured: S4 density ranks are high at DE-Gri (0.885) and DK-Sor (0.951), NL-Loo has only 74.2% parameter coverage at 90%, and every site undercovers at 50%. Projection weaknesses differ by site—BE-Vie NBE/ET, DE-Gri ET, and DK-Sor GPP—arguing against overfitting solely to one flux pattern. Nevertheless, this is one kernel seed, one truth per site, with no holdout or mode-weight evidence, so it is only a promising screen.

## 2. RISKS

The single-seed candidate is being compared with a three-seed baseline; the apparent no-worsening guard and 0.799 gain are not yet valid promotion statistics. Zero `stuck_frac` is weak reassurance because all chains may coherently occupy the wrong basin. The capped mean still lets DK-Sor dominate the improvement below the cap. Most importantly, neither required high-allocation mode-fraction stability nor the real-data NL-Loo comparison is reported; good marginal coverage can conceal incorrect mode weights. Repeated selection on the four development A truths also creates substantial dev/truth-A overfitting risk.

## 3. NEXT STEPS

1. **Confirm S4 exactly over three fresh seeds**, because it has the best and most site-balanced screen: `atlas_engine=surgery`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `sg_flag_topk=16`, `atlas_rounds=10`, varying only `kernel_seed`.

2. **If confirmed, run the mandated milestone immediately**, because DK-Sor supplies 77% of the gain: keep the S4 knobs and score all holdouts, dev-B truths, and real NL-Loo before further tuning.

3. **Combine S4 with volume weighting**, since S3 independently reached 1.16 and may improve ridge allocation: set `sg_weight_rule=volume` on the full S4 configuration and screen one seed before confirmation.

4. **Tune the DE scale for rank calibration**, targeting the persistent high ranks at DE-Gri/DK-Sor: run matched variants with `de_gamma=0.12` and `de_gamma=0.25`.

5. **Test more ensemble diversity without the failed 512-walker extreme**, which may stabilize mode fractions: set `n_chains=256`, `n_steps=8000` while retaining `kernel=chart_de` and `mix=0.5`.

## 4. STOP/CONTINUE

Continue S4/surgery-plus-DE through confirmation. Abandon the `sg_branch_tau=100` branch-suppression variant: it loses at three of four sites and sharply worsens rank calibration. Pause standalone surgery and further broad kernel-family exploration until S4’s mode-weight gate and milestone results are known.
