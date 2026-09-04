# Log

Plain-language record, newest at the bottom. One entry per iteration plus
setup notes. Times are US Pacific.

## 2026-09-01 setup

- Protocol written (autoresearch.md). Public repo created. Two GPU hosts
  prepared: an H100 (3 slots) and two Blackwell RTX PRO 4500 (1 slot each).
- The first truth rule (iid EDC-feasible prior draws) was rejected before any
  fit: at every site checked, feasible prior draws are near-dead ecosystems
  with GPP below 5% of the observed value. Truths are now jittered real-data
  modes with a GPP and biomass plausibility check.

## Iteration 0 (baseline), launched 2026-09-01 22:15 PDT

- What: the current fast path (v3, `variants/v3_baseline.json`) at the four
  development sites with three kernel seeds each, and once at the four
  holdout sites. 16 fits, five GPU slots.
- Why: fixes the noise floor delta (2 sd of G over seeds) that every later
  accept/reject decision uses, and the baseline G on both site sets.
- Smoke tests before launch: new fitter reproduces v3 bitwise on CPU; the
  DE, stretch and adaptive-covariance kernels run without error at toy scale;
  the queue ran two tiny jobs end to end on the H100.

## Iteration 0 result (2026-09-02 02:40 PDT): baseline G = 1.19 on the development sites, 2.01 on holdout

- The v3 fast path is well calibrated at two sites (ES-LJu G 0.60, DE-Gri 0.78),
  acceptable at NL-Loo (0.79, but one of three seeds never reached the typical
  set: density rank 1.00), and poor at BE-Vie (2.59): there, 22 to 31 of the 89
  parameters sit more than 2 sd from the truth and the LAI projection band
  misses the truth almost everywhere. The BE-Vie truth has a nearly empty wood
  pool, and the sampler's posterior does not contain that solution.
- Holdout: CZ-wet 1.21, DE-Geb 1.05, FR-Pue 1.58, DK-Sor 4.18 (the flagged
  relaxed-plausibility truth; the sampler never found its region at all).
- Noise floor: the dev-set mean G over three kernel seeds has sd 0.11, so the
  acceptance threshold delta is fixed at 0.22 from here on.
- Cost: median 53 min per fit with three fits sharing the H100 or one per
  Blackwell GPU (about 25 min alone on the H100), 2.4M model evaluations.
- No chain was stuck at any site (the region screen and restarts from the
  earlier OSSE work hold up), so the remaining error is mixing and coverage,
  not junk regions.

## Iteration 1 result (2026-09-02 03:35 PDT): more walkers alone do not help; stretch moves match the baseline faster

- Three variants at the same 2.05M sampling evaluations, 512 walkers x 4,000
  steps each: H1 plain chart moves G 1.43, H2 chart + differential-evolution
  moves 1.30, H3 chart + Goodman-Weare stretch moves 1.20. Baseline 1.19,
  acceptance needs < 0.97. All three discarded.
- Why H1 got worse: with 4,000 steps a chart-shaped walker does not contract
  from its diverse start onto the typical set (ES-LJu 50% intervals held the
  truth 78% of the time; density rank 0.9). Steps per walker matter more than
  walker count for this kernel.
- Stretch moves repaired most of that: same quality as the baseline in 34 min
  instead of 53 (not the 2x needed for the speed path). Iteration 2 tests DE
  and stretch at 128 walkers x 16k steps, which gives each walker four times
  the steps.
- BE-Vie stayed at G 2.3 to 2.8 under every variant: no kernel tried so far
  reaches the near-zero-wood truth there.

## Protocol v2 (2026-09-02 04:00 PDT): the v1 truths were invalid

- While iteration 2 ran, I checked why BE-Vie was so poor and why one NL-Loo
  seed never reached the truth's density: the truth itself sits 780 (BE-Vie)
  to 1,230 (NL-Loo) nats below the posterior's bulk. The data terms are fine;
  the difference is entirely the model's soft ecological-constraint (EDC)
  penalties, which the random jitter had violated. A truth the model's own
  priors reject at e^-1000 is not a recovery test of the sampler.
- Consequence: runs 1-4 stay on the page as "protocol v1" but decide nothing.
  All twelve site datasets are being regenerated with an EDC-consistency check
  on the truth (within 10 nats of the mode's penalty). Iteration 4 will be
  the v2 baseline; the noise floor is re-measured there. The
  pending iteration-3 jobs were cancelled; the running iteration-2 jobs are
  allowed to finish and will be logged as v1.
- What survives from v1: the relative behaviour of the kernels (plain chart
  walkers at 512 x 4k do not contract; stretch moves match the baseline in
  62% of the time) and the fact that no chain was ever stuck.
- Update 03:10 PDT: the EDC-checked jitter cannot work either, because the
  pilot's real-data modes themselves carry soft-EDC penalties near 500 nats
  (posterior draws: about 6). The v2 truth is therefore a typical accepted
  draw from a short run of CARDAMOM's own ADEMCMC on the real data (4 chains
  x 30k iterations per site, running now on the local CPUs, about 2 h), the
  same recipe the NL-Loo OSSE used. Independent of the sampler under test and
  EDC-consistent by construction.

## Iteration 2 result (2026-09-02 05:10 PDT, protocol v1 truths, for the record only)

- DE at 128 walkers x 16k steps: 1.36; stretch at 128 x 16k: 1.19; flat-direction
  inflation x sqrt(3): 1.45. Baseline 1.19. Judged against the invalid v1
  truths, so none of this decides anything; the consistent pattern across
  iterations 1 and 2 is that stretch moves are the one change that never
  hurt, and DE moves are erratic (very good at some sites, collapsed at
  BE-Vie with density rank 0.01).
- No advisor call for this iteration (invalid truths). The GPUs idle until the
  v2 datasets exist; the truth chains are about 60% through.

## v2 truths (2026-09-02 05:15 PDT)

- The reference chains converged at NL-Loo, DE-Gri, BE-Vie, DK-Sor and CZ-wet
  (soft-EDC penalty of the last 30% of draws: median -11 to -14, the same as
  the 33-h NL-Loo reference), and not at ES-LJu, FR-Pue, DE-Geb (-28 to -125).
  Development set under v2 is therefore NL-Loo, DE-Gri, BE-Vie, DK-Sor; the
  three slow sites join CZ-wet as holdout once their 60k-iteration runs finish
  (about 4 h). Iteration 4 (v2 baseline) starts as soon as the first five
  datasets are generated.

