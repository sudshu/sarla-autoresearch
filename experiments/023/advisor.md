# Codex advisor, iteration 023

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S11 is a clear regression: \(G_{\rm dev}=1.356\), versus 0.934 for the simpler S9 gate fix, 0.964 for surgery+DE, and 1.717 for baseline. Relative to S9 it worsened NL-Loo by 0.65, BE-Vie by 0.18, and DK-Sor by 0.90, with only a negligible 0.04 improvement at DE-Gri. Runtime was 3,240 s—only 6% above baseline and within the guard—so quality, not cost, is decisive.

The mean contributions to G were rank 2.45, cover90 1.61, projection 1.56, cover50 1.32, rms-z 1.20, and stuck 0. NL-Loo and DK-Sor both have rank 1.00, severe parameter undercoverage, and elevated rms-z; DK-Sor also has poor projections (mean term 2.48). BE-Vie finds the truth’s density rank almost perfectly, but remains too narrow and projects poorly. DE-Gri has nearly ideal marginal coverage and rms-z, yet rank 0.966: even the apparently successful site samples the wrong joint-density distribution.

There is no evidence of convergence to junk regions (`stuck_frac=0` everywhere), but strong evidence of wrong-mode or under-dispersed posteriors. Site consistency is poor: G spans 0.68–1.96. One seed, one A truth, and no mode-fraction results make generalization or mode-weight stability unassessable; repeated design against these same four truths creates growing adaptive-overfitting risk.

## 2. RISKS

The run-history description says S11 achieved “about 1.1,” conflicting with the authoritative aggregate value 1.356; automated summaries or rankings may therefore be wrong. No surgery-operation counts were reported, so the feasible-path mechanism itself was not verified—its failure could be algorithmic or simply failure to activate. The six equally weighted terms can also hide severe joint-rank failure behind good marginal coverage, as at DE-Gri. Finally, capped aggregation protects against domination but can conceal whether catastrophic tails are improving.

## 3. NEXT STEPS

1. Test the best atlas correction with the best kernel: use `atlas_engine=surgery`, `sg_connectivity_rule=<S9 no-branch-on-infeasible setting>`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `atlas_rounds=10`, and `sg_flag_topk=16`; this directly combines S9’s 0.934 atlas result with cross-mode moves.

2. Test whether trajectory length, rather than population size, stabilizes DE mode weights using `kernel=chart_de`, `mix=0.5`, `n_chains=64`, `n_steps=32000`, and `de_gamma=0.12/0.25`; H13 showed that 256×8k was too short.

3. Confirm S9 alone over three fresh `kernel_seed` values before further topology work, retaining `atlas_engine=surgery` and its no-branch-on-infeasible `sg_connectivity_rule`; require the NL-Loo and DK-Sor mode-weight gate, not merely mean G.

4. Test whether audit starvation limits atlas coverage with `n_audit=16384`, `sg_stop_ess=0.3`, and `n_steps=16000`; the persistent audit ESS of 0.0002 indicates the current atlas evidence is exceptionally weak.

## 4. STOP/CONTINUE

Abandon S11’s current feasible-path repair: it is decisively worse than the simpler gate treatment and offers no demonstrated mechanistic benefit. Continue surgery only through S9 confirmation and the S9+DE hybrid; if neither stabilizes mode weights, stop the topology-surgery family.
