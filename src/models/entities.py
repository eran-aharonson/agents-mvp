"""Core data models for the multi-agent system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4


class AgentRole(Enum):
    LEADER = "leader"
    WORKER = "worker"
    OBSERVER = "observer"


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Option:
    """Represents a decision option."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    estimated_utility: float = 0.0


@dataclass
class Agent:
    """Agent entity representing an autonomous agent in the system."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    role: AgentRole = AgentRole.WORKER
    status: AgentStatus = AgentStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    local_state: dict[str, Any] = field(default_factory=dict)
    expertise_score: float = 1.0  # Used for weighted voting

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "expertise_score": self.expertise_score,
        }


@dataclass
class Task:
    """Task entity representing work to be done."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    priority: int = 5  # 1-10
    constraints: dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    required_capabilities: list[str] = field(default_factory=list)
    assigned_agents: list[UUID] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "required_capabilities": self.required_capabilities,
            "assigned_agents": [str(a) for a in self.assigned_agents],
        }


@dataclass
class Decision:
    """Decision record for audit trail."""
    id: UUID = field(default_factory=uuid4)
    context_hash: str = ""
    task_id: Optional[UUID] = None
    options_considered: list[Option] = field(default_factory=list)
    selected_option: Optional[Option] = None
    rationale: str = ""
    consensus_score: float = 0.0
    votes: dict[str, str] = field(default_factory=dict)  # agent_id -> vote
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "task_id": str(self.task_id) if self.task_id else None,
            "selected_option": self.selected_option.name if self.selected_option else None,
            "rationale": self.rationale,
            "consensus_score": self.consensus_score,
            "votes": self.votes,
            "timestamp": self.timestamp.isoformat(),
        }
