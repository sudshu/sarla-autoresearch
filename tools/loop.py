"""Iteration mechanics for the autoresearch loop.

    loop.py jobs  --iter N --variant NAME [--sites 183,71,58,178] [--seeds 5]
                  [--tag ""]           -> writes job JSONs, prints their paths
    loop.py score --iter N             -> scores every pulled fit of iteration N
                                          per site (osse_score_site.py), writes
                                          experiments/NNN/scores/<site><tag>.json
    loop.py aggregate --iter N         -> per-variant dev G, per-site table, JSON
    loop.py record --iter N --variant NAME --status keep|discard|dev-only|crash
                  --description "..." [--hypothesis H2] [--category moves]
                                       -> appends autoresearch.jsonl, dashboard
Job id: i<NNN>_<variant>_<site><tag>_s<seed>
"""
import argparse
import glob
import numpy as np
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AR = os.path.dirname(HERE)
ROOT = os.path.dirname(AR)
LOCAL = os.path.join(ROOT, "runs", "autoresearch")
PY = os.path.join(ROOT, ".venv", "bin", "python")
PROTOCOL_VERSION = 4
G_CAP = 5.0   # protocol v3: a site's G is capped at 5 in every aggregate (a catastrophic site is a failure, not a lever)
SITES_ROOT = os.path.join(ROOT, "runs", "osse_sites_v2")
if os.environ.get("SITES_V1"): SITES_ROOT = os.path.join(ROOT, "runs", "osse_sites")
DEV = [183, 58, 26, 71]
HOLDOUT = [55, 57, 82, 178]
SITE_NAMES = {26: "BE-Vie", 55: "CZ-wet", 57: "DE-Geb", 58: "DE-Gri", 71: "DK-Sor",
              82: "FR-Pue", 178: "ES-LJu", 183: "NL-Loo"}


def exp_dir(it):
    os.makedirs(os.path.join(AR, "experiments", f"{it:03d}"), exist_ok=True)
    return os.path.join(AR, "experiments", f"{it:03d}")


def job_id(it, variant, site, tag, seed):
    return f"i{it:03d}_{variant}_{site}{tag}_s{seed}"


def make_jobs(it, variant, sites, seeds, tag, overrides):
    jd = os.path.join(LOCAL, "queue", "new")
    os.makedirs(jd, exist_ok=True)
    paths = []
    for site in sites:
        for seed in seeds:
            jid = job_id(it, variant, site, tag, seed)
            job = dict(id=jid, site_dir=f"runs/osse_sites_v2/{site}{tag}",
                       variant_file=f"variants/{variant}.json", kernel_seed=seed,
                       overrides=overrides, attempts=0, iteration=it, variant=variant,
                       site=site, tag=tag)
            p = os.path.join(jd, f"{jid}.json")
            json.dump(job, open(p, "w"), indent=1)
            paths.append(p)
    return paths


def pulled_fits(it):
    """{(site, tag): {variant_seedlabel: fit_path}} for iteration it."""
    out = {}
    for rd in sorted(glob.glob(os.path.join(LOCAL, "jobs", f"i{it:03d}_*"))):
        res = os.path.join(rd, "result.json")
        fit = os.path.join(rd, "fit.npz")
        if not (os.path.exists(res) and os.path.exists(fit)):
            continue
        jid = os.path.basename(rd)
        _, rest = jid.split("_", 1)
        variant, site_tag, seed = rest.rsplit("_", 2)
        site = int("".join(ch for ch in site_tag if ch.isdigit()))
        tag = site_tag[len(str(site)):]
        out.setdefault((site, tag), {})[f"{variant}_{seed}"] = fit
    return out


