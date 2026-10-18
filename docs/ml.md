# CPU machine learning

`flask --app app train-models --username demo --as-of 2026-06-30` is the only training entrypoint. Web requests never fit estimators. Artifacts are written atomically to `MODEL_DIR/<user-id>/<cutoff>.joblib`, with adjacent JSON evaluation reports. Use the same Python/scikit-learn environment for training and inference; only trusted local CLI artifacts belong in this directory because joblib uses pickle.

## Forecasting

Per-product daily consumption is the sum of negative `consumption` movements. Missing days become zero; receipts, quantity corrections and archive movements are excluded. A product needs 45 calendar days and at least 14 nonzero consumption days. Insufficient histories display an unavailable state instead of fabricated forecasts.

GradientBoostingRegressor uses Huber loss, 70 estimators, depth two and a fixed seed. Predictors are the preceding day's consumption, the seven-day lag, preceding 7/14-day means, and sine/cosine weekday encoding. Every feature precedes its target. The final chronological 20% of eligible samples is held out; the estimator fits the earlier 80%. MAE evaluates rolling one-step predictions against a seven-day moving-average baseline at identical origins. Actual earlier holdout observations may be used as lags, because they are known at each subsequent one-day prediction origin. The model is then refitted to all data through the training cutoff for deployment.

The dashboard recursively predicts 90 future daily consumptions. The first cumulative prediction crossing historical stock gives days remaining and the estimated stockout date. No crossing means no estimated stockout within the horizon, not infinite stock. The next seven predictions give expected weekly demand. Suggested orders are `ceil(max(0, 2 * weekly_demand - stock))`, capped at one million. They are application calculations, not LLM calculations. The one-step MAE is not a measured 90-day forecast error.

## Anomalies

IsolationForest uses 100 trees, a fixed seed, contamination 0.025 and `n_jobs=1`. It requires at least 30 receipt/consumption/adjustment movements. Features are magnitude divided by a product/type median, its log transform, direction and weekday. Median scaling is fitted only within the training cutoff and stored in the artifact. Opening/archive events are excluded as administrative lifecycle events.

Inference flags unusual movements and displays the latest 30 alerts at or before the selected date. This is retrospective anomaly review, not an automatically actionable decision. In-sample detection counts are descriptive, not independent anomaly accuracy estimates. Controlled anomaly recall on synthetic data is a demonstration check; flags can include normal movements. Notes identifying injected anomalies are never model features. No prediction modifies quantities or records.

## Historical correctness

Every training and prediction query excludes movement times after the chosen day. Artifacts include owner and cutoff. Inference selects the newest artifact whose cutoff is no later than the requested date; if none exists, it does not train on demand or reuse a future model. For a historical demonstration, explicitly train an earlier cutoff. Tests append extreme future events and verify historical forecasts and retrained metrics remain unchanged.

The seeded demo has 30 products, four suppliers, 180 daily consumption observations per product, weekly demand patterns, mild trends, replenishments and ten controlled spikes (five products, two spikes each). Existing usernames are rejected and unrelated users are untouched. Fixed seed 42 plus the same date range reproduces all business events; password hashes and insertion timestamps are intentionally not deterministic.

Reference algorithms and validation practices: [Gradient Boosting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html), [time series evaluation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split), [Isolation Forest documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).
