"""Utility functions for agent decision-making."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class UtilityWeights:
    """Weights for utility function components."""
    success_probability: float = 0.4
    resource_cost: float = 0.3
    time_efficiency: float = 0.3

    def normalize(self):
        """Ensure weights sum to 1."""
        total = self.success_probability + self.resource_cost + self.time_efficiency
        if total > 0:
            self.success_probability /= total
            self.resource_cost /= total
            self.time_efficiency /= total


class UtilityFunction:
    """
    Utility function for evaluating actions.
    U(action) = w1*P(success) + w2*resource_cost + w3*time_efficiency
    """

    def __init__(self, weights: UtilityWeights = None):
        self.weights = weights or UtilityWeights()
        self.weights.normalize()

    def evaluate(
        self,
        success_probability: float,
        resource_cost: float,
        time_efficiency: float,
    ) -> float:
        """
        Evaluate utility of an action.

        Args:
            success_probability: Probability of success (0-1)
            resource_cost: Normalized cost (0-1, lower is better)
            time_efficiency: Time efficiency score (0-1, higher is better)

        Returns:
            Utility score (0-1)
        """
        # Invert resource cost since lower cost = higher utility
        resource_utility = 1.0 - resource_cost

        utility = (
            self.weights.success_probability * success_probability +
            self.weights.resource_cost * resource_utility +
            self.weights.time_efficiency * time_efficiency
        )

        return max(0.0, min(1.0, utility))

    def evaluate_option(self, option: dict) -> float:
        """Evaluate utility from an option dict."""
        return self.evaluate(
            success_probability=option.get("success_probability", 0.5),
            resource_cost=option.get("resource_cost", 0.5),
            time_efficiency=option.get("time_efficiency", 0.5),
        )

    def rank_options(self, options: list[dict]) -> list[tuple[int, float]]:
        """Rank options by utility score."""
        scored = [(i, self.evaluate_option(opt)) for i, opt in enumerate(options)]
        return sorted(scored, key=lambda x: x[1], reverse=True)