## 2026-09-02 05:50 PDT: disk quota, and iterations 4-5 launched

- The home directory has a 100 GB quota, and the 32 truth chains (8.5 GB) plus
  the running 33-h NL-Loo arm filled it while the last v2 datasets were being
  written. Freed by thinning the finished truth chains to compact files
  (last 30%, every 10th draw; the truth selection is unchanged) and deleting
  the v1 fit outputs, which are fully represented by their scores. Fits are
  pruned after scoring from now on.
- v2 truths at NL-Loo, DE-Gri, BE-Vie, DK-Sor and CZ-wet all sit at their
  site's pooled-median log-posterior (-213 to -226) with soft-EDC penalties of
  -9 to -17, the converged range. ES-LJu, FR-Pue and DE-Geb are re-running at
  60k iterations with a smaller output footprint.
- Iteration 4 (v2 baseline, 4 dev sites x 3 seeds) and iteration 5 (stretch at
  128 x 16k, seed starts, DE at 128 x 16k) are on the GPUs; 24 fits, about
  4.5 h.

## 2026-09-02 08:20 PDT: the v2 baseline fails by not finding the basin, and L-BFGS cannot help

- First v2 baseline scores: NL-Loo G 0.94 to 1.66 with density rank 1.00 for
  all three seeds (the truth, a typical posterior draw at log-posterior -284,
  has higher density than every one of 20,000 draws; the atlas's best chart
  sits at -310 to -340). DK-Sor is worse: truth -276, seeds -946 at best, the
  kernel climbs to -351 in 32k steps and never arrives (G 14, 85 of 89
  parameters off). BE-Vie and DE-Gri are fine (rank 0.4 to 0.8).
- Diagnostic: L-BFGS from the DK-Sor seeds makes no progress at all, even
  with 3,000 iterations (the EDC penalties make the surface piecewise, and
  the optimizer stops at once). Every nat of climbing in the fast path has
  been done by the MCMC kernel. The seed/atlas stage therefore needs an
  ensemble warm-up (queued as iterations 6 and 7: 1,000 and 4,000 stretch
  steps over the seed population before the atlas is built).

## 2026-09-02 09:30 PDT: research target redirected to the atlas itself

- An external review (relayed by the user) asked the loop to make the
  self-correcting, rank-adaptive Laplace atlas its primary target instead of
  the downstream kernel. Review of `sarla.py`: rank detection, the importance
  audit, normal projection and the diagnostic labels existed, but every label
  ended in "append another Gaussian"; there were no neighbours, extents,
  strata or rank transitions.
- Implemented `sarla2.py` (see ATLAS_SURGERY.md): charts with rank, tangent
  extents, neighbours, branch ids and typed links; extend grows a chart instead
  of adding one; refine caps and tiles at a bend; split replaces a chart by two;
  branch starts a new stratum when the corrected point is not density-connected;
  rank-change links strata of different local dimension; merge fuses redundant
  neighbours. Exact MH is preserved (mixture weights known; atlas frozen before
  sampling). Round-by-round diagnostics are logged and reach the score files.
- Box problems: the hidden mode is now classified as a branch (exact 0.50
  mass); on a ridge that turns into a bump, true extend gives KL 0.23 vs 0.58
  for v1 with one chart instead of two; the banana is on par; seeding on the
  bump fires rank-change correctly but repeated splits cost coverage.
- The idea bank now carries an atlas-geometry family S1-S10 with priority
  over kernel tuning. Iteration 8 tests S1 (surgery defaults), S2 (no normal
  projection) and S3 (tangent-volume weights). The surgery knobs are
  first-class Variant fields (prefix sg_).
- The v2 baseline's defect fits this redirect exactly: at NL-Loo, DK-Sor and
  CZ-wet the atlas never covers the posterior's basin (baseline G 0.9-1.7,
  3.0-14, 5.2 respectively), while BE-Vie and DE-Gri are fine.
- 09:15 PDT: queue reordered. The 16 not-yet-started warm-up jobs (iterations
  6 and 7) were withdrawn so the surgery experiments (iteration 8) run right
  after the remaining kernel jobs of iteration 5; the warm-up jobs are
  resubmitted once iteration 8 is on the GPUs (job files kept under
  runs/autoresearch/queue/deferred).

## Iteration 4 result (2026-09-02 09:45 PDT): v2 baseline G = 1.72 on the development sites (capped), 5.0 on the one holdout site scored

- With valid truths the fast path's problem is no longer under-dispersion but
  coverage: at NL-Loo every seed gives density rank 1.00 (the truth has
  higher density than all 20,000 draws; the atlas's best chart sits 30 to 60
  nats below the truth), at DK-Sor the posterior sits in the wrong basin
  altogether (G 14.0 / 2.6 / 3.0 across seeds, 85 of 89 parameters more than
  2 sd off in the worst case), and CZ-wet (holdout) scores 5.2. BE-Vie (1.11)
  and DE-Gri (0.82) are fine.
- Protocol v3: site G capped at 5 in aggregates, because DK-Sor's fat tail
  alone had set the acceptance threshold to 3.4. Under v3 the baseline is
  G_dev 1.72, noise floor delta 0.86 (still large: the baseline itself is
  erratic at the two hard sites).
- Consequence for the research direction: the atlas must find and cover the
  posterior's basin. Iteration 8 (surgery engine, three variants) is next in
  the queue after the remaining kernel jobs of iteration 5.
- Advisor (iteration 4) concurs: surgery first, then seed starts and
  tangent-volume weights (all queued), restart tuning afterwards; kernel tuning
  paused until the basin is shown to be represented. Page redesigned: live
  "right now" panel, per-site heatmap, protocol bands, reading guide.

## Iteration 5 result (2026-09-02 10:50 PDT): population kernels halve the gap at the hard site; decision deferred to more seeds

