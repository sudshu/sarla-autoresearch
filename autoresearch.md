# SARLA autoresearch: program and pre-registered protocol

**Goal.** Make CARDAMOM's Bayesian calibration of the DALEC_1100 land model
(89 parameters) fast enough to run at many sites in minutes instead of days,
without degrading the posterior. The candidate is SARLA, a GPU fast path
(audited Laplace atlas + population sampler) that today takes ~30 min where
CARDAMOM's ADEMCMC takes ~33 h at one site. The loop proposes sampler-design
hypotheses, tests them on synthetic-truth experiments at several FLUXNET
sites, keeps what helps, and publishes every step.

**Metric.** Calibration gap G (lower is better; NOT 0 for a perfect sampler: measured floor 0.52, 90% range 0.23-0.81; ADEMCMC reference 0.62. See the 2026-09-04 addendum: G is uncorrelated with mode mass
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

## Addendum 2026-09-04 (post-stop): the metric had a floor and a blind spot

Measured after the loop was stopped, using the converged ADEMCMC reference on the
same v2 site-183 dataset (8 chains, 400k rows) and on the v1 pilot OSSE.

1. **G has a floor near 0.5, not 0.** Monte Carlo of the G formula under exact
   calibration (89 parameters, one truth draw, binomial coverage, rank ~ U(0,1),
   rms_z ~ sqrt(chi2_D/D)) gives G mean 0.52 with 90% range 0.23 to 0.81
   (an independent replication with fully independent projection steps gives 0.45,
   90% range 0.17 to 0.72; the difference is only the assumed effective sample
   size of the projection streams). The rank term alone contributes 1.67 of the
   six-term average, because with a single truth realisation the density rank is
   uniform, not 0.5. The ADEMCMC reference scores G 0.618 at site 183 and 0.707 on
   the v1 pilot: statistically indistinguishable from a perfect sampler. The best
   non-tempering SARLA run at site 183 scored 0.55, i.e. already at the floor.
   The statement "0 = perfectly calibrated" in the original protocol is wrong.

2. **G does not see the mode error.** Across the 53 non-tempering runs scored at
   site 183, Spearman correlation between G and the high-allocation mass fraction
   is rho = -0.00 (p = 0.99); mode fractions span 0.01 to 1.00 over that set. The
   clearest case is the v1 pilot, four arms on identical pseudo-data (truth
   f_wood 0.80): ADEMCMC G 0.707 / mode 0.88; sarla_v3 G 0.833 / mode 0.03;
   sarla_v2 G 1.385 / mode 0.15; sarla_v1 G 1.481 / mode 0.14. The fast version
   with the best G has the worst mode recovery of any arm.

3. **Decision noise.** Across-seed sd of G at site 183 is 0.21 and the
   perfect-sampler 90% range spans 0.58 in G. Most accept/reject margins in the
   39 iterations were inside that.

4. **OSSE confirmation of peak versus mass.** On the v1-truth OSSE (truth f_wood
   0.80, realised tau_wood 10.1 yr) the converged 32-chain ADEMCMC puts 0.896 of
   its mass in the high-allocation mode (chain-bootstrap 90% CI 0.874 to 0.917)
   and recovers tau_wood near the truth (high-mode median 8.5 yr), while the MAP
   sits in the low-allocation mode. 23 of 32 chains visit both modes.

**If the loop is ever restarted:** G must be scored against the reference value,
not against zero, and must be paired with a mode-mass term or gate scored against
the ADEMCMC fraction. Protocol v4 results should not be re-judged under this
addendum; they should be read as largely inside the noise floor.

## Addendum 2026-09-04b: scoring against the reference posterior, not a point truth

Retained real-data fits at NL-Loo compared to the converged 64-chain ADEMCMC
posterior itself (scripts/sarla_vs_ref.py; artifacts runs/sarla_vs_ref_*.json).
Instrument floor from splitting the reference fleet in half over 12 random splits:
per-parameter 1-Wasserstein distance 0.033 reference-sd units (95th pct 0.092),
half-fleet high-allocation mass in [0.810, 0.846].

  variant                   loop verdict  mass_hi  90% CI         tau_wood  W1 med  in floor
  ADEMCMC reference         -             0.805    [0.783,0.826]  10.43 yr  0.033   -
  s7_surgery_volume_de128   discard       0.911    [0.873,0.945]  10.11 yr  0.43    0/89
  s4_surgery_de128          confirm/disc  0.583    [0.512,0.653]  13.43 yr  0.50    0/89
  h2_de128                  confirm       0.580    [0.510,0.649]  15.40 yr  0.55    0/89
  v3_baseline               baseline      0.539    [0.448,0.628]  19.16 yr  0.89    0/89
  t2_pt16_full              VOID          0.215    [0.183,0.247]  43.11 yr  0.38    0/89

1. **Real progress was made.** Median distance to the reference posterior fell
   from 0.89 to 0.43 sd-units, baseline to best variant; dev-site rms_z fell from
   2.19 (first three iterations) to 1.67 (last three), reference 0.96.
2. **No variant is close.** Zero of 89 parameters land inside the reference's own
   split-half floor for any variant; the closest is ~13x the floor. Worst
   offenders are hydrology/phenology nuisance terms: init_LAIW_mem, thetas_opt,
   LY1_vhc, LY2_z, beta_lgrHMF, t_lab, k_leaf.
3. **The best variant was discarded on noise.** s7_surgery_volume_de128 has the
   smallest posterior distance and the only correct wood residence time
   (10.11 vs 10.43 yr). It was dropped at iteration 12 because its single-seed
   G_dev 1.03 lost to s4's 0.92 — a gap of 0.11 against an across-seed sd of 0.21.
   s4 was itself discarded at iteration 14 on the mode gate. s7 also overshoots
   the mode mass (0.911 vs 0.805) with a tau_wood interval much narrower than the
   reference's, so it finds the right hill but loses the low-allocation tail.

**Caveat:** one real-data seed per variant; the bootstrap intervals are Monte
Carlo only and the loop's own across-seed mode-mass sd at NL-Loo was 0.23. s7's
advantage is suggestive, not established. The recorded next step, NOT run because
the campaign is stopped: three seeds of s7 on real NL-Loo, ranked on distance to
the reference posterior rather than on G.

## Addendum 2026-09-04c: the atlas was built on the wrong curvature (RETRACTION)

Found by a Codex advisor via the companion session, confirmed independently here.

**The bug.** `build_logpost(gate="none")` is not equal to the hard-gate target
inside the feasible set, contrary to its docstring. The "hard" branch calls
`mlf2()`, which returns the likelihood PLUS finite EDC penalties; the "none"
branch calls `likelihood()`, which drops them along with the -inf gate. Several
EDCs contribute finite penalties, not just gates (vcmax_lcma contributes
-0.5*r^2; state_trajectories accumulates a squared log-ratio penalty).

**Measured here** on 40 evenly spaced feasible draws of the 64-chain NL-Loo
reference: logpost(hard) - logpost(none) has median -11.11 nats, range -18.62 to
-6.58, and is never zero. The companion session measured median -10.94 over 185
draws with a wider range. The two targets are simply different functions.

**What this invalidates.** `scripts/osse_fit.py:69` builds the Laplace atlas
curvature with `gate="none"`. So every chart in every SARLA atlas across all 39
iterations was fitted to a Hessian of the wrong function. The same applies to the
companion session's newton_map.py, gauss_newton_map.py and laplace_mode_mass.py.

**Claims now retracted, not disproved:**
- that damped Newton "stalls 25 nats short" and Newton-family optimisers are off
  the table (LOG entries of 2026-09-03);
- that a two-hill Laplace mass estimate is unusable because the maxima carry 9 to
  13 negative eigenvalues;
- that Laplace geometry does not work for this posterior.
These were all measured on the wrong curvature and are unresolved, not settled.

**Why it may matter for the campaign's central failure.** The atlas is the object
that is supposed to supply cross-budget proposals. Building it on a curvature that
omits the EDC penalties, which are exactly the terms that shape the 10 to 38 nat
ridge between the two allocation budgets, is a plausible mechanism for the fast
path misplacing mode weights. Untested: nothing has been rebuilt, the campaign is
stopped.

**Two further corrections from the same review.**
- `scripts/gauss_newton_map.py` uses diag(u*(1-u)) for the logit-Jacobian
  curvature; the correct value is 2*u*(1-u), so that term is half its true size.
- The chart "volume" weight (`sarla2.py` log_volume) sums 0.5*log(var) over
  tangent directions only, omitting density height, normal-direction width,
  feasible fraction and overlap. It is not posterior mass. It also feeds only
  `atlas.draw`/`atlas.logq`, which the production chart_de kernel does not use,
  so with chart_de the weight flag can act only through surgery audit draws and
  initialisation. The open s7 question is therefore "better atlas, or merely a
  better starting population".

**Ecological correction.** On 3840 reference draws split at f_wood 0.5, the two
modes differ 4.9x in allocation and 0.21x in wood residence time but give the SAME
standing carbon: C_wood 5967 vs 5478 (ratio 1.09), ABGB at step 179 6377 vs 6376
(ratio 1.00), GPP and NBE identical. Near equilibrium C_wood ~ f_wood * NPP * tau
and the products agree to one percent. This is an allocation-turnover confound.
The mode error must NOT be described as a large disagreement about present carbon
storage; it changes future stock change and turnover-limited persistence.

## Addendum 2026-09-04d: the curvature fix works, and mode weighting is not the main error

Both results from the companion session, both checked here.

**1. gate="soft" is the correct curvature target, and it un-retracts Laplace.**
The new branch keeps the likelihood, every FINITE EDC term and the Jacobian, and
zeroes only the -inf cliffs. Verified here on 30 evenly spaced reference draws at
NL-Loo: max |logpost(hard) - logpost(soft)| = 5.7e-14 nats over the 29 feasible
ones, and soft is finite on all 30. Compare the old gate="none", measured in
addendum 4c at a median 11 nats off, with gradient directions differing by a
median relative 0.99, so it was not a mild distortion.

With the corrected curvature the companion session reports the high hill carrying
2 negative eigenvalues out of 89 and the low hill 0, against the 9 to 13 we
previously reported, and a two-hill Laplace mass estimate of 0.827 against the
reference 0.815, from two Hessians in about five minutes (peak height alone gives
0.007). So "Laplace geometry is unusable for this posterior" was our own bug, and
that retraction is now itself withdrawn: Laplace geometry works here. Caveats
carried from the source: the feasibility correction rests on about 4 and 12
feasible draws out of 400 per hill, and the convention for flat and negative
directions moves the answer between 0.827 and 0.949. A 20k-draw re-estimate was
running when this was written.

**2. Mode weighting is NOT the main error (this changes the priority order).**
Each real-data fit's own draws were reweighted to the reference mode proportions
and per-parameter 1-Wasserstein distance re-measured, median over 89 parameters,
in reference-sd units. Sample sizes are matched between the floor and the variant
figures (4000 vs 4000 unconditional, 2000 vs 2000 within-high, 1000 vs 1000
within-low).

  variant                  mass_hi  W1 all  W1 rewt  W1|high  W1|low
  reference (floor)          0.812   0.039    0.039    0.045   0.065
  v3_baseline                0.539   0.873    0.791    0.795   0.741
  h2_de128                   0.576   0.528    0.515    0.529   0.581
  s4_surgery_de128           0.592   0.505    0.490    0.477   0.512
  s7_surgery_volume_de128    0.916   0.429    0.464    0.465   0.596

Reweighting removes only 5 to 10 percent of the discrepancy, and for s7 it makes
matters slightly worse because s7 overshoots the mass. Conditional on being in the
correct hill the fast path is still 10 to 18 times the reference's own noise floor
(within-high: baseline 17.8x, h2 11.8x, s4 10.7x, s7 10.4x). A correct
mode-weighting rule, including the one the fixed Laplace now supplies, would NOT
rescue the fast path. The within-mode shape error is the thing to attack.

**This also settles the s7 question ahead of the seed runs.** Within the high hill
s7 and s4 are effectively tied (0.465 vs 0.477, both about 10x floor). s7's whole
apparent advantage was that its mode proportion happened to land nearer the
reference. Consistent with the chart-volume weight being unable to act through the
production chart_de kernel at all. **Caveat added here:** the claim that s7 is
worse in the low hill (0.596 vs 0.512) is partly a sample-size artifact, since
s7's 0.916 mass leaves only ~506 low-hill draws against the floor's 1000-vs-1000
construction, which inflates W1. The high-hill tie is the solid part.

**Recorded next step, not taken:** `scripts/osse_fit.py:69` still builds the atlas
on gate="none". The fix is one word once target.py is synced, but the six refcheck
fits are running against the current code, so nothing is being redeployed.

## Addendum 2026-09-04e: I mutated an input file mid-campaign (methodological error)

On 2026-09-03 at 10:46 I added the real-data MAP point to
`runs/osse_sites_v2/183real/seeds.npz` in place, with no versioning, after 14
iterations of real-data fits had already been run against the previous contents.
Every real-data fit after that date used a different atlas from the ones before
it. This was recorded in LOG.md at the time as a one-line aside and its
consequences were not thought through.

**The original is recoverable.** `runs/osse_sites_v2/183realb/seeds.npz` holds
exactly the pre-edit 24 rows: all 24 are bytewise present in the current 25-row
file, and the added row is index 24. No data was lost.

**The seed-count explanation does not hold.** Running the forward model on all 25
points: the original 24 contained 1 high-allocation point (f_wood 0.65), 4 low and
19 degenerate (f_wood <= 0, i.e. NPP below zero); the current 25 contain 1 high, 5
low, 19 degenerate. The number of healthy high-allocation seeds is ONE in both. So
the observation that today's fits land at 9 to 17 percent high-allocation mass
cannot be attributed to the seed set being high-allocation-poor, because the set
that produced 0.594 and 0.912 was equally poor.

**The specific mechanism to test instead.** The row I added is the global MAP
(f_wood 0.194, log-posterior -161.9), the highest-density point known anywhere in
the space, and it sits in the LOW-allocation budget. Injecting the global density
maximum into the L-BFGS seed set plausibly builds a dominant chart at the low peak
and restructures the atlas around it. That predicts the observed collapse.

**Ruled out as confounds.** (a) Code drift: the three surgery changes committed
between the two run dates (branch_on_infeasible, connectivity_rule, rank_min_diff)
all default to the previous behaviour, and the s4/s7 variant files do not pin them.
(b) Start assignment: chain starts come from init_seed, fixed at 99 in both
variants, while kernel_seed drives only the sampler. Starts therefore differ
between the two run dates only through the atlas, hence only through the added
point.

**The clean A/B, well posed and not run:** the same kernel seeds against 183realb
(24 points, no MAP) and 183real (25 points). If mode mass follows the seed file,
the MAP injection caused the collapse. If it does not, then kernel-seed variance
in mode mass is enormous, which is itself the finding. Either way the s7-vs-s4
comparison across the two dates is confounded and cannot be read as a seed effect.

**Rule for any restart:** input data files are immutable once any fit has run
against them. A change means a new site directory and a new name, never an in-place
edit.

## Addendum 2026-09-04f: correcting 4e — the seed edit also hit the primary dev site

Two corrections to addendum 4e, both found by following up a companion-session
report that the Sep-3 code changes had silently altered every variant.

**1. The code-drift claim is wrong; I checked all three diffs.** The three
SurgeryConfig knobs added on Sep 3 are exactly back-compatible under their
defaults, so no pre-existing variant changed behaviour:
- `branch_on_infeasible=True`: old code returned
  `all(isfinite(lpm)) and lpm.min() > ...`; new code returns
  `not branch_on_infeasible` when any midpoint is infeasible, i.e. False, then the
  same comparison. Identical.
- `connectivity_rule="segment"`: the feasible_path logic is guarded by
  `== "feasible_path"`, and its RNG draws happen only inside that branch, so the
  random stream is also unperturbed.
- `rank_min_diff=0.0`: the added conjunct is `abs(...) >= 0.0 * D`, always true.
The presence of `sg_branch_on_infeasible` in a run's echoed variant dict is a
useful PROVENANCE marker for which code version ran, but it is not evidence of a
behaviour change. Cross-iteration comparisons are not confounded by code drift.

**2. The seed edit is worse than 4e said: it also hit dev site 183.** I checked
mtimes across all site directories. `183/seeds.npz` and `183B/seeds.npz` were
edited at the same moment as `183real`, on Sep 3 at 10:46, 24 rows to 25. The
other dev and holdout sites (58, 26, 71, 55, 57, 82, 178 and their B variants)
were NOT touched and have 24 rows.

At site 183 the appended row is far more damaging than at 183real:

  appended row 24: f_wood 0.194 (low-allocation), log-posterior -268.6
  best of the original 24 rows:                    log-posterior -621.4

The injected point is 353 nats denser than every other seed. An L-BFGS seed set
anchored by such an outlier, in the low-allocation budget, will dominate the atlas
it produces. Note also that the original 24 rows at this site were mostly
high-allocation (20 of 24), unlike 183real, so the edit did not merely add a point
to a poor set: it added a dominating low-allocation attractor to a good one.

**Blast radius.** Iterations 0 to 28 ran before the edit; iterations 29 to 36 ran
after. [CORRECTED: this was first estimated as a 27/28 boundary from job-directory
mtimes. Labelling each fit from its OWN log line "N feasible seed points from ..."
(19 = restored 24-row set, 20 = contaminated 25-row set) puts i027 and i028 on the
restored set and i029 first on the contaminated one. Provenance from artifacts
beats provenance from timestamps.] Site 183 is one of
the four development sites and is one of the two sites the mode-weight gate is
evaluated on. So dev-G and mode-gate comparisons that straddle iteration 27/28 are
confounded at that site. Site 183 real-data fits are affected from Sep 3 10:46 too.
Comparisons within either group, and at the other sites, are unaffected.

**Recovery (verified, not inferred).** All four site directories share the same
24 base seeds, and the appended row 24 is bitwise identical across 183, 183B and
183real. Rows 0-23 of `183/seeds.npz` are bitwise identical to rows 0-23 of
`183real/seeds.npz`, and the pre-edit file preserved as `183realb/seeds.npz` is
bitwise identical (uint64 view, shape and dtype) to rows 0-23 of both. So the
pre-edit seed set is RESTORED, not reconstructed: it is saved as
`seeds.pre_map_2026-09-03.npz` in 183, 183B and 183real, each verified against the
preserved copy. Any rerun of a pre-edit variant can use it without caveat.

**Update (4f, same day):** the companion session independently diffed the merged
variant dicts that sarla_fit.py echoes for a pre-edit and a post-edit run of the
same variant. The only differences are the seven newly added keys plus the
kernel seed; no key present in both changed value. That is a stronger check than
reading the diffs, and it agrees: the code is a no-op at these defaults. The
companion session has retracted its code-drift claim. With code drift eliminated
and kernel-seed noise measured at sd 0.019-0.033 in mode mass and 1.7-2.7 yr in
tau_wood, far too small to move tau_wood from 10 to 45 yr, the seed edit is the
only surviving explanation for the collapse, pending the control runs.

## Addendum 2026-09-04g: the seed edit flips the answer, and BOTH metrics hide it

**Control result (companion session, 3 of 6 fits).** Identical code, identical
kernel seeds, only the seed file swapped (reference mass_hi 0.813, tau_wood
10.36 yr):

  restored 24-seed set   s4_s6 mass 0.599 tau 13.54 | s4_s7 0.809 / 10.33 | s7_s6 0.669 / 11.76
  contaminated 25-seed   s4 mass 0.146 +/- 0.033 tau 40.63 +/- 1.68 (n=3)
                         s7 mass 0.085 +/- 0.019 tau 46.10 +/- 2.73 (n=3)

Mean tau_wood 11.9 yr restored vs 43.4 yr contaminated, against measured
kernel-seed noise of 1.7-2.7 yr: roughly 15x the sampler's own scatter. One fit
(s4 seed 7) reproduces the reference mode summaries almost exactly, 0.809/10.33
against 0.813/10.36. A single 353-nat seed flips the sampler's answer to the
central scientific question. This is seeding dominance, not a mixing failure.

**The distance metric prefers the WRONG answer, and I verified it and found why.**
Recomputing per-parameter 1-Wasserstein against the reference for s4 seed 7:

  contaminated (wrong mode)  W1 median 0.294   closer on 64 of 89 parameters
  restored     (right mode)  W1 median 0.414

The mechanism is dimensional dilution. Only 11 of 89 parameters separate the two
modes by more than 0.5 reference-sd. On those the restored fit is far closer:

  parameter     mode separation   W1 contaminated   W1 restored
  phi_WL             1.79 sd           1.19            0.32
  i_cwd              1.37 sd           1.28            0.48
  tr_lit2som         1.28 sd           1.19            0.35
  t_wood             1.07 sd           0.60            0.60
  LCMA               1.06 sd           0.42            0.36
  i_labile           1.06 sd           0.96            0.88

The other 78 parameters are nuisance dimensions where the contaminated fit happens
to sit closer, and they swamp the median. So the median-over-89 distance is not a
better metric than G; it fails the same way, by averaging a low-dimensional but
decisive structure into 89 dimensions of noise. G's floor problem and this are the
same structural error at bottom.

**Consequence for the loop record.** Any decision made on distance-to-reference at
sites 183/183B over iterations 28-36 may have been driven the wrong way, on top of
the seed confound itself. Re-reading those iterations is deferred until all six
control fits land.

**Concrete fix for any restart (revised, see 4h).** Report the decisive-subset
distance alongside, not inside, the 89-parameter average, and use the disagreement
between them as a cheap alarm. But the GATE should be mode mass and tau_wood
against the reference. See addendum 4h: the decisive subset fixes the sign of the
comparison but does not separate the two conditions robustly enough to gate on.

## Addendum 2026-09-04h: the decisive subset is a diagnostic, not a gate

I proposed in 4g that a restart should score on the decisive parameter subset. The
companion session pushed back, and it is right. Both of us then measured the same
thing and landed on opposite sides of the boundary, which settles it more firmly
than either result alone.

  companion session (12-parameter subset): worst restored 0.600 > best
      contaminated 0.580, i.e. the conditions OVERLAP
  this session (11-parameter subset):      worst restored 0.616 < best
      contaminated 0.629, i.e. clean separation by a margin of 0.013

The subset definition differs only by where the 0.5-sd threshold falls (11 versus
12 parameters). A classifier whose verdict flips between "overlapping" and
"separated" under that benign a choice, on a margin of 0.013, is not fit to gate
promotions. That is exactly how G went wrong: a number with a real signal in it,
used at a resolution finer than its own stability.

What the subset IS good for, confirmed at n=9 here: it explains the inversion. The
sign flips cleanly on the aggregate (decisive 0.66 contaminated vs 0.49 restored;
nuisance 0.27 contaminated vs 0.42 restored), which is the dimensional-dilution
mechanism. And the cross-check stands: if the decisive-subset distance and the
89-parameter median disagree in sign, distrust the run.

The direct quantities separate with no overlap and a wide margin, so they are the
gate:

  mass_hi    restored 0.57-0.81      contaminated 0.07-0.16
  tau_wood   restored 10.3-13.9 yr   contaminated 39.3-48.5 yr

  [OVERTURNED 2026-09-04 by control fits 4 and 5 -- see addendum 4i. The restored
   range above was n=3; at n=5 it becomes 0.057-0.810 and OVERLAPS the
   contaminated range. This gate is not clean.]

**Rule for a restart:** gate on mode mass and tau_wood against the reference;
report decisive-subset and full-median distances side by side as diagnostics; never
promote or discard on a margin smaller than the metric's own definitional
sensitivity.

**4h refinement (threshold sweep, both sessions).** Rather than trading single
threshold choices, both sessions swept it. The two sweeps agree closely in the
robust region and disagree exactly where the margins are tiny:

  thresh  n_par   margin (companion)   margin (this session)   AUC (this session)
   0.30    17-18       -0.108                -0.100                0.78
   0.40    13          +0.033                +0.033                1.00
   0.50    11-12       -0.020                +0.013                1.00
   0.55    11          +0.013                +0.013                1.00
   0.65     8          +0.180                +0.180                1.00
   0.70     7          +0.413                +0.413                1.00
   0.85     6          +0.456                +0.456                1.00

Margin = best contaminated minus worst restored, so positive means separated.
AUC = P(a restored run scores closer than a contaminated one), 1.0 = perfect
ranking. Below 0.40 the subset genuinely degrades. Between 0.40 and 0.60 the
verdict is unstable and the two sessions disagree, with every margin under 0.04.
At 0.65 sd and above, on the 6 to 8 strongest parameters, both sweeps agree
exactly and margins are an order of magnitude larger.

**Two cautions on that robust region, so it is not over-read.**
(a) It was identified AFTER seeing which thresholds separate. Adopting it now
would manufacture a metric that works on the data that built it, which is the
error this whole addendum series is about.
(b) The statistic itself is weak at these sample sizes. "Worst restored versus
best contaminated" is an extreme-order statistic on 3 and 6 points. Even the
perfect AUC of 1.00 carries a best-achievable p-value of 1/C(9,3) = 0.012 with
n=3 versus n=6, so neither "overlap" nor "separated" is well determined here.

**Recorded as a pre-registered candidate, explicitly NOT a metric in use:**
subset = parameters whose two-mode means differ by more than 0.65 reference-sd;
statistic = AUC over runs, not a min/max margin; to be validated at a different
site, with more seeds per condition, before it is allowed to gate anything.

The gate remains mode mass and tau_wood, whose margins are one to two orders of
magnitude more robust: mass gap +0.409 (3.5x) and tau_wood gap 25.4 yr (2.8x)
between the worst restored and the best contaminated run.

## Addendum 2026-09-04i: CORRECTION to 4g and 4h — the gate overlaps too

Control fits 4 and 5 landed and overturn the central claim of 4g and the
recommendation of 4h. Verified independently here by recomputing mode mass from
every control fit's own draws.

  condition     host   run                          mass_hi
  restored      h100   s4 seed 6                     0.594
  restored      h100   s4 seed 7                     0.810
  restored      h100   s7 seed 6                     0.655
  restored      kyo    s4 seed 8                     0.110   <- new
  restored      kyo    s7 seed 7                     0.057   <- new
  contaminated  h100   s4 seed 6 / s4 seed 7         0.156 / 0.109
  contaminated  h100   s7 seed 6 / s7 seed 8         0.094 / 0.068
  contaminated  kyo    s4 seed 8 / s7 seed 7         0.166 / 0.086

**What is overturned.** 4g reported the restored condition at mass 0.57-0.81
against contaminated 0.07-0.16, "no overlap, factor-of-three margin", and 4h made
that the recommended gate. At n=5 the restored range is 0.057-0.810 and overlaps
the contaminated range completely. The two new runs read 19 feasible seed points
from the restored file with rc=0, so they are genuine restored-seed runs that
collapsed, and they collapsed harder than any contaminated run.

**What survives, and the precise logical statement.** Pooling with the i014 fits:
restored recovered the high-allocation mode in 7 of 9 runs, contaminated in 0 of 7
(Fisher one-sided p = 0.0031). Locally on the controls alone: restored 3/5,
contaminated 0/6. So seed contamination is a SUFFICIENT cause of failure, and it
is highly reliable as such; restoring the seeds is NOT sufficient for success. The
4g headline "one seed flips the answer" holds in one direction only. "Remove the
seed and the method is correct" does not hold: it is 3/5 on fresh runs.

**A second possible factor, confounded with host.** Within the restored condition
the control fits split perfectly by machine: h100 3/3 recovered, kyo 0/2. Pooling
the companion session's wider set gives h100 6/6 and kyo 1/3 (Fisher one-sided
p = 0.083, suggestive only), and one earlier kyo run did recover, which argues
against hard hardware determinism. Candidate explanations: GPU numerics, the
memory-fraction difference (0.3 on h100 vs 0.9 on kyo), or nothing. This matters
beyond these runs because the loop's 39 iterations were spread across both
machines, so if it is real it is a second confound running through the entire
record.

