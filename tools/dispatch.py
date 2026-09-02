"""Local dispatcher: ships code, data and jobs to GPU hosts; pulls results.

    dispatch.py sync     [--host H]      push code + dalec_jax + osse_sites + variants
    dispatch.py workers  [--host H]      (re)start missing pull workers
    dispatch.py submit JOB.json ...      queue jobs (assigned to the freest host)
    dispatch.py poll     [--pull]        status of all hosts -> status.json; --pull
                                         retrieves finished jobs' fit.npz/result.json
    dispatch.py loop     [--tick 60]     poll --pull forever (run under tmux/nohup)
    dispatch.py wait IDS... [--timeout S] block until these job ids are done/failed

Transfers use tar over ssh so a two-hop host (aws_kyo -> az-ms) works the same
as a direct one. Local mirror: runs/autoresearch/{queue,jobs,status.json}.
"""
import argparse
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AR = os.path.dirname(HERE)                       # autoresearch/
ROOT = os.path.dirname(AR)                       # research repo
HOSTS = json.load(open(os.path.join(HERE, "hosts.json")))
LOCAL = os.path.join(ROOT, "runs", "autoresearch")
STALE_S = 15 * 60


def ssh(host, cmd, timeout=300, input_bytes=None, capture=True):
    """Run cmd on host; a two-hop host gets the command shell-quoted for the
    inner ssh so operators like && stay on the final host."""
    h = HOSTS["hosts"][host]
    full = h["ssh"] + ([h["hop"] + " " + shlex.quote(cmd)] if h.get("hop") else [cmd])
    return subprocess.run(full, input=input_bytes, capture_output=capture,
                          timeout=timeout)


def push(host, local_paths, remote_dir, strip=None):
    """tar the given local paths (relative to strip or ROOT) into remote_dir."""
    base = strip or ROOT
    rel = [os.path.relpath(p, base) for p in local_paths]
    tar = subprocess.run(["tar", "czf", "-", "-C", base] + rel, capture_output=True)
    r = ssh(host, f"mkdir -p {remote_dir} && tar xzf - -C {remote_dir}",
            input_bytes=tar.stdout, timeout=600)
    if r.returncode:
        raise RuntimeError(f"push to {host} failed: {r.stderr.decode()[-500:]}")


def pull(host, remote_rel_paths, local_dir):
    h = HOSTS["hosts"][host]
    paths = " ".join(remote_rel_paths)
    r = ssh(host, f"cd {h['workdir']} && tar czf - {paths} 2>/dev/null", timeout=900)
    if r.returncode and not r.stdout:
        raise RuntimeError(f"pull from {host} failed: {r.stderr.decode()[-300:]}")
    os.makedirs(local_dir, exist_ok=True)
    subprocess.run(["tar", "xzf", "-", "-C", local_dir], input=r.stdout, check=True)


def sync(host):
    h = HOSTS["hosts"][host]
    code = [os.path.join(ROOT, "scripts", f) for f in HOSTS["code_files"]]
    code.append(os.path.join(HERE, "worker.py"))
    push(host, code, f"{h['workdir']}/scripts", strip=None)
    # tar of files from two dirs: flatten by pushing one at a time
    ssh(host, f"cd {h['workdir']}/scripts && mv -f scripts/*.py . 2>/dev/null; "
              f"mv -f autoresearch/tools/worker.py . 2>/dev/null; "
              f"rm -rf scripts autoresearch", timeout=60)
    src = os.path.join(ROOT, HOSTS["dalec_src"])
    push(host, [src], f"{h['workdir']}/scripts/dalec_jax_src",
         strip=os.path.dirname(src))
    sites = sorted(glob.glob(os.path.join(ROOT, "runs", "osse_sites_v2", "*")))
    if sites:
        push(host, sites, f"{h['workdir']}/runs/osse_sites_v2",
             strip=os.path.join(ROOT, "runs", "osse_sites_v2"))
    var = sorted(glob.glob(os.path.join(AR, "variants", "*.json")))
    if var:
        push(host, var, f"{h['workdir']}/variants", strip=os.path.join(AR, "variants"))
    print(f"synced {host}: {len(code)} code files, dalec_jax, {len(sites)} sites, "
          f"{len(var)} variants", flush=True)


