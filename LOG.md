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
