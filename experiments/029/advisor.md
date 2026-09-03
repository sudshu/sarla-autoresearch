# Codex advisor, iteration 029

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S14 scores **G_dev=1.107**, 0.611 below the v3 baseline’s 1.717, with acceptable runtime (**3330 s versus 3060 s; +8.8%**), but one seed makes this only a screen. Relative to baseline site means, all sites improve: NL-Loo −0.084, BE-Vie −0.270, DE-Gri −0.044, and DK-Sor −2.045; thus **84% of the aggregate gain comes from DK-Sor**, limiting per-site consistency.

The remaining gap is dominated by density rank (mean term **2.41**), followed by projection coverage (**1.27**), 90% parameter coverage (**1.05**), RMS-z (**0.95**), and 50% coverage (**0.96**); stuck chains contribute zero. Failures differ by site:

- NL-Loo is broadly too narrow/biased: c90=0.730, rms_z=2.14, rank=0.214.
- DK-Sor has severe undercoverage and misses the typical set: c50=0.303, rank=1.000, projection term=1.90.
- DE-Gri has reasonable marginal coverage but rank=0.906, indicating incorrect joint geometry or mode weights.
- BE-Vie is best overall, though rank=0.756 and ET-like projection coverage of 0.674 remain weak.

Increasing `n_audit` fourfold therefore did not solve the stated audit problem: ESS never approached 0.3, and G is worse than the three-seed surgery+DE result (0.964). There is no direct evidence of truth-B or holdout generalization. Repeated tuning on these four sites creates material dev-selection risk, although this run’s improvement is not confined to BE-Vie.

## 2. RISKS

The unmatched comparison—one candidate seed against a noisy three-seed baseline—can easily exaggerate improvement, as S9’s 0.93 screen later became 1.47±0.56. Mode fractions were not reported, so S14 cannot pass the promotion gate regardless of G. The capped aggregate can conceal catastrophic raw fits, while the mean G also obscures qualitatively different rank failures. Finally, reallocating evaluations from sampling to an audit whose ESS remains ~0.0002 risks reducing posterior equilibration without improving atlas coverage.

## 3. NEXT STEPS

1. **Confirm T2 on all four sites with three fresh seeds**, because full-posterior tempering is the first approach to reach the NL-Loo truth density with healthy swaps: `kernel="pt_de"`, `pt_rungs=16`, `pt_beta_min=0.03`, `pt_swap_every=5`, `pt_temper_edc=true`, `n_chains=256`, `n_steps=8000`.

2. **Screen selective EDC tempering against T2**, testing whether crossing only identified barriers improves mode weights without over-flattening: `pt_temper_edc=false`, `pt_temper_edc_terms="state_trajectories,cfcr_ratio,nsc_ratio"` with the same PT knobs.

3. **Within T2, sweep DE scale first on NL-Loo and DK-Sor**, since successful swaps have not yet produced correct mode mass: `de_gamma=0.12` versus `de_gamma=0.25`, holding all other T2 knobs fixed.

4. **[NEW CODE] Replace heuristic repair selection with held-out audit-loss reduction**, accepting an atlas operation only when it reduces uncovered importance mass, using `atlas_engine="surgery"`, `sg_flag_topk=16`, and `sg_stop_ess=0.3`.

## 4. STOP/CONTINUE

**Abandon the “larger audit alone” S14/S8 family**: 4× auditing neither raised ESS nor beat established candidates. Stop further connectivity/rank-threshold surgery tweaks; continue only audit-loss surgery research and the T2/T3 tempering family.
