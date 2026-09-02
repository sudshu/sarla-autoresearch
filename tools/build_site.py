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
PROTOCOL_VERSION = 3
FIRST_VALID_PROTOCOL = 2
ADEMCMC_H = 33.0
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 110, "savefig.bbox": "tight"})


def load_runs():
    runs = []
    for l in open(os.path.join(AR, "autoresearch.jsonl")):
        if l.strip():
            d = json.loads(l)
            if d.get("type") != "config":
                if d.get("protocol_version", 1) < FIRST_VALID_PROTOCOL:
                    d = dict(d, status="v1-invalid")
                runs.append(d)
    return runs


def load_aggregates():
    out = {}
    for f in sorted(glob.glob(os.path.join(AR, "experiments", "*", "aggregate.json"))):
        it = int(os.path.basename(os.path.dirname(f)))
        out[it] = json.load(open(f))
    return out


CAT_COLOR = {"baseline": "#4d4d4d", "walkers": "#8c6bb1", "moves": "#1f77b4", "charts": "#ff7f0e",
             "atlas": "#2ca02c", "atlas_geometry": "#d62728", "starts": "#17becf", "restarts": "#bcbd22",
             "budget": "#7f7f7f", "speed": "#e377c2", "other": "#999999"}


def chart_progress(runs):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    if runs:
        # protocol bands
        pv = [r.get("protocol_version", 1) for r in runs]
        xs = [r["run"] for r in runs]
        for v in sorted(set(pv)):
            sel = [x for x, p in zip(xs, pv) if p == v]
            ax.axvspan(min(sel) - 0.5, max(sel) + 0.5, color="0.92" if v < FIRST_VALID_PROTOCOL else "#eef6ee", zorder=0)
            ax.text(np.mean(sel), 5.15, f"protocol v{v}" + (" (invalid truths)" if v < FIRST_VALID_PROTOCOL else ""),
                    ha="center", fontsize=8, color="0.4")
        best, bests = np.inf, []
        for r in runs:
            g = None if r["metric"] is None else min(r["metric"], 5.0)
            valid = r["status"] != "v1-invalid"
            if valid and r["status"] in ("keep", "baseline") and g is not None:
                best = min(best, g)
            bests.append(best if np.isfinite(best) else np.nan)
            if g is None:
                continue
            col = CAT_COLOR.get(r.get("category") or "other", "#999") if valid else "0.75"
            marker = {"keep": "*", "baseline": "s", "discard": "o", "dev-only": "D", "crash": "x"}.get(r["status"], "o")
            ax.scatter(r["run"], g, color=col, marker=marker, s=110 if marker == "*" else 55, zorder=3,
                       edgecolor="k" if valid else "none", linewidth=0.6)
            h = r["metrics"].get("G_holdout")
            if h is not None and valid:
                ax.scatter(r["run"], min(h, 5.0), marker="s", facecolor="none", edgecolor="k", s=70, zorder=3)
        ax.step(xs, bests, where="post", color="#2166ac", lw=1.6, label="current default (best accepted)")
        for c, col in CAT_COLOR.items():
            if any((r.get("category") or "other") == c and r["status"] != "v1-invalid" for r in runs):
                ax.scatter([], [], color=col, label=c)
        ax.scatter([], [], marker="s", facecolor="none", edgecolor="k", label="holdout sites")
        ax.scatter([], [], color="0.75", label="invalid truths (v1)")
        ax.legend(fontsize=7.5, ncol=4, loc="upper left", bbox_to_anchor=(0, -0.18))
    ax.set_xlabel("experiment number")
    ax.set_ylabel("calibration gap G, development sites\n(0 = perfect; capped at 5)")
    ax.set_ylim(-0.1, 5.4)
    ax.set_title("Progress: lower is better", loc="left")
    ax.axhline(0, color="0.7", lw=0.8)
    fig.savefig(os.path.join(CH, "progress.png"))
    plt.close(fig)


