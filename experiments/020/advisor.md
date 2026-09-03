# Codex advisor, iteration 020

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S9 is the strongest surgery-only screen so far: dev G fell from 1.717 to 0.934 (−0.784, 46%). Every site improved versus baseline: NL-Loo 1.416→0.955, BE-Vie 1.113→1.002, DE-Gri 0.817→0.722, and DK-Sor 3.523→1.057. The gain is not isolated to one site, although DK-Sor supplies most of it; the current site range, 0.72–1.06, is much more consistent than baseline’s 0.82–3.52.

The remaining gap has two distinct causes. Joint ranks remain pathological at NL-Loo and DK-Sor (rank=1.00; term=3.33) and nearly so at DE-Gri (0.961; term=3.07), indicating that credible marginal coverage is masking typical-set or mode-weight failure. BE-Vie instead suffers broad undercoverage: c90=0.775, c50=0.360, with projection coverage only 0.58–0.76 for three streams. DK-Sor also has a projection term of 1.79. RMS-z penalties are modest (0.06–0.82), and stuck-chain penalties are zero everywhere.

This is only one kernel seed on truth A, so neither the score test nor the mode-weight gate can yet be evaluated. Its G is statistically indistinguishable at screening resolution from S4’s 0.919; there is no evidence yet that suppressing false branches beats surgery+DE. Repeated development-site iteration creates meaningful selection-overfitting risk despite the encouraging cross-site consistency.

## 2. RISKS

Baseline term-level decompositions are absent, so the aggregate improvement cannot be attributed confidently to coverage, rank, or projections. The rank failures at three sites could make G look satisfactory because six heterogeneous terms are averaged. Mode fractions were not reported, despite previous candidates with similar G failing dramatically on that gate. Wall time is 3,750 s, 23% above baseline and slower than S4, leaving little benefit unless robustness improves. No dev-B or holdout evidence exists.

## 3. NEXT STEPS

1. Confirm S9 on three fresh seeds and report mode fractions before further tuning, changing only `kernel_seed` while retaining all other S9 settings.

2. Test the implemented feasible-path repair because 77–82 rank changes suggest “unknown connectivity” merely shifted false operations: `atlas_engine=surgery`, `sg_connectivity_rule=feasible_path`, `kernel=chart_rwm`, `n_chains=64`, `n_steps=32000`.

3. Combine S9’s corrected branching with the best-scoring kernel to test complementary atlas coverage and mixing: `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `atlas_rounds=10`, `sg_flag_topk=16`.

4. Test whether audit noise drives excessive repairs by increasing `n_audit=16384`, enabling `sg_stop_ess=0.3`, and reducing `n_steps` to preserve the evaluation budget.

## 4. STOP/CONTINUE

Continue S9 only through confirmation. Abandon further threshold tuning of straight-segment branch/rank rules (S6–S8); the diagnostic is geometrically invalid. Also stop likelihood-only tempering under the fixed budget: a working 16-rung ladder still underweighted the target mode and starved cold-chain exploration.
