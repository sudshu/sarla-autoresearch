# Codex advisor, iteration 031

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

The single-seed dev score is 0.960, 0.758 below the capped baseline mean of 1.717, with nominal improvements at every site: NL-Loo 1.416→1.124, BE-Vie 1.113→0.913, DE-Gri 0.817→0.691, and DK-Sor 3.523→1.111. However, it is effectively tied with the already-tested surgery+DE result, 0.964±0.04, while being slower (3450 versus 2880 seconds).

The remaining gap is dominated by density rank: term penalties are 2.49 at NL-Loo, 2.06 at DE-Gri, and 3.30 at DK-Sor. Parameter intervals under-cover at NL-Loo and BE-Vie (c90=0.775/0.764; c50=0.360/0.360), while projection failure is concentrated in BE-Vie NBE (coverage 0.570) and DK-Sor GPP (0.536). No chains are classified as stuck, so the problem is wrong basin/mode weighting rather than junk chains.

Per-site scores look superficially consistent, but mode behavior does not: high-allocation mass is only 0.03–0.15 at every site, despite high-mode truths at NL-Loo (0.64) and BE-Vie (0.74). Thus the acceptable mean score masks systematic low-mode collapse. With one seed, no B truths, and no holdouts, there is no evidence of seed stability or truth generalization.

## 2. RISKS

Comparing this seed with the baseline’s three-seed mean exaggerates certainty, particularly because baseline DK-Sor was highly variable and capped. G also averages compensating errors: excellent projections or zero stuck fraction can obscure a badly wrong joint rank and mode weight. The mode-weight gate was not formally evaluated across seeds, but the uniformly tiny high-mode fractions already make failure very likely. Exact term-by-term movement from baseline cannot be established because baseline term decompositions are absent.

## 3. NEXT STEPS

1. **Confirm T2 full-posterior tempering first:** its first run reached the truth-density basin at NL-Loo, unlike T1; use `kernel="chart_de"`, `mix=0.5`, `n_chains=256`, `n_steps=8000`, and three `kernel_seed` values across all four dev sites.

2. **[NEW CODE] Add explicit mode-stratified replica accounting to T2:** preserve balanced high/low populations and measure round trips rather than letting the low mode absorb the cold ensemble; use `start_policy="balanced"`, `kernel="chart_de"`, `n_chains=256`, `n_steps=8000`.

3. **[NEW CODE] Implement S17’s held-out audit-loss repair selection:** prioritize operations that reduce uncovered importance mass instead of operation-count heuristics; use `atlas_rounds=10`, `n_audit=16384`, and shorten `n_steps` to preserve the evaluation budget.

4. **Test tighter burn-in rescue only with the best non-tempered kernel:** determine whether early low-mode capture is reversible using `kernel="chart_de"`, `restart_gap=50`, `restart_every=250`, and `restart_until=0.5`.

## 4. STOP/CONTINUE

Abandon S15 and the broader connectivity/rank-heuristic surgery branch: it matches ordinary surgery+DE in G, costs more, and worsens modal representation. Abandon likelihood-only T1. Continue full-posterior tempering T2 and objective-driven atlas repair.