- Against valid truths: chart + DE moves at 128 walkers x 16k steps gives
  dev G 0.96, chart + stretch 1.05, seed starts 1.33; baseline 1.72. At DK-Sor
  the two population kernels score 1.3 to 1.4 where the baseline scored 3.5
  (capped), so ensemble moves do find the basin that the chart walk misses.
- Neither clears the acceptance threshold (0.86 below baseline) on one seed,
  and the protocol's confirmation rule asks for three seeds before promotion.
  Two more kernel seeds of both variants are queued as iteration 9.
- Seed starts (H9) discarded: NL-Loo and DK-Sor still miss the basin.
- First surgery fits (iteration 8, still running): DK-Sor G 1.02 with a
  perfect typical-set gap (44 vs the expected 44.5) but density rank still
  1.00; the 89-D audit trace is dominated by "branch" operations and the
  importance ESS stays near zero through six rounds, so the audit-driven
  repair is far from converged at this scale (a knob problem: branch_tau and
  the segment test are tuned for 2-D). Full verdict when all 12 fits land.

## Iteration 8 result (2026-09-02 13:20 PDT): first surgery experiments, all better than baseline, none by enough yet

- Surgery defaults 1.33, without normal projection 1.29, with tangent-volume
  weights 1.16; baseline 1.72 (threshold 0.86 below). All discarded on one
  seed under the rule, but the trend is consistent: the surgery atlas lifts
  DK-Sor from 3.5 to about 1.0 and the sampler's best draws now reach the
  truth's density at three of four sites (at NL-Loo still 8 to 14 nats short).
- What the round-by-round diagnostics say at 89-D: six audit rounds add
  40 to 50 charts, almost all by "branch" (17 to 35 per fit) and "rank-change"
  (5 to 28); extend never fires, merge never fires, splits are rare, and the
  importance ESS stays at 0.0002 with 50 to 114 uncovered draws at the end.
  The 2-D-tuned tolerances (model error 2 nats, branch dip 10 nats) make
  every discrepancy a new stratum in 89 dimensions. Iteration 11 tests
  tolerances scaled for 89-D (model_tol 20, bend_tol 3, branch_tau 100, 16
  flags per round, volume weights).
- Wall-clock: surgery adds no time (49 to 61 min per fit, same as baseline).
- Advisor (iteration 8): combine volume-weighted surgery with the DE kernel,
  confirm S3 with two more seeds, test branch_tau 20 next to the queued 100.
  Queued as iteration 12 (12 fits). Kernel-only DE/stretch confirmations
  (iteration 9) and surgery+DE / branch_tau 100 (iteration 10) are running.
- 14:40 PDT: all twelve v2 datasets exist. The three slow holdout sites'
  truths come from 60k-iteration reference runs; ES-LJu and FR-Pue posteriors
  sit at soft-EDC penalties near -118 for every draw, so the consistency rule
  is now relative to each site's reference chain (see autoresearch.md). Their
  baseline fits are queued to complete the baseline's holdout score.
- 16:30 PDT: the 33-h NL-Loo ADEMCMC reference arm (run by a sibling session)
  had crashed at 05:57 with a write error: the home-directory quota that my
  truth chains filled. It is being restarted on the large local data volume.
  The loop's job mirror and truth-chain archives now live there as well
  (symlinked from runs/), so the loop can no longer starve the home quota.

## Iterations 9 and 10 (2026-09-02 17:30 PDT): population kernels confirmed at 1.05; surgery + DE is the best screen at 0.92

- Three-seed results: chart + DE 1.05 +/- 0.09, chart + stretch 1.05 +/- 0.01,
  baseline 1.72 +/- 0.43. Under the v3 rule neither is accepted (0.67 short of
  the 0.86 threshold that the baseline's own erratic seeds set); the
  two-sample test gives t = 2.6 for both. Protocol v4 (logged) adopts that
  test from iteration 13, where DE runs three fresh seeds.
- Iteration 10 single-seed screens: surgery atlas + DE kernel 0.92 (best so
  far; NL-Loo 0.97, BE-Vie 0.80, DE-Gri 0.85, DK-Sor 1.06), surgery with a
  100-nat branch threshold 1.01. Confirmation seeds for surgery + DE queued.
- Mode weights are the unsolved part. The NL-Loo OSSE truth is in the
  high-allocation mode (f_wood 0.64). Fraction of posterior mass there across
  seeds: baseline 0.11 / 0.58 / 0.55, DE 0.52 / 1.00 / 0.82, stretch
  0.51 / 0.26 / 0.81. From now on promotion also requires that this fraction
  be stable across seeds (sd <= 0.10) at NL-Loo and DK-Sor, and every
  candidate is fitted once to the real NL-Loo data to compare with ADEMCMC's
  0.815 (queued for baseline, DE, surgery+DE, volume-surgery+DE).
- Suggestions received from the sibling OSSE session (relayed from the user)
  and added to the idea bank: likelihood-only tempering with the EDC gate at
  every rung and mode-stratified initialisation (T1), and a two-cell bridge
  estimator of the relative mode mass to reweight pooled DE draws (B1).
- Correction (19:55 PDT): the 13-h partial output of the crashed reference
  arm no longer exists (deleted during the redirect by the sibling session);
  nothing will be scored on it. The 32-chain NL-Loo OSSE reference arm was
  relaunched at about 19:50 PDT on the data volume, a fresh 33 h.

## B1 first test (2026-09-02 20:00 PDT): a bridge estimate of the mode weights points the right way but is noisy

- Two-cell bridge sampling (cells: wood allocation above / below 0.5) with a
  kernel-density proposal on the cell's own draws (a moment-matched Gaussian
  is entirely EDC-infeasible at 89-D; bandwidth 0.3 sd also infeasible, 0.1 sd
  works). On the volume-surgery + DE fit at NL-Loo the pooled draws put 8% of
  the mass in the high-allocation mode; the bridge says about 100% (split
  halves 0.99 and 0.72). The OSSE truth is in that mode, and ADEMCMC on real
  data puts 82% there, so the direction is right but the estimate is too
  noisy to reweight with yet. Next: smaller bandwidth, more proposal draws,
  and the three fresh DE fits of iteration 13 as test cases.

## Iteration 11 result (2026-09-02 20:30 PDT): scaling the tolerances does not change what the surgery does at 89-D

