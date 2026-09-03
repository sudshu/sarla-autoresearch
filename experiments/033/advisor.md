# Codex advisor, iteration 033

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

T2 is the strongest family so far: development \(G=0.952\) versus baseline \(1.717\), an improvement of 0.766 (45%), while wall time falls from 3,060 to 2,100 seconds (0.69×). Mean site changes are uniformly favorable: NL-Loo −0.725, DK-Sor −2.179, BE-Vie −0.051, and DE-Gri −0.108; no mean site triggers the +0.25 worsening guard.

Consistency is incomplete. NL-Loo is score-stable (0.748/0.647/0.679, sd 0.05), but its high-allocation fractions 0.39/0.36/0.17 have sd 0.12 and therefore fail the 0.10 mode-weight gate. DK-Sor is moderately score-stable (1.295/1.456/1.283, sd 0.10) and passes that gate (mode-fraction sd 0.02). BE-Vie and DE-Gri have only one seed each, so the reported development mean has only one complete four-site replicate and no candidate sd.

The displayed term decomposition is apparently from the first seed, not the three-seed site mean: its six terms average to 0.748 at NL-Loo and 1.295 at DK-Sor. On that seed, density rank remains the leading defect at both sites (2.97 and 3.07 term units); DK-Sor also has projection 1.73, cover90 1.13, and cover50 1.07. BE-Vie’s single run shows broad undercoverage (cover90 0.764, cover50 0.348) and weak projection coverage, while DE-Gri is mainly penalized by rank 0.870 and projection coverage.

There is substantial development overfitting risk: T2 was motivated and repeatedly tuned using NL-Loo/DK-Sor, with no holdout, B-truth, or real-NL-Loo result yet.

## 2. RISKS

The aggregate \(G=0.952\) can look confirmatory despite unequal replication and cannot yet support the two-sample acceptance test. The term-reporting/seed mismatch may lead to false attribution of improvements. Zero stuck fraction only excludes junk chains; it does not establish mode equilibration, as NL-Loo demonstrates. The capped, highly variable baseline—especially DK-Sor—also makes the apparent effect larger and the eventual test sensitive to seed accounting.

## 3. NEXT STEPS

1. Complete the preregistered decision before further tuning, because BE-Vie and DE-Gri determine both candidate variance and site guards: `kernel_seed=6,7` at sites 26 and 58, followed by dev-B, holdout, and real-NL-Loo scoring if eligible.

2. Increase replica diffusion at negligible evaluation cost, testing whether NL-Loo mode-weight sd falls below 0.10: `pt_swap_every=1` versus 5, with all other knobs fixed.

3. Use the existing swap-rate headroom to flatten the hottest posterior further and test barrier crossing: `pt_beta_min=0.01` versus 0.03, `pt_rungs=16`.

4. Improve DE population size per rung while preserving approximately 2.05M evaluations: `pt_rungs=12`, `n_chains=240`, `n_steps=8533`.

5. **[NEW CODE]** Adapt and then freeze ladder spacing during burn-in, optimizing round trips rather than adjacent acceptance alone: add `pt_ladder=adaptive`, with `adapt_start=0.25`, `adapt_every=200`.

## 4. STOP/CONTINUE

Continue T2 full-posterior tempering, but do not promote this result yet; abandon T1 likelihood-only tempering and the current S-family surgery/atlas-mixture family, whose repeated failures and ESS ≈0.0002 show diminishing returns.
