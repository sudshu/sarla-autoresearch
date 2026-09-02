"""Build the public progress page (docs/) from the loop's state files.

Inputs: autoresearch.jsonl, autoresearch.ideas.md, LOG.md, experiments/*/
aggregate.json. Outputs: docs/index.html, docs/data.json, docs/charts/*.png.
Only aggregate metrics and public FLUXNET site IDs are written.
"""
import glob
import html
import json
import os
import re
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AR = os.path.dirname(HERE)
DOCS = os.path.join(AR, "docs")
CH = os.path.join(DOCS, "charts")
DEV = [183, 58, 26, 71]
HOLDOUT = [55, 57, 82, 178]
NAMES = {26: "BE-Vie (MF)", 55: "CZ-wet (WET)", 57: "DE-Geb (CRO)", 58: "DE-Gri (GRA)",
         71: "DK-Sor (DBF)", 82: "FR-Pue (EBF)", 178: "ES-LJu (OSH)", 183: "NL-Loo (ENF)"}
STATUS_COLOR = {"keep": "#2166ac", "discard": "#b2182b", "dev-only": "#e08214",
                "crash": "#777777", "baseline": "#4d4d4d", "running": "#999999",
                "v1-invalid": "#bbbbbb"}
PROTOCOL_VERSION = 2
ADEMCMC_H = 33.0
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 110, "savefig.bbox": "tight"})


def load_runs():
    runs = []
    for l in open(os.path.join(AR, "autoresearch.jsonl")):
        if l.strip():
            d = json.loads(l)
            if d.get("type") != "config":
                if d.get("protocol_version", 1) < PROTOCOL_VERSION:
                    d = dict(d, status="v1-invalid")
                runs.append(d)
    return runs


def load_aggregates():
    out = {}
    for f in sorted(glob.glob(os.path.join(AR, "experiments", "*", "aggregate.json"))):
        it = int(os.path.basename(os.path.dirname(f)))
        out[it] = json.load(open(f))
    return out


def chart_progress(runs):
    fig, ax = plt.subplots(figsize=(8, 4))
    if runs:
        x = [r["run"] for r in runs]
        y = [r["metric"] for r in runs]
        best, bests = np.inf, []
        for r in runs:
            if r["status"] in ("keep", "baseline") and r["metric"] is not None:
                best = min(best, r["metric"])
            bests.append(best if np.isfinite(best) else np.nan)
        for r in runs:
            if r["metric"] is None:
                continue
            ax.scatter(r["run"], r["metric"], color=STATUS_COLOR.get(r["status"], "k"), s=45, zorder=3)
            h = r["metrics"].get("G_holdout")
            if h is not None:
                ax.scatter(r["run"], h, marker="s", facecolor="none", edgecolor="k", s=60, zorder=3)
        ax.step(x, bests, where="post", color="#2166ac", lw=1.5, label="best accepted so far")
        for st, c in STATUS_COLOR.items():
            if any(r["status"] == st for r in runs):
                ax.scatter([], [], color=c, label=st)
        ax.scatter([], [], marker="s", facecolor="none", edgecolor="k", label="holdout sites (milestone)")
        ax.legend(fontsize=8, ncol=3)
    ax.set_xlabel("experiment number")
    ax.set_ylabel("calibration gap G on the development sites\n(lower is better, 0 = perfectly calibrated)")
    ax.set_title("Progress", loc="left")
    ax.axhline(0, color="0.7", lw=0.8)
    fig.savefig(os.path.join(CH, "progress.png"))
    plt.close(fig)


def chart_categories(runs):
    cats = sorted({r.get("category") or "other" for r in runs}) or ["baseline"]
    sts = ["keep", "discard", "dev-only", "crash", "baseline"]
    counts = {c: {s: 0 for s in sts} for c in cats}
    for r in runs:
        counts[r.get("category") or "other"][r["status"] if r["status"] in sts else "crash"] += 1
    fig, ax = plt.subplots(figsize=(8, 0.5 + 0.5 * len(cats)))
    left = np.zeros(len(cats))
    for s in sts:
        v = np.array([counts[c][s] for c in cats])
        ax.barh(cats, v, left=left, color=STATUS_COLOR[s], label=s)
        left += v
    ax.set_xlabel("experiments")
    ax.set_title("What has been tried, by category and outcome", loc="left")
    ax.legend(fontsize=8, ncol=5)
    fig.savefig(os.path.join(CH, "categories.png"))
    plt.close(fig)