**Pre-registered test (companion session, before the last fit landed):** the final
control fit is queued on h100 with restored seeds. Host hypothesis predicts mass
> 0.5 and tau_wood 10-14 yr; seed-only hypothesis predicts roughly 60-70% chance
of the same. A collapse on h100 kills the host hypothesis and means the method
simply fails on about 40% of runs.

**Consequences.** The iterations 28-36 re-read stays deferred, now for two reasons
rather than one. And the recommended follow-up is 6 to 8 more restored-seed fits
split deliberately across hosts; neither the host claim nor the irreducible-failure
claim can be written up without it. That is GPU work beyond the stopped campaign
and is the user's call, not ours.

**Method note on us, and the most transferable finding of the campaign.** In 4h I
warned that a min/max margin on 3 and 6 points is an extreme-order statistic and
that neither verdict was well determined. That warning was aimed at the
decisive-subset metric; it applied just as much to the gate endorsed in the same
breath, and the gate is what it broke. Both sessions over-read an n=3 range as a
clean separation.

Generalised, agreed by both sessions: in this campaign THREE metrics in turn --
the calibration gap G, decisive-subset W1, and the mode-mass/tau_wood gate -- each
looked clean and then failed as n grew. In all three cases the failure was
predictable in advance from the sample size alone, with no knowledge of the metric.
So the rule is NOT "prefer direct physical quantities", which is what the evidence
appeared to say at 4h. The rule is:

  STATE THE ACHIEVABLE RESOLUTION BEFORE READING THE VERDICT.
  Compute what the metric can resolve at the n you have, and refuse to read a
  margin finer than that, whatever the metric is measuring.

