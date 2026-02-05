"""Base agent class for autonomous agents."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID

from ..models.entities import Agent, AgentRole, AgentStatus, Task
from ..collaboration.protocols import Message, MessageType, Proposal, VoteType
from ..collaboration.message_bus import MessageBus
from ..decision.framework import DecisionFramework
from ..decision.utility import UtilityWeights


class BaseAgent(ABC):
    """
    Base class for autonomous agents.
    Implements perception, reasoning, and action capabilities.
    """

    def __init__(
        self,
        name: str,
        role: AgentRole = AgentRole.WORKER,
        capabilities: list[str] = None,
        utility_weights: UtilityWeights = None,
    ):
        self.entity = Agent(
            name=name,
            role=role,
            capabilities=capabilities or [],
        )
        self.id = self.entity.id
        self.name = name

        self._message_bus: Optional[MessageBus] = None
        self._message_queue: Optional[asyncio.Queue] = None
        self._decision_framework: Optional[DecisionFramework] = None
        self._utility_weights = utility_weights or UtilityWeights()

        self._running = False
        self._current_task: Optional[Task] = None
        self._knowledge: dict[str, Any] = {}

    @property
    def status(self) -> AgentStatus:
        return self.entity.status

    @status.setter
    def status(self, value: AgentStatus):
        self.entity.status = value

    def connect(
        self,
        message_bus: MessageBus,
        decision_framework: DecisionFramework,
    ):
        """Connect agent to the system infrastructure."""
        self._message_bus = message_bus
        self._decision_framework = decision_framework
        self._message_queue = message_bus.register_agent(self.id)
        decision_framework.register_agent_utility(self.id, self._utility_weights)

    async def start(self):
        """Start the agent's execution loop."""
        if not self._message_bus:
            raise RuntimeError("Agent not connected to message bus")

        self._running = True
        self.status = AgentStatus.IDLE

        # Announce presence
        await self._message_bus.broadcast(
            self.id,
            Message(
                type=MessageType.AGENT_REGISTER,
                payload=self.entity.to_dict(),
            ),
        )

        # Start main loop
        await self._run_loop()

    async def stop(self):
        """Stop the agent."""
        self._running = False
        self.status = AgentStatus.OFFLINE

        if self._message_bus:
            await self._message_bus.broadcast(
                self.id,
                Message(
                    type=MessageType.AGENT_DEREGISTER,
                    payload={"agent_id": str(self.id)},
                ),
            )

    async def _run_loop(self):
        """Main execution loop."""
        while self._running:
            try:
                # Check for messages (non-blocking with timeout)
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=0.1,
                    )
                    await self._handle_message(message)
                except asyncio.TimeoutError:
                    pass

                # Perform autonomous actions if idle
                if self.status == AgentStatus.IDLE:
                    await self._autonomous_cycle()

                await asyncio.sleep(0.01)  # Prevent busy loop

            except Exception as e:
                print(f"[{self.name}] Error in loop: {e}")

    async def _handle_message(self, message: Message):
        """Handle incoming messages."""
        if message.type == MessageType.EMERGENCY_HALT:
            await self.stop()
            return

        if message.type == MessageType.TASK_ASSIGN:
            await self._handle_task_assignment(message)
        elif message.type == MessageType.PROPOSAL:
            await self._handle_proposal(message)
        elif message.type == MessageType.STATE_UPDATE:
            await self._handle_state_update(message)
        else:
            await self.on_message(message)

    async def _handle_task_assignment(self, message: Message):
        """Handle task assignment."""
        task_data = message.payload
        task = Task(
            name=task_data.get("name", ""),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", 5),
            required_capabilities=task_data.get("required_capabilities", []),
        )

        # Check if we have required capabilities
        if task.required_capabilities:
            has_caps = all(
                cap in self.entity.capabilities
                for cap in task.required_capabilities
            )
            if not has_caps:
                await self._send_message(
                    message.sender_id,
                    MessageType.REJECT,
                    {"reason": "Missing required capabilities"},
                )
                return

        self._current_task = task
        self.status = AgentStatus.BUSY
        await self.execute_task(task)

    async def _handle_proposal(self, message: Message):
        """Handle voting proposal."""
        proposal_data = message.payload
        vote, option, rationale = await self.evaluate_proposal(proposal_data)

        await self._send_message(
            message.sender_id,
            MessageType.VOTE,
            {
                "proposal_id": proposal_data.get("id"),
                "vote": vote.value,
                "selected_option": option,
                "rationale": rationale,
                "weight": self.entity.expertise_score,
            },
        )

    async def _handle_state_update(self, message: Message):
        """Handle global state update."""
        self._knowledge.update(message.payload.get("state", {}))

    async def _send_message(
        self,
        recipient_id: UUID,
        msg_type: MessageType,
        payload: dict,
    ):
        """Send a message to another agent."""
        if self._message_bus:
            await self._message_bus.send_direct(
                self.id,
                recipient_id,
                Message(type=msg_type, payload=payload),
            )

    async def broadcast(self, msg_type: MessageType, payload: dict):
        """Broadcast a message to all agents."""
        if self._message_bus:
            await self._message_bus.broadcast(
                self.id,
                Message(type=msg_type, payload=payload),
            )

    def update_knowledge(self, key: str, value: Any):
        """Update local knowledge base."""
        self._knowledge[key] = value

    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """Get value from local knowledge base."""
        return self._knowledge.get(key, default)

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def _autonomous_cycle(self):
        """
        Perform autonomous actions when idle.
        Called repeatedly in the main loop.
        """
        pass

    @abstractmethod
    async def execute_task(self, task: Task):
        """Execute an assigned task."""
        pass

    @abstractmethod
    async def evaluate_proposal(
        self,
        proposal: dict,
    ) -> tuple[VoteType, int, str]:
        """
        Evaluate a proposal and return vote.

        Returns:
            Tuple of (vote_type, selected_option_index, rationale)
        """
        pass

    @abstractmethod
    async def on_message(self, message: Message):
        """Handle custom message types."""
        pass
