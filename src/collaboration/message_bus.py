"""Message bus for inter-agent communication."""

import asyncio
from collections import defaultdict
from typing import Callable, Optional
from uuid import UUID

from .protocols import Message, MessageType


class MessageBus:
    """
    In-memory message bus for agent communication.
    Supports pub/sub patterns and direct messaging.
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._agent_queues: dict[UUID, asyncio.Queue] = {}
        self._message_log: list[Message] = []
        self._running = False

    async def start(self):
        """Start the message bus."""
        self._running = True

    async def stop(self):
        """Stop the message bus."""
        self._running = False

    def register_agent(self, agent_id: UUID) -> asyncio.Queue:
        """Register an agent and return its message queue."""
        if agent_id not in self._agent_queues:
            self._agent_queues[agent_id] = asyncio.Queue()
        return self._agent_queues[agent_id]

    def deregister_agent(self, agent_id: UUID):
        """Remove an agent from the bus."""
        if agent_id in self._agent_queues:
            del self._agent_queues[agent_id]

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic with a handler function."""
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable):
        """Unsubscribe from a topic."""
        if handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)

    async def publish(self, message: Message):
        """Publish a message to a topic or direct to an agent."""
        self._message_log.append(message)

        # Direct message to specific agent
        if message.recipient_id and message.recipient_id in self._agent_queues:
            await self._agent_queues[message.recipient_id].put(message)
            return

        # Broadcast to topic subscribers
        if message.topic:
            for handler in self._subscribers[message.topic]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    print(f"Error in message handler: {e}")

        # Broadcast to all agents (for system messages)
        if message.recipient_id is None and message.type in [
            MessageType.BROADCAST,
            MessageType.STATE_UPDATE,
            MessageType.EMERGENCY_HALT,
        ]:
            for agent_id, queue in self._agent_queues.items():
                if agent_id != message.sender_id:  # Don't send to self
                    await queue.put(message)

    async def send_direct(self, sender_id: UUID, recipient_id: UUID, message: Message):
        """Send a direct message to a specific agent."""
        message.sender_id = sender_id
        message.recipient_id = recipient_id
        await self.publish(message)

    async def broadcast(self, sender_id: UUID, message: Message):
        """Broadcast a message to all agents."""
        message.sender_id = sender_id
        message.recipient_id = None
        await self.publish(message)

    def get_message_log(self, limit: int = 100) -> list[Message]:
        """Get recent messages for auditing."""
        return self._message_log[-limit:]

    def get_agent_count(self) -> int:
        """Get number of registered agents."""
        return len(self._agent_queues)
