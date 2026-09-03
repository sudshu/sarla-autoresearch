# Codex advisor, iteration 022

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

`s10_surgery_adaptcov` reaches \(G_{\rm dev}=1.163\), 0.554 (32%) below the 1.717 baseline, with wall time 3330 s—9% slower than baseline but within the 1.5× guard. It is nevertheless only a single-seed screen and would currently fail the per-site guard: NL-Loo worsens 1.416→1.711 (+0.295) and BE-Vie 1.113→1.433 (+0.320), while DE-Gri improves 0.817→0.526 and DK-Sor improves dramatically 3.523→0.983.

The errors are site-specific rather than a uniform calibration improvement:

- NL-Loo is severely under-dispersed (c90=0.663, c50=0.281, rms_z=1.82) and misses the truth’s typical set (rank=0.996).
- BE-Vie is likewise too narrow and biased, but in the opposite density-rank direction (rank=0.126); projection coverage is also poor for GPP/ET (0.686/0.523).
- DE-Gri has good parameter and density calibration, but one projection stream covers only 0.548, making projection error its largest term.
- DK-Sor has near-target c90=0.888 but low c50=0.315, rank=0.788, and weak first-stream projection coverage (0.536).
- No chains are stuck at any site, so the problem is incorrect geometry/mode weighting, not junk-region trapping.

Because this uses one kernel seed, one truth, no mode-weight report, and no holdout, its strong DK-Sor result could be seed- or truth-specific. The cross-site reversals are stronger evidence of instability than of a generally improved sampler.

## 2. RISKS

The capped aggregate makes the 2.54-point DK-Sor improvement dominate the apparent gain while concealing two promotion-guard failures. Baseline term-level values are absent, so individual-term “improvements” cannot be distinguished from redistribution of error. Adaptive covariance learned from one ensemble can reinforce whichever mode was initially overrepresented; zero stuck fraction does not detect that failure. Repeated development-A screening also creates selection pressure even without explicit parameter tuning to its truth.

## 3. NEXT STEPS

1. Test corrected topology together with the strongest cross-mode kernel over three seeds: `atlas_engine=surgery`, `sg_connectivity_rule=feasible_path`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`; this directly combines better atlas coverage with the best-scoring transport mechanism.

2. Give DE longer trajectories to test whether mode weights stabilize: `kernel=chart_de`, `mix=0.5`, `n_chains=64`, `n_steps=32000`, with `de_gamma=0.12` and `0.25`; the 256×8000 result suggests trajectory length matters more than walker count.

3. Confirm `s9_surgery_nobranchinf` across three seeds using `atlas_engine=surgery` and its existing gate-crossing rule before further surgery tuning; its 0.934 screen is competitive and removes the known false-branch mechanism.

4. Test persistent early rescue with `restart_gap=50`, `restart_every=250`, `restart_until=0.75` on the best feasible-path configuration; this asks whether initial mode imbalance can be corrected before covariance or DE adaptation locks in.

5. **NEW CODE:** add mode-stratified adaptation so pooled covariance is estimated within `f_wood` cells and mixed only afterward (`kernel=chart_adaptcov`, `adapt_start=0.25`, `adapt_every=200`); this isolates whether covariance estimation itself or cross-mode pooling caused the reversals.

## 4. STOP/CONTINUE

Abandon adaptive pooled covariance as a standalone replacement for cross-mode moves: it is worse than surgery+DE, fails two site guards, and reproduces mode-dependent undercoverage. Continue feasible-path surgery and longer-trajectory DE; do not confirm this exact S10 configuration.
