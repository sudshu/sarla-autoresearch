# SARLA autoresearch: program and pre-registered protocol

**Goal.** Make CARDAMOM's Bayesian calibration of the DALEC_1100 land model
(89 parameters) fast enough to run at many sites in minutes instead of days,
without degrading the posterior. The candidate is SARLA, a GPU fast path
(audited Laplace atlas + population sampler) that today takes ~30 min where
CARDAMOM's ADEMCMC takes ~33 h at one site. The loop proposes sampler-design
hypotheses, tests them on synthetic-truth experiments at several FLUXNET
sites, keeps what helps, and publishes every step.

**Metric.** Calibration gap G (lower is better; 0 = perfectly calibrated
posterior). Computed per site by `scripts/osse_score_site.py` from an OSSE
(observing-system simulation experiment): a known truth generates
pseudo-observations, the sampler fits them, and the posterior is scored
against the truth.

```
G_s = mean( |c90-0.90|/0.10,  |c50-0.50|/0.10,  |r-0.5|/0.15,
            max(0, rms_z-1)/0.5,  mean_streams |p90_s-0.90|/0.10,  stuck_frac/0.10 )
```
- c90, c50: fraction of the 89 parameters whose 90% / 50% posterior interval
  contains the truth (targets 0.90 / 0.50)
- r: joint density rank P(logpost(draw) < logpost(truth)) (target 0.5)
- rms_z: RMS over parameters of (truth - posterior mean) / posterior sd
- p90_s: fraction of truth values inside the 90% band of the posterior's
  GPP / NBE / ET / LAI projection over the unobserved months (target 0.90)
- stuck_frac: fraction of chains whose median log-posterior is > 100 nats
  below the best (a chain that never left a junk region)

Each term is a distance from its target in units of about its binomial
noise floor (sd(cover90) = 0.032 over 89 parameters).

**Sites and split.** Eight CARDAMOM-FluxVal sites (FLUXNET2015, CC-BY-4.0).
Development set, drives accept/reject: NL-Loo (183, ENF), DE-Gri (58, GRA),
ES-LJu (178, OSH), BE-Vie (26, MF). Holdout set, scored only at milestones,
never used to choose: CZ-wet (55, WET), DE-Geb (57, CRO), FR-Pue (82, EBF),
DK-Sor (71, DBF; no real-data mode reaches 30% of its observed GPP, so its
truth uses a relaxed 20% plausibility bound and is flagged). Every site has 192 monthly steps with observations ending
by step 113, so the last 78+ months are a projection test at every site.

**Truth.** Per site: a plausible EDC-feasible point near (not at) one of the
pilot's real-data L-BFGS modes -- a random plausible mode plus N(0, 0.3 prior
sd) jitter in z, redrawn until feasible and plausible. Plausible = finite
trajectory, mean GPP within [0.3x, 3x] of the site's observed mean GPP, and
biomass at the observation month within [0.3x, 3x] of the site's observed
biomass. The jitter keeps the truth off the seed set the fitter starts from.
A second truth + noise realisation ("B") exists for each development site and
is used only at milestones. Iid EDC-feasible prior draws were tried first and
rejected (2026-09-01): at all five sites checked they are near-dead
ecosystems (GPP < 5% of observed).

**Pseudo-observations.** The CBF's own declared error model per stream
(lognormal sigma = ln 3 for GPP and ET, N(0, 1) for NBE, lognormal ln 1.5 for
LAI, lognormal ln 1.05 for biomass), observation times copied from the real
site, everything assimilated.

**Budget.** Fixed model-evaluation budget per fit equal to the baseline (128
L-BFGS seeds, atlas 6 rounds x 4096 audit draws, sampling 64 chains x 32,000
steps = 2.05M evaluations). Variants that change chains x steps keep the
sampling-evaluation total. Wall-clock is recorded per job and GPU type.

**Accept rule.** A candidate becomes the new default iff (a) dev G improves
on the current default by more than delta, where delta = 0.10 until iteration
0 replaces it with 2 sd(G) over three kernel seeds of the baseline on the
development set; (b) no development site worsens by more than 0.25 in G_s;
(c) H100 wall-clock <= 1.5x the default's. Speed path: accept if wall-clock
<= 0.5x at G <= default + 0.05. An iteration with fewer than 3 of 4
development sites scored is incomplete and is requeued once, never counted.

**Milestones.** At each new default and at least every 5 iterations, the
default is scored on the 4 holdout sites and the 4 "B" truths. If holdout G
worsens by > 0.05 relative to the previous default, the change is labelled
"dev-only" and reverted. Development and holdout results are always shown
side by side.

**Advisor.** After each iteration a Codex agent (OpenAI Codex CLI, reasoning
effort high) receives the protocol, the run history and the iteration's
scores (aggregate numbers only) and proposes next steps; its reply is saved
under `experiments/<iter>/advisor.md`, its proposals enter the idea bank
tagged `codex`, and the Claude session running the loop decides what to
implement next, combining those with its own.

**Breakthrough notification.** The user is emailed when a new default
improves dev G by >= 0.20, when the speed path accepts, or when a holdout
milestone confirms either.

**Frozen.** This protocol is frozen from iteration 1. Any change is logged as
a new protocol version in `LOG.md`; earlier results are never re-judged
under a later version.

**Data on this page.** Aggregate metrics and public FLUXNET site IDs only; no
observation series. Data: FLUXNET2015 (Pastorello et al. 2020, CC-BY-4.0)
via CARDAMOM-FluxVal v1.0 (Yang et al. 2022, GMD).

