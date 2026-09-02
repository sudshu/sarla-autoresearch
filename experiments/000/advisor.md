# Codex advisor, iteration 000

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

This iteration establishes the baseline; no calibration-gap term “moved” because no candidate was tested. The decision threshold is now relatively demanding: \(\delta=0.219\), so a replacement must reach \(G_{\rm dev}<0.971\), with no site worsening by more than 0.25.

Performance is sharply site-dependent. ES-LJu, DE-Gri, and NL-Loo are moderate at 0.597, 0.776, and 0.794, whereas BE-Vie is 2.591 and contributes 54% of the summed development gap. BE-Vie fails broadly rather than through stuck chains: cover90=0.629, cover50=0.281, rank=0.802, rms_z=3.80, and LAI projection coverage=0.105. Across all sites, stuck_frac=0, indicating that the remaining problem is posterior geometry, mode weighting, or insufficient exploration—not obvious junk-chain trapping.

Kernel-seed sensitivity is material: site ranges are 0.453–0.816 (ES-LJu), 0.553–1.118 (NL-Loo), 0.656–0.863 (DE-Gri), and 2.189–2.911 (BE-Vie). Thus a candidate near the threshold could win through seed luck, particularly by improving one difficult site.

Holdout \(G=2.005\) is substantially worse than development, but DK-Sor alone scores 4.182; excluding flagged DK-Sor gives 1.279, only 0.089 above development. There is therefore no evidence yet of sampler overfitting to development sites or one truth—only a baseline split difference. Development-B remains essential before interpreting any apparent breakthrough.

## 2. RISKS

The acceptance metric averages six terms, allowing major projection or standardized-bias failure to be diluted by the uniformly perfect stuck term. Single-seed holdout scores are not directly comparable in precision with three-seed development scores. Aggregate pooled diagnostics and mean per-seed \(G_s\) are nonlinear summaries and need not reconcile, so proposal diagnosis should use seed-level terms where possible. Finally, the fixed evaluation budget does not equal fixed effective sampling: 512×4k may improve mode coverage while shortening each trajectory enough to damage within-mode mixing.

## 3. NEXT STEPS

1. Test H1 first with `n_chains=256`, `n_steps=8000`, then `n_chains=512`, `n_steps=4000`; this directly tests whether start diversity reduces BE-Vie’s broad undercoverage without immediately sacrificing as much trajectory length.

2. **[NEW CODE]** Test H2 with `kernel=chart_de`, `mix=0.5`, `n_chains=512`, `n_steps=4000`, and tune `de_gamma` around the standard dimension-scaled value; ensemble difference moves have the best chance of crossing curved valleys and correcting mode weights.

3. Test H9 using `start_policy=seeds` while retaining `kernel=chart_rwm`, `n_chains=64`, and `n_steps=32000`; this isolates initialization/mode representation from kernel effects before combining it with H1 or H2.

4. Test H5 at `flat_mult=3.0`, followed by `flat_mult=2.0` if acceptance collapses; inflated flat directions specifically target severe rms_z and interval undercoverage at BE-Vie.

5. Run any apparent winner on development truth B before promotion, changing only `kernel_seed` across three seeds; require improvement outside BE-Vie as evidence against single-site or single-truth selection.

## 4. STOP/CONTINUE

Continue the walker-diversity, ensemble-move, and start-policy families. Do not pursue H6 yet: `stuck_frac=0` at every site provides no evidence that more aggressive restarts address the observed failure.