- Surgery with model error 20 nats, bend 3 sigma, branch dip 100 nats, 16 flags
  per round and volume weights: dev G 1.05 on one seed (NL-Loo 1.22, BE-Vie
  0.79, DE-Gri 0.82, DK-Sor 1.39). Better than the baseline, no better than the
  earlier surgery variants.
- The diagnostics are the point: 36 to 45 branch and 34 to 45 rank-change
  operations per fit, 1 to 3 splits, 3 to 6 refines, no extend, no merge,
  importance ESS 0.0002 after six rounds, 70 to 100 uncovered draws at the
  end. So (a) a straight segment between a chart centre and a corrected point
  dips by more than 100 nats almost always in 89-D (the EDC penalties make
  the surface rugged), so "not density-connected" is not a usable branch
  criterion here; and (b) local rank as counted by the spectral-gap rule
  varies between 24 and 54 from chart to chart on a near-continuous spectrum,
  so "rank-change" is mostly noise. The surgery is real, but its two
  topological tests are tuned to 2-D geometry. Iteration 16 disables the gap
  rule (rank = eigenvalues below prior curvature), demands a 4x-robust rank
  change and a 1000-nat dip for a branch, to see whether extend/refine/merge
  then carry the repair.

## Iteration 12 result (2026-09-02 21:00 PDT): volume-weighted surgery confirmed at 1.16 over three seeds; adding the DE kernel to it does not help further

- Surgery with tangent-volume weights, three seeds: 1.16 with a seed spread of
  about 0.05 (baseline 1.72 +/- 0.43). Under v3 not promoted. NL-Loo remains
  the site where the atlas never reaches the truth's density (rank 1.00 for
  all three seeds), so the gain comes from DK-Sor and BE-Vie.
- Volume-weighted surgery + DE kernel, one seed: 1.03; the uniform-weight
  surgery + DE (0.92, iteration 10) remains the best screen and its
  confirmation seeds are queued (iteration 14).
- Running now: fresh DE seeds (iteration 13) for the first v4 decision.
- 21:40 PDT: likelihood-only parallel tempering implemented
  (scripts/sarla_tempered.py): 4 rungs with inverse temperatures 1 to 0.05,
  32 walkers each, chart/DE moves within rungs, adjacent swaps every 10 steps,
  EDC gate and EDC penalties at full strength on every rung, only the cold
  rung recorded (exact). Toy-scale check: swap acceptance 0.38 / 0.51 / 0.14.
  Queued as iteration 17 with and without the surgery atlas (8 fits).
- B1 second test (22:00 PDT): on a fresh DE fit at NL-Loo (pooled high-mode
  fraction 0.62) the bridge gives 0.22 at bandwidth 0.05 sd and 0.10 at 0.1
  sd, with split halves disagreeing by 0.3, and the cell evidences shift by 44
  nats between bandwidths. The kernel-density proposal is too narrow to
  bridge an 89-D cell; the estimator is not usable as built. Parked; the
  tempering test (iteration 17) is the route to correct mode weights.

## Iteration 13 result (2026-09-02 23:15 PDT): the DE kernel passes the score test and fails the mode-weight gate

- Three fresh kernel seeds, protocol v4: chart + DE moves at 128 walkers x
  16k steps gives dev G 1.07 +/- 0.08 against the baseline's 1.72 +/- 0.43;
  the two-sample test passes (t = 2.6), the per-site guard passes, wall-clock
  is unchanged.
- The mode-weight gate fails, and not marginally: the fraction of posterior
  mass in the high-wood-allocation mode is 0.61 / 0.84 / 0.71 across seeds at
  NL-Loo (truth is in that mode) and 0.97 / 0.06 / 0.27 at DK-Sor (truth in
  the low mode). The kernel visits both modes but their relative weight is
  set by which walkers happened to start where. This is exactly the mode
  inversion seen on the real NL-Loo data, now reproduced under a known truth.
- Not promoted. Tempering (iteration 17, queued) is the candidate designed
  to fix this; surgery + DE confirmation (iteration 14) and stretch fresh
  seeds (15) are running.

## Iteration 14 result (2026-09-03 01:00 PDT): surgery + DE is the best score yet (0.96) and still fails the mode-weight gate; first real-data check

- Surgery atlas + DE kernel over three seeds: dev G 0.96 +/- 0.04 (baseline
  1.72 +/- 0.43; two-sample t = 3.0). Per site 1.02 / 0.78 / 0.78 / 1.21
  (NL-Loo / BE-Vie / DE-Gri / DK-Sor). Not promoted: at NL-Loo the
  high-allocation mode holds 54%, 32% and 79% of the mass across seeds
  (gate needs an sd of 0.10 or less); at DK-Sor the weights are stable
  (5 to 11%).
- Real NL-Loo data, one fit each, fraction of mass in the high-allocation
  mode against the converged ADEMCMC reference of 0.815 (90% CI 0.79-0.83):
  baseline 0.54, DE 0.59, surgery + DE 0.61, volume-weighted surgery + DE
  0.91. None inside the interval. Every chain sits entirely in one mode
  (per-chain spread 0.25 to 0.47), so the fraction is set at initialisation.
  Interesting aside: the surgery + DE fits reach best log-posteriors of
  -184.5 and -179.2 on the real data, above the 64-chain ADEMCMC fleet's best
  of -192.8.
- Conclusion so far: the population kernels and the surgery atlas fix
  coverage and score; the relative mode weight remains a coin toss decided
  by where walkers start. Tempering (iteration 17) is the queued remedy;
  256-walker DE (18) tests the cheap alternative.

## Iteration 15 result (2026-09-03 02:50 PDT): stretch kernel, same verdict as DE

- Three fresh seeds: dev G 1.00 +/- 0.03 (t = 2.9 against the baseline). Mode
  weights: 60% / 75% / 30% at NL-Loo and 4% / 99% / 8% at DK-Sor. The
  population kernels are all better than the baseline by about 0.7 in G and
  all fail the mode-weight gate the same way: every chain lives in one mode
  for the whole run, so the mixture weight is whatever the initialisation
  gave. Not promoted.
