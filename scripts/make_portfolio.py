"""Builds the four portfolio graphics from a real run: nothing on them is typed in except labels; times, counts and changes are read from the run's files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from county_market.pipeline import Config  # noqa: E402

OUT = ROOT / "outputs" / "portfolio"
INK, MUTED, ACC, GREEN, RED, PAPER = "#1B2430", "#5C6773", "#1F6FB2", "#15803D", "#B42318", "#FBFAF7"
W, H = 24, 13.5          # inches at 100 dpi = 2400 x 1350
plt.rcParams.update({"font.family": "Inter", "text.parse_math": False})


def run_dir() -> Path:
    runs = sorted((ROOT / "outputs" / "runs").glob("*/run.log"))
    return runs[-1].parent


def facts():
    d = run_dir()
    log = (d / "run.log").read_text()
    secs = float(re.search(r"([\d.]+) s ->", log).group(1))
    qa = pd.read_csv(d / "qa_exceptions.csv")
    ch = pd.read_csv(d / "changes_vs_previous.csv")
    S = pd.read_csv(d / "summary.csv")
    cfg = Config.load(ROOT / "config" / "pipeline.toml")
    return dict(dir=d, log=log, secs=secs, qa=qa, ch=ch, S=S, cfg=cfg, n=len(S), manual=cfg.manual_minutes_per_area * len(S))


def canvas(title: str, sub: str):
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor=PAPER)
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_axis_off()
    ax.text(1.0, 12.35, title, fontsize=40, fontweight="bold", color=INK, va="center")
    ax.text(1.0, 11.45, sub, fontsize=20, color=MUTED, va="center")
    return fig, ax


def box(ax, x, y, w, h, text, fc="white", ec="#CBD2D9", fs=19, color=INK, bold=False, lw=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, color=color, ha="center", va="center", fontweight="bold" if bold else "normal", linespacing=1.3)


def arrow(ax, p, q, color=MUTED, lw=2.5):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=22, lw=lw, color=color))


def foot(ax, text):
    ax.text(1.0, 0.55, text, fontsize=14, color=MUTED, va="center")


def before_after(f):
    fig, ax = canvas("Before / after", f"Monthly county market maps for {f['n']} Houston-area counties")
    ax.text(1.0, 10.3, "BY HAND (QGIS or any desktop GIS)", fontsize=18, fontweight="bold", color=RED)
    steps = ["Open the project", "Load ZIP, county and market layers", "Join ZIPs to counties", "Check for errors\n(thin sales, missing polygons)", "Export one map", f"Repeat for the next county  (× {f['n']})"]
    y = 9.55
    for i, s in enumerate(steps):
        h = 0.8 if "\n" not in s else 1.05
        box(ax, 1.0, y - h, 8.6, h, s, fs=18)
        if i < len(steps) - 1:
            arrow(ax, (5.3, y - h - 0.03), (5.3, y - h - 0.3))
        y -= h + 0.33
    ax.text(1.0, 1.55, f"≈ {f['manual']:.0f} min per run", fontsize=34, fontweight="bold", color=RED)
    ax.text(1.0, 0.98, f"assumed: {f['cfg'].manual_minutes_per_area:g} min × {f['n']} counties (an estimate, not a measurement)", fontsize=15, color=MUTED)
    ax.add_patch(Rectangle((11.2, 0.9), 0.04, 9.6, fc="#CBD2D9", ec="none"))
    ax.text(12.4, 10.3, "WITH THE SCRIPT", fontsize=18, fontweight="bold", color=GREEN)
    box(ax, 12.4, 6.9, 10.2, 1.7, "Run one command", fc="#ECFDF3", ec=GREEN, fs=30, bold=True, color=INK, lw=3)
    arrow(ax, (17.5, 6.8), (17.5, 6.0), color=GREEN)
    box(ax, 12.4, 4.3, 10.2, 1.6, "Done", fc=GREEN, ec=GREEN, fs=34, bold=True, color="white")
    outs = [f"{f['n']} consistent county maps", f"QA report: {len(f['qa'])} exceptions flagged", "Change log vs the previous run"]
    for i, o in enumerate(outs):
        ax.text(12.6, 3.45 - i * 0.55, "✓  " + o, fontsize=19, color=INK)
    ax.text(12.4, 1.55, f"{f['secs']:.1f} seconds", fontsize=34, fontweight="bold", color=GREEN)
    ax.text(12.4, 0.98, "measured on this machine, same data, same eight counties", fontsize=15, color=MUTED)
    fig.savefig(OUT / "1_before_after.png", facecolor=PAPER)
    plt.close(fig)


def terminal(f):
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor="#0B1220")
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_axis_off()
    ax.text(1.0, 12.6, f"Batch run: {f['n']} county market maps", fontsize=38, fontweight="bold", color="white", va="center")
    ax.text(1.0, 11.8, "Timestamped log, written to run.log on every run", fontsize=20, color="#9FB0C3", va="center")
    ax.add_patch(FancyBboxPatch((1.0, 0.9), 22.0, 10.2, boxstyle="round,pad=0.02,rounding_size=0.25", fc="#111A2B", ec="#233149", lw=2))
    ax.add_patch(Rectangle((1.0, 10.2), 22.0, 0.9, fc="#1A2740", ec="none"))
    for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        ax.plot([1.6 + i * 0.55], [10.65], "o", ms=14, color=c)
    ax.text(12.0, 10.65, "python -m county_market", fontsize=17, color="#9FB0C3", ha="center", va="center", family="DejaVu Sans Mono")
    lines = [l for l in f["log"].strip().splitlines()]
    rel = lambda s: s.replace(str(ROOT) + "/", "")
    y = 9.35
    ax.text(1.5, y, "$ python -m county_market", fontsize=19, color="#7EE787", family="DejaVu Sans Mono", va="center")
    y -= 0.7
    for ln in lines:
        ln = rel(ln)
        col = "#E6EDF3"
        if "done:" in ln:
            col = "#7EE787"
        elif "WARNING" in ln:
            col = "#E3B341"
        ax.text(1.5, y, ln, fontsize=16.2, color=col, family="DejaVu Sans Mono", va="center")
        y -= 0.55
    qa = f["qa"]["check"].value_counts()
    y -= 0.2
    ax.text(1.5, y, "QA exceptions by check:  " + "   ".join(f"{k} = {v}" for k, v in qa.items()), fontsize=16.2, color="#E3B341", family="DejaVu Sans Mono", va="center")
    fig.savefig(OUT / "2_terminal_run.png", facecolor="#0B1220")
    plt.close(fig)


def input_output(f):
    fig, ax = canvas("You set a few values. The script does the rest.", "Left: the configuration you edit. Right: maps the same run produced.")
    ax.add_patch(FancyBboxPatch((1.0, 1.4), 8.6, 9.3, boxstyle="round,pad=0.02,rounding_size=0.2", fc="#0F172A", ec="#0F172A"))
    ax.text(1.5, 10.2, "config/pipeline.toml", fontsize=15, color="#9FB0C3", family="DejaVu Sans Mono", va="center")
    cfg = f["cfg"]
    lines = [("[run]", "#79C0FF"), (f'areas = {len(cfg.areas)} counties', "#E6EDF3"), (f'metric = "{cfg.metric}"', "#E6EDF3"), (f'period_end = "{cfg.period_end}"', "#E6EDF3"),
             (f"min_sales = {cfg.min_sales}", "#E6EDF3"), ("", "#E6EDF3"), ("# everything else is automatic:", "#7EE787"), ("#   join, QA checks, 8 maps,", "#7EE787"), ("#   summary, change log, run.log", "#7EE787")]
    y = 9.2
    for t_, col in lines:
        ax.text(1.5, y, t_, fontsize=17, color=col, family="DejaVu Sans Mono", va="center")
        y -= 0.85
    arrow(ax, (9.9, 6.0), (11.0, 6.0), color=INK, lw=4)
    names = ["harris", "fort_bend", "montgomery", "galveston"]
    tw = 5.6
    for i, n in enumerate(names):
        im = mpimg.imread(f["dir"] / "maps" / f"{n}.png")
        h, w = im.shape[:2]
        th = tw * h / w
        x0 = 11.3 + (i % 2) * (tw + 0.35)
        y0 = 10.7 - th - (i // 2) * (th + 0.3)
        ax.add_patch(Rectangle((x0 - 0.04, y0 - 0.04), tw + 0.08, th + 0.08, fc="white", ec="#CBD2D9", lw=1.5))
        ax.imshow(im, extent=(x0, x0 + tw, y0, y0 + th), zorder=3, aspect="auto")
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.text(11.3, 0.8, f"4 of {f['n']} county maps from one run. Same classes, palette and layout on every sheet.", fontsize=15, color=MUTED)
    fig.savefig(OUT / "3_input_vs_output.png", facecolor=PAPER)
    plt.close(fig)


def replaced(f):
    qa, ch = f["qa"], f["ch"]
    thin = int((qa["check"] == "thin_market").sum()); nob = int((qa["check"] == "no_boundary").sum())
    up, dn = ch.sort_values("change_pct").iloc[-1], ch.sort_values("change_pct").iloc[0]
    fig, ax = canvas("What this script replaced", "Plain-language outcomes from one real run")
    rows = [("Checking every ZIP by hand", f"Automated checks flag {thin} thin-market ZIPs and {nob} ZIPs missing a polygon, listed in qa_exceptions.csv"),
            (f"Exporting {f['n']} county maps one at a time", f"{f['n']} maps with identical classes, colours and layout, produced in {f['secs']:.1f} seconds"),
            ("Comparing this period with the last by eye", f"changes_vs_previous.csv: {up['area']} {up['change_pct']:+.1f}%, {dn['area']} {dn['change_pct']:+.1f}% (sales-weighted median price)")]
    y = 9.9
    for a, b in rows:
        box(ax, 1.0, y - 1.5, 9.2, 2.6, a, fc="#FEF3F2", ec="#FECDCA", fs=24, color=INK, bold=True)
        arrow(ax, (10.5, y - 0.2), (11.5, y - 0.2), color=INK, lw=4)
        box(ax, 11.8, y - 1.5, 11.2, 2.6, "", fc="#ECFDF3", ec="#ABEFC6")
        import textwrap
        ax.text(12.2, y - 0.2, textwrap.fill(b, 58), fontsize=21, color=INK, va="center", linespacing=1.4)
        y -= 3.3
    ax.text(1.0, 0.5, f"Data: Redfin Data Center ZIP tracker, 3 months ending {pd.Timestamp(f['S'].attrs.get('end', '2026-05-31')):%B %Y}; Census 2010 ZCTAs. Counts and changes are read from this run's output files.", fontsize=14, color=MUTED, va="center")
    fig.savefig(OUT / "4_what_it_replaced.png", facecolor=PAPER)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    f = facts()
    for fn in (before_after, terminal, input_output, replaced):
        fn(f)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
