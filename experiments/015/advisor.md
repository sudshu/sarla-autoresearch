# Codex advisor, iteration 015

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

Stretch mixing substantially improves the score but fails the posterior-mode requirement. Mean development G falls from 1.717 to 1.001 (−0.717; two-sample \(t=2.88\)), with low aggregate seed variation (SD 0.033), while wall time falls 9% from 3060 to 2790 seconds.

Every site improves versus baseline: NL-Loo 1.416→1.038, BE-Vie 1.113→0.965, DE-Gri 0.817→0.757, and DK-Sor 3.523→1.242. Thus the gain is not driven by one site; 70% of the total summed improvement nevertheless comes from repairing catastrophic DK-Sor behavior.

The remaining gap is dominated by density rank: \(r=0.87\)–1.00, contributing 2.47–3.33 units before six-term averaging at every site. Parameter intervals also remain too narrow: 90% coverage is only 0.75–0.81 at three sites, and 50% coverage is 0.40–0.43 there. DK-Sor additionally has poor projection calibration (projection term 1.79). No chains are stuck.

Stable G conceals unstable mode weights: high-allocation fractions are 0.60/0.75/0.30 at NL-Loo and 0.04/0.99/0.08 at DK-Sor, far beyond the 0.10 SD gate. There is no holdout, dev-B, or current real-data result, so robustness to another truth or real data is untested.

## 2. RISKS

- Averaging G can look stable while mutually incompatible modal mixtures produce similar marginal coverage scores.
- The capped baseline limits DK-Sor’s leverage, but the reported improvement still depends heavily on that site’s recovery.
- Repeated selection on the same four truths and noise realizations creates development-set multiple-testing risk; three kernel seeds do not address truth/noise sensitivity.
- Projection coverage of 1.0 is penalized symmetrically as overcoverage, but it does not distinguish useful conservatism from excessively diffuse forecasts.
- Near-unity density ranks across all sites suggest the sampler still misses important posterior mass; interpreting G≈1 as broadly calibrated would be misleading.

## 3. NEXT STEPS

1. **[NEW CODE] Test likelihood-only parallel tempering with DE within rungs**, because direct communication between allocation modes targets the gate failure: `kernel="chart_de"`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `de_gamma=0.12`, with four and six temperatures compared.

2. **Complete the 256-walker DE test across three seeds**, because greater simultaneous representation of both modes may stabilize their weights at fixed evaluations: `kernel="chart_de"`, `n_chains=256`, `n_steps=8000`, `mix=0.5`.

3. **Run a DE-scale sweep at 256 walkers**, scoring mode-weight SD before G, to test whether cross-mode jumps are presently too short or too disruptive: `de_gamma=0.12` versus `de_gamma=0.25`, with `n_chains=256`, `n_steps=8000`.

4. **Test longer-lived restart protection during burn-in**, because losing a represented mode may be an early population-extinction event: `restart_gap=50`, `restart_every=250`, `restart_until=0.5`, otherwise using the best DE configuration.

5. **Only after a mode-stable screen, run dev-B and holdouts**, retaining identical sampler knobs and requiring the improvement outside DK-Sor to persist.

## 4. STOP/CONTINUE

Abandon standalone chart+stretch and chart+DE kernel tuning as promotion candidates: both improve G yet repeatedly produce seed-dependent mode weights. Continue them only as components of a mechanism that explicitly exchanges mass between modes, especially tempering.
