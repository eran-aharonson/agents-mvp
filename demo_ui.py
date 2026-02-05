#!/usr/bin/env python3
"""
Visual Demo: Autonomous AI Agents for Collaborative Decision-Making

A tkinter UI showing agents collaborating in real-time.
"""

import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from uuid import UUID
import random

from src.agent.base import BaseAgent
from src.agent.engine import AgentEngine
from src.models.entities import AgentRole, AgentStatus, Task
from src.collaboration.protocols import Message, MessageType, VoteType
from src.decision.utility import UtilityWeights


# Colors
COLORS = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "accent": "#0f3460",
    "highlight": "#e94560",
    "success": "#00d26a",
    "warning": "#ffc107",
    "text": "#ffffff",
    "text_dim": "#8892b0",
    "leader": "#ffd700",
    "worker": "#00bcd4",
    "observer": "#9c27b0",
}

ROLE_COLORS = {
    AgentRole.LEADER: COLORS["leader"],
    AgentRole.WORKER: COLORS["worker"],
    AgentRole.OBSERVER: COLORS["observer"],
}

STATUS_COLORS = {
    AgentStatus.IDLE: COLORS["success"],
    AgentStatus.BUSY: COLORS["warning"],
    AgentStatus.OFFLINE: COLORS["text_dim"],
}


class VisualAgent(BaseAgent):
    """Agent with UI callback support."""

    def __init__(self, name: str, role: AgentRole, specialization: str, bias: str, ui_callback=None):
        weights = {
            "cost_focused": UtilityWeights(0.2, 0.6, 0.2),
            "speed_focused": UtilityWeights(0.2, 0.2, 0.6),
            "quality_focused": UtilityWeights(0.6, 0.2, 0.2),
            "balanced": UtilityWeights(0.34, 0.33, 0.33),
        }

        super().__init__(
            name=name,
            role=role,
            capabilities=[specialization, "general"],
            utility_weights=weights.get(bias, UtilityWeights()),
        )

        self.specialization = specialization
        self.bias = bias
        self.entity.expertise_score = random.uniform(0.7, 1.0)
        self.ui_callback = ui_callback
        self._idle_cycles = 0

    def notify_ui(self, event_type: str, data: dict):
        if self.ui_callback:
            self.ui_callback(event_type, {"agent": self.name, **data})

    async def _autonomous_cycle(self):
        self._idle_cycles += 1

    async def execute_task(self, task: Task):
        self.notify_ui("task_start", {"task": task.name})
        await asyncio.sleep(random.uniform(0.5, 1.5))
        task.status = "completed"
        task.result = {"success": True}
        self.status = AgentStatus.IDLE
        self._current_task = None
        self.notify_ui("task_complete", {"task": task.name})

    async def evaluate_proposal(self, proposal: dict) -> tuple[VoteType, int, str]:
        options = proposal.get("options", [])
        if not options:
            return VoteType.ABSTAIN, 0, "No options"

        await asyncio.sleep(random.uniform(0.2, 0.6))  # Thinking time

        if self._decision_framework:
            ranked = self._decision_framework.evaluate_options(self.id, options)
            best_idx, best_score, _ = ranked[0]

            if best_score > 0.5:
                vote = VoteType.YES
                rationale = f"Supports (utility={best_score:.2f})"
            else:
                vote = VoteType.NO
                rationale = f"Opposes (utility={best_score:.2f})"

            self.notify_ui("vote", {
                "vote": vote.value,
                "option": best_idx,
                "score": best_score,
            })
            return vote, best_idx, rationale

        return VoteType.ABSTAIN, 0, "No framework"

    async def on_message(self, message: Message):
        pass