Applied to this campaign that single rule would have caught the G floor at
iteration 0, the decisive-subset instability at 4g, and the gate overlap at 4h,
before any of them was acted on.

**4i caution, carried from the companion session.** Even if the host split proves
real, it does not rescue the method. Six of six on one machine is still a sampler
whose answer to the central scientific question depends on something outside the
data. It would move the diagnosis from "unreliable" to "unreliable in a way we can
point at", which helps debugging but is not evidence that the fast path can replace
the 33-hour reference. Nothing in the seed or host analysis changes the
distance-to-reference numbers: every variant in the set remains 10 to 15 times the
reference's split-half floor.

**Division of labour agreed:** the companion session takes the host-split
submission and scoring (dispatch state and provenance-aware scorers are there);
this session takes the iterations 28-36 re-read once the host question is settled
(that record is this session's). Neither is launching GPU work; the host-split
experiment is with the user.

## Addendum 2026-09-04j: host hypothesis dead; the real result is variance

**The pre-registered prediction failed, which settles the host question.** The
final control fit ran on h100 with restored seeds and gave mass 0.327, tau_wood
21.90 yr, against a predicted mass > 0.5 and tau 10-14 yr. It is also a third
outcome type, neither clean recovery nor the 40-68 yr collapse. Within the restored
set the host split is now h100 6/7 versus kyo 1/3, Fisher p = 0.18, weaker than
before. Recorded as TESTED AND NOT SUPPORTED, not as open. Because the prediction
was registered before the fit landed, this is a real test rather than a story
fitted afterwards.

**The seed effect survives:** restored recovered 7 of 10, contaminated 0 of 7,
Fisher one-sided p = 0.0062.

**The headline result is about variance, not location.** Verified independently
here on all twelve control fits, matched variants and matched kernel seeds:

  restored      n=6  mean 0.426  sd 0.308  range 0.057-0.810
  contaminated  n=6  mean 0.113  sd 0.039  range 0.068-0.166
  spread ratio 7.8x;  Levene p = 0.0012;  Mann-Whitney on location p = 0.066

The variance difference is an order of magnitude better determined than the mean
difference. The contaminated seed set does not merely bias the answer: it makes the
method reproducibly wrong, sd 0.039 across independent runs. Restoring the seeds
does not make it right, it makes it IRREPRODUCIBLE, sd 0.308 spanning nearly the
whole range. The contamination was masking the instability, and every consistency
check run during the contaminated period would have looked reassuring for exactly
the wrong reason.

This also retires an earlier number: the "kernel-seed noise is small, sd 0.019 to
0.033" measurement quoted in 4f and 4g was taken entirely inside the collapsed
state. It measured the reproducibility of a failure mode, not of the sampler.

The result is threshold-free and needs no subset definition and no gate, which
after the 4g/4h/4i sequence is the main thing to recommend it.

**Re-read feasibility (this session's task).** Draws for 10 of 11 site-183 fits in
iterations 30-36 were pruned by loop.py after scoring, so mode mass cannot be
recomputed from them. It CAN be recovered: the per-fit `mode.high_frac` survives in
experiments/NNN/scores/183*.json, and log.txt and result.json survive pruning too,
so seed set, host and code era remain recoverable per fit. `scripts/reread_28_36.py`
labels every fit from its own artifacts and falls back to the stored score. Dry run
over iterations 20-37: 23 jobs, mass available for all 23 (2 from draws, 21 from
stored scores). The re-read is therefore possible and is no longer blocked by the
host question, which is now settled.

## Addendum 2026-09-04k: the iterations 28-36 re-read (this session's task, complete)

Every site-183 fit in the loop record relabelled from its own artifacts
(`scripts/reread_28_36.py`): seed set from the log's "N feasible seed points"
line, host from result.json, mode mass from the fit's draws or, where loop.py had
pruned them, from `mode.high_frac` in experiments/NNN/scores. 70 jobs, mass
recovered for all 70 (6 from draws, 64 from stored scores).

**The boundary is stark and confirms 4f as corrected.** Iterations 0-28 ran on the
restored 24-row set, 29-37 on the contaminated 25-row set:

  restored(24)      n=57  mean 0.559  sd 0.234  range 0.014-0.990  recovered 39/57
  contaminated(25)  n=13  mean 0.251  sd 0.124  range 0.008-0.506  recovered  1/13
  Mann-Whitney on location p < 0.0001

Per-iteration means fall off a cliff at the boundary: i028 averages 0.990, i029
averages 0.008, and no iteration from 29 onward exceeds 0.506. So every conclusion
drawn at NL-Loo in iterations 29-36 was drawn in the collapsed state. That window
contains the tempering iterations (33-36), the surgery variants at 31-32 and the
de64 kernel test at 30.

**The loop record refutes the host hypothesis far more decisively than the controls
could.** Within the uncontaminated portion alone, n=57 rather than the controls'
n=10:

  restored on h100  n=23  mean 0.566  sd 0.235  recovered 14/23
  restored on kyo   n=34  mean 0.554  sd 0.237  recovered 25/34

The two machines are indistinguishable in both mean and spread. Combined with the
failed pre-registered prediction in 4j, the host hypothesis is closed.

**On the variance result, a caveat in the loop record's favour and against it.**
The same direction appears here, restored sd 0.234 versus contaminated sd 0.124,
ratio 1.9x, Levene p = 0.041. But the loop's restored runs span many different
variants, so their spread mixes genuine irreproducibility with real
variant-to-variant differences. The matched-variant, matched-seed control fits
(sd 0.308 vs 0.039, ratio 7.8x, Levene p = 0.0012) remain the primary evidence for
the variance claim; the loop record corroborates its direction only.

**Consequence for the campaign's conclusions.** Iterations 29-36 cannot be compared
against 0-28 at this site, and the mode-weight gate readings in that window are not
informative about the variants they were attributed to. Nothing needs re-judging in
the other direction: no variant was promoted in that window, so the contamination
did not cause a false acceptance. Its cost was wasted compute and a set of
conclusions about tempering and late surgery variants that were really conclusions
about a broken configuration.

## Addendum 2026-09-04l: three corrections to this record, and a defect in my kernel

**1. "Split-half floor" is the wrong term throughout this document.** Splitting the
reference fleet in half and measuring distance between the halves bounds the
reference's own PRECISION, not its accuracy: any bias shared by all its chains
survives the split untouched. Everywhere addenda 4d, 4g, 4h, 4i and 4k say
"split-half floor" or "the reference's own noise floor", read
"split-half self-consistency benchmark". The comparative statements are unaffected
(every variant remains 10 to 15 times that benchmark) but the word "floor" implies
an accuracy limit that this quantity does not establish.

**2. The variance result: descriptive claim stands, two-mechanism reading does
not.** 4j reported "spread ratio 7.8x"; that is an SD ratio, and the variance ratio
is about 61 here (72 on the companion session's set), which should be stated
explicitly rather than left to be inferred. More importantly, 4j went on to read
the result as two distinct phenomena, contamination BIASING the answer versus
restoration making it IRREPRODUCIBLE. That does not follow. Run-level mode mass is
bounded in [0,1], so its mean and variance move together as basin-capture
probability changes; Levene achieving a smaller p than Mann-Whitney is not evidence
of two mechanisms. What stands: the contaminated condition is tightly clustered
low, the restored condition is dispersed across nearly the whole range, and both
are described by a single capture-probability shift. The rhetorical framing in 4j
("does not merely bias, it makes the method reproducibly wrong") is withdrawn.

**3. A non-reversible burn-in heuristic ran in all 39 iterations
(scripts/sarla_kernels.py:78-90).** Every 500 steps, any walker more than
restart_gap=100 nats below the current best is HARD-COPIED onto a randomly chosen
better walker with 1e-3 jitter, with no Metropolis correction. It fires 16 times
per production run.

Verified here on the exact defaults: restart_end = restart_until * n_steps =
0.5 * n_steps and burn_end = burn_frac * n_steps = 0.5 * n_steps, i.e. the copying
stops precisely when recording begins. So it is NOT a detailed-balance violation of
the sampling phase, and no copied state is ever recorded. The accurate description
is a non-reversible burn-in pruning rule. But its consequence is not benign: it
shapes the walker population entering the sampling phase, and since this kernel
demonstrably cannot cross between allocation budgets, the mode composition left at
the end of burn-in largely determines the recorded mode mass. It is therefore a
MECHANISM AMPLIFYING seeding dominance, which is the campaign's central failure.

A clean negative from the companion session, worth keeping because the rule is a
natural thing to blame: it does not preferentially cull high-allocation walkers.
On 5534 reference draws the two modes sit at almost the same level, median HIGH
-218.3 versus LOW -219.2, a 0.9 nat separation, and at the threshold a real run
would use the rule removes 1.5% of HIGH and 4.6% of LOW draws, i.e. very slightly
biased against the LOW mode, the opposite of the proposed mechanism.

**4. On the kept-region diagnostic (refining my own 4-outcome suggestion).**
keep_regs never enters run_kernel, which I verified independently, so a low
kept-region fraction diagnoses the INITIALISATION screen rather than the production
kernel. And nearest-chart assignment is not a coverage measure at all, since every
point has a nearest chart however distant. Mode-specific nearest Mahalanobis
distances are the right diagnostic and the companion session is recording them.

**5. Power.** The stationarity check is a mechanism screen, not certification. With
six replicates, six successes and zero failures still leaves a one-sided 95% upper
bound near 39% on the per-run failure probability. Nothing from it should be
written as "the kernel is fine".
