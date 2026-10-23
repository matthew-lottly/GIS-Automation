from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import ROOT, Config, Pipeline


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="county_market")
    p.add_argument("--config", default=str(ROOT / "config" / "pipeline.toml"))
    p.add_argument("--period-end", help="override the config's period_end")
    a = p.parse_args(argv)
    cfg = Config.load(Path(a.config))
    if a.period_end:
        cfg.period_end = a.period_end
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    Pipeline(cfg).run()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
