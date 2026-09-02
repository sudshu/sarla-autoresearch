# Codex advisor, iteration 008

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S3 is the strongest surgery variant, but none qualifies for acceptance. Its \(G_{\rm dev}=1.163\) improves on the 1.717 baseline by 0.555 (32%), short of the 0.86 noise-floor threshold; it also worsens BE-Vie from 1.113 to 1.467 (+0.354), violating the +0.25 site guardrail. S1 and S2 improve by only 0.385 and 0.431 and violate the guardrail at NL-Loo (+1.369 and +0.324).

The improvement is not consistent across sites. All three variants reliably rescue DK-Sor (3.523 to 0.995–1.483) and leave DE-Gri good (0.752–0.884), but NL-Loo is highly geometry-sensitive and BE-Vie reverses under volume weighting. S3’s advantage over S2 comes mainly from lower mean cover90 penalty (0.91 versus 1.36) and rms-z penalty (0.59 versus 1.10), partly offset by worse projection penalty (1.47 versus 1.11). At BE-Vie, S3’s projection penalty reaches 2.58 because LAI coverage is only 0.116; DK-Sor GPP coverage remains only 0.512.

Density rank is the dominant unresolved failure: every S3 site has \(r=0.971\)–1.000, contributing 3.14–3.33 to the six-term score even where marginal coverage and rms-z are good. Zero stuck fractions show this is not the current chain-junk diagnostic.

There is substantial site-specific tradeoff suggestive of development-set tuning, but one seed, no B truths, and no holdouts make overfitting impossible to distinguish from stochastic variation. Runtime is acceptable: S3 is 1% faster than baseline, S2 6% faster, and S1 20% slower.

## 2. RISKS

The reported differences are single-seed results against a baseline whose threshold reflects extreme seed variance, so ranking S1–S3 is fragile. More fundamentally, v2 truths are selected from real-data posteriors rather than the fitting prior; therefore nominal 90%/50% coverage and rank 0.5 are not guaranteed calibration targets without a conditional-SBC justification. The near-universal rank saturation could consequently mix sampler failure with truth-selection mismatch. Averaging correlated coverage, rms-z, rank, and projection terms can also make one underlying basin error count several times, while capping catastrophic sites hides magnitude beyond \(G=5\).

## 3. NEXT STEPS

1. Test the most promising complement—S3 geometry plus the previously best DE sampler—to attack both basin coverage and within-basin density rank: `atlas_engine=surgery`, `sg_weight_rule=volume`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`.

2. Confirm that candidate and S3 with two additional stochastic replicates before any further tuning, then score the winner on dev-B: keep all knobs fixed except `kernel_seed=11` and `kernel_seed=17`.

3. Test whether excessive branching caused the 27-branch, ESS 0.0002 atlas by changing only `sg_branch_tau=20` under `atlas_engine=surgery`, `sg_weight_rule=volume`.

4. Spend more of the fixed budget on detecting missing atlas mass while preserving approximately the evaluation total: `n_audit=16384`, `sg_stop_ess=0.3`, `n_chains=128`, `n_steps=15424`, `atlas_engine=surgery`, `sg_weight_rule=volume`.

## 4. STOP/CONTINUE

Continue the surgery family, specifically volume weighting and surgery-plus-DE. Abandon S1 default surgery and S2 no-projection as standalone promotion candidates; do not yet abandon normal projection globally because its effect reverses between NL-Loo and DK-Sor.
