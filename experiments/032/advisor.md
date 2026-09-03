# Codex advisor, iteration 032

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

`s16_surgery_indep` failed: \(G_{\rm dev}=1.851\), 0.134 worse than the baseline, 0.67 worse than the closest surgery-geometry predecessor S13, and 0.89 worse than S15.

The regression is almost entirely NL-Loo: G rose from 1.76 in S13 to 4.42, while BE-Vie improved by 0.05, DE-Gri worsened by 0.12, and DK-Sor improved by 0.05. Site performance is therefore extremely inconsistent (0.74–4.42).

Averaged across sites, the six gap contributions were cover90 2.06, cover50 1.60, rank 2.55, rms-z 2.47, projection 2.42, and stuck 0. NL-Loo was catastrophically narrow and biased: cover90 0.326, cover50 0.169, rms-z 5.13, and projection coverages as low as 0–0.14. Density rank was essentially 1 at NL-Loo, DE-Gri, and DK-Sor, so apparently reasonable marginal coverage at the latter two hides typical-set failure. Zero `stuck_frac` only says chains avoided junk regions, not that they mixed between posterior modes.

There is no evidence of development-site or truth-A overfitting because there is no improvement to generalize; with one kernel seed and no dev-B or holdout scores, such overfitting also cannot be excluded.

## 2. RISKS

The independence-jump effect is slightly confounded because S16 changed both `kernel`/`mix` and `sg_connectivity_rule` relative to S13. Nevertheless, acceptance of only \(5\times10^{-5}\)–\(10^{-4}\) means roughly 99.99% of global proposals were rejected, strong direct evidence that the atlas mixture is unusable as an 89-D independence proposal.

The single-seed result has no variance estimate or mode-weight gate result. Aggregation also obscures that one site caused nearly the entire loss. Wall time was 3,810 s—1.25× baseline and slower than most competitive DE/PT variants—so there is no compensating speed benefit.

## 3. NEXT STEPS

1. Confirm T2 on all four development sites and three fresh seeds because full-posterior tempering is the only tempering variant to reach the NL-Loo truth-density region with healthy swaps; knobs: `kernel="pt_de"`, `pt_temper_edc=true`, `pt_rungs=16`, `pt_beta_min=0.03`, `pt_swap_every=5`, `n_chains=256`, `n_steps=8000`, `kernel_seed={three fresh values}`.

2. Test mode-stratified T2 because its remaining failure is underweighting the high-allocation mode; knobs: `start_policy="mode_stratified"` with the T2 settings above.

3. Test selective-EDC tempering to flatten the identified barriers without unnecessarily broadening all intermediate targets; knobs: `pt_temper_edc=false`, `pt_temper_edc_terms="state_trajectories,cfcr_ratio,nsc_ratio"`.

4. Screen DE scale within T2 at NL-Loo and DK-Sor before full confirmation; knobs: `de_gamma=0.12` versus `de_gamma=0.25`.

5. **[NEW CODE]** Replace heuristic surgery operations with held-out audit-loss selection, retaining repairs only when they reduce uncovered mass; knobs: `atlas_engine="surgery"`, `n_audit=16384`, `sg_stop_ess=0.3`.

## 4. STOP/CONTINUE

Abandon atlas-mixture independence-MH (`kernel="chart_indep"`): its acceptance rate is decisively fatal. Also stop likelihood-only T1 tempering; continue T2 full/selective-EDC tempering. Pause heuristic surgery variants except the fundamentally different audit-loss proposal.
