# Codex advisor, iteration 021

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

This is an incomplete two-site, one-seed screen, so it cannot support an accept/reject decision. Mean G across NL-Loo and DK-Sor is 1.208, slightly worse than four-rung T1 on the same sites (1.190): NL-Loo improved 1.076→0.960, but DK-Sor worsened 1.304→1.456. Both sites still have the worst possible density-rank term (rank = 1.0; contribution 3.33), showing that successful replica swaps did not carry the cold population into the truth’s typical set. NL-Loo’s high-mode mass is only 0.12 despite the truth occupying that mode, and its median cold log-posterior remains 40 nats below truth.

NL-Loo’s remaining terms are fairly good—c50 contribution 0.17, rms-z 0.29, projections 0.94—but c90 is low at 0.798. DK-Sor is broadly worse: c90 = 0.753, c50 = 0.404, rms-z = 1.40, and projection error contributes 2.17, driven by GPP coverage 0.43 and NBE 0.70. Zero stuck fraction is therefore misleadingly reassuring: chains can agree within the wrong basin.

Wall time is 2,250 s, 26% below baseline, but not the ≤1,530 s speed-path threshold. There is no evidence about BE-Vie, DE-Gri, holdouts, or B truths; selecting on the two known multimodal sites also risks site-specific tuning.

## 2. RISKS

The protocol says fewer than three development sites is incomplete and requeued once, yet this result is labelled discarded; it should remain an uncounted screen. A maximum rank failure adds only 0.56 to averaged G, allowing apparently respectable G despite complete typical-set failure. Sixteen rungs obtain 26–42% swaps by reducing each population to 16 walkers, confounding improved ladder communication with degraded within-rung exploration. The G cap, single A truth, and absence of holdout/B results can conceal catastrophic or truth-specific behavior.

## 3. NEXT STEPS

1. **[NEW CODE]** Test corrected topology before more kernel work, using `atlas_engine=surgery`, `sg_connectivity_rule=feasible_path`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, and `n_steps=16000`, because the present branch detector mostly identifies hard-gate crossings rather than posterior strata.

2. Run the staged non-cross-mode alternative with `atlas_engine=surgery`, `kernel=chart_adaptcov`, `mix=0.5`, `adapt_start=0.25`, and `adapt_every=200`, because pooled local covariance may improve exploration without DE’s unstable cross-mode jumps.

3. After feasible-path surgery works, test audit-first allocation with `n_audit=16384`, `sg_stop_ess=0.3`, and `n_steps=16000`, because atlas ESS ≈0.0002 indicates that evaluations currently spent sampling a bad atlas have little value.

4. Confirm any winner on all four development sites and three `kernel_seed` values before dev-B/holdout scoring; require both mode-weight gates, since single-seed G has repeatedly hidden mode-weight instability.

## 4. STOP/CONTINUE

Abandon likelihood-only T1 tempering under the fixed evaluation budget: four rungs do not communicate, while sixteen communicate but starve within-rung exploration. Also stop tuning straight-segment surgery; continue the atlas family only through feasible-path connectivity and adaptive-covariance tests.
