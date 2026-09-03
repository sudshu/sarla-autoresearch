# Codex advisor, iteration 018

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

H13 is a clear regression from longer-chain ensemble variants. On the two tested sites, mean G is 1.61 versus 1.27 for H2 DE128, 1.14 for stretch128, and 1.12 for surgery+DE128—worsening by 0.34–0.49 despite identical sampling-evaluation budgets. Runtime falls only 21% versus H2 (2,220 versus 2,820 s), far short of the 50% speed-path requirement.

The displayed term decomposition appears to be for seed 1, not the three-seed aggregate: its six-term mean exactly matches `G_seeds[0]`. That seed shows the same failure at both sites: severe 90% undercoverage (0.652/0.685), 50% undercoverage (0.326/0.360), and truth density ranks near one (0.955/0.986). NL-Loo additionally has `rms_z=1.79`; DK-Sor has uneven projection coverage, including 0.524 and 0.726 for two streams. No chains are formally stuck, so chains reach respectable-density regions but represent the wrong or overly narrow posterior mixture.

NL-Loo G is moderately seed-stable (1.44–1.64), but its high-mode fractions 0.38/0.46/0.67 remain unstable and all underweight the truth’s mode. DK-Sor G spans 1.59–1.81, but its mode fractions were not reported. This is only two development sites and truth A, so there is no evidence of cross-site or cross-truth generalization.

## 2. RISKS

Under the frozen rule, `n_dev=2` makes this iteration incomplete and it should be requeued once, not treated as a completed discard. However, completing all four sites has low scientific value unless needed for protocol compliance because the targeted two-site screen already rejects the hypothesis.

Term summaries from one seed can misleadingly look like aggregate diagnostics. Mode-weight conclusions also cannot be completed without DK-Sor fractions. The cap can conceal catastrophic fits, although it was not active here. Finally, equal evaluation counts are not equal effective budgets: 8,000 steps evidently sacrifice convergence for parallelism.

## 3. NEXT STEPS

1. Test the staged topology correction with `atlas_engine=surgery`, `sg_connectivity_rule=feasible_path`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`; rationale: fixing false branch detections attacks atlas coverage while retaining the best-scoring kernel. **[NEW CODE already implemented/staged]**

2. Test `atlas_engine=surgery`, `kernel=chart_adaptcov`, `mix=0.5`, `n_chains=128`, `n_steps=16000`; rationale: pooled covariance may improve within-basin exploration without DE’s unstable cross-mode jumps.

3. Tighten basin rescue using `restart_gap=50`, `restart_every=250`, `restart_until=0.5`; rationale: more frequent burn-in replacement directly tests whether persistent low-weight modes originate from initialization attrition.

4. On the 128×16k DE design, test `de_gamma=0.12` and `de_gamma=0.25`; rationale: transition scale may determine whether mode exchange is genuine or seed-contingent.

## 4. STOP/CONTINUE

Abandon the many-walkers-at-fixed-budget family (`n_chains>=256`, short chains): both 512×4k and 256×8k fail, and extra starting diversity does not stabilize weights. Continue topology-aware atlas work; retain DE/stretch only as components, not as standalone solutions.