def chart_heatmap(aggs, runs):
    """Variants (valid runs) x sites, colour = capped G."""
    rows = [r for r in runs if r["status"] != "v1-invalid" and r["metric"] is not None]
    if not rows:
        return
    sites = DEV + HOLDOUT
    M = np.full((len(rows), len(sites)), np.nan)
    for i, r in enumerate(rows):
        ps = r["metrics"].get("per_site", {})
        for j, s_ in enumerate(sites):
            if str(s_) in ps:
                M[i, j] = min(ps[str(s_)], 5.0)
    fig, ax = plt.subplots(figsize=(9, 0.6 + 0.42 * len(rows)))
    im = ax.imshow(M, cmap="RdYlGn_r", vmin=0, vmax=5, aspect="auto")
    ax.set_xticks(range(len(sites)))
    ax.set_xticklabels([NAMES[s_].split(" ")[0] + ("" if s_ in DEV else " (hold)") for s_ in sites], rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"#{r['run']} {r['variant']}" for r in rows], fontsize=8)
    for i in range(len(rows)):
        for j in range(len(sites)):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=7,
                        color="w" if M[i, j] > 2.5 else "k")
    ax.axvline(len(DEV) - 0.5, color="k", lw=1)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("G (0 good, 5 = failed)", fontsize=8)
    ax.set_title("Where each variant succeeds or fails, by site (green good, red bad)", loc="left", fontsize=10)
    fig.savefig(os.path.join(CH, "heatmap.png"))
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


def now_panel():
    ROOT = os.path.dirname(AR)
    st_path = os.path.join(ROOT, "runs", "autoresearch", "status.json")
    lines = []
    if os.path.exists(st_path):
        st = json.load(open(st_path))
        by_it = {}
        for jid, j in st["jobs"].items():
            if jid.startswith("i999"):
                continue
            it = jid.split("_")[0]
            by_it.setdefault(it, {}).setdefault(j["state"], 0)
            by_it[it][j["state"]] += 1
        for it in sorted(by_it):
            c = by_it[it]
            if c.get("running") or c.get("pending"):
                lines.append(f"iteration {int(it[1:])}: {c.get('running', 0)} fits running, {c.get('pending', 0)} waiting, {c.get('done', 0)} done")
        hosts = [f"{h}: {'down' if 'error' in v else str(len(v['running'])) + ' running'}" for h, v in st["hosts"].items()]
        lines.append("GPU hosts: " + "; ".join(hosts))
        lines.append(f"queue snapshot {time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(st['time']))}")
    log = open(os.path.join(AR, "LOG.md")).read()
    heads = [l[3:] for l in log.splitlines() if l.startswith("## ")]
    latest = heads[-1] if heads else ""
    return latest, lines


def build():
    os.makedirs(CH, exist_ok=True)
    runs = load_runs()
    aggs = load_aggregates()
    chart_progress(runs); chart_categories(runs); chart_sites(aggs, runs); chart_speed(aggs, runs)
    chart_heatmap(aggs, runs)
    latest, now_lines = now_panel()
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
.now{{background:#fff8e6;border-left:4px solid #e0a800;padding:.6rem 1rem;margin:1rem 0;font-size:.95rem}}
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
<div><b>{'--' if best is None else f'{best:.2f}'}</b>current default G (dev sites)</div>
<div><b>~50 min</b>per site fit (vs 33 h)</div>
</div>

<div class="now"><b>Latest:</b> {html.escape(latest)}<br>
<b>Right now:</b> {"<br>".join(html.escape(l) for l in now_lines) or "idle"}</div>

<h2>How to read this page</h2>
<ul>
<li><b>G</b> is the single score: how far the sampler's uncertainty ranges are from being right, averaged over
several checks (do 90% and 50% intervals hold the truth 90% and 50% of the time; does the truth's probability
density rank in the middle of the draws; are the forecasts' bands right). <b>0 is perfect</b>; about 0.3 is the
noise between repeated runs; <b>5 means the sampler landed in the wrong place</b> entirely.</li>
<li><b>Development sites</b> decide whether a change is kept. <b>Holdout sites</b> are only scored occasionally to
catch changes that merely fit the development sites.</li>
<li>Grey experiments were scored against truths later found to be invalid (protocol v1) and decide nothing.</li>
</ul>

<h2>Progress</h2>
<img src="charts/progress.png" alt="progress chart">
<p class="small">One dot per experiment, coloured by what kind of change was tried; a star marks a change that was
kept, a square the baseline. Hollow squares are the same variant on the holdout sites. The blue line is the current
default.</p>
<img src="charts/heatmap.png" alt="per-site heatmap">
<p class="small">Same experiments, one row each, one column per site. Green cells are well-calibrated fits, red
cells are failures. A variant that fixes the red columns without turning green ones yellow is what we are after.</p>
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