def remote_status(host):
    h = HOSTS["hosts"][host]
    try:
        r = ssh(host, f"{h['python']} {h['workdir']}/scripts/worker.py status "
                      f"--root {h['workdir']}", timeout=120)
        if r.returncode:
            return dict(error=r.stderr.decode()[-300:])
        return json.loads(r.stdout.decode().strip().splitlines()[-1])
    except Exception as e:  # unreachable
        return dict(error=str(e))


def start_workers(host, st=None):
    h = HOSTS["hosts"][host]
    st = st or remote_status(host)
    if "error" in st:
        print(f"{host}: unreachable ({st['error'][:80]})")
        return
    alive = set(int(s) for s in st.get("workers", []))
    for s in h["slots"]:
        if s["slot"] in alive:
            continue
        cmd = (f"cd {h['workdir']} && mkdir -p logs && setsid nohup {h['python']} "
               f"scripts/worker.py run --root {h['workdir']} --slot {s['slot']} "
               f"--gpu {s['gpu']} --mem-frac {s['mem_frac']} --python {h['python']} "
               f"--host {host} --gpu-name '{h['gpu_name']}' "
               f">> logs/worker_slot{s['slot']}.log 2>&1 < /dev/null & disown; sleep 1")
        try:
            ssh(host, cmd, timeout=45)
        except subprocess.TimeoutExpired:
            pass  # the detached worker is up; the hop sometimes holds the session
        print(f"{host}: started worker slot {s['slot']} (gpu {s['gpu']})", flush=True)


def submit(job_files):
    """Assign each job to the host with the most free capacity, push it."""
    os.makedirs(os.path.join(LOCAL, "queue", "submitted"), exist_ok=True)
    stats = {h: remote_status(h) for h in HOSTS["hosts"]}
    load = {}
    for h, st in stats.items():
        if "error" in st:
            continue
        load[h] = len(st["pending"]) + len(st["running"]) - len(HOSTS["hosts"][h]["slots"])
    if not load:
        raise SystemExit("no reachable host")
    assigned = {}
    for jf in job_files:
        h = min(load, key=load.get)
        load[h] += 1
        assigned.setdefault(h, []).append(jf)
    for h, files in assigned.items():
        push(h, files, f"{HOSTS['hosts'][h]['workdir']}/queue/pending",
             strip=os.path.dirname(files[0]))
        for jf in files:
            job = json.load(open(jf))
            job["host"] = h
            json.dump(job, open(os.path.join(LOCAL, "queue", "submitted",
                                             os.path.basename(jf)), "w"), indent=1)
            print(f"submitted {job['id']} -> {h}", flush=True)
        start_workers(h, stats[h])


def poll(pull_results=False):
    status = dict(time=time.time(), hosts={}, jobs={})
    for h in HOSTS["hosts"]:
        st = remote_status(h)
        status["hosts"][h] = st
        if "error" in st:
            continue
        # stale heartbeat -> requeue (attempts+1) once
        for jid, info in st["running"].items():
            age = info.get("heartbeat_age")
            if age is not None and age > STALE_S:
                w = HOSTS["hosts"][h]["workdir"]
                ssh(h, f"{HOSTS['hosts'][h]['python']} {w}/scripts/worker.py requeue "
                       f"--root {w} --job {jid} --slot {info['slot']}", timeout=60)
                print(f"{h}: requeued stale job {jid} (heartbeat {age:.0f}s)", flush=True)
        for jid in st["pending"]:
            status["jobs"][jid] = dict(state="pending", host=h)
        for jid, info in st["running"].items():
            status["jobs"][jid] = dict(state="running", host=h, **info)
        for k in ("done", "failed"):
            for jid in st[k]:
                r = st["results"].get(jid, {})
                status["jobs"][jid] = dict(state=k, host=h, wall=r.get("wall"),
                                           rc=r.get("rc"), gpu_name=r.get("gpu_name"))
                local = os.path.join(LOCAL, "jobs", jid)
                have = os.path.exists(os.path.join(local, "result.json"))
                if pull_results and not have:
                    want = [f"jobs/{jid}/result.json", f"jobs/{jid}/log.txt"]
                    if k == "done":
                        want.append(f"jobs/{jid}/fit.npz")
                    try:
                        pull(h, want, LOCAL)
                        print(f"pulled {jid} from {h} ({k}, {r.get('wall', 0):.0f}s)",
                              flush=True)
                    except Exception as e:
                        print(f"pull {jid} failed: {e}", flush=True)
        if pull_results and all(k in st for k in ("done",)):
            pass
    os.makedirs(LOCAL, exist_ok=True)
    json.dump(status, open(os.path.join(LOCAL, "status.json"), "w"), indent=1)
    return status


