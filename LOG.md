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
