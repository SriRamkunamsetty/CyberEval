"""
CyberEval - Statistical Reliability Engine (Innovation 5)
Computes bootstrap confidence intervals, standard errors, and run-to-run stability metrics.
"""

from typing import List, Tuple, Dict, Any
import numpy as np


class StatisticalEngine:
    """Computes statistical significance and empirical confidence intervals."""

    @classmethod
    def compute_bootstrap_ci(
        cls,
        scores: List[float],
        n_bootstraps: int = 1000,
        ci_level: float = 0.95,
    ) -> Tuple[float, float, float, Dict[str, Any]]:
        """
        Computes 95% bootstrap confidence interval and standard error.
        Returns: (ci_lower, ci_upper, standard_error, stats_summary)
        """
        if not scores:
            return 0.0, 0.0, 0.0, {}

        arr = np.array(scores)
        n = len(arr)
        mean_score = float(np.mean(arr))
        std_dev = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        standard_error = float(std_dev / np.sqrt(n)) if n > 0 else 0.0

        if n < 2:
            return mean_score, mean_score, 0.0, {
                "sample_size": n,
                "mean": mean_score,
                "std_dev": 0.0,
                "standard_error": 0.0,
            }

        # Bootstrap resampling
        rng = np.random.default_rng(seed=42)
        boot_means = []
        for _ in range(n_bootstraps):
            sample = rng.choice(arr, size=n, replace=True)
            boot_means.append(float(np.mean(sample)))

        alpha = (1.0 - ci_level) / 2.0
        ci_lower = float(np.percentile(boot_means, alpha * 100))
        ci_upper = float(np.percentile(boot_means, (1.0 - alpha) * 100))

        stats_summary = {
            "sample_size": n,
            "mean": round(mean_score, 3),
            "std_dev": round(std_dev, 3),
            "standard_error": round(standard_error, 3),
            "ci_lower": round(ci_lower, 3),
            "ci_upper": round(ci_upper, 3),
            "ci_level": ci_level,
        }

        return round(ci_lower, 3), round(ci_upper, 3), round(standard_error, 3), stats_summary
