"""Agent engine for managing agent lifecycle and orchestration."""

import asyncio
from typing import Optional
from uuid import UUID

from .base import BaseAgent
from ..models.entities import AgentRole, AgentStatus, Task
from ..collaboration.message_bus import MessageBus
from ..collaboration.protocols import Message, MessageType, Proposal, VoteType
from ..decision.framework import DecisionFramework
from ..decision.consensus import ConsensusManager


class AgentEngine:
    """
    Runtime engine for managing agents.
    Handles lifecycle, task distribution, and orchestration.
    """

    def __init__(self):
        self.message_bus = MessageBus()
        self.consensus = ConsensusManager()
        self.decision_framework = DecisionFramework(self.consensus)

        self._agents: dict[UUID, BaseAgent] = {}
        self._agent_tasks: dict[UUID, asyncio.Task] = {}
        self._running = False
        self._kill_switch = False

    async def start(self):
        """Start the engine."""
        await self.message_bus.start()
        self._running = True
        self._kill_switch = False

    async def stop(self):
        """Stop the engine and all agents."""
        self._running = False

        # Stop all agents
        for agent in self._agents.values():
            await agent.stop()

        # Cancel agent tasks
        for task in self._agent_tasks.values():
            task.cancel()

        await self.message_bus.stop()

    async def emergency_halt(self):
        """Emergency kill switch - immediately stop all agents."""
        self._kill_switch = True
        await self.message_bus.broadcast(
            None,
            Message(type=MessageType.EMERGENCY_HALT, payload={}),
        )
        await self.stop()

    def register_agent(self, agent: BaseAgent) -> UUID:
        """Register an agent with the engine."""
        agent.connect(self.message_bus, self.decision_framework)
        self._agents[agent.id] = agent
        return agent.id

    def deregister_agent(self, agent_id: UUID):
        """Remove an agent from the engine."""
        if agent_id in self._agents:
            del self._agents[agent_id]
        if agent_id in self._agent_tasks:
            self._agent_tasks[agent_id].cancel()
            del self._agent_tasks[agent_id]
        self.message_bus.deregister_agent(agent_id)

    async def start_agent(self, agent_id: UUID):
        """Start a specific agent."""
        agent = self._agents.get(agent_id)
        if agent:
            task = asyncio.create_task(agent.start())
            self._agent_tasks[agent_id] = task

    async def start_all_agents(self):
        """Start all registered agents."""
        for agent_id in self._agents:
            await self.start_agent(agent_id)

    def get_agent(self, agent_id: UUID) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_agents_by_role(self, role: AgentRole) -> list[BaseAgent]:
        """Get all agents with a specific role."""
        return [a for a in self._agents.values() if a.entity.role == role]

    def get_idle_agents(self) -> list[BaseAgent]:
        """Get all idle agents."""
        return [a for a in self._agents.values() if a.status == AgentStatus.IDLE]

    def get_agents_with_capability(self, capability: str) -> list[BaseAgent]:
        """Get agents that have a specific capability."""
        return [
            a for a in self._agents.values()
            if capability in a.entity.capabilities
        ]

    async def assign_task(
        self,
        task: Task,
        agent_id: UUID = None,
    ) -> bool:
        """
        Assign a task to an agent.
        If agent_id is None, automatically selects best agent.
        """
        if agent_id:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
        else:
            # Find best agent for task
            candidates = self.get_idle_agents()

            if task.required_capabilities:
                candidates = [
                    a for a in candidates
                    if all(c in a.entity.capabilities for c in task.required_capabilities)
                ]

            if not candidates:
                return False

            # Select agent with highest expertise
            agent = max(candidates, key=lambda a: a.entity.expertise_score)

        # Send task assignment
        await self.message_bus.send_direct(
            None,  # System sender
            agent.id,
            Message(
                type=MessageType.TASK_ASSIGN,
                payload=task.to_dict(),
            ),
        )

        task.assigned_agents.append(agent.id)
        return True

    async def run_collaborative_decision(
        self,
        description: str,
        options: list[dict],
        voter_role: AgentRole = None,
        required_capability: str = None,
        threshold: float = 0.5,
    ) -> tuple[bool, Optional[int], dict]:
        """
        Run a collaborative decision-making process.

        Args:
            description: What we're deciding
            options: List of option dicts
            voter_role: Only include agents with this role
            required_capability: Only include agents with this capability
            threshold: Vote threshold for approval

        Returns:
            Tuple of (passed, winning_option_index, tally)
        """
        # Select voters
        voters = list(self._agents.values())

        if voter_role:
            voters = [a for a in voters if a.entity.role == voter_role]

        if required_capability:
            voters = [a for a in voters if required_capability in a.entity.capabilities]

        if not voters:
            return False, None, {"error": "No eligible voters"}

        # Create proposal
        leader = self.get_agents_by_role(AgentRole.LEADER)
        proposer_id = leader[0].id if leader else voters[0].id

        proposal = self.consensus.create_proposal(
            proposer_id=proposer_id,
            description=description,
            options=options,
            threshold=threshold,
        )

        # Broadcast proposal
        await self.message_bus.broadcast(
            proposer_id,
            Message(
                type=MessageType.PROPOSAL,
                topic=f"proposal.{proposal.id}",
                payload=proposal.to_dict(),
            ),
        )

        # Collect votes (with callback)
        async def vote_callback(agent_id: UUID, prop: Proposal):
            agent = self._agents.get(agent_id)
            if agent:
                return await agent.evaluate_proposal(prop.to_dict())
            return VoteType.ABSTAIN, 0, "Agent not found"

        decision = await self.consensus.run_voting_round(
            proposal,
            [(a.id, a.entity.expertise_score) for a in voters],
            vote_callback,
        )

        tally = self.consensus.get_vote_tally(proposal.id)
        passed = tally["would_pass"]
        winning_option = None

        if passed and tally["option_votes"]:
            winning_option = max(tally["option_votes"], key=tally["option_votes"].get)

        return passed, winning_option, tally

    def get_system_status(self) -> dict:
        """Get overall system status."""
        return {
            "running": self._running,
            "kill_switch": self._kill_switch,
            "total_agents": len(self._agents),
            "agents_by_role": {
                role.value: len(self.get_agents_by_role(role))
                for role in AgentRole
            },
            "agents_by_status": {
                status.value: len([
                    a for a in self._agents.values()
                    if a.status == status
                ])
                for status in AgentStatus
            },
            "message_bus_agents": self.message_bus.get_agent_count(),
            "decisions_made": len(self.consensus.get_decision_log()),
        }
