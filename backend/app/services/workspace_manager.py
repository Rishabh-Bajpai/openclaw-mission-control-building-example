import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from app.models.schemas import FiveFileContent


class AgentWorkspaceManager:
    """
    Manages the workspace files for agents with the following structure:

    .openclaw/agents/<agent_name>/
    ├── agent/
    │   └── models.json
    ├── sessions/
    └── workspace/
        ├── SOUL.md - Personality, voice, values
        ├── IDENTITY.md - Name, role, team
        ├── AGENTS.md - Governance rules, protocols
        ├── MEMORY.md - Long-term memory (Markdown)
        ├── USER.md - Context about the human boss
        ├── HEARTBEAT.md - Heartbeat check instructions
        └── TASKS.md - Current task board state
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.expanduser("~/.openclaw/agents")
        self.base_dir = Path(base_dir)

    def _get_agent_dir(self, agent_name: str) -> Path:
        """Get the agent directory"""
        safe_name = agent_name.lower().replace(" ", "_")
        agent_dir = self.base_dir / safe_name
        return agent_dir

    def _get_workspace_dir(self, agent_name: str) -> Path:
        """Get the workspace directory where agent files and work live"""
        return self._get_agent_dir(agent_name) / "workspace"

    def _get_agent_subdir(self, agent_name: str) -> Path:
        """Get the agent subdirectory (where models.json lives)"""
        return self._get_agent_dir(agent_name) / "agent"

    def _get_sessions_dir(self, agent_name: str) -> Path:
        """Get the sessions directory"""
        return self._get_agent_dir(agent_name) / "sessions"

    def ensure_directories(self, agent_name: str) -> None:
        """Create all necessary directories for an agent"""
        agent_dir = self._get_agent_dir(agent_name)
        workspace_dir = self._get_workspace_dir(agent_name)
        agent_subdir = self._get_agent_subdir(agent_name)
        sessions_dir = self._get_sessions_dir(agent_name)

        agent_dir.mkdir(exist_ok=True, parents=True)
        workspace_dir.mkdir(exist_ok=True, parents=True)
        agent_subdir.mkdir(exist_ok=True, parents=True)
        sessions_dir.mkdir(exist_ok=True, parents=True)

    def get_agent_workspace(self, agent_name: str) -> str:
        """Get the workspace path for OpenClaw config"""
        workspace_dir = self._get_workspace_dir(agent_name)
        self.ensure_directories(agent_name)
        return str(workspace_dir.absolute())

    def get_agent_dir(self, agent_name: str) -> str:
        """Get the agentDir path"""
        return str(self._get_agent_dir(agent_name).absolute())

    def save_file(
        self, agent_name: str, filename: str, content: str, in_workspace: bool = True
    ) -> bool:
        """Save a file to agent workspace"""
        try:
            if in_workspace:
                file_path = self._get_workspace_dir(agent_name) / filename
            else:
                file_path = self._get_agent_dir(agent_name) / filename
            file_path.write_text(content)
            return True
        except Exception as e:
            print(f"Error saving {filename} for {agent_name}: {e}")
            return False

    def read_file(
        self, agent_name: str, filename: str, in_workspace: bool = True
    ) -> Optional[str]:
        """Read a file from agent workspace"""
        try:
            if in_workspace:
                file_path = self._get_workspace_dir(agent_name) / filename
            else:
                file_path = self._get_agent_dir(agent_name) / filename
            if file_path.exists():
                return file_path.read_text()
            return None
        except Exception as e:
            print(f"Error reading {filename} for {agent_name}: {e}")
            return None

    def save_all(self, agent_name: str, content: FiveFileContent) -> bool:
        """Save all agent files to workspace"""
        self.save_file(agent_name, "SOUL.md", content.soul, in_workspace=True)
        self.save_file(agent_name, "IDENTITY.md", content.identity, in_workspace=True)
        self.save_file(agent_name, "AGENTS.md", content.agents, in_workspace=True)
        self.save_file(agent_name, "MEMORY.md", content.memory, in_workspace=True)
        self.save_file(agent_name, "USER.md", content.user, in_workspace=True)
        self.save_file(agent_name, "HEARTBEAT.md", content.heartbeat, in_workspace=True)
        return True

    def read_all(self, agent_name: str) -> Optional[FiveFileContent]:
        """Read all agent files from workspace"""
        soul = self.read_file(agent_name, "SOUL.md", in_workspace=True)
        identity = self.read_file(agent_name, "IDENTITY.md", in_workspace=True)
        agents = self.read_file(agent_name, "AGENTS.md", in_workspace=True)
        memory = self.read_file(agent_name, "MEMORY.md", in_workspace=True)
        user = self.read_file(agent_name, "USER.md", in_workspace=True)
        heartbeat = self.read_file(agent_name, "HEARTBEAT.md", in_workspace=True)

        if any(f is None for f in [soul, identity, agents, memory, user]):
            return None

        return FiveFileContent(
            soul=soul or "",
            identity=identity or "",
            agents=agents or "",
            memory=memory or "",
            user=user or "",
            heartbeat=heartbeat or "",
        )

    def update_memory(self, agent_name: str, key: str, value: Any) -> bool:
        content = self.read_all(agent_name)
        if content is None:
            return False
        content.memory += f"\n\n## {key}\n{value}"
        self.save_file(agent_name, "MEMORY.md", content.memory, in_workspace=True)
        return True

    def add_memory_entry(self, agent_name: str, entry: Dict[str, Any]) -> bool:
        content = self.read_all(agent_name)
        if content is None:
            return False
        entry_text = f"\n\n- **{entry.get('timestamp', 'Unknown')}**: {entry.get('action', '')} - {entry.get('details', '')}"
        content.memory += entry_text
        self.save_file(agent_name, "MEMORY.md", content.memory, in_workspace=True)
        return True

    def update_tasks_md(self, agent_name: str, tasks_content: str) -> bool:
        """Update the TASKS.md file with current task board state"""
        return self.save_file(agent_name, "TASKS.md", tasks_content, in_workspace=True)

    def update_identity(
        self, agent_name: str, name: str, role: str, team: Optional[str] = None
    ) -> bool:
        """Update IDENTITY.md with new name, role, or team"""
        try:
            new_identity = f"""# IDENTITY.md for {name}

