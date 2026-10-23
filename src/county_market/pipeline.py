from __future__ import annotations

import logging
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CRS_AREA = "EPSG:3081"          # Texas Centric Albers, metres


@dataclass
class Config:
    areas: list[str]
    metric: str = "median_sale_price"
    period_end: str = "latest"
    min_sales: int = 10
    output_dir: Path = ROOT / "outputs" / "runs"
    manual_minutes_per_area: float = 6.0

    @classmethod
    def load(cls, path: Path) -> "Config":
        d = tomllib.loads(Path(path).read_text())
        r = d["run"]
        out = Path(r.get("output_dir", "outputs/runs"))
        return cls(r["areas"], r.get("metric", "median_sale_price"), r.get("period_end", "latest"), int(r.get("min_sales", 10)),
                   out if out.is_absolute() else ROOT / out, float(d.get("portfolio", {}).get("manual_minutes_per_area", 6)))


@dataclass
class Result:
    run_dir: Path
    seconds: float
    summary: pd.DataFrame
    exceptions: pd.DataFrame
    changes: pd.DataFrame
    maps: list[Path] = field(default_factory=list)


class Loader:
    def __init__(self, data: Path = ROOT / "data"):
        self.market = pd.read_csv(data / "houston_zip_market.csv", dtype={"zip": str})
        self.zips = gpd.read_file(data / "houston_zip_boundaries.geojson")
        self.counties = gpd.read_file(data / "texas_counties.geojson")

    def snapshot(self, period_end: str) -> tuple[pd.DataFrame, str]:
        end = max(self.market["period_end"]) if period_end == "latest" else period_end
        rows = self.market[self.market["period_end"] == end]
        if rows.empty:
            raise ValueError(f"no market rows for period_end={end}")
        return rows, end


class Assigner:
    """Spatial join: each ZIP polygon goes to the county that contains most of its area."""

    def __init__(self, zips: gpd.GeoDataFrame, counties: gpd.GeoDataFrame):
        z = zips.to_crs(CRS_AREA)
        c = counties.to_crs(CRS_AREA)[["NAME", "geometry"]]
        z["geometry"] = z.geometry.make_valid()
        inter = gpd.overlay(z[["zip", "geometry"]], c, how="intersection", keep_geom_type=True)
        inter["a"] = inter.geometry.area
        best = inter.sort_values("a", ascending=False).drop_duplicates("zip")
        tot = z.set_index("zip").geometry.area
        best["share"] = best["a"].to_numpy() / tot.reindex(best["zip"]).to_numpy()
        self.table = best[["zip", "NAME", "share"]].rename(columns={"NAME": "county"})
        self.z = z


