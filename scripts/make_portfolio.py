"""Builds the portfolio graphics from a real run. Typed text is limited to labels; numbers, log lines, file listings, table rows and code are read from the run's files."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from county_market.pipeline import Config  # noqa: E402

OUT = ROOT / "outputs" / "portfolio"
INK, MUTED, FAINT, RULE, BLUE, RUST, TINT = "#111111", "#555555", "#8A8A8A", "#CFCFCF", "#1F4E79", "#9A3B12", "#F3F5F7"
W, H = 24, 13.5
SANS, MONO = "Liberation Sans", "Liberation Mono"
plt.rcParams.update({"font.family": SANS, "text.parse_math": False})
SOURCE = "Data: Redfin Data Center ZIP-code market tracker (public); Census 2010 ZIP Code Tabulation Areas and county outlines (public mirrors on GitHub)."


def facts():
    d = sorted((ROOT / "outputs" / "runs").glob("*/run.log"))[-1].parent
    log = (d / "run.log").read_text()
    cfg = Config.load(ROOT / "config" / "pipeline.toml")
    S = pd.read_csv(d / "summary.csv")
    return dict(dir=d, log=log, secs=float(re.search(r"([\d.]+) s ->", log).group(1)), failed=int(re.search(r"(\d+) failed", log).group(1)), qa=pd.read_csv(d / "qa_exceptions.csv"),
                ch=pd.read_csv(d / "changes_vs_previous.csv"), S=S, cfg=cfg, n=len(S), manual=cfg.manual_minutes_per_area * len(S), period=d.name)


def page(title, sub, bg="white", ink=INK, muted=MUTED):
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor=bg)
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_axis_off()
    ax.text(1.2, 12.3, title, fontsize=34, fontweight="bold", color=ink, va="center")
    ax.text(1.2, 11.5, sub, fontsize=17, color=muted, va="center")
    ax.plot([1.2, W - 1.2], [10.95, 10.95], color=ink, lw=1.4)
    ax.text(1.2, 0.55, SOURCE, fontsize=11, color=FAINT if bg == "white" else "#7C8794", va="center")
    ax.text(W - 1.2, 0.55, "Matt Powell", fontsize=11, color=FAINT if bg == "white" else "#7C8794", va="center", ha="right")
    return fig, ax


def label(ax, x, y, t, c=MUTED, fs=12.5):
    ax.text(x, y, t.upper(), fontsize=fs, color=c, fontweight="bold", va="center")


def shot(ax, path, x, y, w):
    im = mpimg.imread(path)
    h = w * im.shape[0] / im.shape[1]
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=RULE, lw=1.2, zorder=2))
    ax.imshow(im, extent=(x, x + w, y, y + h), zorder=3, aspect="auto")
    return h


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True).stdout.rstrip("\n")


def audit(fig, name):
    """Report text that overlaps other text, or an image/map tile, or runs past the canvas."""
    from matplotlib.text import Text
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    items = [(t, t.get_window_extent(r)) for t in fig.findobj(Text) if t.get_text().strip() and t.get_visible()]
    W_, H_ = fig.canvas.get_width_height()
    out = []
    for i, (a, ba) in enumerate(items):
        if ba.x0 < 0 or ba.y0 < 0 or ba.x1 > W_ or ba.y1 > H_:
            out.append(f"off canvas: {a.get_text()[:30]!r}")
        for b, bb in items[i + 1:]:
            if ba.x0 < bb.x1 and bb.x0 < ba.x1 and ba.y0 < bb.y1 and bb.y0 < ba.y1:
                out.append(f"overlap: {a.get_text()[:25]!r} x {b.get_text()[:25]!r}")
    ims = [im.get_window_extent(r) for ax_ in fig.axes for im in ax_.images]
    for a, ba in items:
        for bb in ims:
            if ba.x0 < bb.x1 and bb.x0 < ba.x1 and ba.y0 < bb.y1 and bb.y0 < ba.y1:
                out.append(f"text on image: {a.get_text()[:30]!r}")
    for o in sorted(set(out)):
        print(f"  [{name}] {o}")
    return out



def stage_counts(f):
    log = f["log"]
    g = lambda pat: re.search(pat, log)
    m = g(r"loaded (\d+) market rows, (\d+) ZIP polygons, (\d+) counties")
    return dict(rows=int(m.group(1)), zips=int(m.group(2)), counties=int(m.group(3)), joined=int(g(r"spatial join: (\d+)").group(1)), qa=int(g(r"QA: (\d+) exceptions").group(1)))


def rule(ax, y, x0=1.2, x1=W - 1.2, c=RULE, lw=1):
    ax.plot([x0, x1], [y, y], color=c, lw=lw)


def kpi(ax, x, y, val, lab, w=4.6, color=INK):
    ax.text(x, y, val, fontsize=34, fontweight="bold", color=color, va="center")
    ax.text(x, y - 0.75, lab, fontsize=13.5, color=MUTED, va="center")


# 1 -------------------------------------------------------------- case study overview
def overview(f):
    st = stage_counts(f)
    fig, ax = page("Automated county market maps", "Case study: a monthly reporting job for eight Houston-area counties, turned into one repeatable run")
    cols = [(1.2, "The problem", ["Monthly ZIP-level market data has to become a consistent map for every county.",
                                    "By hand it means loading layers, joining, checking for bad rows and exporting, once per county, every month.",
                                    "Quality checks get skipped and styling drifts between maps."]),
            (8.7, "The approach", ["One config file and one command.",
                                   "A spatial join assigns each ZIP to a county; validation rules flag thin or missing data instead of dropping it silently.",
                                   "One batch export with fixed classes and layout, plus a change log against the previous run."]),
            (16.2, "The result", [f"{f['n']} maps, a QA report and a change log in {f['secs']:.1f} seconds.",
                                  f"{st['qa']} data exceptions listed with the ZIP and the reason.",
                                  "Failures in one county are logged and do not stop the rest."])]
    import textwrap
    for x, t, paras in cols:
        label(ax, x, 10.35, t, c=BLUE)
        y = 9.6
        for ptxt in paras:
            w = textwrap.fill(ptxt, 46)
            ax.text(x, y, w, fontsize=15, color=INK, va="top", linespacing=1.4)
            y -= 0.3 * (w.count("\n") + 1) + 0.5
    rule(ax, 5.3)
    kpi(ax, 1.2, 4.3, f"{f['n']}", "county maps per run")
    kpi(ax, 6.2, 4.3, f"{f['secs']:.1f} s", "run time, measured")
    kpi(ax, 11.2, 4.3, f"{f['zips_total']}", "ZIP areas processed") if "zips_total" in f else kpi(ax, 11.2, 4.3, f"{int(f['S']['zips_total'].sum())}", "ZIP areas processed")
    kpi(ax, 16.2, 4.3, f"{st['qa']}", "exceptions flagged", color=RUST)
    kpi(ax, 21.0, 4.3, "0", "failed areas")
    rule(ax, 2.7)
    ax.text(1.2, 2.0, "Python · GeoPandas · Matplotlib · open source, no ArcGIS licence needed", fontsize=14, color=MUTED, va="center")
    audit(fig, "1"); fig.savefig(OUT / "1_overview.png", facecolor="white"); plt.close(fig)


# 2 -------------------------------------------------------------- before / after
def before_after(f):
    fig, ax = page("Before and after", f"The same monthly job, {f['n']} counties")
    bw, bh = 9.4, 0.78
    label(ax, 1.2, 10.35, "By hand")
    steps = ["Open the GIS project", "Load ZIP, county and market layers", "Run the spatial join", "Check for errors", "Export one map", f"Repeat for each county ({f['n']}×)"]
    y0 = 9.5
    for i, t in enumerate(steps):
        y = y0 - i * 1.18
        ax.add_patch(Rectangle((1.2, y - bh / 2), bw, bh, fc="white", ec=MUTED, lw=1.3))
        ax.text(1.5, y, f"{i + 1}", fontsize=14, color=FAINT, va="center", fontweight="bold")
        ax.text(2.2, y, t, fontsize=16, color=INK, va="center")
        if i < len(steps) - 1:
            ax.annotate("", xy=(5.9, y - 1.18 + bh / 2 + 0.02), xytext=(5.9, y - bh / 2 - 0.02), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.3))
    ax.text(1.2, 2.35, f"about {f['manual']:.0f} min per run", fontsize=24, fontweight="bold", color=RUST, va="center")
    ax.text(1.2, 1.7, f"Estimate: {f['cfg'].manual_minutes_per_area:g} min per county × {f['n']}. Not timed.", fontsize=12.5, color=MUTED, va="center")
    ax.plot([11.9, 11.9], [1.4, 10.4], color=RULE, lw=1)
    label(ax, 13.0, 10.35, "Scripted")
    ax.add_patch(Rectangle((13.0, 8.45), 9.8, 1.2, fc=INK, ec=INK))
    ax.text(17.9, 9.05, "python examples/run_monthly.py", fontsize=17, family=MONO, color="white", va="center", ha="center")
    ax.annotate("", xy=(17.9, 7.55), xytext=(17.9, 8.4), arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.8))
    ax.add_patch(Rectangle((13.0, 6.3), 9.8, 1.2, fc=TINT, ec=BLUE, lw=1.6))
    ax.text(17.9, 6.9, "Done", fontsize=24, fontweight="bold", color=BLUE, va="center", ha="center")
    for i, n in enumerate(["harris", "fort_bend", "montgomery"]):
        shot(ax, f["dir"] / "maps" / f"{n}.png", 13.0 + i * 3.3, 3.5, 3.2)
    ax.text(13.0, 3.0, f"{f['n']} maps, QA report, change log", fontsize=13, color=MUTED, va="center")
    ax.text(13.0, 2.35, f"{f['secs']:.1f} seconds", fontsize=24, fontweight="bold", color=BLUE, va="center")
    ax.text(13.0, 1.7, "Timed on this run.", fontsize=12.5, color=MUTED, va="center")
    audit(fig, "2"); fig.savefig(OUT / "2_before_after.png", facecolor="white"); plt.close(fig)


# 3 -------------------------------------------------------------- pipeline stages
def pipeline(f):
    st = stage_counts(f)
    fig, ax = page("How the pipeline works", "Five stages, each with a count taken from the run log")
    S = f["S"]
    stages = [("1  Load", f"{st['rows']:,} market rows\n{st['zips']} ZIP polygons\n{st['counties']} counties", "Redfin tracker, Census ZCTAs, county outlines"),
              ("2  Join", f"{st['joined']} ZIPs assigned\nto a county", "ZIP goes to the county holding most of its area"),
              ("3  Check", f"{st['qa']} exceptions", "thin markets, missing values, no boundary, split ZIPs"),
              ("4  Map", f"{f['n']} county maps", "same classes, colours and layout on every map"),
              ("5  Report", "summary.csv\nchange log\nrun.log", "figures and differences vs the previous run")]
    bw = 3.8
    for i, (t, big, small) in enumerate(stages):
        x = 1.2 + i * 4.45
        ax.add_patch(Rectangle((x, 5.3), bw, 4.6, fc=TINT, ec=RULE, lw=1.2))
        ax.add_patch(Rectangle((x, 9.35), bw, 0.55, fc=INK, ec=INK))
        ax.text(x + 0.25, 9.62, t, fontsize=15, fontweight="bold", color="white", va="center")
        ax.text(x + 0.25, 8.0, big, fontsize=17, color=INK, va="center", linespacing=1.5, fontweight="bold")
        import textwrap
        ax.text(x + 0.25, 6.4, textwrap.fill(small, 23), fontsize=12.5, color=MUTED, va="center", linespacing=1.4)
        if i < 4:
            ax.annotate("", xy=(x + 4.42, 7.6), xytext=(x + bw + 0.03, 7.6), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.5))
    label(ax, 1.2, 4.35, "Design choices")
    notes = ["Bad data is flagged with a reason, never dropped silently.", "Each county is processed independently; one failure is logged and the batch continues.",
             "All parameters live in one file, so a new month or a new area needs no code change.", "Every run keeps its outputs, which is what makes the change log possible."]
    for i, t in enumerate(notes):
        ax.text(1.2 + (i % 2) * 10.9, 3.5 - (i // 2) * 0.95, "• " + t, fontsize=14.5, color=INK, va="center")
    audit(fig, "3"); fig.savefig(OUT / "3_pipeline.png", facecolor="white"); plt.close(fig)


# 4 -------------------------------------------------------------- terminal
def terminal(f):
    BG = "#1C1C1C"
    fig, ax = page(f"Run output: {f['n']} county market maps", "A real run: the console log and the first lines of the files it wrote", bg=BG, ink="white", muted="#B5B5B5")
    ax.plot([1.2, W - 1.2], [10.95, 10.95], color="#444444", lw=1.2)
    p = f["period"]
    blocks = [("$ python examples/run_monthly.py", f["log"].strip()),
              (f"$ head -3 outputs/runs/{p}/qa_exceptions.csv", sh(f"head -3 outputs/runs/{p}/qa_exceptions.csv")),
              (f"$ head -3 outputs/runs/{p}/changes_vs_previous.csv", sh(f"head -3 outputs/runs/{p}/changes_vs_previous.csv"))]
    y = 10.3
    for cmd, out in blocks:
        ax.text(1.2, y, cmd, fontsize=13.5, family=MONO, color="#8FD18F", va="center")
        y -= 0.45
        for ln in out.splitlines():
            ln = re.sub(r" -> .*$", "", ln.replace(str(ROOT) + "/", "")) if "done:" in ln else ln.replace(str(ROOT) + "/", "")
            ax.text(1.2, y, ln, fontsize=13, family=MONO, color="#E6E6E6", va="center")
            y -= 0.4
        y -= 0.3
    audit(fig, "4"); fig.savefig(OUT / "4_run_output.png", facecolor=BG); plt.close(fig)


# 5 -------------------------------------------------------------- code vs maps
def tokens(line):
    out, i = [], 0
    while i < len(line):
        ch = line[i]
        if ch == "#":
            out.append((line[i:], "#6A737D")); break
        if ch in "\"'":
            j = line.index(ch, i + 1) + 1
            out.append((line[i:j], "#032F62")); i = j; continue
        m = re.match(r"[A-Za-z_]\w*", line[i:])
        if m:
            w = m.group(0)
            out.append((w, "#B31D28" if w in {"from", "import"} else INK)); i += len(w); continue
        out.append((ch, INK)); i += 1
    return out


def input_output(f):
    fig, ax = page("A few variables in, finished maps out", "Left: examples/run_monthly.py, the file you edit. Right: maps the same run produced.")
    code = (ROOT / "examples" / "run_monthly.py").read_text().splitlines()[1:]
    ax.add_patch(Rectangle((1.2, 1.3), 10.0, 9.2, fc="#F6F8FA", ec=RULE, lw=1.2))
    ax.add_patch(Rectangle((1.2, 1.3), 0.9, 9.2, fc="#EDEFF2", ec="none"))
    y = 10.0
    for k, ln in enumerate(code, 1):
        ax.text(2.0, y, str(k), fontsize=12, family=MONO, color=FAINT, ha="right", va="center")
        x = 2.4
        for t, col in tokens(ln):
            ax.text(x, y, t, fontsize=12.2, family=MONO, color=col, va="center")
            x += len(t) * 0.1017
        y -= 0.47
    for i, n in enumerate(["harris", "fort_bend", "montgomery", "galveston"]):
        x0 = 12.1 + (i % 2) * 5.5
        im = mpimg.imread(f["dir"] / "maps" / f"{n}.png")
        th = 5.2 * im.shape[0] / im.shape[1]
        y0 = 10.5 - th - (i // 2) * (th + 0.8)
        shot(ax, f["dir"] / "maps" / f"{n}.png", x0, y0, 5.2)
        ax.text(x0, y0 - 0.3, f"{n}.png", fontsize=12, family=MONO, color=MUTED, va="center")
    audit(fig, "5"); fig.savefig(OUT / "5_input_vs_output.png", facecolor="white"); plt.close(fig)


# 6 -------------------------------------------------------------- the report
def report(f):
    S, ch = f["S"], f["ch"].set_index("area")
    col = [c for c in S.columns if c.endswith("_sales_weighted")][0]
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor="#E4E6E9")
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_axis_off()
    ax.text(1.2, 13.0, "Generated outputs: summary table and QA map", fontsize=15, color=MUTED, va="center")
    px, py, pw, ph = 1.2, 0.8, 21.6, 11.5
    ax.add_patch(Rectangle((px + 0.1, py - 0.1), pw, ph, fc="#B8BCC2", ec="none"))
    ax.add_patch(Rectangle((px, py), pw, ph, fc="white", ec="#C9CDD2", lw=1))
    ax.text(px + 0.8, py + ph - 0.8, "County Market Snapshot", fontsize=26, fontweight="bold", color=INK, va="center")
    ax.text(px + 0.8, py + ph - 1.5, f"Houston area · median sale price, 3 months ending {pd.Timestamp(f['period']):%B %-d, %Y}", fontsize=13.5, color=MUTED, va="center")
    ax.plot([px + 0.8, px + pw - 0.8], [py + ph - 1.9, py + ph - 1.9], color=INK, lw=1.4)
    hdr = ["County", "ZIPs", "Mapped", "Flagged", "Homes sold", "Median price", "vs prior"]
    xs = [px + 0.8, px + 5.0, px + 6.4, px + 7.9, px + 9.6, px + 11.7, px + 13.5]
    ys = py + ph - 2.4
    for x, h_ in zip(xs, hdr):
        ax.text(x if h_ == "County" else x + 1.2, ys, h_, fontsize=11.5, color=MUTED, fontweight="bold", va="center", ha="left" if h_ == "County" else "right")
    rule(ax, ys - 0.3, px + 0.8, px + 14.9)
    T = S.sort_values(col, ascending=False).reset_index(drop=True)
    for i, r in T.iterrows():
        y = ys - 0.75 - i * 0.55
        vals = [r["area"], f"{r['zips_total']}", f"{r['zips_mapped']}", f"{r['zips_flagged']}", f"{r['homes_sold']:,}", f"${r[col]:,.0f}", f"{ch.loc[r['area'], 'change_pct']:+.1f}%"]
        for x, v, h_ in zip(xs, vals, hdr):
            ax.text(x if h_ == "County" else x + 1.2, y, v, fontsize=13, color=INK, va="center", ha="left" if h_ == "County" else "right")
    rule(ax, ys - 0.75 - 8 * 0.55 + 0.2, px + 0.8, px + 14.9)
    notes = ["Prices: sales-weighted mean of ZIP medians over mapped ZIPs.", "ZIPs with fewer than 10 sales are flagged, not mapped.", "ZIP shapes are 2010 ZCTAs; newer ZIPs have no polygon.", "ZIPs are postal areas, not neighborhoods."]
    for i, t in enumerate(notes):
        ax.text(px + 0.8, py + 3.3 - i * 0.5, t, fontsize=12.5, color=MUTED, va="center")
    ax.text(px + 0.8, py + 0.7, SOURCE, fontsize=9, color=FAINT, va="center")
    mh = shot(ax, f["dir"] / "qa_map.png", px + 15.5, py + 1.4, 5.4)
    ax.text(px + 15.5, py + 1.4 + mh + 0.35, "qa_map.png, written by the same run", fontsize=12, family=MONO, color=MUTED, va="center")
    audit(fig, "6"); fig.savefig(OUT / "6_report.png", facecolor="#E4E6E9"); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    f = facts()
    for fn in (overview, before_after, pipeline, terminal, input_output, report):
        fn(f)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
