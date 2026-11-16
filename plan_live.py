"""python plan_live.py [--data path.csv] [--asof YYYY-MM-DD] [--threshold 55] [--ratio 3] [--out plan.txt]

Issue a next-day planning summary from a daily history CSV. With the packaged dataset and an --asof date inside it,
only data up to that date are used. Supplying fresh rows (same columns, see data/data_dictionary.csv) turns the
replay into a real workflow; fetch_open_meteo.py can produce such rows (untested without network access)."""
import argparse
from pathlib import Path
import pandas as pd
from operational import issue_forecast, summary_text
from evaluation import load_series

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(Path(__file__).resolve().parent / 'data/air_quality_historical.csv'))
    ap.add_argument('--asof'); ap.add_argument('--threshold', type=float, default=55.); ap.add_argument('--ratio', type=int, default=3, choices=[1, 3, 5])
    ap.add_argument('--out')
    a = ap.parse_args()
    raw = load_series(a.data)
    text = summary_text(issue_forecast(raw, a.asof, a.threshold, a.ratio))
    print(text)
    if a.out: Path(a.out).write_text(text + '\n', encoding='utf-8')