def score(it, ndraw=500):
    ed = exp_dir(it)
    sd = os.path.join(ed, "scores")
    os.makedirs(sd, exist_ok=True)
    fits = pulled_fits(it)
    for (site, tag), d in fits.items():
        out = os.path.join(sd, f"{site}{tag}.json")
        have = json.load(open(out))["fits"] if os.path.exists(out) else {}
        todo = {k: v for k, v in d.items() if k not in have}
        if not todo:
            continue
        if tag == "real":
            # real-data mode-weight check (no truth): high-allocation fraction vs ADEMCMC 0.815
            cmd = [PY, os.path.join(ROOT, "scripts", "realdata_mode_check.py"), "--out", out + ".part"]
            for k, v in d.items():
                cmd += ["--fit", f"{k}={v}"]
            env = dict(os.environ, JAX_PLATFORMS="cpu"); env.pop("LD_LIBRARY_PATH", None)
            r = subprocess.run(cmd, env=env, capture_output=True, text=True)
            print("\n".join(l for l in r.stdout.splitlines() if "high-mode" in l))
            if r.returncode == 0:
                os.replace(out + ".part", out)
            else:
                print(r.stderr[-1500:])
            continue
        cmd = [PY, os.path.join(ROOT, "scripts", "osse_score_site.py"),
               "--site-dir", os.path.join(SITES_ROOT, f"{site}{tag}"),
               "--out", out + ".part", "--ndraw", str(ndraw),
               "--fig-dir", os.path.join(ed, "figures")]
        for k, v in d.items():          # rescore all fits of the site together
            cmd += ["--fit", f"{k}={v}"]
        env = dict(os.environ, JAX_PLATFORMS="cpu", XLA_FLAGS="--xla_cpu_multi_thread_eigen=true",
                   OMP_NUM_THREADS="16")
        env.pop("LD_LIBRARY_PATH", None)
        print(f"scoring site {site}{tag}: {len(d)} fits", flush=True)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        tail = "\n".join(l for l in r.stdout.splitlines() if l and "Warning" not in l
                         and "smean" not in l and "sann" not in l)
        print(tail[-3000:])
        if r.returncode:
            print(r.stderr[-2000:])
            continue
        os.replace(out + ".part", out)
    return sd