- Three of the four families tested so far (kernels, atlas surgery, starts)
  improve calibration without fixing the mode weights. Iterations 16 to 18
  (absolute-rank surgery, tempering, 256 walkers) are on the GPUs; tempering
  is the only one designed to move mass between modes.
- 03:15 PDT: first full-scale tempering fit (4 rungs, beta 1 / 0.37 / 0.14 /
  0.05): DE-Gri G 0.87, but adjacent-rung swap acceptance only 3-5%: the
  ladder is far too coarse for a likelihood whose spread across modes is tens
  of nats. A 16-rung ladder (ratio 0.79, 16 walkers per rung, same budget) is
  queued as iteration 21 on the two mode-sensitive sites.

## Iteration 16 result (2026-09-03 03:40 PDT): the surgery's branch test was measuring infeasibility, not topology

- Surgery with the spectral-gap rank rule off, a 4x-robust rank change and a
  1000-nat branch threshold: dev G 1.20 on one seed (BE-Vie 0.75, DE-Gri 0.85,
  DK-Sor 1.79, NL-Loo 1.39). Still 39 branch and 45 rank-change operations per
  fit. Reading the code against the trace: the connectivity test declared
  "not connected" whenever any midpoint of the straight segment was
  infeasible under the hard EDC gate, and at 89-D almost every segment between
  two feasible points leaves the thin feasible set. The engine was labelling
  gate crossings as new strata. This is now a switch (default unchanged for
  reproducibility); iteration 20 tests the variant where gate crossings are
  "unknown" and the repair falls to refine/extend.

## Iteration 17 result (2026-09-03 05:00 PDT): a 4-rung ladder does not temper this posterior

- Likelihood-only parallel tempering, 4 rungs, 32 walkers each: dev G 0.98
  (0.99 with the surgery atlas), single seeds. Adjacent-rung swap acceptance
  0 to 2% at every site: the temperature steps (factor 2.7) are far too large
  for a data likelihood whose spread is tens of nats, so the rungs never
  exchange walkers and the result is DE with a quarter of the walkers.
  NL-Loo high-allocation mass 0.22 with the truth in that mode.
- A 16-rung ladder (temperature ratio 0.79, 16 walkers per rung, swaps every
  5 steps, same evaluation budget) is queued as iteration 21 on the two
  mode-sensitive sites; if its swap rates reach 20-40% it becomes the first
  variant that can actually move mass between the wood-allocation modes.
- 05:10 PDT: queue reordered again so the 16-rung tempering test (iteration
  21) runs right after the 256-walker DE test (18); the six-rung tempering
  (19), the no-branch-on-gate surgery (20) and surgery + adaptive covariance
  (22) are withdrawn for now and will be resubmitted afterwards
  (runs/autoresearch/queue/deferred2).

## Iteration 18 result (2026-09-03 05:15 PDT): more walkers do not stabilise the mode weights

- Chart + DE at 256 walkers x 8,000 steps (same evaluations), three seeds on
  the two mode-sensitive sites: G worse (NL-Loo 1.44 to 1.64, DK-Sor 1.59 to
  1.81; each walker gets too few steps) and the high-allocation mass at
  NL-Loo still 0.38 / 0.46 / 0.67 across seeds. Discarded. The 16-rung
  tempering fits are running now.

## Iteration 21 result (2026-09-03 06:20 PDT): a working temperature ladder, and still the wrong mode weight

- 16 rungs (temperature ratio 0.79), 16 walkers each, swaps every 5 steps:
  adjacent-rung swap acceptance 26 to 42% at both sites, so the rungs now
  exchange walkers freely. Yet at NL-Loo the cold rung ends with density rank
  1.00, its median log-posterior 40 nats below the truth's, and 12% of its
  mass in the high-allocation mode where the truth sits (G 0.96); DK-Sor G
  1.46 with 20% in the high mode (truth in the low mode).
- Reading: with 8,000 steps and 16 walkers per rung the cold chain has not
  equilibrated; tempering is not yet disproved, but at the fixed budget it
  does not beat the plain population kernels. A diagnostic run at twice the
  sampling budget (iteration 24, labelled as such and not a promotion
  candidate) will tell whether the ladder equilibrates the weights given
  time. Six-rung tempering (iteration 19) is landing with swap rates of 3 to
  18% and G 0.81 to 0.91 on the first two sites.

## Iteration 19 result (2026-09-03 07:20 PDT): six rungs, same story

- Six-rung tempering, 24 walkers per rung: dev G 0.98 (single seed), swap
  acceptance 3 to 18%. High-allocation mass 0.30 at NL-Loo and 0.23 at
  BE-Vie against truths in that mode; DK-Sor 0.35 against a low-mode truth.
  Every tempering configuration at the fixed budget lands between 0.96 and
  0.99 in G with the same mode-weight problem as the plain kernels. The
  2x-budget diagnostic (iteration 24) decides whether time is the missing
  ingredient. Feasible-path surgery with the DE kernel queued (iteration 25).

## Iteration 20 result (2026-09-03 08:20 PDT): removing the false branches makes the surgery atlas the best chart-walk variant so far

- Surgery with gate-crossing segments treated as "unknown" instead of new
  strata (plus 89-D tolerances, no spectral-gap rank rule, volume weights),
  baseline chart-shaped kernel, one seed: dev G 0.93 (NL-Loo 0.96, BE-Vie
  1.00, DE-Gri 0.72, DK-Sor 1.06). Level with surgery + DE (0.92) without any
  population moves, and better than every earlier surgery variant (1.05 to
  1.33). Confirmation seeds queued (iteration 28).
- The operation mix moved from branch to rank-change (77 to 82 per fit): the
  local rank still varies between charts by dozens of dimensions, so
  "rank-change" is doing the work of add-a-chart. Iteration 26 requires a rank
  jump of at least 18 dimensions before calling it a rank change.

## Iteration 22 result (2026-09-03 08:50 PDT): surgery + adaptive covariance is erratic

- Surgery atlas with the adaptive pooled-covariance kernel (no DE jumps),
  single seed: dev G 1.16 but 0.53 to 1.71 across sites. A globally learned
  within-mode covariance does not substitute for cross-mode moves. Discarded.
- Feasible-path surgery (iteration 23) is landing: 0.68 to 1.60 on the first
  three sites, so not obviously better than the gate-fix variant (0.93).

