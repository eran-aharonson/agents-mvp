"""Decision framework for agent reasoning."""

from typing import Any, Optional
from uuid import UUID

from .utility import UtilityFunction, UtilityWeights
from .consensus import ConsensusManager
from ..models.entities import Option, Decision


class DecisionFramework:
    """
    Framework for agent decision-making.
    Supports both individual and collaborative decisions.
    """

    def __init__(self, consensus_manager: ConsensusManager = None):
        self.consensus = consensus_manager or ConsensusManager()
        self._utility_functions: dict[UUID, UtilityFunction] = {}

    def register_agent_utility(
        self,
        agent_id: UUID,
        weights: UtilityWeights = None,
    ):
        """Register a utility function for an agent."""
        self._utility_functions[agent_id] = UtilityFunction(weights)

    def get_utility_function(self, agent_id: UUID) -> UtilityFunction:
        """Get or create utility function for an agent."""
        if agent_id not in self._utility_functions:
            self._utility_functions[agent_id] = UtilityFunction()
        return self._utility_functions[agent_id]

    def evaluate_options(
        self,
        agent_id: UUID,
        options: list[dict],
    ) -> list[tuple[int, float, dict]]:
        """
        Evaluate options using agent's utility function.

        Returns list of (index, score, option) sorted by score descending.
        """
        utility = self.get_utility_function(agent_id)
        scored = [
            (i, utility.evaluate_option(opt), opt)
            for i, opt in enumerate(options)
        ]
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def make_individual_decision(
        self,
        agent_id: UUID,
        context: str,
        options: list[dict],
    ) -> tuple[int, Option, str]:
        """
        Make an individual decision based on utility maximization.

        Returns:
            Tuple of (selected_index, Option, rationale)
        """
        if not options:
            raise ValueError("No options provided")

        ranked = self.evaluate_options(agent_id, options)
        best_idx, best_score, best_opt = ranked[0]

        selected = Option(
            name=best_opt.get("name", f"Option {best_idx}"),
            description=best_opt.get("description", ""),
            estimated_utility=best_score,
        )

        rationale = f"Selected based on utility score {best_score:.3f}"
        if len(ranked) > 1:
            second_score = ranked[1][1]
            rationale += f" (margin: {best_score - second_score:.3f})"

        return best_idx, selected, rationale

    def simulate_outcome(
        self,
        option: dict,
        context: dict[str, Any] = None,
    ) -> dict:
        """
        Simulate the outcome of an option.
        Returns estimated metrics.
        """
        # Simple simulation based on option parameters
        base_success = option.get("success_probability", 0.5)
        complexity = option.get("complexity", 0.5)
        resources = option.get("resource_cost", 0.5)

        # Adjust based on context
        if context:
            if context.get("time_pressure", False):
                base_success *= 0.9  # Pressure reduces success rate
            if context.get("extra_resources", False):
                resources *= 0.8  # More resources available

        return {
            "estimated_success": base_success * (1 - complexity * 0.3),
            "estimated_cost": resources,
            "estimated_time": complexity * 10,  # arbitrary units
            "risk_level": complexity * (1 - base_success),
        }

    def compare_options(
        self,
        agent_id: UUID,
        options: list[dict],
    ) -> dict:
        """
        Compare options with detailed analysis.
        """
        ranked = self.evaluate_options(agent_id, options)

        return {
            "ranking": [
                {
                    "index": idx,
                    "name": opt.get("name", f"Option {idx}"),
                    "score": score,
                    "simulation": self.simulate_outcome(opt),
                }
                for idx, score, opt in ranked
            ],
            "recommended": ranked[0][0] if ranked else None,
            "confidence": ranked[0][1] - ranked[1][1] if len(ranked) > 1 else 1.0,
        }
