"""Builds the portfolio graphics from a real run. Labels are typed; every number (times, counts, changes, log lines, code) is read from the run's files."""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from county_market.pipeline import Config  # noqa: E402

OUT = ROOT / "outputs" / "portfolio"
NAVY, INK, MUTED, FAINT = "#0B2540", "#1B2430", "#5C6773", "#98A1AB"
TEAL, TEAL_L, AMBER, AMBER_L, RED, PAPER, LINE = "#0F766E", "#E6F4F1", "#B45309", "#FEF3E2", "#B42318", "#F4F6F8", "#D9DEE4"
W, H = 24, 13.5
plt.rcParams.update({"font.family": "Inter", "text.parse_math": False})
MONO = "DejaVu Sans Mono"


def facts():
    d = sorted((ROOT / "outputs" / "runs").glob("*/run.log"))[-1].parent
    log = (d / "run.log").read_text()
    secs = float(re.search(r"([\d.]+) s ->", log).group(1))
    failed = int(re.search(r"(\d+) failed", log).group(1))
    cfg = Config.load(ROOT / "config" / "pipeline.toml")
    S = pd.read_csv(d / "summary.csv")
    return dict(dir=d, log=log, secs=secs, failed=failed, qa=pd.read_csv(d / "qa_exceptions.csv"), ch=pd.read_csv(d / "changes_vs_previous.csv"), S=S, cfg=cfg, n=len(S),
                manual=cfg.manual_minutes_per_area * len(S), zips=int(S["zips_total"].sum()), period=d.name)


def canvas(eyebrow, title, sub, bg=PAPER):
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor=bg)
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_axis_off()
    ax.add_patch(Rectangle((0, H - 0.22), W, 0.22, fc=TEAL, ec="none"))
    ax.text(1.0, 12.3, eyebrow.upper(), fontsize=15, fontweight="bold", color=TEAL, va="center")
    ax.text(1.0, 11.45, title, fontsize=39, fontweight="bold", color=NAVY, va="center")
    ax.text(1.0, 10.6, sub, fontsize=19, color=MUTED, va="center")
    ax.text(W - 1.0, 0.6, "Matt Powell  ·  GIS automation", fontsize=14, color=FAINT, ha="right", va="center")
    return fig, ax


def card(ax, x, y, w, h, fc="white", ec=LINE, r=0.25, shadow=True):
    if shadow:
        ax.add_patch(FancyBboxPatch((x + 0.07, y - 0.09), w, h, boxstyle=f"round,pad=0.0,rounding_size={r}", fc="#0B2540", ec="none", alpha=0.07, zorder=1))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.0,rounding_size={r}", fc=fc, ec=ec, lw=1.6, zorder=2))


def arrow(ax, p, q, color=MUTED, lw=2.6, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=22, lw=lw, color=color, connectionstyle=f"arc3,rad={rad}", zorder=4))


def thumb(ax, path, x, y, w, border=LINE, shadow=True):
    im = mpimg.imread(path)
    h = w * im.shape[0] / im.shape[1]
    card(ax, x, y, w, h, fc="white", ec=border, r=0.12, shadow=shadow)
    ax.imshow(im, extent=(x + 0.05, x + w - 0.05, y + 0.05, y + h - 0.05), zorder=3, aspect="auto")
    return h


def badge(ax, x, y, t, fc=NAVY, r=0.3, fs=17):
    ax.add_patch(Circle((x, y), r, fc=fc, ec="none", zorder=5))
    ax.text(x, y, t, fontsize=fs, color="white", fontweight="bold", ha="center", va="center", zorder=6)


def chip(ax, x, y, text, fc=TEAL_L, color=TEAL, fs=15, pad=0.35):
    w = len(text) * fs * 0.0128 + pad * 2
    ax.add_patch(FancyBboxPatch((x, y - 0.3), w, 0.6, boxstyle="round,pad=0,rounding_size=0.3", fc=fc, ec="none", zorder=3))
    ax.text(x + w / 2, y, text, fontsize=fs, color=color, fontweight="bold", ha="center", va="center", zorder=4)
    return w


