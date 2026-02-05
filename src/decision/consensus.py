"""Consensus and voting mechanisms for collaborative decision-making."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from ..collaboration.protocols import Proposal, Vote, VoteType
from ..models.entities import Decision, Option


@dataclass
class VotingSession:
    """Tracks an active voting session."""
    proposal: Proposal
    votes: dict[UUID, Vote] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    closed: bool = False
    result: Optional[str] = None  # "accepted" or "rejected"


class ConsensusManager:
    """
    Manages collaborative consensus through weighted voting.

    Flow:
    1. Proposal Phase: Leader broadcasts a plan
    2. Evaluation Phase: Workers simulate/evaluate locally
    3. Voting Phase: Agents cast weighted votes
    4. Execution Phase: If threshold met, execute
    """

    def __init__(self, default_threshold: float = 0.5, vote_timeout: float = 30.0):
        self.default_threshold = default_threshold
        self.vote_timeout = vote_timeout
        self._sessions: dict[UUID, VotingSession] = {}
        self._decision_log: list[Decision] = []

    def create_proposal(
        self,
        proposer_id: UUID,
        description: str,
        options: list[dict],
        task_id: UUID = None,
        threshold: float = None,
    ) -> Proposal:
        """Create a new proposal for voting."""
        proposal = Proposal(
            proposer_id=proposer_id,
            task_id=task_id,
            description=description,
            options=options,
            threshold=threshold or self.default_threshold,
        )
        self._sessions[proposal.id] = VotingSession(proposal=proposal)
        return proposal

    def cast_vote(
        self,
        proposal_id: UUID,
        voter_id: UUID,
        vote_type: VoteType,
        selected_option: int = 0,
        weight: float = 1.0,
        rationale: str = "",
    ) -> Optional[Vote]:
        """Cast a vote on a proposal."""
        session = self._sessions.get(proposal_id)
        if not session or session.closed:
            return None

        vote = Vote(
            proposal_id=proposal_id,
            voter_id=voter_id,
            vote=vote_type,
            selected_option=selected_option,
            weight=weight,
            rationale=rationale,
        )
        session.votes[voter_id] = vote
        return vote

    def get_vote_tally(self, proposal_id: UUID) -> dict:
        """Get current vote tally for a proposal."""
        session = self._sessions.get(proposal_id)
        if not session:
            return {}

        yes_weight = 0.0
        no_weight = 0.0
        abstain_weight = 0.0
        option_votes: dict[int, float] = {}

        for vote in session.votes.values():
            if vote.vote == VoteType.YES:
                yes_weight += vote.weight
                opt = vote.selected_option
                option_votes[opt] = option_votes.get(opt, 0) + vote.weight
            elif vote.vote == VoteType.NO:
                no_weight += vote.weight
            else:
                abstain_weight += vote.weight

        total_weight = yes_weight + no_weight + abstain_weight
        yes_ratio = yes_weight / total_weight if total_weight > 0 else 0

        return {
            "yes_weight": yes_weight,
            "no_weight": no_weight,
            "abstain_weight": abstain_weight,
            "total_weight": total_weight,
            "yes_ratio": yes_ratio,
            "option_votes": option_votes,
            "vote_count": len(session.votes),
            "threshold": session.proposal.threshold,
            "would_pass": yes_ratio >= session.proposal.threshold,
        }

    def close_voting(self, proposal_id: UUID) -> Optional[Decision]:
        """Close voting and record decision."""
        session = self._sessions.get(proposal_id)
        if not session or session.closed:
            return None

        session.closed = True
        tally = self.get_vote_tally(proposal_id)

        # Determine winning option
        selected_option = None
        if tally["would_pass"] and tally["option_votes"]:
            winning_idx = max(tally["option_votes"], key=tally["option_votes"].get)
            if winning_idx < len(session.proposal.options):
                opt_data = session.proposal.options[winning_idx]
                selected_option = Option(
                    name=opt_data.get("name", f"Option {winning_idx}"),
                    description=opt_data.get("description", ""),
                )

        # Create decision record
        decision = Decision(
            task_id=session.proposal.task_id,
            context_hash=str(hash(session.proposal.description)),
            options_considered=[
                Option(name=o.get("name", f"Option {i}"))
                for i, o in enumerate(session.proposal.options)
            ],
            selected_option=selected_option,
            rationale=f"Consensus reached with {tally['yes_ratio']:.1%} approval"
            if tally["would_pass"]
            else f"Consensus not reached ({tally['yes_ratio']:.1%} < {tally['threshold']:.1%})",
            consensus_score=tally["yes_ratio"],
            votes={str(k): v.vote.value for k, v in session.votes.items()},
        )

        session.result = "accepted" if tally["would_pass"] else "rejected"
        self._decision_log.append(decision)

        return decision

    def get_session(self, proposal_id: UUID) -> Optional[VotingSession]:
        """Get a voting session by proposal ID."""
        return self._sessions.get(proposal_id)

    def get_decision_log(self) -> list[Decision]:
        """Get all recorded decisions."""
        return self._decision_log.copy()

    async def run_voting_round(
        self,
        proposal: Proposal,
        voters: list[tuple[UUID, float]],  # (agent_id, weight)
        vote_callback,  # async fn(agent_id, proposal) -> (VoteType, int, str)
    ) -> Decision:
        """
        Run a complete voting round.

        Args:
            proposal: The proposal to vote on
            voters: List of (agent_id, weight) tuples
            vote_callback: Async function to get vote from each agent

        Returns:
            Decision record
        """
        # Collect votes with timeout
        async def collect_vote(agent_id: UUID, weight: float):
            try:
                vote_type, selected_opt, rationale = await asyncio.wait_for(
                    vote_callback(agent_id, proposal),
                    timeout=self.vote_timeout,
                )
                self.cast_vote(
                    proposal.id, agent_id, vote_type, selected_opt, weight, rationale
                )
            except asyncio.TimeoutError:
                self.cast_vote(
                    proposal.id, agent_id, VoteType.ABSTAIN, 0, weight, "timeout"
                )

        # Collect all votes concurrently
        await asyncio.gather(*[
            collect_vote(agent_id, weight)
            for agent_id, weight in voters
        ])

        return self.close_voting(proposal.id)