def rebalance(status):
    """Move pending jobs from the host with the longest expected queue to the
    one with the shortest, using rate_per_h from hosts.json (work stealing)."""
    up = {h: st for h, st in status["hosts"].items() if "error" not in st}
    if len(up) < 2:
        return
    def eta(h, extra=0):
        st = up[h]
        n = len(st["pending"]) + len(st["running"]) + extra
        return n / HOSTS["hosts"][h].get("rate_per_h", 1.0)
    moved = 0
    while True:
        slow = max(up, key=lambda h: eta(h))
        fast = min(up, key=lambda h: eta(h))
        if slow == fast or not up[slow]["pending"]:
            return
        if eta(slow) - eta(fast, 1) < 0.5:      # less than half an hour to gain
            return
        jid = up[slow]["pending"][-1]           # newest pending first
        ws, wf = HOSTS["hosts"][slow]["workdir"], HOSTS["hosts"][fast]["workdir"]
        r = ssh(slow, f"cat {ws}/queue/pending/{jid}.json && rm {ws}/queue/pending/{jid}.json",
                timeout=60)
        if r.returncode or not r.stdout:
            return
        r2 = ssh(fast, f"mkdir -p {wf}/queue/pending && cat > {wf}/queue/pending/{jid}.json",
                 input_bytes=r.stdout, timeout=60)
        if r2.returncode:
            ssh(slow, f"cat > {ws}/queue/pending/{jid}.json", input_bytes=r.stdout, timeout=60)
            return
        up[slow]["pending"].remove(jid); up[fast]["pending"].append(jid)
        moved += 1
        print(f"rebalanced {jid}: {slow} -> {fast}", flush=True)


def summarize(status):
    hs = []
    for h, st in status["hosts"].items():
        if "error" in st:
            hs.append(f"{h}: DOWN")
        else:
            hs.append(f"{h}: {len(st['running'])} running, {len(st['pending'])} pending, "
                      f"{len(st['done'])} done, {len(st['failed'])} failed, "
                      f"workers {sorted(st['workers'])}")
    return " | ".join(hs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sync", "workers", "submit", "poll", "loop", "wait", "rebalance"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--host", default=None)
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--tick", type=int, default=60)
    ap.add_argument("--timeout", type=float, default=6 * 3600)
    a = ap.parse_args()
    hosts = [a.host] if a.host else list(HOSTS["hosts"])
    if a.mode == "sync":
        for h in hosts:
            try:
                sync(h)
            except Exception as e:
                print(f"sync {h} failed: {e}")
    elif a.mode == "workers":
        for h in hosts:
            start_workers(h)
    elif a.mode == "submit":
        submit(a.args)
    elif a.mode == "poll":
        print(summarize(poll(a.pull)))
    elif a.mode == "rebalance":
        st = poll(False); rebalance(st); print(summarize(poll(False)))
    elif a.mode == "loop":
        while True:
            try:
                st = poll(True)
                rebalance(st)
                print(f"[{time.strftime('%H:%M:%S')}] {summarize(st)}", flush=True)
            except Exception as e:
                print(f"poll error: {e}", flush=True)
            if os.path.exists(os.path.join(AR, "STOP")):
                print("STOP present; dispatcher exiting")
                return
            time.sleep(a.tick)
    elif a.mode == "wait":
        t0 = time.time()
        while time.time() - t0 < a.timeout:
            st = poll(True)
            states = {j: st["jobs"].get(j, {}).get("state", "unknown") for j in a.args}
            print(f"[{time.strftime('%H:%M:%S')}] " + " ".join(f"{j}:{s}" for j, s in states.items()),
                  flush=True)
            if all(s in ("done", "failed") for s in states.values()):
                return
            time.sleep(a.tick)
        print("wait timed out")
        sys.exit(2)


if __name__ == "__main__":
    main()
