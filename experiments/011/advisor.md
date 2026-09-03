# Codex advisor, iteration 011

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S6 reached \(G_{\rm dev}=1.054\), 0.664 below the baseline’s 1.717, while wall time rose 25% (3,840 vs 3,060 s), remaining within the 1.5× guard; however, one seed makes this only a screen, not a promotion candidate.

The apparent gain is highly site-concentrated: DK-Sor improved 2.136 points (3.523→1.388), accounting for 80% of the summed per-site improvement; BE-Vie improved 0.323, NL-Loo 0.194, and DE-Gri was effectively unchanged (0.817→0.815). Thus it is not purely a single-site win, but DK-Sor still dominates.

Term-level changes versus baseline cannot be identified because baseline decompositions are absent. Remaining failures are clear: NL-Loo and DK-Sor both have rank \(=1.0\), contributing the maximum 3.33 rank penalty, so the sampler still misses or misweights relevant typical-set mass. Projection is also poor at NL-Loo (term 2.92, including LAI coverage 0) and DK-Sor (1.96); BE-Vie instead shows broad parameter undercoverage (\(c90=0.787\), rms-z 1.53), while DE-Gri has nearly ideal \(c90=0.899\) but poor \(c50=0.404\) and rank 0.920. No chains are classified as stuck.

S6 is worse than the S4 surgery+DE screen overall (1.054 vs 0.919), especially at DK-Sor (1.388 vs 1.060), and has no holdout, B-truth, or mode-fraction evidence. Overfitting to truth A or one kernel seed therefore remains entirely unresolved.

## 2. RISKS

The capped aggregate conceals how catastrophic raw DK-Sor behavior can be, while the single-seed per-site guard says nothing about seed stability. The surgery diagnostics—ESS 0.0002, no extend/merge operations, and 34–45 rank changes—show that improved \(G\) is not evidence that the intended self-correcting atlas mechanism is working. The rank target can also penalize wrong mode weights even when marginal coverage looks acceptable, making the missing high-allocation fractions a critical omission.

## 3. NEXT STEPS

1. Confirm S4 on three fresh seeds because it is the strongest and most uniform screen; knobs: `atlas_engine=surgery`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `sg_flag_topk=16`, `atlas_rounds=10`, `sg_weight_rule=volume`.

2. **[NEW CODE]** Test likelihood-only parallel tempering because ranks of 1.0 indicate cross-basin movement or weighting remains the principal defect; knobs: `kernel=chart_de`, `de_gamma=0.12/0.25`, `n_chains`, `n_steps`, plus new temperature-count and swap-interval knobs.

3. **[NEW CODE]** Apply the two-cell bridge reweighting to stored DE draws and require agreement with the NL-Loo real-data high-mode fraction 0.815; knobs: `kernel=chart_de`, `mix=0.5`, plus a new bridge-reweight switch.

4. Ablate splitting on the S4 backbone because repeated topology operations may spend atlas budget without increasing coverage; knob: `sg_do_split=false`, holding all S4 knobs fixed.

## 4. STOP/CONTINUE

Abandon further tuning of the S6 rank/tolerance family (`sg_gap_min`, `sg_rank_tau`, `model_tol`, `bend_tol`): its diagnostics did not change and it lost to S4. Continue surgery only through the S4 confirmation and split ablation; if neither passes seed stability and mode-weight gates, pivot to tempering/explicit mode reweighting.
