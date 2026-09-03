# Codex advisor, iteration 028

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S9 is decisively not promotable: mean dev G improved only 1.717→1.467 (−0.251), versus the required \(2SE=0.814\) (`v4_t=0.62`), while runtime rose 3060→3750 s (+23%, although still within the 1.5× guard).

The result is almost entirely an NL-Loo failure:

- NL-Loo: 1.416→2.864, worsening by 1.448 and therefore independently violating the +0.25 site guard; seeds span 0.955, 2.638, and 5.200.
- DK-Sor: 3.523→1.132, a large 2.391 improvement with tight 1.057–1.172 variation.
- BE-Vie: 1.113→1.033; DE-Gri: 0.817→0.837—both essentially unchanged and seed-stable.

Thus the promising 0.934 screen was seed luck, not a general atlas improvement. First-seed term data indicate typical-set/mode errors rather than stuck chains: `stuck=0` everywhere, while the rank term is near maximal at NL-Loo and DK-Sor (3.33 each) and DE-Gri (3.07); BE-Vie is instead dominated by projection (1.80) and marginal undercoverage (`cover50=1.40`, `cover90=1.25`). Mode-weight instability at DK-Sor also remains (0.42/0.14/0.20). No holdout or dev-B evidence exists, so robustness to another truth remains unknown rather than demonstrated.

## 2. RISKS

The displayed `terms` are apparently from seed one, not averages: for NL-Loo they reproduce G=0.955 rather than the reported three-seed G=2.864. They therefore cannot explain the two failed seeds and could misleadingly make the aggregate failure look well calibrated.

Capping also hides part of the NL-Loo catastrophe (one seed is 5.20, while capped aggregation uses 5), although it does not affect this verdict. Repeated selection on the same four A truths creates development-set overfitting risk; the absent dev-B/holdout evaluation is increasingly important. Finally, zero stuck chains does not imply mixing: rank=1 and unstable mode fractions show internally healthy chains sampling the wrong basin.

## 3. NEXT STEPS

1. **Confirm T2 first:** full-posterior tempering is the only tempering variant to reach the NL-Loo truth density, so run all four sites with three fresh `kernel_seed` values while holding the existing `t2_pt16_full` configuration fixed, then trigger dev-B/holdout and real-NL checks only if both score and mode gates pass.

2. **[NEW CODE] Replace surgery heuristics with S17:** optimize repairs against held-out importance discrepancy/uncovered mass because every operation-based surgery still ends near ESS 0.0002; use `atlas_engine=surgery`, `n_audit=16384`, `sg_stop_ess=0.3`, and reduce `n_steps` to preserve the evaluation budget.

3. **Combine full-posterior tempering with the most seed-stable surgery atlas:** test whether tempering fixes S4’s mode weights while surgery preserves its G≈0.96; set `atlas_engine=surgery`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, and budget-adjusted `n_steps`.

4. **Test persistent burn-in rescue:** directly test whether chains lose viable basins after initialization using `restart_until=1.0`, `restart_gap=50`, and `restart_every=250`, with three `kernel_seed` values at NL-Loo and DK-Sor first.

## 4. STOP/CONTINUE

Abandon S9 and the broader branch/connectivity/rank-threshold surgery heuristic family; also stop likelihood-only tempering T1 and standalone walker/kernel tuning. Continue atlas research only through audit-loss-driven S17, and continue T2 full-posterior tempering through its registered confirmation.