class QualityChecks:
    """Every check returns rows of (area, zip, check, detail). Nothing is silently dropped."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def run(self, market: pd.DataFrame, asg: Assigner, raw_zips: gpd.GeoDataFrame) -> pd.DataFrame:
        m, out = self.cfg.metric, []
        poly = set(asg.table["zip"])
        county_of = asg.table.set_index("zip")["county"]
        share = asg.table.set_index("zip")["share"]
        for _, r in market.iterrows():
            z = r["zip"]
            area = county_of.get(z, "(no polygon)")
            if z not in poly:
                out.append((area, z, "no_boundary", "ZIP is in the market table but has no polygon in the boundary file"))
            elif area not in self.cfg.areas:
                continue
            if pd.isna(r[m]):
                out.append((area, z, "missing_value", f"{m} is empty"))
            if r["homes_sold"] < self.cfg.min_sales:
                out.append((area, z, "thin_market", f"{int(r['homes_sold'])} sales < {self.cfg.min_sales}"))
            if z in share.index and share[z] < 0.5:
                out.append((area, z, "split_zip", f"only {share[z]:.0%} of the ZIP lies in {area}"))
        bad = raw_zips[~raw_zips.geometry.is_valid]
        for z in bad["zip"]:
            out.append((county_of.get(z, "(no polygon)"), z, "invalid_geometry", "polygon was repaired before use"))
        dup = market[market.duplicated("zip", keep=False)]
        for z in dup["zip"].unique():
            out.append((county_of.get(z, "(no polygon)"), z, "duplicate_row", "more than one market row for this ZIP and period"))
        return pd.DataFrame(out, columns=["area", "zip", "check", "detail"])


class CountyMap:
    """One consistent map per area: same classes, palette, layout and source note on every sheet."""

    def __init__(self, cfg: Config, edges: np.ndarray, period_label: str):
        self.cfg, self.edges, self.period = cfg, edges, period_label

    def draw(self, area: str, z: gpd.GeoDataFrame, county: gpd.GeoDataFrame, path: Path, cmap, flagged: set[str]) -> Path:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch

        plt.rcParams["text.parse_math"] = False
        fig = plt.figure(figsize=(10, 6.4), dpi=150)
        ax = fig.add_axes([0.02, 0.09, 0.63, 0.74])
        fig.patch.set_facecolor("#FBFAF7")
        county.plot(ax=ax, fc="#EDEAE0", ec="#8A8578", lw=1.0)
        v = z[self.cfg.metric].to_numpy()
        cls = np.clip(np.searchsorted(self.edges[1:-1], v, side="right"), 0, len(self.edges) - 2)
        ok = ~z["flag"].to_numpy() & ~np.isnan(v)
        z[ok].plot(ax=ax, color=[cmap(c / (len(self.edges) - 2)) for c in cls[ok]], ec="white", lw=0.5)
        if (~ok).any():
            z[~ok].plot(ax=ax, fc="#E4E6E9", ec="#9AA3AD", lw=0.4, hatch="////")
        county.boundary.plot(ax=ax, color="#1B2430", lw=1.1)
        x0, y0, x1, y1 = county.total_bounds
        pad = max(x1 - x0, y1 - y0) * 0.04
        ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad); ax.set_aspect("equal"); ax.set_axis_off()
        fig.text(0.03, 0.935, f"{area} County: {self.cfg.metric.replace('_', ' ')}", fontsize=16, fontweight="bold", color="#1B2430", va="center")
        fig.text(0.03, 0.885, f"3 months ending {self.period}  ·  {int(ok.sum())} ZIPs mapped, {int((~ok).sum())} flagged", fontsize=9.5, color="#5C6773", va="center")
        n = len(self.edges) - 1
        handles = [Patch(fc=cmap(i / (n - 1)), ec="white", label=f"${self.edges[i] / 1e3:,.0f}K – ${self.edges[i + 1] / 1e3:,.0f}K") for i in range(n)]
        handles.append(Patch(fc="#E4E6E9", ec="#9AA3AD", hatch="////", label="Flagged (see QA report)"))
        fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.68, 0.46), fontsize=8.5, frameon=False, title="Median sale price\n(same classes on every county)", title_fontsize=8.5, alignment="left")
        fig.text(0.03, 0.03, "Data: Redfin Data Center ZIP-code tracker; Census 2010 ZCTAs; county outlines. Generated by county_market.", fontsize=6.5, color="#7B8794")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, facecolor=fig.get_facecolor())
        plt.close(fig)
        return path


class Pipeline:
    def __init__(self, cfg: Config, logger: logging.Logger | None = None):
        import sys
        self.cfg, self.log = cfg, logger or logging.getLogger("county_market")
        if not self.log.handlers:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%H:%M:%S"))
            self.log.addHandler(h)
            self.log.setLevel(logging.INFO)

    def run(self, run_label: str | None = None) -> Result:
        import io

        import matplotlib.pyplot as plt

        buf = io.StringIO()
        cap = logging.StreamHandler(buf)
        cap.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%H:%M:%S"))
        self.log.addHandler(cap)
        t0 = time.perf_counter()
        L = Loader()
        rows, end = L.snapshot(self.cfg.period_end)
        self.log.info("loaded %d market rows, %d ZIP polygons, %d counties; period ending %s", len(L.market), len(L.zips), len(L.counties), end)
        asg = Assigner(L.zips, L.counties)
        self.log.info("spatial join: %d ZIP polygons assigned to counties", len(asg.table))
        qa = QualityChecks(self.cfg).run(rows, asg, L.zips)
        self.log.info("QA: %d exceptions across %d checks", len(qa), qa["check"].nunique())
        z = asg.z.merge(rows, on="zip", how="inner").merge(asg.table[["zip", "county"]], on="zip")
        z["flag"] = z["zip"].isin(qa.loc[qa["check"].isin(["thin_market", "missing_value", "split_zip", "duplicate_row"]), "zip"])
        z = z[z["county"].isin(self.cfg.areas)]
        good = z.loc[~z["flag"], self.cfg.metric].dropna()
        edges = np.unique(np.quantile(good, np.linspace(0, 1, 7)))
        cmap = plt.get_cmap("YlGnBu")
        run_dir = self.cfg.output_dir / (run_label or end)
        label = pd.Timestamp(end).strftime("%B %Y")
        painter = CountyMap(self.cfg, edges, label)
        maps, summary, failed = [], [], []
        for area in self.cfg.areas:
            za = z[z["county"] == area].copy()
            if za.empty:
                self.log.warning("%s: no ZIPs after join, skipped", area)
                continue
            county = L.counties.to_crs(CRS_AREA)
            county = county[county["NAME"] == area]
            try:
                maps.append(painter.draw(area, za, county, run_dir / "maps" / f"{area.lower().replace(' ', '_')}.png", cmap, set()))
            except Exception as exc:                       # one bad area must not stop the batch
                failed.append(area)
                self.log.error("%s: failed (%s)", area, exc)
                continue
            g = za[~za["flag"]]
            w = g["homes_sold"]
            summary.append({"area": area, "zips_total": len(za), "zips_mapped": len(g), "zips_flagged": int(za["flag"].sum()),
                            "homes_sold": int(w.sum()), f"{self.cfg.metric}_sales_weighted": round(float((g[self.cfg.metric] * w).sum() / w.sum()), 0) if w.sum() else np.nan})
            self.log.info("%-11s %3d ZIPs  %3d mapped  %2d flagged  -> %s", area, len(za), len(g), int(za["flag"].sum()), maps[-1].name)
        S = pd.DataFrame(summary)
        run_dir.mkdir(parents=True, exist_ok=True)
        S.to_csv(run_dir / "summary.csv", index=False)
        qa.to_csv(run_dir / "qa_exceptions.csv", index=False)
        changes = self._changes(S, run_dir)
        changes.to_csv(run_dir / "changes_vs_previous.csv", index=False)
        secs = time.perf_counter() - t0
        self.log.info("done: %d areas processed, %d failed, %d maps, %d QA exceptions, %d changed rows vs previous run, %.1f s -> %s",
                      len(maps), len(failed), len(maps), len(qa), len(changes), secs, run_dir)
        (run_dir / "run.log").write_text(buf.getvalue())
        self.log.removeHandler(cap)
        return Result(run_dir, secs, S, qa, changes, maps)

    def _changes(self, S: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
        prev = sorted(p for p in self.cfg.output_dir.glob("*/summary.csv") if p.parent != run_dir and p.parent.name < run_dir.name)
        col = f"{self.cfg.metric}_sales_weighted"
        if not prev:
            return pd.DataFrame(columns=["area", "previous_run", "previous", "current", "change_pct"])
        P = pd.read_csv(prev[-1]).set_index("area")[col]
        rows = [{"area": r["area"], "previous_run": prev[-1].parent.name, "previous": P.get(r["area"]), "current": r[col],
                 "change_pct": round((r[col] / P.get(r["area"]) - 1) * 100, 1) if P.get(r["area"]) else np.nan} for _, r in S.iterrows()]
        return pd.DataFrame(rows)
