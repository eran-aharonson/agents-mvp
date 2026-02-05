#!/usr/bin/env python3
"""
Demo: Autonomous AI Agents for Collaborative Decision-Making

This demo shows multiple agents collaborating to solve a resource allocation problem.
"""

import asyncio
import random
from uuid import UUID

from src.agent.base import BaseAgent
from src.agent.engine import AgentEngine
from src.models.entities import AgentRole, AgentStatus, Task
from src.collaboration.protocols import Message, MessageType, VoteType
from src.decision.utility import UtilityWeights


class ResourceAllocationAgent(BaseAgent):
    """
    An agent specialized in resource allocation decisions.
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        specialization: str,
        bias: str = "balanced",
    ):
        # Different agents have different priorities
        weights = {
            "cost_focused": UtilityWeights(0.2, 0.6, 0.2),
            "speed_focused": UtilityWeights(0.2, 0.2, 0.6),
            "quality_focused": UtilityWeights(0.6, 0.2, 0.2),
            "balanced": UtilityWeights(0.34, 0.33, 0.33),
        }

        super().__init__(
            name=name,
            role=role,
            capabilities=[specialization, "resource_allocation"],
            utility_weights=weights.get(bias, UtilityWeights()),
        )

        self.specialization = specialization
        self.bias = bias
        self.entity.expertise_score = random.uniform(0.7, 1.0)
        self._idle_cycles = 0

    async def _autonomous_cycle(self):
        """Periodic autonomous behavior."""
        self._idle_cycles += 1

        # Occasionally share observations
        if self._idle_cycles % 50 == 0:
            observation = f"{self.name} observes system load: {random.randint(20, 80)}%"
            self.update_knowledge("last_observation", observation)

    async def execute_task(self, task: Task):
        """Execute assigned task."""
        print(f"  [{self.name}] Executing task: {task.name}")

        # Simulate work
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # Complete task
        task.status = "completed"
        task.result = {"success": True, "agent": self.name}
        self.status = AgentStatus.IDLE
        self._current_task = None

        print(f"  [{self.name}] Task completed!")

    async def evaluate_proposal(
        self,
        proposal: dict,
    ) -> tuple[VoteType, int, str]:
        """Evaluate proposal using utility function."""
        options = proposal.get("options", [])

        if not options:
            return VoteType.ABSTAIN, 0, "No options provided"

        # Evaluate each option
        if self._decision_framework:
            ranked = self._decision_framework.evaluate_options(self.id, options)
            best_idx, best_score, _ = ranked[0]

            # Decide vote based on score
            if best_score > 0.6:
                rationale = f"Strong support (utility={best_score:.2f}, bias={self.bias})"
                return VoteType.YES, best_idx, rationale
            elif best_score > 0.4:
                rationale = f"Moderate support (utility={best_score:.2f})"
                return VoteType.YES, best_idx, rationale
            else:
                rationale = f"Low utility ({best_score:.2f})"
                return VoteType.NO, best_idx, rationale

        return VoteType.ABSTAIN, 0, "No decision framework"

    async def on_message(self, message: Message):
        """Handle custom messages."""
        if message.type == MessageType.BROADCAST:
            # Process broadcast information
            pass


async def run_demo():
    """Run the multi-agent demo."""
    print("=" * 60)
    print("AUTONOMOUS AI AGENTS - COLLABORATIVE DECISION DEMO")
    print("=" * 60)
    print()

    # Create engine
    engine = AgentEngine()
    await engine.start()

    # Create diverse agents
    agents = [
        ResourceAllocationAgent("Leader-1", AgentRole.LEADER, "strategy", "balanced"),
        ResourceAllocationAgent("Worker-Cost", AgentRole.WORKER, "finance", "cost_focused"),
        ResourceAllocationAgent("Worker-Speed", AgentRole.WORKER, "operations", "speed_focused"),
        ResourceAllocationAgent("Worker-Quality", AgentRole.WORKER, "engineering", "quality_focused"),
        ResourceAllocationAgent("Observer-1", AgentRole.OBSERVER, "analytics", "balanced"),
    ]

    # Register all agents
    print("Registering agents...")
    for agent in agents:
        engine.register_agent(agent)
        print(f"  - {agent.name} ({agent.entity.role.value}, {agent.bias})")

    print()

    # Start all agents
    print("Starting agents...")
    await engine.start_all_agents()
    await asyncio.sleep(0.5)  # Let agents initialize

    print(f"System status: {engine.get_system_status()}")
    print()

    # === Demo 1: Collaborative Decision ===
    print("-" * 60)
    print("SCENARIO 1: Resource Allocation Decision")
    print("-" * 60)
    print()

    options = [
        {
            "name": "Cloud Scale-Up",
            "description": "Increase cloud resources by 50%",
            "success_probability": 0.9,
            "resource_cost": 0.8,  # High cost
            "time_efficiency": 0.9,  # Fast
        },
        {
            "name": "Optimize Existing",
            "description": "Optimize current infrastructure",
            "success_probability": 0.7,
            "resource_cost": 0.3,  # Low cost
            "time_efficiency": 0.4,  # Slow
        },
        {
            "name": "Hybrid Approach",
            "description": "Moderate scaling + optimization",
            "success_probability": 0.8,
            "resource_cost": 0.5,  # Medium cost
            "time_efficiency": 0.6,  # Medium speed
        },
    ]

    print("Options for voting:")
    for i, opt in enumerate(options):
        print(f"  {i+1}. {opt['name']}: {opt['description']}")
    print()

    print("Running collaborative decision (workers vote)...")
    passed, winning_idx, tally = await engine.run_collaborative_decision(
        description="How should we handle increased system load?",
        options=options,
        voter_role=AgentRole.WORKER,
        threshold=0.5,
    )

    print()
    print("Voting Results:")
    print(f"  Total votes: {tally['vote_count']}")
    print(f"  Yes weight: {tally['yes_weight']:.2f}")
    print(f"  No weight: {tally['no_weight']:.2f}")
    print(f"  Approval: {tally['yes_ratio']:.1%}")
    print(f"  Threshold: {tally['threshold']:.1%}")
    print(f"  Passed: {passed}")

    if passed and winning_idx is not None:
        print(f"  Selected: {options[winning_idx]['name']}")
    print()

    # === Demo 2: Task Assignment ===
    print("-" * 60)
    print("SCENARIO 2: Autonomous Task Execution")
    print("-" * 60)
    print()

    task = Task(
        name="Implement Cost Analysis",
        description="Analyze resource costs for the selected approach",
        priority=8,
        required_capabilities=["finance"],
    )

    print(f"Assigning task: {task.name}")
    print(f"Required capability: {task.required_capabilities}")

    success = await engine.assign_task(task)
    print(f"Assignment success: {success}")

    if success:
        await asyncio.sleep(0.5)  # Let task complete
    print()

    # === Demo 3: Another Collaborative Decision ===
    print("-" * 60)
    print("SCENARIO 3: All Agents Vote (Different Threshold)")
    print("-" * 60)
    print()

    deployment_options = [
        {
            "name": "Immediate Deploy",
            "success_probability": 0.6,
            "resource_cost": 0.2,
            "time_efficiency": 1.0,
        },
        {
            "name": "Staged Rollout",
            "success_probability": 0.85,
            "resource_cost": 0.4,
            "time_efficiency": 0.5,
        },
        {
            "name": "Full Testing First",
            "success_probability": 0.95,
            "resource_cost": 0.6,
            "time_efficiency": 0.3,
        },
    ]

    print("Deployment strategy vote (all agents, 60% threshold)...")
    passed, winning_idx, tally = await engine.run_collaborative_decision(
        description="How should we deploy the changes?",
        options=deployment_options,
        threshold=0.6,
    )

    print()
    print("Voting Results:")
    print(f"  Approval: {tally['yes_ratio']:.1%} (threshold: 60%)")
    print(f"  Passed: {passed}")
    if passed and winning_idx is not None:
        print(f"  Selected: {deployment_options[winning_idx]['name']}")
    print()

    # === System Summary ===
    print("-" * 60)
    print("SYSTEM SUMMARY")
    print("-" * 60)
    status = engine.get_system_status()
    print(f"Total agents: {status['total_agents']}")
    print(f"Decisions made: {status['decisions_made']}")
    print(f"Messages logged: {len(engine.message_bus.get_message_log())}")
    print()

    # Decision audit trail
    print("Decision Log:")
    for decision in engine.consensus.get_decision_log():
        print(f"  - {decision.rationale}")
        print(f"    Consensus: {decision.consensus_score:.1%}")
        print(f"    Votes: {decision.votes}")
    print()

    # Cleanup
    print("Shutting down...")
    await engine.stop()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(run_demo())
