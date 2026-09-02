# Codex advisor, iteration 005

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

H2 is the strongest candidate: \(G_{\rm dev}=0.962\), improving 0.755 from the 1.717 baseline, although this remains below the current 0.86 acceptance threshold and is based on only one kernel seed. It improved every site: NL-Loo −0.642, BE-Vie −0.123, DE-Gri −0.095, and DK-Sor −2.162. Runtime was 3,300 s versus 3,060 s (+8%), safely within the 1.5× limit but not a speed-path result.

H3 also improved every site (\(G=1.045\), −0.672), particularly DK-Sor (−2.237), but its joint-rank term averages 2.96 versus 1.89 for H2. H3’s apparently good DE-Gri score (0.732) masks rank \(r=0.996\); DK-Sor is similarly extreme (\(r=0.999\)). H2 materially changes NL-Loo’s previous basin-miss signature from \(r=1.00\) to 0.629, whereas H3 leaves it at 0.952.

For H2, the remaining mean term contributions are rank 1.89, cover90 1.19, projection 1.10, cover50 0.93, rms-z 0.67, and stuck 0. DK-Sor remains the weakest site: \(G=1.36\), \(r=0.981\), with GPP projection coverage only 0.524. Thus DE appears to help basin traversal, but calibration is not yet consistently joint-posterior accurate.

H9 should be rejected: \(G=1.329\), NL-Loo worsened by 0.325—already violating the 0.25 site guardrail—and both NL-Loo and DK-Sor retain near-unit ranks. Its NL-Loo projection coverage is only 0.24–0.81 across streams.

## 2. RISKS

The apparent H2/H3 gains are single-seed results compared with a three-seed baseline; DK-Sor’s extreme seed variability can easily reverse their ordering. Neither `sd_dev` nor `delta` is estimable here, and no holdout or dev-B truth was scored, so truth-specific or development-site overfitting remains completely unresolved. The cap at five appropriately limits catastrophes but obscures the magnitude and frequency of basin failures. Finally, a low averaged \(G\) can conceal pathological density ranks, as H3 at DE-Gri demonstrates.

## 3. NEXT STEPS

1. Complete the preregistered H2 confirmation on two additional seeds, then score all dev-B and available holdouts if it clears the rule: `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`, `kernel_seed=<two prespecified values>`.

2. Test topology-aware atlas surgery under the baseline kernel, because missing-basin coverage remains the dominant failure mechanism: `atlas_engine=surgery`, `kernel=chart_rwm`, `mix=0.0`, `n_chains=64`, `n_steps=32000`.

3. If surgery improves atlas coverage, test whether its benefit combines with DE rather than substituting for it: `atlas_engine=surgery`, `kernel=chart_de`, `mix=0.5`, `n_chains=128`, `n_steps=16000`.

4. Run the normal-projection ablation alongside surgery to identify whether projected repair locations drive any gain: `atlas_engine=surgery`, `sg_normal_projection=false`.

5. Only if H2 replicates, tune DE scale at fixed budget to reduce extreme ranks: `kernel=chart_de`, `mix=0.5`, `de_gamma=0.12/0.25`, `n_chains=128`, `n_steps=16000`.

## 4. STOP/CONTINUE

Abandon the polished-seed-start family (`start_policy=seeds`) in its present form. Continue H2 only through confirmation; retain H3 as a comparator, but pause broader kernel tuning until surgery establishes whether the atlas represents the missing basins.