# ---------------------------------------------------------------- 1 before / after
def before_after(f):
    fig, ax = canvas("Workflow", "Before / after", f"Monthly market maps for {f['n']} Houston-area counties: from a manual routine to one command")
    card(ax, 1.0, 1.7, 10.3, 8.4, fc="white")
    ax.add_patch(Rectangle((1.0, 9.2), 10.3, 0.9, fc=AMBER_L, ec="none", zorder=2))
    ax.text(1.5, 9.65, "THE MANUAL WAY  (desktop GIS)", fontsize=17, fontweight="bold", color=AMBER, va="center", zorder=5)
    steps = ["Open the GIS project", "Load ZIP, county and market data", "Run spatial join", "Check for errors", "Export map", f"Repeat for the next county  (× {f['n']})"]
    y = 8.35
    for i, t in enumerate(steps):
        badge(ax, 1.9, y, str(i + 1), fc=AMBER, r=0.27, fs=15)
        ax.text(2.5, y, t, fontsize=19, color=INK, va="center", zorder=5)
        if i < len(steps) - 1:
            ax.plot([1.9, 1.9], [y - 0.32, y - 0.73], color=AMBER, lw=2.2, alpha=0.5, zorder=3)
        y -= 1.05
    arrow(ax, (10.7, 3.3), (10.7, 7.9), color=AMBER, lw=2, rad=-0.35)
    ax.text(1.5, 2.25, f"≈ {f['manual']:.0f} min per run", fontsize=30, fontweight="bold", color=AMBER, va="center", zorder=5)
    ax.text(8.5, 2.25, "every month", fontsize=15, color=MUTED, va="center", ha="right", zorder=5)
    card(ax, 12.7, 1.7, 10.3, 8.4, fc="white")
    ax.add_patch(Rectangle((12.7, 9.2), 10.3, 0.9, fc=TEAL_L, ec="none", zorder=2))
    ax.text(13.2, 9.65, "WITH THE SCRIPT", fontsize=17, fontweight="bold", color=TEAL, va="center", zorder=5)
    card(ax, 13.4, 7.4, 8.9, 1.3, fc=NAVY, ec=NAVY, r=0.2, shadow=False)
    ax.text(17.85, 8.05, "Run script", fontsize=28, fontweight="bold", color="white", ha="center", va="center", zorder=6)
    arrow(ax, (17.85, 7.3), (17.85, 6.75), color=TEAL, lw=3.5)
    card(ax, 13.4, 5.4, 8.9, 1.25, fc=TEAL, ec=TEAL, r=0.2, shadow=False)
    ax.text(17.85, 6.02, "Done", fontsize=30, fontweight="bold", color="white", ha="center", va="center", zorder=6)
    names = ["harris", "fort_bend", "montgomery", "galveston"]
    for i, n in enumerate(names):
        thumb(ax, f["dir"] / "maps" / f"{n}.png", 13.4 + i * 2.28, 3.55, 2.1, shadow=False)
    ax.text(13.4, 3.2, f"{f['n']} maps, same classes and layout", fontsize=14, color=MUTED, va="center", zorder=5)
    ax.text(13.4, 2.25, f"{f['secs']:.1f} seconds", fontsize=30, fontweight="bold", color=TEAL, va="center", zorder=5)
    ax.text(22.5, 2.25, "measured", fontsize=15, color=MUTED, va="center", ha="right", zorder=5)
    ax.text(1.0, 1.0, f"The {f['manual']:.0f}-minute figure is an assumption ({f['cfg'].manual_minutes_per_area:g} min per county, set in config/pipeline.toml); the {f['secs']:.1f} s is timed on this run.", fontsize=14, color=MUTED, va="center")
    fig.savefig(OUT / "1_before_after.png", facecolor=PAPER); plt.close(fig)


