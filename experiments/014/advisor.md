# Codex advisor, iteration 014

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S4 is the strongest calibration result so far: \(G_{\text{dev}}=0.964\pm0.039\), down 0.754 (44%) from the \(1.717\pm0.43\) baseline, with \(t=3.03\) and wall time 2,880 s versus 3,060 s. Every site improved versus baseline: NL-Loo 1.416→1.022, BE-Vie 1.113→0.837, DE-Gri 0.817→0.783, and DK-Sor 3.523→1.212; thus the gain is not solely DK-Sor, although DK-Sor supplies 2.31 points of uncapped improvement.

No chains were stuck. Remaining error is dominated by density rank and projection calibration: rank penalties are 2.57 at DE-Gri and 3.01 at DK-Sor because ranks remain 0.885 and 0.951, while projection penalties are 1.39 and 1.64. NL-Loo instead has under-wide parameter coverage (c90=0.742, c50=0.393) and rms-z=1.58, despite overcoverage of all projection streams. Site-level seed stability is good at NL-Loo and DE-Gri but weaker at BE-Vie (G range 0.775–0.937) and especially DK-Sor (1.060–1.377).

Critically, score stability does not imply posterior-mixture stability: NL-Loo high-mode fractions 0.54/0.32/0.79 have sd 0.23, and the real-data fraction is 0.61 versus ADEMCMC 0.815. With no holdout or dev-B results, this could be optimization to four truths while retaining incorrect mode weights. S5’s single-seed \(G=1.007\) does not change that conclusion; its ranks of 0.96–1.00 show persistent typical-set imbalance.

## 2. RISKS

The six-term arithmetic mean can hide catastrophic density-rank errors behind zero stuck-chain penalties and acceptable marginal coverage. Per-site averaging likewise makes DK-Sor disproportionately responsible for the apparent breakthrough. The mode gate was added after observing mode instability, so it is scientifically sensible but not fully preregistered independently of these results. Finally, comparisons combine only three kernel seeds with one pseudo-noise realization; neither truth/noise robustness nor holdout transfer has been demonstrated.

## 3. NEXT STEPS

1. **[NEW CODE] Test likelihood tempering with cross-temperature swaps**, because the central failure is discovering and correctly weighting separated modes rather than local within-mode calibration; knobs: `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, with stratification implemented under `start_policy`.

2. **Run S4 with more simultaneous walkers**, testing whether population diversity stabilizes NL-Loo mode mass without sacrificing its score; knobs: `n_chains=256`, `n_steps=8000`, retaining `atlas_rounds=10`, `sg_flag_topk=16`, and `kernel=chart_de`.

3. **Tune DE jump scale on S4**, because transitions may be too rare or too aggressive even when marginal G is good; knobs: `de_gamma=0.12` and `de_gamma=0.25`, `mix=0.5`.

4. **Test continuous burn-in rescue**, targeting DK-Sor’s seed trend and missed basins; knobs: `restart_gap=50`, `restart_every=250`, `restart_until=0.5`.

5. **Confirm the best mode-stable variant before promotion** on dev-B and holdouts using fresh `kernel_seed` values, with all other knobs frozen.

## 4. STOP/CONTINUE

Continue S4 only as a platform for explicit mode-exchange experiments; abandon further surgery threshold/rank-rule/volume-weight tuning and standalone DE, which improve G but have repeatedly failed to establish reliable mixture weights.
