# Codex advisor, iteration 026

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S13 lowers dev G from 1.72 to 1.18 (−0.54, 31%), but it is only a single-seed screen and would already fail the per-site guard: NL-Loo worsens from 1.42 to 1.76 (+0.34), while most of the aggregate gain comes from DK-Sor improving 3.52→1.48; BE-Vie improves 1.11→0.79 and DE-Gri 0.82→0.69.

The dominant remaining error is density rank: its mean contribution is 2.79, versus 1.19 for 90% coverage, 1.07 for 50% coverage, 0.99 for rms-z, 1.05 for projections, and zero for stuck chains. At NL-Loo and DK-Sor, rank is essentially 1.0, intervals are too narrow (c90 0.663/0.742; c50 0.270/0.371), and rms-z is 2.09/1.53. Projection calibration is comparatively good at NL-Loo, but DK-Sor has poor first two stream coverages (0.56 and 0.80); BE-Vie and DE-Gri also contain individual poorly covered streams (0.56 and 0.75).

The more “geometric” operation mix did not translate into calibration: G=1.18 is worse than S9’s 0.93 single-seed result and S4’s confirmed 0.96±0.04. No holdout, B-truth, or mode-weight result exists here, so generalization cannot be assessed; the NL-Loo regression is consistent with site-specific tuning rather than a robust improvement.

## 2. RISKS

Repeated selection over the same four development truths makes single-seed improvements optimistic, especially when the gain is driven by one historically unstable site. The unchanged audit ESS of about 0.0002 and roughly 100 uncovered draws indicate that operation counts are a weak proxy for atlas quality. Missing mode fractions are particularly consequential because several variants improved G while giving wildly seed-dependent mode weights. Finally, the history appears not to show the mandated five-iteration holdout/B milestones; if they were not run, adaptive development-set overfitting is currently unmeasured.

## 3. NEXT STEPS

1. Confirm the simpler S9 gate-crossing fix because it achieved G=0.93 without S13’s elaborate but ineffective geometry; knobs: exact `s9_surgery_nobranchinf` configuration with three distinct `kernel_seed` values, plus the registered mode-weight and real-data checks.

2. Test whether S9 supplies coverage while DE supplies within-atlas transport, using `atlas_engine=surgery`, S9’s existing gate-crossing rule, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, and three `kernel_seed` values.

3. Test whether substantially denser auditing actually reduces uncovered mass and rank error, with `n_audit=16384`, `sg_stop_ess=0.3`, `atlas_rounds=10`, `n_chains=128`, and `n_steps=16000`, preserving the fixed total budget.

4. **[NEW CODE]** Replace operation-count heuristics with an objective that directly minimizes held-out audit importance discrepancy and uncovered posterior mass, exposed as `sg_stop_ess` plus a new audit-loss selection rule, because ESS remained 0.0002 despite radically different surgery operations.

5. Run the overdue milestone before further dev selection, scoring the unchanged default on all four holdouts and four B truths with no sampler knobs changed.

## 4. STOP/CONTINUE

Abandon S11/S13 feasible-path and geometric-operation classification as a promotion family: they changed diagnostics but not coverage or calibration. Also stop likelihood-only T1 tempering after failure even at 2× budget. Continue only the simpler gate-fixed surgery branch, especially S9 combined with DE, until its three-seed mode-weight test resolves it.
