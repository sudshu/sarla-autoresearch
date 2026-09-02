# Codex advisor, iteration 004

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

This is the first valid v3 baseline, so no calibration term can be claimed to have improved relative to earlier runs; protocol-v1 comparisons are invalid. Capped \(G_{\rm dev}=1.717\), but performance is strongly site-dependent: DE-Gri 0.817 and BE-Vie 1.113 are adequate, NL-Loo is worse at 1.416, and DK-Sor dominates at 3.523 capped-site aggregation (raw seed mean 6.532).

The failure pattern is basin miss rather than ordinary chain sticking. NL-Loo and DK-Sor have rank 1.0, severe projection undercoverage, and zero `stuck_frac`: all chains can agree with each other while occupying the wrong basin. DK-Sor is catastrophic—cover90 0.034, cover50 0, rms_z 31.49—and highly seed-sensitive (raw G 14.03, 2.59, 2.98). NL-Loo is moderately seed-sensitive (1.66, 0.94, 1.66); BE-Vie and DE-Gri are comparatively consistent.

CZ-wet’s single holdout result is also catastrophic (raw G 5.186): cover90 0.225, rms_z 6.54, and rank 1.0. Thus there is no evidence of development-site overfitting yet—there is no candidate change—but clear evidence that baseline failure generalizes beyond development sites. No conclusion about truth-realisation overfitting is possible without dev-B results.

## 2. RISKS

The reported `terms` are not seed averages: their means reproduce the first seed’s G (e.g. DK-Sor 14.025), while `per_site.G` averages three seeds. Term-level interpretation is therefore confounded with kernel seed and should be aggregated per seed before decisions.

Capping prevents DK-Sor from overwhelming selection, but hides enormous changes: reducing raw G from 14 to 5 produces no capped benefit. Conversely, delta 0.859 remains so large that meaningful multi-site gains may not qualify.

`stuck_frac` only detects chains worse than the run’s best chain; it cannot detect population-wide convergence to the same wrong basin. Holdout evidence is only one site and one seed, and wall time is 3,060 seconds—about 51 minutes, materially slower than the stated ~30-minute target.

## 3. NEXT STEPS

1. **[NEW CODE]** Test topology-aware atlas repair first because three sites show shared-basin failure rather than within-basin mixing failure: `atlas_engine="surgery"`.

2. Test seed-distributed initialization because NL-Loo’s known mode inversion and strong seed effect make broader basin coverage the cheapest direct intervention: `start_policy="seeds"`.

3. **[NEW CODE]** Give extended ridges proposal mass proportional to their tangent volume, which should reduce systematic omission of broad basins: `atlas_engine="surgery"`, `sg_weight_rule="volume"`.

4. Test more aggressive discovery during burn-in because zero relative stuckness does not imply the correct region was found: `restart_gap=50`, `restart_every=250`, `restart_until=0.5`.

5. If basic surgery fires useful repairs, increase repair capacity in a pre-registered follow-up: `atlas_engine="surgery"`, `sg_flag_topk=16`, `atlas_rounds=10`.

## 4. STOP/CONTINUE

Continue the atlas-coverage and initialization families. Abandon pure walker-count inflation as a primary strategy, and pause local-kernel tuning (DE/stretch/adaptive covariance) until a valid-v3 experiment demonstrates that the correct basin is already represented; local mixing cannot repair a missing basin.
