"""
Causal inference.

Given the per-test-case DataFrame for a single test definition, this module
tries to answer "what *caused* the failures?" rather than "what correlates
with them". It runs two complementary causal analyses:

1. Regression (time-based / difference-in-differences): did something change at
   a point in time that *caused* the pass rate to drop? Treatment = the
   post-change period, outcome = passed, confounders = environment + browser.

2. Environment effect: does a particular environment/browser *cause* failures,
   controlling for time? Treatment = "is the minority/suspect environment".

The primary estimator is dowhy's full pipeline
(identify_effect -> estimate_effect -> refute_estimate). If dowhy is
unavailable or errors out, we fall back to a manual difference-in-means with a
scipy significance test so the feature still produces a result.

The final verdict is one of: regression | env_issue | flaky | inconclusive.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Significance / effect-size thresholds.
_P_THRESHOLD = 0.05
_EFFECT_THRESHOLD = 0.15  # absolute change in pass-rate considered meaningful
_MIN_SAMPLES_PER_SIDE = 3


def _best_split_index(passed: np.ndarray) -> int:
    """Find the split index maximizing |mean(after) - mean(before)| in pass rate."""
    n = len(passed)
    best_idx = -1
    best_diff = 0.0
    for i in range(_MIN_SAMPLES_PER_SIDE, n - _MIN_SAMPLES_PER_SIDE + 1):
        before = passed[:i].mean()
        after = passed[i:].mean()
        diff = abs(after - before)
        if diff > best_diff:
            best_diff = diff
            best_idx = i
    return best_idx


def _dowhy_effect(
    data: pd.DataFrame,
    treatment: str,
    outcome: str,
    common_causes: List[str],
) -> Optional[Dict[str, Any]]:
    """Run dowhy's full identify -> estimate -> refute pipeline."""
    try:
        from dowhy import CausalModel

        usable_causes = [c for c in common_causes if data[c].nunique() > 1]
        model = CausalModel(
            data=data,
            treatment=treatment,
            outcome=outcome,
            common_causes=usable_causes or None,
        )
        identified = model.identify_effect(proceed_when_unidentifiable=True)
        estimate = model.estimate_effect(
            identified,
            method_name="backdoor.linear_regression",
        )
        effect = float(estimate.value)

        p_value = None
        try:
            sig = estimate.test_stat_significance()
            p_value = float(np.ravel(sig["p_value"])[0])
        except Exception:  # noqa: BLE001
            p_value = None

        refutation = None
        try:
            refute = model.refute_estimate(
                identified,
                estimate,
                method_name="placebo_treatment_refuter",
                placebo_type="permute",
                num_simulations=20,
            )
            refutation = {
                "method": "placebo_treatment_refuter",
                "new_effect": float(refute.new_effect),
                # A robust estimate should collapse to ~0 under placebo treatment.
                "passed": abs(float(refute.new_effect)) < abs(effect) * 0.5 + 1e-6,
            }
        except Exception as exc:  # noqa: BLE001
            logger.debug("dowhy refutation skipped: %s", exc)

        return {
            "engine": "dowhy",
            "method": "backdoor.linear_regression",
            "effect": effect,
            "p_value": p_value,
            "confounders_checked": usable_causes,
            "refutation": refutation,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("dowhy estimation failed (%s); using fallback", exc)
        return None


def _fallback_effect(
    data: pd.DataFrame,
    treatment: str,
    outcome: str,
) -> Dict[str, Any]:
    """Manual difference-in-means + scipy test as a dowhy fallback."""
    treated = data[data[treatment] == 1][outcome]
    control = data[data[treatment] == 0][outcome]
    effect = float(treated.mean() - control.mean()) if len(treated) and len(control) else 0.0

    p_value = None
    try:
        from scipy import stats

        # Chi-square on the 2x2 outcome/treatment table.
        table = pd.crosstab(data[treatment], data[outcome])
        if table.shape == (2, 2):
            _, p_value, _, _ = stats.chi2_contingency(table)
            p_value = float(p_value)
    except Exception as exc:  # noqa: BLE001
        logger.debug("scipy fallback test skipped: %s", exc)

    return {
        "engine": "manual_did",
        "method": "difference_in_means + chi2",
        "effect": effect,
        "p_value": p_value,
        "confounders_checked": [],
        "refutation": None,
    }


def _estimate(data: pd.DataFrame, treatment: str, outcome: str, common_causes: List[str]) -> Dict[str, Any]:
    result = _dowhy_effect(data, treatment, outcome, common_causes)
    if result is None:
        result = _fallback_effect(data, treatment, outcome)
    return result


class CausalAnalyzer:
    """Causal analysis over a single test definition's execution history."""

    def analyze(self, df: pd.DataFrame, def_id: Optional[int]) -> Dict[str, Any]:
        """
        Analyze the failures of one test definition.

        Args:
            df: Full extracted DataFrame (all definitions).
            def_id: Target test definition id. If None, analyze the whole frame.

        Returns:
            A structured causal result dict including a `verdict`.
        """
        if df is None or df.empty:
            return self._inconclusive("No execution data available.")

        sub = df[df["def_id"] == def_id].copy() if def_id is not None else df.copy()
        if sub.empty:
            return self._inconclusive("No execution data for this test.")

        # Sort chronologically.
        sub["ts"] = pd.to_datetime(sub["case_created_at"], errors="coerce")
        sub = sub.sort_values("ts").reset_index(drop=True)

        n = len(sub)
        pass_rate = float(sub["passed"].mean())
        time_series = self._pass_rate_series(sub)

        # Encode confounders.
        sub["env_code"] = sub["environment"].astype("category").cat.codes
        sub["browser_code"] = sub["browser"].astype("category").cat.codes

        # --- Analysis 1: regression (time-based change point) ---
        regression = None
        if n >= 2 * _MIN_SAMPLES_PER_SIDE:
            split = _best_split_index(sub["passed"].to_numpy())
            if split > 0:
                sub["post"] = 0
                sub.loc[split:, "post"] = 1
                intervention_ts = sub.loc[split, "ts"]
                est = _estimate(sub, "post", "passed", ["env_code", "browser_code"])
                regression = {
                    **est,
                    "treatment": "post_change_period",
                    "intervention_at": intervention_ts.isoformat() if pd.notna(intervention_ts) else None,
                    "before_pass_rate": float(sub[sub["post"] == 0]["passed"].mean()),
                    "after_pass_rate": float(sub[sub["post"] == 1]["passed"].mean()),
                }

        # --- Analysis 2: environment effect ---
        environment = None
        if sub["environment"].nunique() > 1:
            # Treat the environment with the lowest pass rate as the suspect.
            env_rates = sub.groupby("environment")["passed"].mean()
            suspect_env = env_rates.idxmin()
            sub["is_suspect_env"] = (sub["environment"] == suspect_env).astype(int)
            if sub["is_suspect_env"].nunique() > 1:
                est = _estimate(sub, "is_suspect_env", "passed", ["browser_code"])
                environment = {
                    **est,
                    "treatment": f"environment={suspect_env}",
                    "suspect_environment": str(suspect_env),
                    "suspect_pass_rate": float(env_rates.min()),
                    "other_pass_rate": float(env_rates.drop(suspect_env).mean()),
                }
        # Also consider browser if a single environment.
        elif sub["browser"].nunique() > 1:
            br_rates = sub.groupby("browser")["passed"].mean()
            suspect_br = br_rates.idxmin()
            sub["is_suspect_env"] = (sub["browser"] == suspect_br).astype(int)
            if sub["is_suspect_env"].nunique() > 1:
                est = _estimate(sub, "is_suspect_env", "passed", ["env_code"])
                environment = {
                    **est,
                    "treatment": f"browser={suspect_br}",
                    "suspect_environment": str(suspect_br),
                    "suspect_pass_rate": float(br_rates.min()),
                    "other_pass_rate": float(br_rates.drop(suspect_br).mean()),
                }

        verdict, primary = self._classify(regression, environment, pass_rate, n)

        return {
            "def_id": def_id,
            "n_samples": n,
            "overall_pass_rate": pass_rate,
            "verdict": verdict,
            "primary": primary,
            "regression": regression,
            "environment": environment,
            "time_series": time_series,
        }

    def _classify(self, regression, environment, pass_rate, n):
        """Decide the verdict from the two analyses."""
        def is_significant(res):
            if not res:
                return False
            eff = res.get("effect")
            p = res.get("p_value")
            if eff is None:
                return False
            sig_effect = abs(eff) >= _EFFECT_THRESHOLD
            sig_p = (p is None) or (p <= _P_THRESHOLD)
            return sig_effect and sig_p

        reg_sig = is_significant(regression) and (regression.get("effect", 0) < 0)
        env_sig = is_significant(environment) and (environment.get("effect", 0) < 0)

        if reg_sig and (not env_sig or abs(regression["effect"]) >= abs(environment["effect"])):
            return "regression", regression
        if env_sig:
            return "env_issue", environment
        # No significant cause but there are failures with a moderate pass rate
        # that fluctuates -> flaky.
        if 0.05 < pass_rate < 0.95 and n >= 2 * _MIN_SAMPLES_PER_SIDE:
            return "flaky", (regression or environment)
        if pass_rate >= 0.95:
            return "healthy", None
        return "inconclusive", (regression or environment)

    def _pass_rate_series(self, sub: pd.DataFrame) -> List[Dict[str, Any]]:
        """Daily pass-rate time series for charting (DID visualization)."""
        if sub.empty or sub["ts"].isna().all():
            return []
        tmp = sub.dropna(subset=["ts"]).copy()
        tmp["date"] = tmp["ts"].dt.strftime("%Y-%m-%d")
        grouped = tmp.groupby("date").agg(
            pass_rate=("passed", "mean"),
            n=("passed", "size"),
        )
        return [
            {"date": idx, "pass_rate": round(float(row.pass_rate), 4), "n": int(row.n)}
            for idx, row in grouped.iterrows()
        ]

    def _inconclusive(self, reason: str) -> Dict[str, Any]:
        return {
            "def_id": None,
            "n_samples": 0,
            "overall_pass_rate": None,
            "verdict": "inconclusive",
            "primary": None,
            "regression": None,
            "environment": None,
            "time_series": [],
            "reason": reason,
        }