# ---------------------------------------------------------------- 2 terminal
def terminal(f):
    BG = "#0B1220"
    fig, ax = canvas("Run log", f"Automated monthly export: {f['n']} county market maps", "Timestamped log with per-area status and a summary, written to run.log on every run", bg=BG)
    ax.texts[1].set_color("white"); ax.texts[2].set_color("white"); ax.texts[3].set_color("#9FB0C3"); ax.texts[0].set_color("#5EEAD4")
    ax.patches[0].set_facecolor("#14B8A6")
    stats = [(f"{f['n']}", "areas"), (f"{f['zips']}", "ZIP areas"), (f"{len(f['qa'])}", "flagged"), (f"{f['failed']}", "failed"), (f"{f['secs']:.1f} s", "total")]
    for i, (v, l) in enumerate(stats):
        x = 1.0 + i * 4.4
        card(ax, x, 8.55, 4.1, 1.25, fc="#111A2B", ec="#233149", r=0.2, shadow=False)
        ax.text(x + 0.35, 9.3, v, fontsize=27, fontweight="bold", color="white", va="center", zorder=6)
        ax.text(x + 0.35, 8.88, l, fontsize=14, color="#9FB0C3", va="center", zorder=6)
    card(ax, 1.0, 0.9, 22.0, 7.3, fc="#111A2B", ec="#233149", r=0.25, shadow=False)
    ax.add_patch(Rectangle((1.0, 7.5), 22.0, 0.7, fc="#1A2740", ec="none", zorder=3))
    for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        ax.plot([1.6 + i * 0.5], [7.85], "o", ms=12, color=c, zorder=5)
    ax.text(12, 7.85, "python examples/run_monthly.py", fontsize=15, color="#9FB0C3", ha="center", va="center", family=MONO, zorder=5)
    y = 7.0
    rel = lambda s: s.replace(str(ROOT) + "/", "")
    for ln in f["log"].strip().splitlines():
        ln = re.sub(r" -> .*$", "", rel(ln)) if "done:" in ln else rel(ln)
        col = "#E6EDF3"
        if " ERROR " in ln:
            col = "#F87171"
        elif "WARNING" in ln:
            col = "#FBBF24"
        elif "done:" in ln:
            col = "#5EEAD4"
        m = re.match(r"(\d\d:\d\d:\d\d)\s+(\w+)\s+(.*)", ln)
        if m:
            ax.text(1.5, y, m.group(1), fontsize=14.5, color="#6B7C93", family=MONO, va="center", zorder=5)
            ax.text(3.7, y, m.group(2), fontsize=14.5, color="#5EEAD4" if m.group(2) == "INFO" else col, family=MONO, va="center", zorder=5)
            body = m.group(3)
            if len(body) > 118:
                body = body[:116] + "…"
            ax.text(5.1, y, body, fontsize=14.5, color=col, family=MONO, va="center", zorder=5)
        y -= 0.52
    fig.savefig(OUT / "2_terminal_run.png", facecolor=BG); plt.close(fig)


# ---------------------------------------------------------------- 3 input vs output
def tokens(line):
    out, i = [], 0
    kw = {"from", "import"}
    while i < len(line):
        ch = line[i]
        if ch == "#":
            out.append((line[i:], "#7EE787")); break
        if ch in "\"'":
            j = line.index(ch, i + 1) + 1
            out.append((line[i:j], "#FDBA74")); i = j; continue
        m = re.match(r"[A-Za-z_]\w*", line[i:])
        if m:
            w = m.group(0)
            col = "#79C0FF" if w in kw else ("#E6EDF3" if not w.isupper() else "#FDE68A")
            out.append((w, col)); i += len(w); continue
        out.append((ch, "#E6EDF3")); i += 1
    return out


