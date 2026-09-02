# Codex advisor, iteration 001

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

H3 (`chart_stretch`) was the only competitive variant: G_dev=1.199 versus 1.190 baseline, while cutting median wall time from 3,270 to 2,040 s (−38%). It meets the speed-path quality bound (≤1.240) but not the required ≤0.5× runtime (observed 0.624×), and it fails the per-site safeguard because ES-LJu worsened by 0.315. Its site changes were NL-Loo −0.100, BE-Vie −0.256, DE-Gri +0.077, and ES-LJu +0.315; thus the apparent improvement at the difficult BE-Vie site was offset elsewhere.

Relative to H1, H3 lowered every mean component: cover90 1.04 versus 1.41, cover50 1.32 versus 1.63, rank 1.98 versus 2.16, rms_z 1.44 versus 1.67, projection 1.41 versus 1.62, and stuck 0 versus 0.059. Relative to H2, however, H3’s rank term was substantially worse (1.98 versus 1.13), despite better coverage, rms_z, projection, and stuck terms. Baseline term-level results are absent, so term movements versus the actual default cannot be established.

BE-Vie remains the dominant failure: undercoverage (c90=0.596, c50=0.270), rms_z=3.70, and weak projections, especially the fourth stream at 0.488. Performance is highly site-dependent rather than a consistent sampler-wide gain. With only truth A and one candidate kernel seed, there is no evidence capable of ruling out truth-specific or dev-set overfitting.

## 2. RISKS

The candidate scores use one kernel seed while the baseline apparently aggregates three; `sd_dev` and `delta` are null, so neither statistical improvement nor formal acceptance can be evaluated consistently.

Averaging projection streams hides concentrated failures: for example, H3 has DE-Gri’s second stream at 0.571 and BE-Vie’s fourth at 0.488 while other streams approach 1.0.

Wall-clock eligibility also requires confirmation that these medians are from comparable H100 jobs. Repeated selection on the same four A truths will increasingly overfit them unless dev-B is used promptly for near-winners.

## 3. NEXT STEPS

1. Test longer stretch trajectories with `kernel="chart_stretch"`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, because 512×4k appears too short for contraction while stretch retained near-baseline G at substantially lower runtime.

2. Test `start_policy="seeds"` with the baseline kernel and budget, because missing region mass is a documented failure and broader feasible-seed starts could improve mode representation without changing the transition kernel.

3. Test `flat_mult=3.0`, because BE-Vie’s extreme rms_z and undercoverage are consistent with charts being too narrow in weakly identified directions.

4. If proposal 1 helps, tune `mix=0.25` and `stretch_a=2.0` at `n_chains=128`, `n_steps=16000`, because reducing stretch frequency may retain cross-valley exploration while correcting H3’s high rank terms.

## 4. STOP/CONTINUE

Abandon the generic 512-chain/4k-step family and stop H11 DE tuning: H1 and H2 worsened G, while H2 damaged DE-Gri by 0.547. Continue the stretch family only through the preplanned longer-chain test; abandon it if that does not beat baseline across at least three sites and multiple kernel seeds.