def chart_sites(aggs, runs):
    """Baseline vs current default: cover90 and rank per site."""
    base = None; cur = None
    for r in runs:
        if r["status"] == "baseline" and base is None:
            base = (r["iteration"], r["variant"])
        if r["status"] in ("keep", "baseline"):
            cur = (r["iteration"], r["variant"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    sites = DEV + HOLDOUT
    xs = np.arange(len(sites))
    for ax, key, target, lab in ((axes[0], "cover90", 0.9, "90% interval coverage of the 89 parameters"),
                                 (axes[1], "rank", 0.5, "density rank of the truth")):
        for off, (tagname, sel, col) in enumerate((("baseline", base, "0.55"), ("current default", cur, "#d62728"))):
            if sel is None or sel[0] not in aggs or sel[1] not in aggs[sel[0]]:
                continue
            ps = aggs[sel[0]][sel[1]]["per_site"]
            vals = [np.mean([e[key] for e in ps[str(s)]["entries"]]) if str(s) in ps else np.nan for s in sites]
            ax.bar(xs + (off - 0.5) * 0.38, vals, 0.38, color=col, label=f"{tagname} ({sel[1]})")
        ax.axhline(target, color="k", ls="--", lw=0.9)
        ax.set_xticks(xs); ax.set_xticklabels([NAMES[s].split(" ")[0] for s in sites], rotation=45, ha="right")
        ax.axvspan(len(DEV) - 0.5, len(sites) - 0.5, color="0.93", zorder=0)
        ax.text(len(DEV) + 1.5, 1.02, "holdout sites", ha="center", fontsize=8, color="0.4")
        ax.set_title(lab, loc="left", fontsize=10)
        ax.set_ylim(0, 1.08)
        ax.legend(fontsize=8)
    fig.savefig(os.path.join(CH, "sites.png"))
    plt.close(fig)


def chart_speed(aggs, runs):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    labels, vals, cols = ["ADEMCMC (CARDAMOM, 32 CPU procs)"], [ADEMCMC_H * 60], ["0.3"]
    for r in runs:
        w = r["metrics"].get("wall_median")
        if w:
            labels.append(f"#{r['run']} {r['variant']}"[:40]); vals.append(w / 60)
            cols.append(STATUS_COLOR.get(r["status"], "k"))
    y = np.arange(len(labels))
    ax.barh(y, vals, color=cols)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xscale("log"); ax.set_xlabel("wall-clock per site fit, minutes (log scale)")
    ax.set_title("Speed: one site, one posterior", loc="left")
    ax.invert_yaxis()
    fig.savefig(os.path.join(CH, "speed.png"))
    plt.close(fig)


def md_to_html(md):
    out, in_list, in_table = [], False, False
    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not in_table:
                out.append("<table>"); in_table = True
                out.append("<tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            continue
        elif in_table:
            out.append("</table>"); in_table = False
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        elif in_list:
            out.append("</ul>"); in_list = False
        if line.startswith("### "):
            out.append(f"<h4>{inline(line[4:])}</h4>")
        elif line.startswith("## "):
            out.append(f"<h3>{inline(line[3:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h2>{inline(line[2:])}</h2>")
        elif line.startswith("```"):
            out.append("<pre>" if "<pre>" not in out[-1:] else "</pre>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def build():
    os.makedirs(CH, exist_ok=True)
    runs = load_runs()
    aggs = load_aggregates()
    chart_progress(runs); chart_categories(runs); chart_sites(aggs, runs); chart_speed(aggs, runs)
    kept = [r for r in runs if r["status"] in ("keep", "baseline")]
    best = min((r["metric"] for r in kept if r["metric"] is not None), default=None)
    rows = "".join(
        f"<tr><td>{r['run']}</td><td>{r['iteration']}</td><td>{html.escape(r['variant'])}</td>"
        f"<td>{html.escape(r.get('category') or '')}</td>"
        f"<td>{'' if r['metric'] is None else f'{r[chr(109)+chr(101)+chr(116)+chr(114)+chr(105)+chr(99)]:.3f}'}</td>"
        f"<td>{'' if r['metrics'].get('G_holdout') is None else f'{r[chr(109)+chr(101)+chr(116)+chr(114)+chr(105)+chr(99)+chr(115)][chr(71)+chr(95)+chr(104)+chr(111)+chr(108)+chr(100)+chr(111)+chr(117)+chr(116)]:.3f}'}</td>"
        f"<td style='color:{STATUS_COLOR.get(r['status'], 'k')}'><b>{r['status']}</b></td>"
        f"<td>{html.escape(r['description'])}</td></tr>" for r in reversed(runs))
    log_html = md_to_html(open(os.path.join(AR, "LOG.md")).read())
    ideas_html = md_to_html(open(os.path.join(AR, "autoresearch.ideas.md")).read())
    proto_html = md_to_html(open(os.path.join(AR, "autoresearch.md")).read())
    n_exp = len(runs); n_keep = sum(r["status"] == "keep" for r in runs)
    now = time.strftime("%Y-%m-%d %H:%M %Z")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SARLA autoresearch: making CARDAMOM faster</title>
<style>
body{{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#222;line-height:1.45}}
h1{{font-size:1.7rem}} h2{{font-size:1.3rem;margin-top:2.2rem;border-bottom:1px solid #ddd}} h3{{font-size:1.1rem}}
img{{max-width:100%;border:1px solid #eee;border-radius:6px;margin:.4rem 0}}
table{{border-collapse:collapse;font-size:.85rem;width:100%}} th,td{{border:1px solid #ddd;padding:.3rem .5rem;text-align:left;vertical-align:top}}
th{{background:#f4f6f8}} code{{background:#f4f6f8;padding:0 .2rem}} pre{{background:#f4f6f8;padding:.6rem;overflow-x:auto}}
.kpi{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}} .kpi div{{background:#f4f6f8;border-radius:8px;padding:.6rem 1rem;min-width:9rem}}
.kpi b{{display:block;font-size:1.4rem}} .small{{color:#666;font-size:.85rem}}
</style></head><body>
<h1>SARLA autoresearch: making CARDAMOM's calibration fast without making it wrong</h1>
<p class="small">Updated {now}. An automated research loop run by a Claude Code session, with a Codex advisor
after each iteration. Repository: <a href="https://github.com/sudshu/sarla-autoresearch">sudshu/sarla-autoresearch</a>.</p>

<h2>In one paragraph</h2>
<p>CARDAMOM estimates the parameters of a land carbon model (DALEC, 89 parameters) from satellite and flux-tower
data using a Markov-chain sampler that takes about 33 hours per site. SARLA is a GPU alternative that takes about
30 minutes. The question is whether the fast answer is also the <i>right</i> answer: does it produce the same
uncertainty ranges the slow method would? We test that with synthetic experiments where the truth is known
(an "OSSE"): a known parameter set generates fake observations at a real site, the sampler fits them, and we
check whether the truth falls inside the sampler's uncertainty ranges as often as it should. The single score
is the <b>calibration gap G</b>: 0 means perfectly calibrated; larger is worse. The loop proposes a change to the
sampler, tests it at four development sites, keeps it only if G improves, and periodically checks four
holdout sites that are never used for choosing, so the method cannot be tuned to one site's quirks.</p>

<div class="kpi">
<div><b>{n_exp}</b>experiments</div><div><b>{n_keep}</b>improvements kept</div>
<div><b>{'--' if best is None else f'{best:.2f}'}</b>best G (dev sites)</div>
<div><b>~30 min</b>per site (vs 33 h)</div>
</div>

<h2>Progress</h2>
<img src="charts/progress.png" alt="progress chart">
<p class="small">Each dot is one experiment (one sampler variant scored at the four development sites). Blue dots were
kept as the new default; red were discarded. Hollow squares show the same variant scored on the four holdout sites.</p>
<img src="charts/categories.png" alt="categories chart">
<img src="charts/sites.png" alt="per-site chart">
<p class="small">Left: fraction of the 89 parameters whose 90% posterior interval contains the truth (should be 0.90).
Right: where the truth's probability density ranks among the posterior draws (should be 0.50; near 0 means the
posterior is too narrow or misplaced). Grey band: holdout sites.</p>
<img src="charts/speed.png" alt="speed chart">

<h2>Experiments</h2>
<p class="small">Rows marked <b>v1-invalid</b> were scored against protocol-v1 truths, which the model's own
ecological constraints reject (see the log entry "Protocol v2"); they are kept for the record and decide nothing.</p>
<table><tr><th>#</th><th>iter</th><th>variant</th><th>category</th><th>G dev</th><th>G holdout</th><th>status</th><th>what and why</th></tr>
{rows}</table>

<h2>Log</h2>
{log_html}

<h2>Idea bank</h2>
{ideas_html}

<h2>Protocol (frozen)</h2>
{proto_html}
</body></html>"""
    open(os.path.join(DOCS, "index.html"), "w").write(page)
    json.dump(dict(updated=now, runs=runs, best_G_dev=best,
                   aggregates={str(k): {v: {kk: vv for kk, vv in s.items() if kk != "per_site"}
                                        for v, s in a.items()} for k, a in aggs.items()}),
              open(os.path.join(DOCS, "data.json"), "w"), indent=1)
    open(os.path.join(DOCS, ".nojekyll"), "w").write("")
    print(f"built docs/: {n_exp} experiments, best G {best}")


if __name__ == "__main__":
    build()