class AgentDemoUI:
    """Visual UI for the multi-agent demo."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Autonomous AI Agents - Collaborative Decision Making")
        self.root.configure(bg=COLORS["bg"])
        self.root.geometry("1200x800")

        self.engine = None
        self.agents = []
        self.agent_cards = {}
        self.log_entries = []

        self._setup_ui()
        self._async_loop = None
        self._thread = None

    def _setup_ui(self):
        # Main container
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = tk.Label(
            main,
            text="AUTONOMOUS AI AGENTS",
            font=("Helvetica", 24, "bold"),
            fg=COLORS["highlight"],
            bg=COLORS["bg"],
        )
        title.pack(pady=(0, 5))

        subtitle = tk.Label(
            main,
            text="Collaborative Decision-Making System",
            font=("Helvetica", 12),
            fg=COLORS["text_dim"],
            bg=COLORS["bg"],
        )
        subtitle.pack(pady=(0, 20))

        # Content area
        content = tk.Frame(main, bg=COLORS["bg"])
        content.pack(fill="both", expand=True)

        # Left: Agents panel
        left = tk.Frame(content, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        agents_label = tk.Label(
            left,
            text="AGENTS",
            font=("Helvetica", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        agents_label.pack(anchor="w", pady=(0, 10))

        self.agents_frame = tk.Frame(left, bg=COLORS["bg"])
        self.agents_frame.pack(fill="both", expand=True)

        # Right: Activity log
        right = tk.Frame(content, bg=COLORS["bg"], width=400)
        right.pack(side="right", fill="both", padx=(10, 0))
        right.pack_propagate(False)

        log_label = tk.Label(
            right,
            text="ACTIVITY LOG",
            font=("Helvetica", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        log_label.pack(anchor="w", pady=(0, 10))

        self.log_frame = tk.Frame(right, bg=COLORS["card"])
        self.log_frame.pack(fill="both", expand=True)

        # Log canvas with scrolling
        self.log_canvas = tk.Canvas(self.log_frame, bg=COLORS["card"], highlightthickness=0)
        self.log_inner = tk.Frame(self.log_canvas, bg=COLORS["card"])
        self.log_canvas.pack(fill="both", expand=True)
        self.log_canvas.create_window((0, 0), window=self.log_inner, anchor="nw")

        # Bottom: Controls and decision display
        bottom = tk.Frame(main, bg=COLORS["bg"])
        bottom.pack(fill="x", pady=(20, 0))

        # Decision result display
        self.decision_frame = tk.Frame(bottom, bg=COLORS["card"], padx=20, pady=15)
        self.decision_frame.pack(fill="x", pady=(0, 15))

        self.decision_label = tk.Label(
            self.decision_frame,
            text="Click 'Run Decision' to start a collaborative vote",
            font=("Helvetica", 12),
            fg=COLORS["text_dim"],
            bg=COLORS["card"],
        )
        self.decision_label.pack()

        # Buttons
        btn_frame = tk.Frame(bottom, bg=COLORS["bg"])
        btn_frame.pack()

        self.start_btn = tk.Label(
            btn_frame,
            text="  Start System  ",
            font=("Helvetica", 12, "bold"),
            fg=COLORS["text"],
            bg=COLORS["success"],
            padx=20,
            pady=10,
            cursor="hand2",
        )
        self.start_btn.pack(side="left", padx=5)
        self.start_btn.bind("<Button-1>", lambda e: self.start_system())

        self.decision_btn = tk.Label(
            btn_frame,
            text="  Run Decision  ",
            font=("Helvetica", 12, "bold"),
            fg=COLORS["text"],
            bg=COLORS["accent"],
            padx=20,
            pady=10,
            cursor="hand2",
        )
        self.decision_btn.pack(side="left", padx=5)
        self.decision_btn.bind("<Button-1>", lambda e: self.run_decision())

        self.task_btn = tk.Label(
            btn_frame,
            text="  Assign Task  ",
            font=("Helvetica", 12, "bold"),
            fg=COLORS["text"],
            bg=COLORS["accent"],
            padx=20,
            pady=10,
            cursor="hand2",
        )
        self.task_btn.pack(side="left", padx=5)
        self.task_btn.bind("<Button-1>", lambda e: self.assign_task())

        self.halt_btn = tk.Label(
            btn_frame,
            text="  Emergency Halt  ",
            font=("Helvetica", 12, "bold"),
            fg=COLORS["text"],
            bg=COLORS["highlight"],
            padx=20,
            pady=10,
            cursor="hand2",
        )
        self.halt_btn.pack(side="left", padx=5)
        self.halt_btn.bind("<Button-1>", lambda e: self.emergency_halt())

    def create_agent_card(self, agent: VisualAgent) -> tk.Frame:
        """Create a visual card for an agent."""
        card = tk.Frame(self.agents_frame, bg=COLORS["card"], padx=15, pady=10)
        card.pack(fill="x", pady=5)

        # Header with name and role
        header = tk.Frame(card, bg=COLORS["card"])
        header.pack(fill="x")

        role_color = ROLE_COLORS.get(agent.entity.role, COLORS["text"])
        role_badge = tk.Label(
            header,
            text=f" {agent.entity.role.value.upper()} ",
            font=("Helvetica", 9, "bold"),
            fg=COLORS["bg"],
            bg=role_color,
        )
        role_badge.pack(side="left")

        name_label = tk.Label(
            header,
            text=f"  {agent.name}",
            font=("Helvetica", 12, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        name_label.pack(side="left")

        status_label = tk.Label(
            header,
            text="IDLE",
            font=("Helvetica", 10),
            fg=STATUS_COLORS[AgentStatus.IDLE],
            bg=COLORS["card"],
        )
        status_label.pack(side="right")

        # Details
        details = tk.Frame(card, bg=COLORS["card"])
        details.pack(fill="x", pady=(5, 0))

        info_text = f"Bias: {agent.bias} | Expertise: {agent.entity.expertise_score:.2f}"
        info_label = tk.Label(
            details,
            text=info_text,
            font=("Helvetica", 10),
            fg=COLORS["text_dim"],
            bg=COLORS["card"],
        )
        info_label.pack(side="left")

        # Activity indicator
        activity_label = tk.Label(
            details,
            text="",
            font=("Helvetica", 10),
            fg=COLORS["warning"],
            bg=COLORS["card"],
        )
        activity_label.pack(side="right")

        return {
            "frame": card,
            "status": status_label,
            "activity": activity_label,
        }

    def add_log(self, message: str, color: str = None):
        """Add entry to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        entry = tk.Label(
            self.log_inner,
            text=f"[{timestamp}] {message}",
            font=("Courier", 10),
            fg=color or COLORS["text"],
            bg=COLORS["card"],
            anchor="w",
            justify="left",
        )
        entry.pack(fill="x", padx=10, pady=2, anchor="w")

        self.log_entries.append(entry)

        # Keep only last 50 entries
        if len(self.log_entries) > 50:
            old = self.log_entries.pop(0)
            old.destroy()

        # Scroll to bottom
        self.log_canvas.update_idletasks()
        self.log_canvas.config(scrollregion=self.log_canvas.bbox("all"))
        self.log_canvas.yview_moveto(1.0)

    def ui_callback(self, event_type: str, data: dict):
        """Handle UI updates from agents."""
        agent_name = data.get("agent", "System")

        if event_type == "vote":
            vote = data.get("vote", "?")
            score = data.get("score", 0)
            color = COLORS["success"] if vote == "yes" else COLORS["highlight"]
            self.root.after(0, lambda: self.add_log(
                f"{agent_name} votes {vote.upper()} (score: {score:.2f})", color
            ))

            # Update agent activity
            if agent_name in self.agent_cards:
                self.root.after(0, lambda: self.agent_cards[agent_name]["activity"].config(
                    text=f"Voted: {vote.upper()}"
                ))

        elif event_type == "task_start":
            task = data.get("task", "?")
            self.root.after(0, lambda: self.add_log(
                f"{agent_name} started: {task}", COLORS["warning"]
            ))
            if agent_name in self.agent_cards:
                self.root.after(0, lambda: self.agent_cards[agent_name]["status"].config(
                    text="BUSY", fg=STATUS_COLORS[AgentStatus.BUSY]
                ))
                self.root.after(0, lambda: self.agent_cards[agent_name]["activity"].config(
                    text=f"Working..."
                ))

        elif event_type == "task_complete":
            task = data.get("task", "?")
            self.root.after(0, lambda: self.add_log(
                f"{agent_name} completed: {task}", COLORS["success"]
            ))
            if agent_name in self.agent_cards:
                self.root.after(0, lambda: self.agent_cards[agent_name]["status"].config(
                    text="IDLE", fg=STATUS_COLORS[AgentStatus.IDLE]
                ))
                self.root.after(0, lambda: self.agent_cards[agent_name]["activity"].config(
                    text=""
                ))

    def start_system(self):
        """Initialize and start the agent system."""
        if self.engine:
            return

        self.add_log("Initializing system...", COLORS["warning"])

        # Create agents
        self.agents = [
            VisualAgent("Alpha", AgentRole.LEADER, "strategy", "balanced", self.ui_callback),
            VisualAgent("Beta", AgentRole.WORKER, "finance", "cost_focused", self.ui_callback),
            VisualAgent("Gamma", AgentRole.WORKER, "operations", "speed_focused", self.ui_callback),
            VisualAgent("Delta", AgentRole.WORKER, "engineering", "quality_focused", self.ui_callback),
            VisualAgent("Epsilon", AgentRole.OBSERVER, "analytics", "balanced", self.ui_callback),
        ]

        # Create agent cards
        for agent in self.agents:
            self.agent_cards[agent.name] = self.create_agent_card(agent)

        # Start async loop in background thread
        def run_async():
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
            self._async_loop.run_until_complete(self._start_engine())

        self._thread = threading.Thread(target=run_async, daemon=True)
        self._thread.start()

        self.start_btn.config(bg=COLORS["text_dim"])
        self.add_log("System started!", COLORS["success"])

    async def _start_engine(self):
        """Start the engine and agents."""
        self.engine = AgentEngine()
        await self.engine.start()

        for agent in self.agents:
            self.engine.register_agent(agent)
            self.root.after(0, lambda a=agent: self.add_log(
                f"Registered: {a.name} ({a.entity.role.value})"
            ))

        await self.engine.start_all_agents()

        # Keep running
        while self.engine._running:
            await asyncio.sleep(0.1)

    def run_decision(self):
        """Trigger a collaborative decision."""
        if not self.engine:
            self.add_log("Start system first!", COLORS["highlight"])
            return

        self.add_log("Starting collaborative decision...", COLORS["warning"])
        self.decision_label.config(text="Voting in progress...", fg=COLORS["warning"])

        # Clear agent activities
        for card in self.agent_cards.values():
            card["activity"].config(text="Thinking...")

        options = [
            {
                "name": "Scale Up",
                "description": "Increase resources",
                "success_probability": 0.9,
                "resource_cost": 0.8,
                "time_efficiency": 0.9,
            },
            {
                "name": "Optimize",
                "description": "Improve efficiency",
                "success_probability": 0.7,
                "resource_cost": 0.3,
                "time_efficiency": 0.4,
            },
            {
                "name": "Hybrid",
                "description": "Balanced approach",
                "success_probability": 0.8,
                "resource_cost": 0.5,
                "time_efficiency": 0.6,
            },
        ]

        def run():
            future = asyncio.run_coroutine_threadsafe(
                self.engine.run_collaborative_decision(
                    "Resource allocation strategy",
                    options,
                    threshold=0.5,
                ),
                self._async_loop,
            )
            passed, winning_idx, tally = future.result(timeout=30)

            # Update UI
            self.root.after(0, lambda: self._show_decision_result(passed, winning_idx, options, tally))

        threading.Thread(target=run, daemon=True).start()

    def _show_decision_result(self, passed, winning_idx, options, tally):
        """Display decision result."""
        # Clear activities
        for card in self.agent_cards.values():
            card["activity"].config(text="")

        if passed and winning_idx is not None:
            result = f"APPROVED: {options[winning_idx]['name']}"
            color = COLORS["success"]
        else:
            result = "REJECTED"
            color = COLORS["highlight"]

        approval = tally.get('yes_ratio', 0) * 100
        self.decision_label.config(
            text=f"{result}  |  Approval: {approval:.0f}%  |  Votes: {tally.get('vote_count', 0)}",
            fg=color,
        )
        self.add_log(f"Decision: {result} ({approval:.0f}% approval)", color)

    def assign_task(self):
        """Assign a task to an agent."""
        if not self.engine:
            self.add_log("Start system first!", COLORS["highlight"])
            return

        tasks = [
            Task(name="Cost Analysis", description="Analyze costs", required_capabilities=["finance"]),
            Task(name="Performance Review", description="Review metrics", required_capabilities=["operations"]),
            Task(name="Code Review", description="Review code", required_capabilities=["engineering"]),
        ]
        task = random.choice(tasks)

        self.add_log(f"Assigning: {task.name}", COLORS["warning"])

        def run():
            future = asyncio.run_coroutine_threadsafe(
                self.engine.assign_task(task),
                self._async_loop,
            )
            success = future.result(timeout=10)
            if success:
                self.root.after(0, lambda: self.add_log(
                    f"Task assigned: {task.name}", COLORS["success"]
                ))

        threading.Thread(target=run, daemon=True).start()

    def emergency_halt(self):
        """Emergency stop."""
        if self.engine and self._async_loop:
            self.add_log("EMERGENCY HALT!", COLORS["highlight"])

            def run():
                future = asyncio.run_coroutine_threadsafe(
                    self.engine.emergency_halt(),
                    self._async_loop,
                )
                future.result(timeout=5)

            threading.Thread(target=run, daemon=True).start()

            for card in self.agent_cards.values():
                card["status"].config(text="OFFLINE", fg=STATUS_COLORS[AgentStatus.OFFLINE])
                card["activity"].config(text="")

            self.decision_label.config(text="System halted", fg=COLORS["highlight"])

    def run(self):
        """Start the UI."""
        self.root.mainloop()


if __name__ == "__main__":
    app = AgentDemoUI()
    app.run()