def aggregate(it, extra_iters=()):
    """Per variant: mean G over dev sites (seed-averaged per site), per-site table.
    extra_iters: earlier iterations whose scores are pooled in (confirmation seeds)."""
    ed = exp_dir(it)
    rows = {}
    score_files = []
    for i2 in list(extra_iters) + [it]:
        score_files += sorted(glob.glob(os.path.join(exp_dir(i2), "scores", "*.json")))
    for f in score_files:
        s = json.load(open(f))
        if "site" not in s:          # real-data mode check, not an OSSE score
            continue
        site, tag = s["site"], s["tag"]
        for name, r in s["fits"].items():
            if "G" not in r:
                continue
            variant, seed = name.rsplit("_s", 1)
            rows.setdefault(variant, {}).setdefault((site, tag), []).append(
                dict(seed=int(seed), G=r["G"], terms=r["G_terms"],
                     cover90=r["param"]["cover90"], cover50=r["param"]["cover50"],
                     rank=r["rank"], rms_z=r["param"]["rms_z"], n_gt2=r["param"]["n_gt2"],
                     stuck_frac=r["stuck_frac"], typical_gap=r["typical_gap"],
                     proj=[r["traj"][k]["projection"]["cover90"] for k in ("GPP", "NBE", "ET", "LAI")],
                     wall=(r["meta"].get("wall") or {}).get("total"),
                     n_eval=r["meta"].get("n_eval"), host=None))
    # attach host/gpu from result.json
    job_dirs = []
    for i2 in list(extra_iters) + [it]:
        job_dirs += glob.glob(os.path.join(LOCAL, "jobs", f"i{i2:03d}_*"))
    for rd in job_dirs:
        rf = os.path.join(rd, "result.json")
        if not os.path.exists(rf):
            continue
        res = json.load(open(rf))
        jid = os.path.basename(rd)
        _, rest = jid.split("_", 1)
        variant, site_tag, seed = rest.rsplit("_", 2)
        site = int("".join(ch for ch in site_tag if ch.isdigit())); tag = site_tag[len(str(site)):]
        for e in rows.get(variant, {}).get((site, tag), []):
            if e["seed"] == int(seed[1:]):
                e["host"] = res.get("host"); e["gpu_name"] = res.get("gpu_name")
                e["wall_job"] = res.get("wall")
    summary = {}
    for variant, sites in rows.items():
        per_site = {}
        for (site, tag), es in sites.items():
            Gs = [e["G"] for e in es]
            Gc = [min(g, G_CAP) for g in Gs]
            per_site[f"{site}{tag}"] = dict(G=float(sum(Gc) / len(Gc)), G_seeds=Gs, G_raw=float(sum(Gs) / len(Gs)),
                                            n=len(es), entries=es)
        dev = [per_site[f"{s}"]["G"] for s in DEV if f"{s}" in per_site]
        hold = [per_site[f"{s}"]["G"] for s in HOLDOUT if f"{s}" in per_site]
        devB = [per_site[f"{s}B"]["G"] for s in DEV if f"{s}B" in per_site]
        walls = [e["wall_job"] for es in sites.values() for e in es if e.get("wall_job")]
        # noise floor: sd over kernel seeds of the dev-set mean G (seeds present at all dev sites)
        seed_sets = [set(e["seed"] for e in sites[(s, "")]) for s in DEV if (s, "") in sites]
        common = set.intersection(*seed_sets) if len(seed_sets) == len(DEV) else set()
        per_seed = []
        for sd in sorted(common):
            per_seed.append(float(np.mean([[min(e["G"], G_CAP) for e in sites[(s, "")] if e["seed"] == sd][0]
                                           for s in DEV])))
        sd_dev = float(np.std(per_seed, ddof=1)) if len(per_seed) >= 2 else None
        summary[variant] = dict(
            G_dev_per_seed=per_seed, sd_dev=sd_dev,
            delta=(max(0.10, 2 * sd_dev) if sd_dev is not None else None),
            G_dev=float(sum(dev) / len(dev)) if dev else None, n_dev=len(dev),
            G_holdout=float(sum(hold) / len(hold)) if hold else None, n_holdout=len(hold),
            G_devB=float(sum(devB) / len(devB)) if devB else None,
            wall_median=float(sorted(walls)[len(walls) // 2]) if walls else None,
            per_site=per_site)
    # protocol v4: two-sample test against the current default (baseline aggregate)
    base = None
    if os.environ.get("BASELINE_ITER"):
        bagg = json.load(open(os.path.join(exp_dir(int(os.environ["BASELINE_ITER"])), "aggregate.json")))
        base = bagg.get(os.environ.get("BASELINE_VARIANT", "v3_baseline"))
    for v, s in summary.items():
        if base and s.get("sd_dev") is not None and base.get("sd_dev") is not None:
            nb, nc = len(base["G_dev_per_seed"]), len(s["G_dev_per_seed"])
            se = float(np.sqrt(base["sd_dev"] ** 2 / nb + s["sd_dev"] ** 2 / nc))
            s["v4_diff"] = float(base["G_dev"] - s["G_dev"]); s["v4_se"] = se
            s["v4_t"] = s["v4_diff"] / se if se > 0 else None
            s["v4_pass"] = bool(nc >= 3 and s["v4_diff"] > 2 * se)
    json.dump(summary, open(os.path.join(ed, "aggregate.json"), "w"), indent=1)
    for v, s in summary.items():
        if "v4_t" in s and s["v4_t"] is not None:
            print(f"{v:28s} v4 test vs default: diff {s['v4_diff']:.3f}, se {s['v4_se']:.3f}, t {s['v4_t']:.2f} -> {'PASS' if s['v4_pass'] else 'no'}")
        print(f"{v:28s} G_dev {fmt(s['G_dev'])} ({s['n_dev']}/4)  G_holdout {fmt(s['G_holdout'])} "
              f"({s['n_holdout']}/4)  G_devB {fmt(s['G_devB'])}  wall med {fmt(s['wall_median'], 0)}s"
              + (f"  per-seed dev G {['%.3f' % g for g in s['G_dev_per_seed']]} sd {s['sd_dev']:.3f} "
                 f"delta {s['delta']:.3f}" if s['sd_dev'] is not None else ""))
        for k, ps in s["per_site"].items():
            e = ps["entries"][0]
            print(f"   {k:5s} G {ps['G']:.3f} (raw {ps['G_raw']:.2f}) {['%.2f' % g for g in ps['G_seeds']]}  c90 {e['cover90']:.2f} "
                  f"c50 {e['cover50']:.2f} rank {e['rank']:.2f} rms_z {e['rms_z']:.2f} stuck {e['stuck_frac']:.2f} "
                  f"proj {['%.2f' % p for p in e['proj']]}")
    return summary


def fmt(x, p=3):
    return "  --  " if x is None else f"{x:.{p}f}"


def record(it, variant, status, description, hypothesis, category, commit, protocol=None):
    ed = exp_dir(it)
    agg = json.load(open(os.path.join(ed, "aggregate.json")))
    s = agg[variant]
    runs = [json.loads(l) for l in open(os.path.join(AR, "autoresearch.jsonl")) if l.strip()]
    n = sum(1 for r in runs if r.get("type") != "config")
    entry = dict(run=n + 1, iteration=it, variant=variant, hypothesis=hypothesis,
                 category=category, metric=s["G_dev"],
                 metrics=dict(G_dev=s["G_dev"], G_holdout=s["G_holdout"], G_devB=s["G_devB"],
                              per_site={k: v["G"] for k, v in s["per_site"].items()},
                              wall_median=s["wall_median"]),
                 status=status, description=description, commit=commit,
                 timestamp=int(time.time()),
                 protocol_version=protocol if protocol is not None else PROTOCOL_VERSION)
    with open(os.path.join(AR, "autoresearch.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["jobs", "score", "aggregate", "record", "prune"])
    ap.add_argument("--iter", type=int, required=True)
    ap.add_argument("--variant")
    ap.add_argument("--sites", default=",".join(map(str, DEV)))
    ap.add_argument("--seeds", default="5")
    ap.add_argument("--tag", default="")
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--status")
    ap.add_argument("--description", default="")
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--commit", default="")
    ap.add_argument("--ndraw", type=int, default=500)
    ap.add_argument("--protocol", type=int, default=None)
    ap.add_argument("--with-iters", default="", help="comma list of earlier iterations to pool into aggregate")
    a = ap.parse_args()
    if a.mode == "jobs":
        sites = [int(s) for s in a.sites.split(",")]
        seeds = [int(s) for s in a.seeds.split(",")]
        for p in make_jobs(a.iter, a.variant, sites, seeds, a.tag, a.set):
            print(p)
    elif a.mode == "score":
        score(a.iter, a.ndraw)
    elif a.mode == "aggregate":
        aggregate(a.iter, [int(x) for x in a.with_iters.split(",") if x])
    elif a.mode == "prune":
        # delete fit.npz of jobs whose site has been scored (scores are in experiments/)
        ed = exp_dir(a.iter)
        scored = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(ed, "scores", "*.json"))}
        n = 0
        for (site, tag), d in pulled_fits(a.iter).items():
            if f"{site}{tag}" in scored:
                for path in d.values():
                    os.remove(path); n += 1
        print(f"pruned {n} fit files of iteration {a.iter}")
    elif a.mode == "record":
        record(a.iter, a.variant, a.status, a.description, a.hypothesis, a.category, a.commit, a.protocol)


if __name__ == "__main__":
    main()
