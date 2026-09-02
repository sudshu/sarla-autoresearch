"""Codex advisor: after each iteration, ask an independent model to weigh in.

    advisor.py --iter N [--model MODEL] [--effort high]

Builds a briefing from the protocol, the run history (autoresearch.jsonl),
the iteration's aggregate scores and the idea bank -- aggregate numbers only,
no observation data -- and runs `codex exec` with the requested reasoning
effort. The reply is saved to experiments/NNN/advisor.md. The loop's own
researcher reads it and decides what to implement; nothing is automatic.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AR = os.path.dirname(HERE)

PROMPT = """You are the external advisor of an autonomous research loop that improves
SARLA, a GPU posterior sampler for an 89-parameter land carbon model
(CARDAMOM / DALEC_1100). Read the protocol, the history and this iteration's
results below, then answer in <= 600 words with these sections:

1. ASSESSMENT: what the numbers say about this iteration (which terms of the
   calibration gap moved, per-site consistency, any sign of overfitting to the
   development sites or to a single truth).
2. RISKS: anything in the protocol or the results that could mislead us.
3. NEXT STEPS: 3-5 concrete, testable proposals ranked by expected payoff,
   each as one sentence of rationale plus the variant knobs to change
   (use the knob names from the variant JSON). Mark proposals that need new
   code rather than a config change.
4. STOP/CONTINUE: whether a hypothesis family should be abandoned.

Be specific and quantitative; do not restate the protocol.

=== PROTOCOL ===
{protocol}

=== RUN HISTORY (autoresearch.jsonl) ===
{history}

=== THIS ITERATION: aggregate.json ===
{aggregate}

=== IDEA BANK ===
{ideas}

=== BASELINE VARIANT (knob names) ===
{variant}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()
    ed = os.path.join(AR, "experiments", f"{a.iter:03d}")
    agg = json.load(open(os.path.join(ed, "aggregate.json")))
    slim = {v: {k: val for k, val in s.items() if k != "per_site"}
            | {"per_site": {site: {kk: vv for kk, vv in ps.items() if kk != "entries"}
                            | {"terms": ps["entries"][0]["terms"],
                               "cover90": ps["entries"][0]["cover90"],
                               "cover50": ps["entries"][0]["cover50"],
                               "rank": ps["entries"][0]["rank"],
                               "rms_z": ps["entries"][0]["rms_z"],
                               "stuck_frac": ps["entries"][0]["stuck_frac"],
                               "proj_cover90": ps["entries"][0]["proj"]}
                            for site, ps in s["per_site"].items()}}
            for v, s in agg.items()}
    hist = [l for l in open(os.path.join(AR, "autoresearch.jsonl")) if l.strip()]
    prompt = PROMPT.format(
        protocol=open(os.path.join(AR, "autoresearch.md")).read(),
        history="".join(hist[-40:]),
        aggregate=json.dumps(slim, indent=1),
        ideas=open(os.path.join(AR, "autoresearch.ideas.md")).read(),
        variant=open(os.path.join(AR, "variants", "v3_baseline.json")).read())
    out = os.path.join(ed, "advisor.md")
    cmd = ["codex", "exec", "--skip-git-repo-check", "-s", "read-only", "-C", ed,
           "-c", f'model_reasoning_effort="{a.effort}"', "-o", out + ".raw"]
    if a.model:
        cmd += ["-m", a.model]
    cmd.append(prompt)
    open(os.path.join(ed, "advisor_prompt.txt"), "w").write(prompt)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        open(out, "w").write("(advisor timed out)\n")
        print("advisor timed out"); return
    text = open(out + ".raw").read() if os.path.exists(out + ".raw") else r.stdout
    header = (f"# Codex advisor, iteration {a.iter:03d}\n\n"
              f"model {a.model or 'default (config.toml)'}, reasoning effort {a.effort}, "
              f"rc {r.returncode}\n\n")
    open(out, "w").write(header + text.strip() + "\n")
    if os.path.exists(out + ".raw"):
        os.remove(out + ".raw")
    print(f"wrote {out} ({len(text)} chars, rc {r.returncode})")
    if r.returncode:
        print(r.stderr[-1500:])


if __name__ == "__main__":
    main()
