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
