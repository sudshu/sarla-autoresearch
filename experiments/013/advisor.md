# Codex advisor, iteration 013

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

H2 materially improves mean development performance: \(G_{\text{dev}}=1.068\pm0.077\), versus baseline \(1.717\pm0.43\); the 0.649 reduction passes the v4 two-sample threshold by 2.58 SE and is 8% faster (2,820 versus 3,060 seconds).

All four sites improve, so there is no per-site regression: NL-Loo −0.258, BE-Vie −0.139, DE-Gri −0.064, and DK-Sor −2.136. However, DK-Sor supplies 82% of the aggregate improvement, and remains seed-variable (G 1.04–1.56).

The remaining gap is principally a typical-set/mode-weight problem, not stuck chains: `stuck_frac=0` everywhere, but rank penalties are 1.70, 1.70, 2.33, and 3.18. NL-Loo, BE-Vie, and DK-Sor also under-cover parameters (`cover90` 0.73, 0.76, 0.71; `cover50` 0.39, 0.35, 0.35), while DK-Sor’s projections are weakest, including 0.52 GPP coverage. DE-Gri has nearly ideal marginal coverage (0.888/0.494) yet rank 0.849, demonstrating that good one-dimensional intervals conceal incorrect joint mass.

Most importantly, mode weights are irreproducible: NL-Loo high-mode fractions 0.61/0.84/0.71 (sd 0.11), and DK-Sor 0.97/0.06/0.27 (sd 0.48). Thus the calibration improvement is real but insufficient for promotion. Holdout and truth-B are absent, so development-site or single-truth overfitting remains unresolved.

## 2. RISKS

The capped baseline makes the DK-Sor improvement statistically manageable but obscures how catastrophic individual fits may be; always retain raw G beside capped decisions. Site-averaged G also hides the contradiction between marginal coverage and joint rank at DE-Gri. Kernel seeds are not independent evidence about truth robustness, and the mode gate was introduced after seeing related instability, so its operating characteristics remain uncalibrated. Finally, changing chains and steps at equal evaluation count does not guarantee equal effective mixing or wall-clock behavior.

## 3. NEXT STEPS

1. Confirm S4 with three fresh `kernel_seed` values using `atlas_engine=surgery`, `sg_flag_topk=16`, `atlas_rounds=10`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, because its one-seed G=0.919 is the best result and it may stabilize basin coverage as well as improve G.

2. **[NEW CODE]** Test likelihood tempering with `kernel=tempered_de`, `n_chains=128`, `n_steps=16000`, and stratified `start_policy=balanced`, because DK-Sor’s 0.97/0.06/0.27 mode fractions require actual cross-mode transport rather than better local proposals.

3. Test H2 at `n_chains=256`, `n_steps=8000`, `kernel=chart_de`, `mix=0.5` across three `kernel_seed` values, because more independent walkers may reduce allocation variance at fixed sampling evaluations.

4. Sweep `de_gamma=0.12` and `de_gamma=0.25` with `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, scoring mode-weight variance first, because the default DE scale improves G but does not equilibrate modes.

5. If S4 passes the mode gate, immediately run all holdouts, dev-B truths, and real NL-Loo before further tuning.

## 4. STOP/CONTINUE

Abandon plain H2/chart+DE as a promotion candidate: two multi-seed studies show stable mean G but the decisive mode-weight failure. Continue DE only inside surgery or tempering; continue the atlas-coverage family pending S4 confirmation.