## Protocol version 2 (2026-09-02 04:00 PDT)

**What changed and why.** Decomposing the log-posterior at the protocol-v1
truths showed that the data terms at the truth equal those at the sampler's
best draw, while the soft EDC (ecological-constraint) penalties differ by 580
to 1,220 nats. The 0.3-sd jitter had pushed every truth into territory the
model's own constraints reject, so the pseudo-data posterior was legitimately
elsewhere and no sampler could recover the truth. Runs 1-4 (iterations 0-1)
were judged against invalid truths and are kept on the page as protocol v1
for the record only; they carry no weight in any decision.

**Truth rule, v2.** The truth is a typical accepted draw of CARDAMOM's own
reference sampler on the real data: a short ADEMCMC run per site (4 chains x
30,000 iterations, 400 walkers each), second half of every chain pooled,
plausibility filter as before (finite trajectory, mean GPP and biomass within
[0.3x, 3x] of the observed), and the draw whose log-posterior is nearest the
pooled median. This is the recipe the NL-Loo OSSE used. It is EDC-consistent
by construction (an accepted draw), independent of the sampler under test,
and typical rather than mode-adjacent. The first v2 attempt (jittered mode
with an EDC check) was abandoned before use: the real-data L-BFGS modes from
the pilot themselves carry soft-EDC penalties near 500 nats, so nothing
built on them can be consistent. Everything else (sites, split, noise model,
budget, metric, accept rule, milestones) is unchanged. Iteration numbering
continues (iteration 4 is the v2 baseline); the baseline and noise floor are
re-measured.

**Sites under v2.** The truth source changed which sites are usable: DK-Sor
now has a converged reference chain and plausible draws, while ES-LJu,
FR-Pue and DE-Geb did not converge in 30,000 iterations (soft-EDC penalties
still -28 to -125) and are re-run at 60,000 iterations. Development set under
v2: NL-Loo (183), DE-Gri (58), BE-Vie (26), DK-Sor (71). Holdout: CZ-wet (55),
DE-Geb (57), FR-Pue (82), ES-LJu (178). The v1 flag on DK-Sor is void.

## Protocol version 3 (2026-09-02 09:40 PDT)

**What changed and why.** The first valid (v2) baseline showed that one site
can dominate everything: DK-Sor scored G = 14.0, 2.6 and 3.0 over three
kernel seeds, so the seed-to-seed sd of the development mean was 1.7 and the
acceptance threshold delta = 2 sd = 3.4, which no realistic improvement could
clear. From v3 every site's G is capped at 5 in every aggregate (per-fit
scores stay uncapped in the score files): a catastrophic site counts as a
failure, not as a lever on the mean, and the noise floor is 2 sd of the
capped development mean over kernel seeds. Nothing else changes; no decision
had been taken under v2, so no result is re-judged. v2 truths and datasets
are unchanged and remain the reference.

**Truth-source detail (2026-09-02 14:20 PDT, protocol v3, affects no scored
result).** The truth's soft-EDC consistency check is relative to its
reference chain: the chosen draw must lie within 10 nats of the pooled median
soft-EDC penalty of the last 30% of the chains (and the chain must not be
both far below -20 and widely spread, the signature of non-convergence). At
the five converged sites this selects the same draws as the earlier absolute
-20 rule (medians -9 to -17). At ES-LJu and FR-Pue the whole reference
posterior sits at about -118 nats with an interquartile range of 6 nats even
after 60,000 iterations: the penalty is a property of those sites' posteriors,
so a typical draw there is the right truth.

## Protocol version 4 (2026-09-02 15:20 PDT; effective for decisions taken from iteration 13 on)

**What changed and why.** Under v3 the threshold delta was 2 sd of the
BASELINE's development mean over kernel seeds (0.86, driven by the baseline's
erratic behaviour at DK-Sor). The first three-seed candidate (chart + DE
moves, iteration 9) scored 1.05 +/- 0.085 against the baseline's 1.72 +/- 0.43:
a 0.67 improvement, 2.6 standard errors, yet below delta because delta ignores
the candidate's own, much smaller, spread. From v4 the acceptance test is
two-sample: a candidate with n_c >= 3 kernel seeds replaces the default with
n_b seeds iff

    G_default - G_cand  >  2 * sqrt( sd_default^2 / n_b  +  sd_cand^2 / n_c )

with the unchanged guards (no development site worse by more than 0.25 in
capped G_s; H100 wall-clock <= 1.5x; speed path unchanged) and the milestone
holdout check. Results judged under v3 are NOT re-judged: the DE kernel's
iteration-9 verdict stands as "discard under v3", and its v4 test uses three
fresh kernel seeds (iteration 13). Single-seed screens remain screens: they
never promote.

**Addendum to v4 (2026-09-02 17:30 PDT): mode-weight gate and real-data check.**
Promotion additionally requires, over the candidate's >= 3 kernel seeds, that
the across-seed standard deviation of the high-allocation mode fraction
(fraction of draws with wood-allocation f_wood > 0.5) is <= 0.10 at both
NL-Loo and DK-Sor: G averages over sites and can improve while the mode
weights, which decide the wood residence time, still swing between seeds.
Each candidate is also fitted once to the REAL NL-Loo data and its
high-allocation fraction compared with the converged 64-chain ADEMCMC
reference (0.815, 90% CI 0.794-0.834); this is reported at every milestone
and is not a truth-selection question.