## Iteration 23 result (2026-09-03 09:20 PDT): feasible-path connectivity does not help

- Surgery with the feasible-path connectivity rule, single seed: dev G 1.36
  (NL-Loo 1.60, BE-Vie 1.18, DE-Gri 0.68, DK-Sor 1.96). Worse than treating
  gate crossings as unknown (0.93, iteration 20), and the operation mix is the
  same (about 75 rank-changes per fit). Discarded. The rank-jump threshold
  (iteration 26) is the remaining lever on the operation mix.

## Iteration 24 result (2026-09-03 10:10 PDT): tempering does not equilibrate the mode weights even with twice the budget

- Diagnostic only (4.1M evaluations, twice the protocol budget), 16 rungs with
  26 to 42% swap acceptance: NL-Loo G 0.87 and DK-Sor 1.47, both with density
  rank 1.00 and the cold rung's median 25 to 30 nats below the truth; high-
  allocation mass 0.19 at NL-Loo (truth in that mode) and 0.08 at DK-Sor.
  With a working ladder and double the steps the cold chain still does not
  reach the truth's density, so time is not what tempering lacks. Tempering
  is parked; the full-posterior variant (iteration 27, which also flattens
  the EDC penalties) is the last tempering test in the queue.
- House rule recorded: the local A100s are never used unless the user asks;
  all local work runs on CPU.

## Iteration 25 result (2026-09-03 10:40 PDT): feasible-path atlas + DE kernel, 1.13

- Single seed, 0.80 to 1.39 across sites. Below surgery + DE with the default
  (0.96 over three seeds) or gate-fix atlas. Discarded.
- Iteration 26 (rank changes only for jumps of 18+ dimensions) is landing and
  its operation mix is, for the first time at 89-D, geometric: 61 to 72
  refines, 9 to 10 splits, 5 to 10 rank changes and 3 to 5 branches per fit
  instead of 80 rank changes; first two sites G 0.79 (BE-Vie) and 0.69
  (DE-Gri). Extend and merge still never fire: the quadratic model error at a
  corrected point is never below 20 nats, so every out-of-extent flag becomes
  a refine (a bend), and no two charts ever explain each other's centres.

## Iteration 26 result (2026-09-03 11:30 PDT): the operation mix is finally geometric, and it does not help yet

- With rank changes restricted to jumps of 18+ dimensions (and gate crossings
  treated as unknown), the repair at 89-D becomes 60 to 73 refines, 6 to 10
  splits, 1 to 10 rank changes and 2 to 5 branches per fit: the surgery is
  doing what it was designed to do. Dev G on one seed: 1.18 (BE-Vie 0.79,
  DE-Gri 0.69, NL-Loo 1.76, DK-Sor 1.48). NL-Loo put 94% of its mass in the
  high-allocation mode this time (truth 0.64), DK-Sor 0%: the mode weights
  are still set by luck.
- The audit still ends every run with about 100 uncovered draws and an
  importance ESS of 0.0002, so the atlas never gets close to covering the
  posterior in six rounds regardless of which operation repairs each flag.
  The large-audit variant (iteration 29) and the atlas independence jumps
  (32) are the next tests of that.

## Iteration 27 result (2026-09-03 12:20 PDT): tempering the EDC penalties too is the first tempering run that reaches the truth's density

- Full-posterior tempering (the EDC penalty terms flattened along with the
  data term; the hard feasibility gate kept at every rung), 16 rungs, swap
  acceptance 27 to 40%: at NL-Loo G 0.75, density rank 0.95, the cold rung's
  best draw above the truth's log-posterior for the first time in any
  tempering run, and 39% of the mass in the high-allocation mode (truth in
  that mode; the likelihood-only ladders gave 12 to 22%). DK-Sor 1.30 with
  9% high-mode mass (truth 0.29). One seed, two sites: the remaining two
  development sites and two more seeds at NL-Loo and DK-Sor are queued
  (iteration 33). This supports the sibling session's reading that the
  barrier between the allocation modes is the EDC penalty surface, not the
  data term.

## Findings received from the sibling OSSE session (2026-09-03 13:00 PDT), real NL-Loo data

- Barrier between the two wood-allocation budgets: along actual ADEMCMC
  transitions the log-posterior dips only 10 to 38 nats below the lower
  endpoint, and the dip is made of soft EDC penalties (state_trajectories
  first, then the cfcr / nsc / fffr ratio constraints), with the data term flat
  or rising. An ADEMCMC walker crosses f_wood = 0.5 dozens of times per few
  thousand iterations: for it the two "modes" are not separate basins but one
  low, EDC-textured ridge. (A 700-nat wall seen along a straight line in z was
  an interpolation artefact.) This matches iteration 27: flattening the EDC
  penalties is what lets the cold chain cross; the chart walk and the DE moves
  at our budget cross it rarely, so the weights depend on initialisation.
- New maximum of the real-data posterior: log-posterior -161.9 (hard gate,
  verified under jitter), found by L-BFGS from a high-allocation Laplace
  chart, and it lies in the LOW-allocation budget (f_wood 0.19, wood residence
  43 yr). ADEMCMC's best draw is -192.5 (f_wood 0.77, 10 yr); 82% of the
  posterior mass is in the high-throughput budget while the density maximum
  is in the plausible one. A MAP product and a posterior-median product would
  report opposite wood residence times at this site. Damped Newton with the
  exact Hessian was not the tool (stalled at -186; some Hessians still NaN).
- Queued: full-posterior tempering on the real NL-Loo CBF (iteration 35), to
  compare its high-mode mass with ADEMCMC's 0.815.
- 13:30 PDT: per the sibling session's per-EDC profile of real ADEMCMC
  mode transitions (state_trajectories carries most of the soft-EDC part of
  the 10-38 nat crossing dip; cfcr_ratio and nsc_ratio occasionally; the other
  12 EDCs nothing), selective tempering is implemented: the data term plus a
  chosen list of EDC penalties is flattened, the hard gate and the remaining
  EDCs stay at full strength. Queued as iteration 36 on NL-Loo and DK-Sor.
  The real-data MAP point (log-posterior -161.9, found by the sibling
  session) is added to the NL-Loo seed files (a feasible point; feasibility
  depends on parameters only).
