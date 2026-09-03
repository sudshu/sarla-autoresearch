# Codex advisor, iteration 030

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

This is an incomplete two-site diagnostic, not a promotable development result: `n_dev=2`, whereas the protocol requires at least three sites and requeueing once.

At NL-Loo, mean G=1.17 hides severe seed sensitivity (0.68/1.17/1.66; sample SD≈0.49). The main gaps are parameter undercoverage (`cover90=0.697`, term 2.03; `cover50=0.337`, term 1.63) and excess standardized error (`rms_z=1.65`, term 1.31); projection coverage is uniformly 1.0, hence also over-wide relative to the 0.90 target.

DK-Sor is more seed-consistent (G=1.08–1.36; SD≈0.14), but its density rank is 0.952, producing the dominant term of 3.01: draws remain systematically below the truth’s posterior density. Projection calibration is also poor (term 1.55), driven by one stream at only 0.512 coverage, despite two streams covering 100%.

Relative to DE128, DE64 is essentially unchanged at NL-Loo (1.17 versus 1.16) and better at DK-Sor (1.21 versus 1.39), but it is worse than stretch128 across these two sites overall. Neither stuck chains nor insufficient nominal trajectory length explains the remaining gap. The 4,770-second median is 1.56× the 3,060-second baseline, narrowly violating the 1.5× wall-clock guard.

There is strong risk of site/seed selection: only two development sites, one truth realization, no B truths, and NL-Loo’s nearly one-point seed range prevents any claim of stabilized mode weights.

## 2. RISKS

Averaging terms conceals qualitatively opposite failures: NL-Loo intervals are too narrow while its projections are too broad, whereas DK-Sor is chiefly a typical-set/mode-weight failure. `G_dev_per_seed` and `sd_dev` are absent, so the two-sample acceptance test cannot be applied. Comparing pooled per-site metrics can also hide correlated good or bad kernel seeds. Finally, optimizing G without reporting high-allocation fractions here would bypass the explicit mode-weight gate.

## 3. NEXT STEPS

1. Complete the promising T2 confirmation on all four development sites with three fresh `kernel_seed` values while holding `n_chains`, `n_steps`, and `burn_frac` fixed; full-posterior tempering is the only recent method that reached the NL-Loo truth-density region.

2. Test persistent burn-in restarts with `restart_gap=50`, `restart_every=250`, and `restart_until=0.5`, using `kernel=chart_de`, `n_chains=128`, and `n_steps=16000`; this directly reallocates chains that remain tens of nats below the competitive basin.

3. **[NEW CODE]** Implement S17’s held-out audit-loss repair selection, initially retaining `atlas_rounds=6` and `n_audit=4096`; operation heuristics repeatedly leave ESS near 0.0002 despite extensive tuning.

4. If T2 passes three seeds but remains biased toward the low-allocation mode, test a mode-stratified cold population with `start_policy=balanced`, `n_chains=128`, and `n_steps=16000` **[NEW CODE for preserving per-mode allocation]**; success must be judged primarily by the mode-weight SD gate and real NL-Loo fraction.

## 4. STOP/CONTINUE

Abandon chain-count redistribution H1/H13/H14: 512, 256, 128, and 64-chain configurations have not stabilized mode weights, and H14 is slower than allowed. Also stop incremental surgery-rule variants; continue atlas work only through the qualitatively different S17 objective, and continue T2 pending full confirmation.
