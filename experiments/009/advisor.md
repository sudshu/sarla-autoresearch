# Codex advisor, iteration 009

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

Both ensemble kernels substantially beat the v2/v3 baseline: DE reaches 1.048 and stretch 1.053 versus 1.717, improvements of 0.669 and 0.665. Their nominal v4 statistics pass (2.65 and 2.68 standard errors), while wall time is acceptable: DE is 6% slower than baseline (3,240 versus 3,060 s), and stretch is 8% faster (2,820 s).

The gain is not fully site-general. DK-Sor supplies 80–84% of the total improvement: 3.523→1.371 with DE and →1.285 with stretch. Nevertheless, neither candidate worsens any site on mean G; excluding DK-Sor, mean G improves modestly from 1.115 to 0.940 (DE) or 0.975 (stretch). DE is less repeatable (`sd_dev=0.085`) than stretch (`0.0065`), although stretch’s tiny aggregate SD partly reflects cancellation among sites.

The remaining gap is primarily calibration rather than stuck chains: `stuck_frac=0` everywhere. DE retains 90%/50% undercoverage at all sites and especially weak joint ranks at DK-Sor (0.981) and DE-Gri (0.765); its mean rank penalty is 1.89. Stretch improves marginal coverage and RMS-z, but its mean rank penalty is 2.96, with ranks 0.952–0.999 at three sites—strong evidence that its draws still sit below the truth in joint density. Projection failures are concentrated at DK-Sor’s GPP/NBE-like first streams (coverage approximately 0.52–0.81) and DE-Gri’s third stream (0.70–0.87).

There is no evidence yet against development-site or single-truth overfitting because neither holdouts nor B truths were evaluated; consequently there is also no evidence ruling it out.

## 2. RISKS

The displayed `v4_pass=true` must not promote either result: these are iteration-9 seeds explicitly judged under v3, while v4 requires three fresh seeds. Treating them retrospectively would violate the frozen protocol.

Kernel seeds measure computational variability, not truth/noise variability. The apparent improvement is dominated by the previously unstable DK-Sor baseline, and capping can conceal the magnitude of catastrophic failures. Site-averaged SD also understates instability when site changes cancel. Finally, configurations with extra atlas rounds must debit those evaluations elsewhere or the fixed-budget comparison becomes invalid.

## 3. NEXT STEPS

1. Reconfirm stretch under v4 with three fresh `kernel_seed` values using `kernel=chart_stretch`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `stretch_a=2.0`; it matches DE’s G, is faster, and is much more seed-stable.

2. Test whether longer trajectories repair stretch’s near-one density ranks using `kernel=chart_stretch`, `mix=0.5`, `n_chains=64`, `n_steps=32000`; this preserves sampling evaluations while doubling steps per chain.

3. Tune DE’s exploration/calibration tradeoff factorially with `kernel=chart_de`, `de_gamma=0.12/0.25`, and `mix=0.25/0.5`; DE currently has substantially better joint ranks than stretch.

4. Combine the most promising atlas geometry with DE using `atlas_engine=surgery`, `sg_weight_rule=volume`, `kernel=chart_de`, `mix=0.5`, `sg_flag_topk=16`, and `atlas_rounds=10`, with `n_steps` reduced to preserve the exact total evaluation budget.

5. If proposal 1 passes, immediately run the unchanged variant on all holdouts and B truths; **new code** only if the runner cannot schedule truth-set milestones independently of variant configuration.

## 4. STOP/CONTINUE

Abandon `start_policy=seeds`, the 512-chain family, and default S1/S2 surgery settings. Continue 128-chain ensemble kernels and volume-weighted surgery; P1’s blanket pause on kernel tuning is now contradicted by valid-v2 results, but no kernel should become default before fresh-v4 confirmation and the milestone.
