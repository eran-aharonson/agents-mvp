"""ACL (Agent Communication Language) message protocols."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class MessageType(Enum):
    # Negotiation messages
    PROPOSAL = "proposal"
    COUNTER_PROPOSAL = "counter_proposal"
    ACCEPT = "accept"
    REJECT = "reject"
    VOTE = "vote"

    # System messages
    BROADCAST = "broadcast"
    STATE_UPDATE = "state_update"
    EMERGENCY_HALT = "emergency_halt"

    # Task messages
    TASK_ASSIGN = "task_assign"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"

    # Agent lifecycle
    AGENT_REGISTER = "agent_register"
    AGENT_DEREGISTER = "agent_deregister"
    HEARTBEAT = "heartbeat"


class VoteType(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class Message:
    """Base message for inter-agent communication."""
    id: UUID = field(default_factory=uuid4)
    type: MessageType = MessageType.BROADCAST
    sender_id: Optional[UUID] = None
    recipient_id: Optional[UUID] = None  # None = broadcast
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[UUID] = None  # For request-response patterns

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "type": self.type.value,
            "sender_id": str(self.sender_id) if self.sender_id else None,
            "recipient_id": str(self.recipient_id) if self.recipient_id else None,
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
        }


@dataclass
class Proposal:
    """A proposal for collaborative decision-making."""
    id: UUID = field(default_factory=uuid4)
    proposer_id: UUID = field(default_factory=uuid4)
    task_id: Optional[UUID] = None
    description: str = ""
    options: list[dict] = field(default_factory=list)
    recommended_option: int = 0  # Index of recommended option
    deadline: Optional[datetime] = None
    min_votes_required: int = 1
    threshold: float = 0.5  # Percentage of weighted yes votes needed

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "proposer_id": str(self.proposer_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "description": self.description,
            "options": self.options,
            "recommended_option": self.recommended_option,
            "threshold": self.threshold,
        }


@dataclass
class Vote:
    """A vote cast by an agent on a proposal."""
    id: UUID = field(default_factory=uuid4)
    proposal_id: UUID = field(default_factory=uuid4)
    voter_id: UUID = field(default_factory=uuid4)
    vote: VoteType = VoteType.ABSTAIN
    selected_option: int = 0
    weight: float = 1.0
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "proposal_id": str(self.proposal_id),
            "voter_id": str(self.voter_id),
            "vote": self.vote.value,
            "selected_option": self.selected_option,
            "weight": self.weight,
            "rationale": self.rationale,
        }