## Name
{name}

## Role
{role}

## Team
{team or "General"}

## Responsibilities
- Complete assigned tasks with excellence
- Report progress to superiors
- Collaborate with team members
- Maintain high quality standards
"""
            return self.save_file(
                agent_name, "IDENTITY.md", new_identity, in_workspace=True
            )
        except Exception as e:
            print(f"Error updating identity for {agent_name}: {e}")
            return False

            lines = identity.split("\n")
            new_lines = []
            for line in lines:
                if (
                    line.startswith("## Name")
                    or line.startswith("## Role")
                    or line.startswith("## Team")
                ):
                    skip_section = True
                elif skip_section and line.startswith("#"):
                    skip_section = False
                    new_lines.append(line)
                    continue
                elif skip_section and line.strip() and not line.startswith("#"):
                    continue
                else:
                    skip_section = False
                    new_lines.append(line)
                new_lines.append(line)

            new_identity = f"""# IDENTITY.md for {name}

## Name
{name}

## Role
{role}

## Team
{team or "General"}

## Responsibilities
- Complete assigned tasks with excellence
- Report progress to superiors
- Collaborate with team members
- Maintain high quality standards
"""
            return self.save_file(
                agent_name, "IDENTITY.md", new_identity, in_workspace=True
            )
        except Exception as e:
            print(f"Error updating identity for {agent_name}: {e}")
            return False

    def delete_agent_files(self, agent_name: str) -> bool:
        try:
            agent_dir = self._get_agent_dir(agent_name)
            import shutil

            shutil.rmtree(agent_dir)
            return True
        except Exception as e:
            print(f"Error deleting files for {agent_name}: {e}")
            return False

    def list_agents(self) -> list[str]:
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def create_default_files(
        self, agent_name: str, role: str, team: Optional[str] = None
    ) -> FiveFileContent:
        self.ensure_directories(agent_name)

        default_content = FiveFileContent(
            soul=f"""# SOUL.md for {agent_name}

## Personality
- You are a dedicated professional focused on achieving excellence
- You communicate with clarity and purpose
- You value efficiency and results

## Voice
- Direct and professional
- Confident but collaborative
- Action-oriented

## Values
- Quality over quantity
- Continuous improvement
- Team success

