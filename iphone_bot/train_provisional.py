"""Train provisional NBA box-score regression models with chronological holdout.

Training uses only prior-game rolling data and pregame context, never a player's
same-game box score. These are NOT calibrated prop win probabilities.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nba/processed/training_dataset.csv"
OUT = ROOT / "models/nba/provisional"
TARGETS = ("PTS", "REB", "AST", "PRA")
# Strict allowlist of lagged stats + pre-game schedule; never use live box-score columns.
BASE = ("MIN_L5", "MIN_L10", "MIN_Season", "DAYS_REST", "IS_HOME",
        "IS_B2B", "IS_FRESH", "GAMES_7D", "IS_4_IN_6")
STATS = ("PTS", "REB", "AST", "FGA", "FG3A", "TOV")
FEATURES = BASE + tuple(f"{s}_{w}" for s in STATS for w in
                        ("L5", "L10", "Season"))
MIN_TEST = 1000

def main():
    if not DATA.exists():
        raise FileNotFoundError(f"Missing input: {DATA}")
    df = pd.read_csv(DATA, low_memory=False)
    required = {"GAME_DATE", "PLAYER_ID", *TARGETS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="raise")
    df = df.sort_values(["GAME_DATE", "PLAYER_ID"]).reset_index(drop=True)
    cols = [c for c in FEATURES if c in df.columns]
    if len(cols) < 12:
        raise ValueError(f"Insufficient available lagged features: {cols}")
    print(f"Loaded {len(df):,} game rows; {len(cols)} lagged features", flush=True)
    # Date boundary, never split different players' games on the same date.
    dates = df["GAME_DATE"].drop_duplicates().sort_values().to_numpy()
    if len(dates) < 150:
        raise ValueError("Not enough historical game dates")
    cutoff = pd.Timestamp(dates[int(len(dates) * 0.8)])
    calibration_start = pd.Timestamp(dates[int(len(dates) * 0.6)])
    cal_train = df["GAME_DATE"] < calibration_start
    cal_dates = (df["GAME_DATE"] >= calibration_start) & (df["GAME_DATE"] < cutoff)
    tr = df["GAME_DATE"] < cutoff
    te = ~tr
    if tr.sum() < 5000 or te.sum() < MIN_TEST:
        raise ValueError(f"Insufficient date-split rows: train={tr.sum()}, test={te.sum()}")
    X = df[cols].apply(pd.to_numeric, errors="coerce")
    # All feature missingness is resolved using ONLY training observations.
    medians = X.loc[tr].median().fillna(0)
    X = X.fillna(medians).replace([np.inf, -np.inf], 0)
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for target in TARGETS:
        y = pd.to_numeric(df[target], errors="coerce")
        train_mask = tr & y.notna()
        test_mask = te & y.notna()
        if test_mask.sum() < MIN_TEST:
            raise ValueError(f"Not enough holdout values for {target}")
        model = HistGradientBoostingRegressor(
            max_iter=180, max_leaf_nodes=21, max_depth=5,
            min_samples_leaf=65, learning_rate=0.055,
            l2_regularization=4.0, early_stopping=False, random_state=42
        )
        # Fit a separate earlier model for out-of-time residuals; never
        # derive residuals from rows the calibration model was trained on.
        calibration_model = HistGradientBoostingRegressor(
            max_iter=180, max_leaf_nodes=21, max_depth=5,
            min_samples_leaf=65, learning_rate=0.055,
            l2_regularization=4.0, early_stopping=False, random_state=42
        )
        calibration_fit = cal_train & y.notna()
        calibration_eval = cal_dates & y.notna()
        if calibration_fit.sum()<5000 or calibration_eval.sum()<2000:
            raise ValueError("Insufficient chronological calibration observations")
        calibration_fill = df[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan).loc[calibration_fit].median().fillna(0)
        # X has already been imputed with first-80%-training medians; build
        # calibration matrix from raw features to prevent that subtle leak.
        x_cal = df[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
        x_cal = x_cal.fillna(calibration_fill).fillna(0)
        calibration_model.fit(x_cal.loc[calibration_fit],y.loc[calibration_fit])
        cal_pred = np.maximum(0,calibration_model.predict(x_cal.loc[calibration_eval]))
        residuals = (y.loc[calibration_eval].to_numpy(dtype=float)-cal_pred)
        if not np.isfinite(residuals).all():
            raise ValueError("Calibration contains nonfinite residuals")
        model.fit(X.loc[train_mask], y.loc[train_mask])
        pred = np.maximum(0, model.predict(X.loc[test_mask]))
        actual = y.loc[test_mask]
        baseline_col = f"{target}_L10"
        if baseline_col in X:
            baseline = X.loc[test_mask, baseline_col].clip(lower=0)
        elif target == "PRA":
            baseline = (X.loc[test_mask, "PTS_L10"] + X.loc[test_mask, "REB_L10"] +
                        X.loc[test_mask, "AST_L10"]).clip(lower=0)
        else:
            baseline = pd.Series(y.loc[train_mask].median(), index=actual.index)
        result = {
            "target": target,
            "train_rows": int(train_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "mae": round(float(mean_absolute_error(actual, pred)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(actual, pred))), 4),
            "baseline_mae": round(float(mean_absolute_error(actual, baseline)), 4),
        }
        joblib.dump({"model": model, "features": cols,
                     "fill_values": medians.to_dict(), "target": target,
                     "cutoff": cutoff.strftime("%Y-%m-%d"),
                     "experimental_residuals": residuals.tolist(),
                     "residual_calibration": {
                         "method": "CHRONOLOGICAL_VALIDATION_EMPIRICAL_RESIDUALS_UNCALIBRATED",
                         "train_before": str(calibration_start.date()),
                         "calibration_from": str(calibration_start.date()),
                         "calibration_through": str(df.loc[calibration_eval,"GAME_DATE"].max().date()),
                         "calibration_rows": int(calibration_eval.sum()),
                         "real_market_calibrated": False
                     }},
                    OUT / f"{target}_model.joblib", compress=3)
        results.append(result)
        print(result, flush=True)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "train_through": str(df.loc[tr, "GAME_DATE"].max().date()),
        "holdout_from": str(cutoff.date()),
        "holdout_through": str(df.loc[te, "GAME_DATE"].max().date()),
        "input_rows": int(len(df)),
        "feature_names": cols,
        "metrics": results,
        "status": "RESEARCH_ONLY",
        "limitations": [
            "Archive lacks verified player position, personal fouls, and first-half data.",
            "This is a chronological offline holdout, not a live betting backtest.",
            "Model residual distributions are derived from a separate chronological 60%-80% slice, not from sportsbook prop outcomes.",
            "Experimental error-frequency estimates are not calibrated probabilities or verified betting hit rates.",
            "Some existing upstream engineered features may reflect future information; only the explicit lagged-feature allowlist is used here."
        ]
    }
    (OUT / "evaluation.json").write_text(json.dumps(report, indent=2))
    print("Finished training provisional models", flush=True)

if __name__ == "__main__":
    main()