def input_output(f):
    fig, ax = canvas("Configuration vs result", "You set a few variables. The script does the rest.", "Left: the real parameter file (examples/run_monthly.py). Right: maps from the same run.")
    code = [l for l in (ROOT / "examples" / "run_monthly.py").read_text().splitlines()][1:]
    code = [l for l in code if l.strip() != "" or True]
    card(ax, 1.0, 1.3, 10.4, 8.8, fc="#0F172A", ec="#0F172A", r=0.3)
    ax.add_patch(Rectangle((1.0, 9.35), 10.4, 0.75, fc="#16213A", ec="none", zorder=3))
    for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        ax.plot([1.6 + i * 0.5], [9.72], "o", ms=10, color=c, zorder=5)
    ax.text(6.2, 9.72, "run_monthly.py", fontsize=13, color="#9FB0C3", ha="center", va="center", family=MONO, zorder=5)
    y = 8.85
    for ln in code:
        x = 1.5
        for t, col in tokens(ln):
            ax.text(x, y, t, fontsize=12.2, color=col, family=MONO, va="center", zorder=5)
            x += len(t) * 0.1017
        y -= 0.44 if ln.strip() else 0.24
    arrow(ax, (11.7, 5.7), (12.9, 5.7), color=TEAL, lw=4)
    ax.text(12.3, 6.25, "run", fontsize=15, color=TEAL, fontweight="bold", ha="center")
    names = [("harris", "Harris"), ("fort_bend", "Fort Bend"), ("montgomery", "Montgomery"), ("galveston", "Galveston")]
    tw = 4.85
    for i, (n, label) in enumerate(names):
        x0 = 13.2 + (i % 2) * (tw + 0.4)
        im = mpimg.imread(f["dir"] / "maps" / f"{n}.png")
        th = tw * im.shape[0] / im.shape[1]
        y0 = 9.9 - th - (i // 2) * (th + 0.45)
        thumb(ax, f["dir"] / "maps" / f"{n}.png", x0, y0, tw)
    w1 = chip(ax, 13.2, 1.55, f"+ {f['n'] - 4} more counties", fs=13)
    chip(ax, 13.2 + w1 + 0.3, 1.55, "same classes on every map", fs=13, fc="#EEF2FF", color="#3730A3")
    fig.savefig(OUT / "3_input_vs_output.png", facecolor=PAPER); plt.close(fig)


# ---------------------------------------------------------------- 4 what it replaced
def replaced(f):
    qa, ch, S = f["qa"], f["ch"], f["S"]
    fig, ax = canvas("Outcomes", "What this script replaced", "Three routine tasks, and what each one produces now (all figures from one real run)")
    ys = [7.2, 4.2, 1.2]
    heads = [("Manual QA checks on every ZIP", "Automated validation with a flagged-exceptions report"),
             (f"Exporting {f['n']} county maps one at a time", f"Batch export: {f['n']} identically styled maps in {f['secs']:.1f} s"),
             ("Comparing this month with the last by eye", "Change log vs the previous run, per county")]
    for (a, b), y in zip(heads, ys):
        card(ax, 1.0, y, 22.0, 2.7, fc="white")
        ax.add_patch(Rectangle((1.0, y + 0.3), 0.14, 2.1, fc=TEAL, ec="none", zorder=3))
        ax.text(1.7, y + 1.95, "BEFORE", fontsize=12, fontweight="bold", color=AMBER, va="center", zorder=5)
        ax.text(1.7, y + 1.3, textwrap.fill(a, 30), fontsize=19, color=INK, va="center", zorder=5, linespacing=1.25)
        arrow(ax, (8.7, y + 1.35), (9.7, y + 1.35), color=TEAL, lw=3.5)
        ax.text(10.1, y + 1.95, "NOW", fontsize=12, fontweight="bold", color=TEAL, va="center", zorder=5)
        ax.text(10.1, y + 1.3, textwrap.fill(b, 34), fontsize=19, color=INK, va="center", zorder=5, linespacing=1.25, fontweight="bold")
    # row 1 evidence: QA categories
    cnt = qa["check"].value_counts()
    lab = {"thin_market": "thin market (< 10 sales)", "no_boundary": "no boundary polygon", "missing_value": "missing value", "split_zip": "split across counties"}
    ev = fig.add_axes((17.0 / W, (ys[0] + 0.45) / H, 5.3 / W, 1.8 / H))
    ev.barh([lab.get(k, k) for k in cnt.index[::-1]], cnt.values[::-1], color=AMBER, height=0.6)
    for i, v in enumerate(cnt.values[::-1]):
        ev.text(v, i, f" {v}", va="center", fontsize=13, color=INK, fontweight="bold")
    ev.set_xlim(0, cnt.max() * 1.25); ev.tick_params(labelsize=12, length=0, colors=MUTED); ev.set_xticks([])
    for sp in ev.spines.values():
        sp.set_visible(False)
    ev.set_facecolor("none")
    ax.text(17.0, ys[0] + 2.5, f"{len(qa)} exceptions flagged, listed in qa_exceptions.csv", fontsize=13, color=MUTED, va="center", zorder=5)
    # row 2 evidence: strip of all maps
    sw = 0.95 * 1.0
    names = list(S["area"])
    for i, a in enumerate(names):
        p = f["dir"] / "maps" / f"{a.lower().replace(' ', '_')}.png"
        im = mpimg.imread(p)
        w = 1.25; h = w * im.shape[0] / im.shape[1]
        x0 = 17.0 + (i % 4) * 1.4; y0 = ys[1] + 1.35 - (i // 4) * 0.95
        ax.add_patch(Rectangle((x0, y0), w, h * 0.78, fc="white", ec=LINE, lw=1, zorder=3))
        ax.imshow(im[int(im.shape[0] * 0.14): int(im.shape[0] * 0.95), :int(im.shape[1] * 0.66)], extent=(x0 + 0.02, x0 + w - 0.02, y0 + 0.02, y0 + h * 0.78 - 0.02), zorder=4, aspect="auto")
    # row 3 evidence: change bars
    c = ch.sort_values("change_pct")
    ev3 = fig.add_axes((17.0 / W, (ys[2] + 0.4) / H, 5.3 / W, 1.85 / H))
    ev3.barh(c["area"], c["change_pct"], color=[TEAL if v >= 0 else AMBER for v in c["change_pct"]], height=0.65)
    for i, v in enumerate(c["change_pct"]):
        ev3.text(v + (0.12 if v >= 0 else -0.12), i, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=11.5, color=INK, fontweight="bold")
    ev3.axvline(0, color=INK, lw=0.8); ev3.set_xlim(c["change_pct"].min() - 2.2, c["change_pct"].max() + 2.4)
    ev3.tick_params(labelsize=11, length=0, colors=MUTED); ev3.set_xticks([])
    for sp in ev3.spines.values():
        sp.set_visible(False)
    ev3.set_facecolor("none")
    ax.text(17.0, ys[2] + 2.5, f"sales-weighted median price vs {ch['previous_run'].iloc[0]}", fontsize=13, color=MUTED, va="center", zorder=5)
    fig.savefig(OUT / "4_what_it_replaced.png", facecolor=PAPER); plt.close(fig)


# ---------------------------------------------------------------- 5 monthly report
def report(f):
    S, ch = f["S"], f["ch"].set_index("area")
    col = [c for c in S.columns if c.endswith("_sales_weighted")][0]
    fig, ax = canvas("Deliverable", "The monthly report, generated", f"3 months ending {pd.Timestamp(f['period']):%B %Y} · built from the run's files")
    card(ax, 1.0, 1.4, 9.6, 8.7, fc="white")
    ax.text(1.5, 9.5, "Median sale price by county", fontsize=19, fontweight="bold", color=NAVY, va="center", zorder=5)
    ax.text(1.5, 9.0, "sales-weighted across mapped ZIPs · arrow = change vs previous run", fontsize=12.5, color=MUTED, va="center", zorder=5)
    T = S.sort_values(col, ascending=False).reset_index(drop=True)
    mx = T[col].max()
    for i, r in T.iterrows():
        y = 8.15 - i * 0.82
        ax.text(1.5, y, r["area"], fontsize=15, color=INK, va="center", zorder=5)
        bw = 4.4 * r[col] / mx
        ax.add_patch(FancyBboxPatch((4.0, y - 0.22), bw, 0.44, boxstyle="round,pad=0,rounding_size=0.1", fc=TEAL, ec="none", alpha=0.9, zorder=4))
        ax.text(4.0 + bw + 0.12, y, f"${r[col] / 1e3:,.0f}K", fontsize=13, color=INK, va="center", fontweight="bold", zorder=5)
        pc = ch.loc[r["area"], "change_pct"]
        ax.text(10.2, y, f"{'▲' if pc >= 0 else '▼'} {abs(pc):.1f}%", fontsize=13, color=TEAL if pc >= 0 else AMBER, va="center", ha="right", fontweight="bold", zorder=5)
    th = thumb(ax, f["dir"] / "maps" / "harris.png", 11.2, 5.0, 11.8)
    ax.text(11.2, 4.6, f"Harris County map, one of {f['n']} produced in the same run", fontsize=13, color=MUTED, va="center", zorder=5)
    k = [(f"{f['zips']}", "ZIP areas processed"), (f"{int(S['zips_mapped'].sum())}", "mapped"), (f"{int(S['zips_flagged'].sum())}", "flagged for QA"), (f"{int(S['homes_sold'].sum()):,}", "home sales covered")]
    for i, (v, l) in enumerate(k):
        x = 11.2 + i * 3.0
        card(ax, x, 1.4, 2.75, 2.5, fc="white")
        ax.text(x + 0.3, 3.0, v, fontsize=28, fontweight="bold", color=NAVY, va="center", zorder=5)
        ax.text(x + 0.3, 2.15, l, fontsize=12.5, color=MUTED, va="center", zorder=5)
    fig.savefig(OUT / "5_monthly_report.png", facecolor=PAPER); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    f = facts()
    for fn in (before_after, terminal, input_output, replaced, report):
        fn(f)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
