import pandas as pd

from county_market.pipeline import Config, Loader, QualityChecks, ROOT


def test_config_loads():
    cfg = Config.load(ROOT / "config" / "pipeline.toml")
    assert "Harris" in cfg.areas and cfg.min_sales == 10


def test_qa_flags_thin_and_missing():
    cfg = Config(["Harris"], min_sales=10)
    rows = pd.DataFrame({"zip": ["77001", "77002"], "median_sale_price": [300000.0, None], "homes_sold": [5, 50]})

    class A:
        table = pd.DataFrame({"zip": ["77001", "77002"], "county": ["Harris", "Harris"], "share": [1.0, 1.0]})

    import geopandas as gpd
    qa = QualityChecks(cfg).run(rows, A(), gpd.GeoDataFrame({"zip": [], "geometry": []}, geometry="geometry"))
    assert set(qa["check"]) == {"thin_market", "missing_value"}
