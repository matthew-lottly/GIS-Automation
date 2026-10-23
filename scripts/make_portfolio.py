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
INK, MUTED, FAINT, RULE, BLUE, RUST = "#111111", "#555555", "#8A8A8A", "#CFCFCF", "#1F4E79", "#9A3B12"
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


# 1 -------------------------------------------------------------- manual vs scripted
def before_after(f):
    fig, ax = page("Monthly county market maps: by hand vs scripted", f"{f['n']} Houston-area counties, one consistently styled map each, plus a QA report and a change log")
    label(ax, 1.2, 10.2, "By hand, in a desktop GIS")
    steps = ["Open the project", "Load the ZIP, county and market layers", "Run the spatial join", "Check for errors (thin sales, missing polygons)", "Export the map", f"Repeat for the next county ({f['n']} times)"]
    y = 9.3
    for i, t in enumerate(steps):
        ax.text(1.2, y, f"{i + 1}.", fontsize=19, color=MUTED, va="center")
        ax.text(2.0, y, t, fontsize=19, color=INK, va="center")
        y -= 0.95
    ax.plot([1.2, 11.0], [3.35, 3.35], color=RULE, lw=1)
    ax.text(1.2, 2.7, f"about {f['manual']:.0f} minutes per run", fontsize=26, fontweight="bold", color=RUST, va="center")
    ax.text(1.2, 2.05, f"Estimate: {f['cfg'].manual_minutes_per_area:g} minutes per county × {f['n']}. Not a timed measurement.", fontsize=13, color=MUTED, va="center")
    ax.plot([12.0, 12.0], [2.0, 10.2], color=RULE, lw=1)
    label(ax, 13.0, 10.2, "Scripted")
    ax.text(13.0, 9.3, "python examples/run_monthly.py", fontsize=19, family=MONO, color=INK, va="center")
    ax.plot([13.0, 22.8], [8.7, 8.7], color=RULE, lw=1)
    ax.text(13.0, 8.15, f"what it writes (outputs/runs/{f['period']}/):", fontsize=14, color=MUTED, va="center")
    listing = sh(f"ls -1 outputs/runs/{f['period']}")
    y = 7.55
    for ln in listing.splitlines():
        ax.text(13.0, y, ln, fontsize=14.5, family=MONO, color=INK, va="center")
        y -= 0.5
    for i, n in enumerate(["harris", "fort_bend", "montgomery"]):
        shot(ax, f["dir"] / "maps" / f"{n}.png", 13.0 + i * 3.35, 2.7, 3.2)
    ax.text(13.0, 2.05, f"{f['secs']:.1f} seconds, timed on this run", fontsize=26, fontweight="bold", color=BLUE, va="center")
    fig.savefig(OUT / "1_before_after.png", facecolor="white"); plt.close(fig)


# 2 -------------------------------------------------------------- terminal
def terminal(f):
    BG = "#1C1C1C"
    fig, ax = page(f"Automated monthly export: {f['n']} county market maps", "Terminal output from one real run, with the files it produced", bg=BG, ink="white", muted="#B5B5B5")
    ax.plot([1.2, W - 1.2], [10.95, 10.95], color="#444444", lw=1.2)
    p = f["period"]
    blocks = [("$ python examples/run_monthly.py", f["log"].strip()),
              (f"$ head -3 outputs/runs/{p}/qa_exceptions.csv", sh(f"head -3 outputs/runs/{p}/qa_exceptions.csv")),
              (f"$ head -3 outputs/runs/{p}/changes_vs_previous.csv", sh(f"head -3 outputs/runs/{p}/changes_vs_previous.csv"))]
    y = 10.3
    for cmd, out in blocks:
        ax.text(1.2, y, cmd, fontsize=13.5, family=MONO, color="#8FD18F", va="center")
        y -= 0.42
        for ln in out.splitlines():
            ln = re.sub(r" -> .*$", "", ln.replace(str(ROOT) + "/", "")) if "done:" in ln else ln.replace(str(ROOT) + "/", "")
            ax.text(1.2, y, ln, fontsize=13, family=MONO, color="#E6E6E6", va="center")
            y -= 0.385
        y -= 0.25
    fig.savefig(OUT / "2_terminal_run.png", facecolor=BG); plt.close(fig)


