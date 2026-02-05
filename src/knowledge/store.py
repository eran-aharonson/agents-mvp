"""Knowledge store for shared state and decision logs."""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


class KnowledgeStore:
    """
    Distributed knowledge store for agents.
    Stores shared world state, ontologies, and decision logs.
    """

    def __init__(self):
        self._world_state: dict[str, Any] = {}
        self._ontologies: dict[str, dict] = {}
        self._decision_log: list[dict] = []
        self._agent_states: dict[UUID, dict] = {}
        self._version = 0

    def update_world_state(self, key: str, value: Any, source: UUID = None):
        """Update shared world state."""
        self._world_state[key] = {
            "value": value,
            "updated_at": datetime.utcnow().isoformat(),
            "source": str(source) if source else None,
        }
        self._version += 1

    def get_world_state(self, key: str, default: Any = None) -> Any:
        """Get value from world state."""
        entry = self._world_state.get(key)
        return entry["value"] if entry else default

    def get_full_world_state(self) -> dict:
        """Get complete world state."""
        return {k: v["value"] for k, v in self._world_state.items()}

    def register_ontology(self, name: str, ontology: dict):
        """Register an ontology (concept definitions)."""
        self._ontologies[name] = {
            "data": ontology,
            "registered_at": datetime.utcnow().isoformat(),
        }

    def get_ontology(self, name: str) -> Optional[dict]:
        """Get an ontology by name."""
        entry = self._ontologies.get(name)
        return entry["data"] if entry else None

    def log_decision(self, decision: dict):
        """Log a decision for audit trail."""
        self._decision_log.append({
            **decision,
            "logged_at": datetime.utcnow().isoformat(),
        })

    def get_decision_log(
        self,
        limit: int = 100,
        task_id: UUID = None,
    ) -> list[dict]:
        """Get decision log, optionally filtered by task."""
        log = self._decision_log

        if task_id:
            log = [d for d in log if d.get("task_id") == str(task_id)]

        return log[-limit:]

    def update_agent_state(self, agent_id: UUID, state: dict):
        """Store an agent's state snapshot."""
        self._agent_states[agent_id] = {
            "state": state,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get_agent_state(self, agent_id: UUID) -> Optional[dict]:
        """Get an agent's stored state."""
        entry = self._agent_states.get(agent_id)
        return entry["state"] if entry else None

    def get_all_agent_states(self) -> dict[UUID, dict]:
        """Get all agent states."""
        return {k: v["state"] for k, v in self._agent_states.items()}

    def query(self, pattern: str) -> list[tuple[str, Any]]:
        """Query world state by key pattern (simple prefix match)."""
        results = []
        for key, entry in self._world_state.items():
            if key.startswith(pattern):
                results.append((key, entry["value"]))
        return results

    def export_snapshot(self) -> dict:
        """Export complete knowledge store snapshot."""
        return {
            "version": self._version,
            "timestamp": datetime.utcnow().isoformat(),
            "world_state": self._world_state,
            "ontologies": self._ontologies,
            "decision_log": self._decision_log,
            "agent_states": {str(k): v for k, v in self._agent_states.items()},
        }

    def import_snapshot(self, snapshot: dict):
        """Import knowledge store from snapshot."""
        self._world_state = snapshot.get("world_state", {})
        self._ontologies = snapshot.get("ontologies", {})
        self._decision_log = snapshot.get("decision_log", [])
        self._agent_states = {
            UUID(k): v for k, v in snapshot.get("agent_states", {}).items()
        }
        self._version = snapshot.get("version", 0)

    def save_to_file(self, filepath: str):
        """Save knowledge store to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.export_snapshot(), f, indent=2)

    def load_from_file(self, filepath: str):
        """Load knowledge store from JSON file."""
        with open(filepath, "r") as f:
            self.import_snapshot(json.load(f))
