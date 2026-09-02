"""Pull worker: one GPU slot on a remote host, runs queued sarla_fit jobs.

    worker.py run    --root DIR --slot K --gpu G --mem-frac F --python PY --host NAME
    worker.py status --root DIR          # JSON: queues, heartbeats, results

Layout under --root:
    queue/pending/<job>.json   queued by the dispatcher (oldest name first)
    queue/running/slot<K>/     the job this slot is executing
    queue/done/ queue/failed/  finished jobs (result.json alongside in jobs/)
    jobs/<id>/{log.txt, heartbeat, result.json, fit.npz}
    STOP                       exit after the current job

Job JSON: {"id", "site_dir", "variant_file", "kernel_seed", "overrides": [..],
           "attempts": n}
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time


def dirs(root):
    d = {k: os.path.join(root, "queue", k) for k in ("pending", "running", "done", "failed")}
    d["jobs"] = os.path.join(root, "jobs")
    return d


def claim(root, slot):
    d = dirs(root)
    mine = os.path.join(d["running"], f"slot{slot}")
    os.makedirs(mine, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(d["pending"], "*.json"))):
        dst = os.path.join(mine, os.path.basename(f))
        try:
            os.rename(f, dst)
            return dst
        except FileNotFoundError:
            continue
    return None


def run_job(root, path, a):
    d = dirs(root)
    job = json.load(open(path))
    jid = job["id"]
    jd = os.path.join(d["jobs"], jid)
    os.makedirs(jd, exist_ok=True)
    out = os.path.join(jd, "fit.npz")
    cmd = [a.python, os.path.join(root, "scripts", "sarla_fit.py"),
           "--cbf", os.path.join(root, job["site_dir"], "osse.cbf.nc"),
           "--seeds", os.path.join(root, job["site_dir"], "seeds.npz"),
           "--out", out, "--variant", os.path.join(root, job["variant_file"]),
           "--kernel-seed", str(job.get("kernel_seed", 5))]
    if job.get("overrides"):
        cmd += ["--set"] + list(job["overrides"])
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(a.gpu),
               XLA_PYTHON_CLIENT_PREALLOCATE="false",
               XLA_PYTHON_CLIENT_MEM_FRACTION=str(a.mem_frac),
               JAX_PLATFORMS="cuda,cpu")
    t0 = time.time()
    with open(os.path.join(jd, "log.txt"), "a") as log:
        log.write(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} host {a.host} slot {a.slot} "
                  f"gpu {a.gpu}\n{' '.join(cmd)}\n")
        log.flush()
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                             cwd=root)
        while p.poll() is None:
            with open(os.path.join(jd, "heartbeat"), "w") as hb:
                hb.write(f"{time.time():.0f} {a.host} slot{a.slot}\n")
            time.sleep(30)
    rc = p.returncode
    wall = time.time() - t0
    tail = subprocess.run(["tail", "-n", "12", os.path.join(jd, "log.txt")],
                          capture_output=True, text=True).stdout
    res = dict(id=jid, rc=rc, wall=wall, host=a.host, slot=a.slot, gpu=a.gpu,
               gpu_name=a.gpu_name, started=t0, finished=time.time(),
               ok=bool(rc == 0 and os.path.exists(out)), log_tail=tail)
    json.dump(res, open(os.path.join(jd, "result.json"), "w"), indent=1)
    dst = d["done"] if res["ok"] else d["failed"]
    os.makedirs(dst, exist_ok=True)
    shutil.move(path, os.path.join(dst, os.path.basename(path)))
    return res


def requeue(root, jid, slot):
    """A stale running job goes back to pending once, then to failed."""
    d = dirs(root)
    slot = slot if isinstance(slot, str) else f"slot{slot}"
    p = os.path.join(d["running"], slot, f"{jid}.json")
    j = json.load(open(p))
    j["attempts"] = j.get("attempts", 0) + 1
    dst = d["pending"] if j["attempts"] <= 1 else d["failed"]
    json.dump(j, open(os.path.join(dst, f"{jid}.json"), "w"))
    os.remove(p)
    print(f"requeued {jid} -> {os.path.basename(dst)} (attempt {j['attempts']})")


def status(root):
    d = dirs(root)
    out = dict(time=time.time(), pending=[], running={}, done=[], failed=[],
               results={}, workers=[])
    out["pending"] = sorted(os.path.basename(f)[:-5]
                            for f in glob.glob(os.path.join(d["pending"], "*.json")))
    for sd in sorted(glob.glob(os.path.join(d["running"], "slot*"))):
        js = glob.glob(os.path.join(sd, "*.json"))
        for f in js:
            jid = os.path.basename(f)[:-5]
            hb = os.path.join(d["jobs"], jid, "heartbeat")
            age = time.time() - os.path.getmtime(hb) if os.path.exists(hb) else None
            out["running"][jid] = dict(slot=os.path.basename(sd), heartbeat_age=age)
    for k in ("done", "failed"):
        for f in sorted(glob.glob(os.path.join(d[k], "*.json"))):
            jid = os.path.basename(f)[:-5]
            out[k].append(jid)
            rf = os.path.join(d["jobs"], jid, "result.json")
            if os.path.exists(rf):
                out["results"][jid] = json.load(open(rf))
    try:
        ps = subprocess.run(["pgrep", "-af", "worker.py run"], capture_output=True,
                            text=True).stdout.strip().splitlines()
        out["workers"] = sorted({l.split("--slot")[1].split()[0] for l in ps
                                 if "--slot" in l and "python" in l.split()[1]
                                 and "pgrep" not in l})
    except Exception:
        pass
    print(json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "status", "requeue"])
    ap.add_argument("--job", default=None)
    ap.add_argument("--root", required=True)
    ap.add_argument("--slot", default=0)
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--mem-frac", type=float, default=0.9)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--host", default=os.uname().nodename)
    ap.add_argument("--gpu-name", default="")
    a = ap.parse_args()
    if a.mode != "requeue":
        a.slot = int(a.slot)
    root = os.path.abspath(a.root)
    if a.mode == "status":
        return status(root)
    if a.mode == "requeue":
        return requeue(root, a.job, a.slot)
    for k in dirs(root).values():
        os.makedirs(k, exist_ok=True)
    print(f"worker {a.host} slot {a.slot} gpu {a.gpu} mem {a.mem_frac} up", flush=True)
    while True:
        if os.path.exists(os.path.join(root, "STOP")):
            print("STOP file present, exiting", flush=True)
            return
        job = claim(root, a.slot)
        if job is None:
            time.sleep(15)
            continue
        print(f"[{time.strftime('%H:%M:%S')}] running {os.path.basename(job)}", flush=True)
        res = run_job(root, job, a)
        print(f"[{time.strftime('%H:%M:%S')}] {res['id']} rc={res['rc']} "
              f"wall={res['wall']:.0f}s ok={res['ok']}", flush=True)


if __name__ == "__main__":
    main()