- 14:00 PDT, from the sibling session's MAP test on the NL-Loo OSSE with the
  ADEMCMC-draw truth (f_wood 0.80): the global posterior maximum (-263.2) is 61
  nats above the truth's density and in the LOW-allocation budget (f_wood
  0.21); optimiser endpoints form two families of local maxima, one per
  budget, the low family holding the peak by about 10 nats as on the real
  data. With a known truth in the high-allocation budget a MAP product gets
  the wood budget wrong while the posterior mass gets it right. This is why
  the loop scores calibration of the mass, and why the real-data MAP at
  -161.9 in the plausible budget is not evidence for that budget at Loobos.
- 12:10 PDT, two more negative results from the sibling session, both about
  weight estimators and both consistent with the loop's bridge failure:
  (a) a two-hill Laplace mass estimate (Gaussian at each budget's maximum)
  cannot work at 89-D with EDC walls: both "maxima" have 9 to 13 negative
  Hessian eigenvalues (wall-bounded points), 13 to 21 eigenvalues below prior
  precision, and only 1% of draws from either Gaussian are feasible; on the
  OSSE it gives 0.000 for a truth in the high hill, and its 0.80 on real data
  is a convention coincidence. (b) Gauss-Newton / Levenberg-Marquardt with the
  exact residual Jacobian stalls where damped Newton stalled (real -185.8,
  OSSE -294.3 vs L-BFGS -161.9 / -263.2): the quadratic model step is
  rejected and the method degenerates to short gradient steps. Newton-family
  optimisers are off the table for the point estimate; L-BFGS seeds stay.

## Iteration 28 result (2026-09-03 13:10 PDT): the gate-fix surgery's 0.93 was seed luck

- Three seeds pooled with iteration 20: dev G 1.47 +/- 0.56. NL-Loo alone
  gives 0.95, 2.64 and 5.20 across seeds (the last a wrong-basin failure),
  while BE-Vie, DE-Gri and DK-Sor are stable (1.03, 0.84, 1.13). With the
  chart-shaped walk, whichever atlas is built, NL-Loo's outcome depends on
  where the 64 chains start. Not promoted. The population kernels never
  showed this failure mode (their worst NL-Loo seed was 1.36), so the
  remaining surgery tests are combined with the DE kernel (iterations 31, 32).

## Iteration 29 result (2026-09-03 13:50 PDT): a four-times larger audit does not improve the atlas

- 16,384 audit draws per round with an ESS stop, sampling shortened to keep
  the budget: dev G 1.11 (0.77 to 1.48 across sites), single seed. Uncovered
  draws per audit grow in proportion (230 to 519 of 16,384) and the ESS stays
  at 0.0001, so the stop never triggers: the audit is not the bottleneck,
  the atlas simply covers a small fraction of the posterior after six repair
  rounds no matter how well the gap is measured. Discarded.

## Iteration 31 result (2026-09-03 15:10 PDT): gate-fix atlas + DE equals the default atlas + DE

- Single seed: dev G 0.96, the same as surgery + DE with the default atlas
  (0.96 over three seeds). This run put only 3 to 15% of the mass in the
  high-allocation budget at every site, including NL-Loo and BE-Vie where the
  truths are in that budget: consistent, and consistently wrong there. The
  sibling session's interactive explainer of today's two-hills findings is
  now linked from the page (Deep dives).

## Iteration 30 result (2026-09-03 15:50 PDT): longer DE trajectories do not stabilise the weights either

- Chart + DE at 64 walkers x 32k steps, three seeds at NL-Loo and DK-Sor:
  G 0.68 / 1.17 / 1.66 at NL-Loo with high-allocation mass 0.48 / 0.06 / 0.07
  (truth 0.64), G 1.08 to 1.36 at DK-Sor with mass 0.07 to 0.19 (truth 0.29,
  low budget). Neither 256 x 8k (iteration 18) nor 64 x 32k moves the DE
  kernel's weights off their initialisation. Discarded. Mode-stratified
  starts (half the walkers on high-allocation charts) are queued for both the
  DE kernel and full-posterior tempering (iteration 39).

## Iteration 32 result (2026-09-03 16:40 PDT): global jumps from the atlas mixture are never accepted

- Exact independence-Metropolis proposals drawn from the frozen surgery atlas
  (20% of steps) were accepted 5 to 10 times in 100,000: an 89-D mixture
  whose importance ESS is 0.0002 is not a usable global proposal, and the
  atlas as built covers too little of the posterior to teleport walkers
  between budgets. Dev G 1.85, with NL-Loo landing in the wrong basin
  (4.42). Discarded. Together with iterations 26 and 29 this closes the
  question for the current engine: the audit-and-repair loop improves where
  the chart walk starts, not what the atlas covers.

## Iteration 33 result (2026-09-03 17:20 PDT): full-posterior tempering is the most seed-stable variant yet

- 16-rung tempering of the whole finite posterior (hard gate kept), three
  seeds at NL-Loo and DK-Sor, one at BE-Vie and DE-Gri: NL-Loo G 0.75 / 0.65
  / 0.68 (seed sd 0.05, against 0.55 to 1.66 for the chart walk and 0.78 to
  1.36 for DE), high-allocation mass 0.39 / 0.36 / 0.17 (truth 0.64); DK-Sor
  1.29 / 1.46 / 1.28, mass 0.07 to 0.12 (truth 0.29); BE-Vie 1.06, DE-Gri
  0.71. Dev G 0.95 so far.
- Verdict pending: the mode-weight gate is marginal at NL-Loo (sd 0.12 vs
  0.10 allowed) and passes at DK-Sor; the score test needs three seeds at
  all four sites, so BE-Vie and DE-Gri seeds 6 and 7 are queued (iteration
  40). Note for the record: stability is not correctness; at NL-Loo the
  tempered mass in the high-allocation budget (0.17 to 0.39) is well below the
  truth's budget, so even a passing gate would leave the weights biased.

## Iteration 35 (2026-09-03 18:30 PDT): full-posterior tempering on the REAL NL-Loo data puts 22% of the mass in the high-allocation budget; ADEMCMC says 82%

- One fit of the 16-rung full-posterior tempering on the real NL-Loo CBF:
  high-allocation fraction 0.22 (ADEMCMC reference 0.815, 90% CI 0.79-0.83),
  per-chain spread 0.32. Its best draw reaches log-posterior -162.0, the
  new maximum found yesterday by L-BFGS (the point was added to the seed
  file), which lies in the low-allocation budget. So on real data the
  tempered chain concentrates around the density peak and under-weights the
  broad high-throughput budget that carries most of the mass: the opposite
  error to the chart walk's, and the same peak-versus-mass tension the
  sibling session measured. None of the fast-path variants so far reproduces
  0.815: baseline 0.54, DE 0.59, surgery+DE 0.61, volume-surgery+DE 0.91,
  tempering 0.22.
- Iteration 34 (DE step scale within tempering) is landing with the best
  NL-Loo scores of the campaign: G 0.47 (gamma 0.12) and 0.54 (gamma 0.25),
  high-allocation mass 0.31 and 0.51 (truth 0.64).
- Follow-up on the 0.22 (sibling session's confound check, 18:50 PDT): per
  cold walker, 12 of 16 visited both budgets during the recorded 308 draws,
  with a mean of 29 budget switches per walker (ADEMCMC: about 16 per 60
  stored draws), while 4 walkers never left the low budget. So the tempered
  cold chain does cross, frequently, and still integrates to 22% high-
  allocation mass against ADEMCMC's 82%: two samplers that both traverse the
  ridge disagree on the weight. A control with the MAP point removed from the
  seed file is queued (iteration 42) to rule out seeding; until it lands the
  0.22 carries that caveat.
- Correction and a finding (19:00 PDT): the real-data tempering fit's cold
  rung accepted 22% of chart moves and only 0.5% of DE moves (swaps 26 to
  46%). With 16 walkers per rung the differential-evolution vectors are drawn
  from 8 partners and almost never accepted, so within the tempering runs the
  movement is chart walk plus swaps. An 8-rung ladder with 32 walkers per rung
  is queued (iteration 43) to see whether DE recovers inside rungs.

## Toy referee (2026-09-03 20:10 PDT): the tempering kernel is biased; its tempering results are withdrawn pending a fix

- On the 24-D toy (six basins with known weights 0.35 / 0.25 / 0.15 / 0.12 /
  0.08 / 0.05), the same code paths used on CARDAMOM give: chart walk 64 x 32k
  basin-mass TV 0.13, chart + DE 128 x 16k TV 0.14, and the tempering kernel
  (16 rungs, 256 x 8k, whole density flattened, swaps 0.5 to 0.7) TV 0.44
  with masses 0.79 / 0.21 / 0.00 / 0.00 / 0.00 / 0.00; 8 rungs TV 0.53. The
  tempering kernel concentrates mass in the largest basin and empties the
  rest, which a posterior-invariant kernel cannot do at any budget. One
  defect is found already (the DE difference vector inside rungs was gathered
  along a single coordinate); ablations without swaps, with one rung, and
  with chart moves only are running to localise the bias.
- Consequence: every tempering result above (iterations 17, 19, 21, 24, 27,
  33, 34, 35) is the output of a kernel that fails a known-answer test and
  must not be read as a posterior estimate; the real-data 0.22 in particular
  is void. The pending tempering jobs (37, 39-T2, 40 to 43) are withdrawn
  until the kernel passes the toy.
- Ablations on the toy (20:40 PDT): one rung 0.10, 16 rungs without swaps
  0.13, 16 rungs with swaps 0.44 (chart-only 0.48; mild ladder to beta 0.3
  0.43). The bias enters through the swap step. The swap acceptance formula
  and the in-place exchange read correctly; a run with all rungs at beta = 1
  (swaps without a temperature gradient) is running to separate mechanics
  from the tempered targets. Iterations 34 and 36 (tempering) recorded as void.

## 2026-09-03 late evening: tempering resolved, run stopped on request

**What the toy referee actually found.** The tempering kernel is exact: with all
rungs at beta = 1 (swaps always accepted) the toy masses are recovered (TV 0.09),
and the swap acceptance and exchange code check out. What fails is ergodicity on
budget. On the toy no rung's own moves change basin (hot-rung basin changes 0.003
per 13 steps without swaps); the swap chain then merely permutes a fixed pool of
basin labels set by the initialisation, and the cold rung collects the densest
states: the two heavy, narrow basins (0.84/0.16 instead of 0.35/0.25/0.15/0.12/
0.08/0.05). Four times more steps, swaps every step (85 round trips), hotter
ladders (beta_min 0.003 and 0.001, 32 rungs), DE-heavy mixes and hot-rung
independence moves from the atlas mixture (accepted 0.1%: the atlas is a poor
proposal for the warped basins at any temperature) all leave the cold rung at
TV 0.42 to 0.57. This is exactly the peak-versus-mass failure: tempering ranks
the initial pool by density, so at NL-Loo it under-weights the broad
high-allocation budget (mass 0.17 to 0.39 against truth 0.64) while looking good
on the per-parameter scores. T1 to T3 are closed as negative. The 17 deferred
tempering jobs were cancelled, not re-queued.

**Referee caveat (important for reading the page).** The v1 toy referee starts
chains spread over the atlas charts, so a kernel that never changes basin looks
correct by construction (chart-RWM/DE at TV 0.13 is initialisation, not mixing).
A referee v2 that starts all chains in one basin (scripts/pt_toy_init.py) was
written but not run: the user stopped the run before it finished. Any future
mode-weight claim must pass that test first.

**Stopped.** At the user's request the loop was stopped: dispatcher loop killed,
STOP file written, GPU workers stopped, in-flight fits of iterations 37 to 39
abandoned (iteration 37 was tempering, void anyway; 38 h15_de128_restart and
39 h16_de128_strat can be re-queued from variants/). Everything needed to resume
is on disk (tools/RESUME.md). Standing: nothing promoted under protocol v4; the
kernels that pass the score test still fail the mode-weight gate; the atlas
(S-family) remains the primary target because mode weights need a proposal that
jumps between budgets with a correct Hastings ratio, which no local kernel or
tempering ladder supplies.