## Core Beliefs
- Every task matters
- Clear communication prevents errors
- Success comes from systematic execution
""",
            identity=f"""# IDENTITY.md for {agent_name}

## Name
{agent_name}

## Role
{role}

## Team
{team or "General"}

## Responsibilities
- Complete assigned tasks with excellence
- Report progress to superiors
- Collaborate with team members
- Maintain high quality standards
""",
            agents=f"""# AGENTS.md for {agent_name}

## Governance Rules
1. Always prioritize tasks based on urgency and importance
2. Report blockers immediately to your chief
3. Keep communication clear and concise
4. Check TASKS.md for your current task board state
5. Update TASKS.md when task status changes

## Task Board Integration
- Read TASKS.md to see your tasks and team tasks
- Update task status using the Mission Control API
- When you start working, mark task as "in_progress"
- When blocked, note what is needed and skip to next BACKLOG task

## Startup Sequence
1. Read TASKS.md for current task state
2. Check for any new tasks assigned to you
3. Review team member task progress
4. Begin or continue highest priority task

## Task Completion Rules:
- If you have completed a task successfully → move it to REVIEW in TASKS.md
- NEVER move a task to DONE (only user can move to done after review)
- NEVER move DONE tasks back to BACKLOG or REVIEW
- If task is blocked → note what is needed and move to next BACKLOG task

## Safety Protocols
1. Never execute destructive actions without confirmation
2. Escalate uncertain decisions to review
3. Maintain audit trail of all actions

## Action Types Supported
- TASK_START: Move task to in_progress and start working
- TASK_REVIEW: Move task to review for approval
- TASK_BLOCKED: Mark task as blocked
- MESSAGE_CHIEF: Send update to your supervisor
""",
            memory=f"""# MEMORY.md - Long-term memory for {agent_name}

## Overview
This agent ({agent_name}) is a {role} on the {team or "General"} team.
Mission Control board tracks all tasks. TASKS.md shows current state.

## Stats
- Tasks Completed: 0
- Tasks Failed: 0

## Recent Accomplishments
(None yet)

## Key Decisions
(None yet)

## Important Notes
(None yet)
""",
            user=f"""# USER.md

## The Boss
Human CEO overseeing operations

## Preferences
- Clear, concise updates
- Actionable insights
- Minimal fluff

## Communication Style
- Direct commands accepted
- "Do it now" = execute immediately
- Updates on completion or failure only
""",
            heartbeat=f"""# HEARTBEAT.md - Task Board Check

## On each heartbeat check:
1. Read TASKS.md to see current task state
2. Check if any tasks need your attention:
   - BACKLOG tasks → move to IN_PROGRESS and START WORKING
   - IN_PROGRESS tasks → CONTINUE WORKING on them
   - REVIEW tasks → wait for user feedback
3. When you complete a task successfully → move to REVIEW
4. Update TASKS.md with any changes
5. If nothing needs attention → reply: HEARTBEAT_OK

## Task Statuses
- BACKLOG: Task assigned, not started yet
- IN_PROGRESS: Currently working on it
- REVIEW: Completed, awaiting approval
- DONE: Fully completed (USER ONLY - never move to DONE)

## Critical Rules:
- NEVER move a task to DONE (only user can do that after review)
- NEVER move DONE tasks back to BACKLOG or REVIEW
- If a task is blocked → note what is needed and skip to next BACKLOG task

## Response Format
If nothing needs attention, reply: HEARTBEAT_OK
If you took action, briefly summarize what you did.
""",
        )
        self.save_all(agent_name, default_content)
        self.save_file(
            agent_name,
            "TASKS.md",
            f"""# TASKS.md - Task Board for {agent_name}

## My Tasks
(No tasks assigned yet)

## Team Tasks
(No team tasks)
""",
            in_workspace=True,
        )

        self._create_models_json(agent_name)

        return default_content

    def _create_models_json(self, agent_name: str) -> None:
        """Create models.json in the agent subdirectory"""
        try:
            models_path = self._get_agent_subdir(agent_name) / "models.json"
            models_content = {
                "agents": {},
                "default": {},
            }
            models_path.write_text(json.dumps(models_content, indent=2))
        except Exception as e:
            print(f"Error creating models.json for {agent_name}: {e}")


workspace_manager = AgentWorkspaceManager()