# 3 -------------------------------------------------------------- code vs maps
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
        y -= 0.5
    for i, (n, nm) in enumerate([("harris", "harris.png"), ("fort_bend", "fort_bend.png"), ("montgomery", "montgomery.png"), ("galveston", "galveston.png")]):
        x0 = 12.2 + (i % 2) * 5.75
        im = mpimg.imread(f["dir"] / "maps" / f"{n}.png")
        th = 5.4 * im.shape[0] / im.shape[1]
        y0 = 10.5 - th - (i // 2) * (th + 0.75)
        shot(ax, f["dir"] / "maps" / f"{n}.png", x0, y0, 5.4)
        ax.text(x0, y0 - 0.28, nm, fontsize=12, family=MONO, color=MUTED, va="center")
    fig.savefig(OUT / "3_input_vs_output.png", facecolor="white"); plt.close(fig)


# 4 -------------------------------------------------------------- what it replaced
def replaced(f):
    qa, ch, S = f["qa"], f["ch"], f["S"]
    fig, ax = page("What the script replaced", "Three routine tasks. Right-hand column: the evidence from one run.")
    for x, t in zip([1.2, 8.0, 13.0], ["Done by hand", "Done by the script", f"From the run ({f['period']})"]):
        label(ax, x, 10.4, t)
    rows = [("Checking every ZIP for problems", "Validation rules; exceptions\nwritten to qa_exceptions.csv"),
            (f"Exporting {f['n']} maps one at a time", f"One batch run, same classes\nand layout, {f['secs']:.1f} seconds"),
            ("Comparing with last month by eye", "Change log against\nthe previous run")]
    tops = [9.8, 6.9, 4.0]
    for (a_, b_), t in zip(rows, tops):
        ax.plot([1.2, W - 1.2], [t, t], color=RULE, lw=1)
        ax.text(1.2, t - 0.85, a_, fontsize=17, color=INK, va="center")
        ax.text(8.0, t - 0.85, b_, fontsize=17, color=INK, va="center", linespacing=1.35)
    ax.plot([1.2, W - 1.2], [1.1, 1.1], color=RULE, lw=1)
    cnt = qa["check"].value_counts()
    nm = {"thin_market": "fewer than 10 sales", "no_boundary": "no boundary polygon", "missing_value": "missing value", "split_zip": "split across counties"}
    ax.text(13.0, tops[0] - 0.55, f"{len(qa)} exceptions flagged", fontsize=15, fontweight="bold", color=INK, va="center")
    for i, (k, v) in enumerate(cnt.items()):
        ax.text(13.0, tops[0] - 1.2 - i * 0.45, nm.get(k, k), fontsize=14, color=INK, va="center")
        ax.text(19.0, tops[0] - 1.2 - i * 0.45, f"{v}", fontsize=14, color=RUST, va="center", ha="right", family=MONO)
    ax.text(13.0, tops[1] - 0.55, f"{f['n']} maps, {f['secs']:.1f} s", fontsize=15, fontweight="bold", color=INK, va="center")
    for i, a_ in enumerate(S["area"]):
        im = mpimg.imread(f["dir"] / "maps" / f"{a_.lower().replace(' ', '_')}.png")
        im = im[int(0.14 * im.shape[0]): int(0.95 * im.shape[0]), : int(0.66 * im.shape[1])]
        x0, y0 = 13.0 + i * 1.22, tops[1] - 2.1
        ax.add_patch(Rectangle((x0, y0), 1.12, 0.95, fc="white", ec=RULE, lw=1, zorder=2))
        ax.imshow(im, extent=(x0 + 0.02, x0 + 1.1, y0 + 0.02, y0 + 0.93), zorder=3, aspect="auto")
    c = ch.sort_values("change_pct", ascending=False).reset_index(drop=True)
    ax.text(13.0, tops[2] - 0.55, "Sales-weighted median price vs " + str(c["previous_run"].iloc[0]), fontsize=14, fontweight="bold", color=INK, va="center")
    for i, r in c.iterrows():
        x, y = 13.0 + (i // 4) * 5.4, tops[2] - 1.2 - (i % 4) * 0.4
        ax.text(x, y, r["area"], fontsize=13.5, color=INK, va="center")
        ax.text(x + 3.6, y, f"{r['change_pct']:+.1f}%", fontsize=13.5, color=BLUE if r["change_pct"] >= 0 else RUST, ha="right", va="center", family=MONO)
    fig.savefig(OUT / "4_what_it_replaced.png", facecolor="white"); plt.close(fig)


# 5 -------------------------------------------------------------- the report as a document
def report(f):
    S, ch = f["S"], f["ch"].set_index("area")
    col = [c for c in S.columns if c.endswith("_sales_weighted")][0]
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor="#E4E6E9")
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_axis_off()
    ax.text(1.2, 12.9, "Generated report (page 1 of 1)", fontsize=15, color=MUTED, va="center")
    px, py, pw, ph = 4.2, 0.9, 15.6, 11.6
    ax.add_patch(Rectangle((px + 0.12, py - 0.12), pw, ph, fc="#B8BCC2", ec="none"))
    ax.add_patch(Rectangle((px, py), pw, ph, fc="white", ec="#C9CDD2", lw=1))
    ax.text(px + 0.8, py + ph - 0.9, "County Market Snapshot", fontsize=27, fontweight="bold", color=INK, va="center")
    ax.text(px + 0.8, py + ph - 1.6, f"Houston area · median sale price, 3 months ending {pd.Timestamp(f['period']):%B %-d, %Y}", fontsize=14, color=MUTED, va="center")
    ax.plot([px + 0.8, px + pw - 0.8], [py + ph - 2.0, py + ph - 2.0], color=INK, lw=1.4)
    hdr = ["County", "ZIPs", "Mapped", "Flagged", "Homes sold", "Median price", "vs prior"]
    xs = [px + 0.8, px + 4.4, px + 5.7, px + 7.1, px + 8.7, px + 10.7, px + 12.4]
    ys = py + ph - 2.55
    for x, h in zip(xs, hdr):
        ax.text(x if h == "County" else x + 1.1, ys, h, fontsize=11.5, color=MUTED, fontweight="bold", va="center", ha="left" if h == "County" else "right")
    ax.plot([px + 0.8, px + pw - 0.8], [ys - 0.3, ys - 0.3], color=RULE, lw=1)
    T = S.sort_values(col, ascending=False).reset_index(drop=True)
    for i, r in T.iterrows():
        y = ys - 0.75 - i * 0.42
        vals = [r["area"], f"{r['zips_total']}", f"{r['zips_mapped']}", f"{r['zips_flagged']}", f"{r['homes_sold']:,}", f"${r[col]:,.0f}", f"{ch.loc[r['area'], 'change_pct']:+.1f}%"]
        for x, v, h in zip(xs, vals, hdr):
            ax.text(x if h == "County" else x + 1.1, y, v, fontsize=13, color=INK, va="center", ha="left" if h == "County" else "right")
    ytab = ys - 0.75 - 7 * 0.42 - 0.3
    ax.plot([px + 0.8, px + pw - 0.8], [ytab, ytab], color=RULE, lw=1)
    h = shot(ax, f["dir"] / "maps" / "harris.png", px + 0.8, py + 1.15, 5.6)
    ax.text(px + 7.0, py + 1.15 + h - 0.2, "Notes", fontsize=13, fontweight="bold", color=INK, va="center")
    notes = ["Prices are the sales-weighted mean of ZIP medians over mapped ZIPs.", "ZIPs with fewer than 10 sales are flagged and not mapped.",
             "ZIP Code Tabulation Areas are 2010 shapes; ZIPs created since have no polygon.", "ZIPs are postal areas, not neighborhoods.", "Map: Harris County, same classes as the other seven."]
    for i, t in enumerate(notes):
        ax.text(px + 7.0, py + 1.15 + h - 0.8 - i * 0.62, "\n".join(__import__("textwrap").wrap(t, 52)), fontsize=11.5, color=MUTED, va="top", linespacing=1.3)
    ax.text(px + 0.8, py + 0.55, SOURCE, fontsize=8.8, color=FAINT, va="center")
    fig.savefig(OUT / "5_monthly_report.png", facecolor="#E4E6E9"); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    f = facts()
    for fn in (before_after, terminal, input_output, replaced, report):
        fn(f)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
