# Codex advisor, iteration 025

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S12 scores 1.132: 0.224 better than feasible-path surgery alone (S11, 1.356), but 0.168 worse than the confirmed surgery+DE result (S4, 0.964) and 0.198 worse than the simpler gate-crossing-as-unknown surgery screen (S9, 0.934). Relative to S11, three sites improve—NL-Loo −0.237, BE-Vie −0.208, DK-Sor −0.571—while DE-Gri worsens +0.120, so DE helps feasible-path surgery broadly rather than at only one site.

The dominant current error is density rank: its mean contribution is 2.59, 38% of the total gap, with ranks at NL-Loo 1.000 and DK-Sor 0.991; projection error contributes 1.22, parameter 50% coverage 1.15, 90% coverage 1.13, and excess `rms_z` 0.70. All sites under-cover parameters (`cover90` 0.719–0.876; `cover50` 0.360–0.416), and all have `rms_z>1`, indicating posteriors that remain too narrow or displaced. Projection failures are stream-specific: DK-Sor has 0.524/0.774 coverage for its first two streams, DE-Gri 0.667 for the third, and BE-Vie 0.686 for the second. No chains are stuck.

Against the baseline, roughly 91% of the summed per-site improvement comes from DK-Sor; NL-Loo improves only 0.052. This is one kernel seed on truth A, with no mode-weight or holdout result, so it provides no evidence of reproducibility or generalization. Wall time is 3,450 s, 1.13× baseline and 1.20× S4.

## 2. RISKS

Comparisons mix this single seed with three-seed means, making the apparent baseline gain fragile. The rank extremes show that a moderate aggregate G can coexist with failure to represent the truth’s typical set. The metric also penalizes projection coverage of 1.0, so some projection “error” is harmless overcoverage, whereas the low DK-Sor bands are genuine misses. Most importantly, S12 lacks the mode-fraction diagnostics that invalidated several otherwise superior candidates; confirmation would be wasteful because it already loses to S4 and violates S4’s NL-Loo per-site score by +0.343.

## 3. NEXT STEPS

1. Test the promising gate-crossing-as-unknown surgery directly with DE over three fresh seeds, because S9 and S4 are independently the strongest screens: `atlas_engine=surgery`, `sg_connectivity_rule=unknown`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, varying `kernel_seed`.

2. Test longer DE trajectories at fixed budget, because 256×8k failed while 128×16k improved scores, suggesting trajectory length matters: `kernel=chart_de`, `mix=0.5`, `n_chains=64`, `n_steps=32000`, `de_gamma=0.12/0.25`.

3. **NEW CODE:** Add an exact Metropolis independence move from the normalized atlas mixture to create explicit global mode jumps, then test `kernel=chart_independence`, `mix=0.1/0.25` with `atlas_engine=surgery`.

4. Apply tighter burn-in rescue to S4 across three seeds to test whether early mode extinction causes unstable weights: `restart_gap=50`, `restart_every=250`, `restart_until=0.5`, retaining `kernel=chart_de`.

## 4. STOP/CONTINUE

Abandon feasible-path connectivity: both S11 and S12 lose decisively to the simpler unknown-connectivity repair. Abandon likelihood-tempering at this budget—the communicating 16-rung ladder still failed at 2× evaluations. Continue surgery only through the no-false-branch variant and mechanisms explicitly targeting reproducible mode transport.
