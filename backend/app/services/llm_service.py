import httpx
import json
import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_url = api_url or settings.LLM_API_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url, headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()
                return (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"LLM HTTP Error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"LLM Error: {str(e)}")
            return None

    async def generate_with_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", self.api_url, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                content = (
                                    data.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"LLM Streaming Error: {str(e)}")
            yield f"Error: {str(e)}"

    def parse_actions(self, response: str) -> List[Dict[str, Any]]:
        actions = []
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("ACTION:"):
                parts = line[7:].split("|")
                action = {"type": parts[0].strip().upper()}
                for part in parts[1:]:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        action[key.strip().lower()] = value.strip()
                actions.append(action)
            elif line.startswith("[ACTION]"):
                import re

                match = re.search(r"\[ACTION\]\s*(\w+)(.*)", line)
                if match:
                    action_type = match.group(1).upper()
                    action = {"type": action_type}
                    rest = match.group(2)
                    key_values = re.findall(r"(\w+):\s*([^\[\]]+)", rest)
                    for key, value in key_values:
                        action[key.lower()] = value.strip()
                    actions.append(action)
        return actions

    async def generate_agent_files(
        self,
        agent_name: str,
        role: str,
        team: Optional[str] = None,
        chief_name: Optional[str] = None,
        can_spawn_subagents: bool = False,
    ) -> Dict[str, str]:
        """Generate agent personality files based on role using LLM"""

        system_prompt = """You are an expert AI agent designer. You create detailed, realistic agent personality files.
Generate content that is:
- Specific to the agent's role and responsibilities
- Practical and actionable
- Consistent across all files
- Written in a professional tone

Output ONLY valid markdown/markdown JSON for each file."""

        role_context = f"""
Agent Name: {agent_name}
Role: {role}
Team: {team or "General"}
Chief: {chief_name or "None specified"}
Can Spawn Subagents: {"Yes" if can_spawn_subagents else "No"}
"""

        messages = [
            {
                "role": "user",
                "content": f"""Create the 5 personality files for this AI agent. Output as JSON with keys: soul, identity, agents, memory, user

{role_context}

SOUL.md - Core personality, values, communication style, decision-making framework
IDENTITY.md - Role details, responsibilities, team position, key skills
AGENTS.md - Governance rules, startup sequence, safety protocols, action types, coordination
MEMORY.json - Template with entries array and stats (tasks_completed, tasks_failed, etc)
USER.md - Context about the human boss/CEO
""",
            }
        ]

        result = await self.generate(
            messages,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=4000,
        )

        if not result:
            return self._get_default_files(agent_name, role, team)

        try:
            data = json.loads(result)
            return {
                "soul": data.get("soul", ""),
                "identity": data.get("identity", ""),
                "agents": data.get("agents", ""),
                "memory": data.get(
                    "memory",
                    {"entries": [], "stats": {"tasks_completed": 0, "tasks_failed": 0}},
                ),
                "user": data.get("user", ""),
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON, using defaults")
            return self._get_default_files(agent_name, role, team)

    def _get_default_files(
        self,
        agent_name: str,
        role: str,
        team: Optional[str] = None,
    ) -> Dict[str, str]:
        return {
            "soul": f"""# SOUL.md for {agent_name}

## Personality
- You are a dedicated professional focused on achieving excellence in your role as {role}
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
            "identity": f"""# IDENTITY.md for {agent_name}

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
            "agents": f"""# AGENTS.md for {agent_name}

## Governance Rules
1. Always prioritize tasks based on urgency and importance
2. Report blockers immediately to your chief
3. Keep communication clear and concise

## Startup Sequence
1. Check pending tasks
2. Review any new messages
3. Assess priorities for the day
4. Begin work on highest priority task

## Safety Protocols
1. Never execute destructive actions without confirmation
2. Escalate uncertain decisions to review
3. Maintain audit trail of all actions

## Action Types Supported
- MOVE_TASK: Move task between columns
- MESSAGE_AGENT: Send message to another agent
- SPAWN_SUBAGENT: Create a sub-agent for micro-tasks
- REQUEST_REVIEW: Move task to review column
""",
            "memory": json.dumps(
                {
                    "entries": [],
                    "stats": {
                        "tasks_completed": 0,
                        "tasks_failed": 0,
                        "messages_sent": 0,
                        "subagents_created": 0,
                    },
                }
            ),
            "user": """# USER.md

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
        }

    async def generate_task_plan(
        self,
        task_title: str,
        task_description: str,
        agent_role: str,
        agent_soul: str,
    ) -> str:
        """Generate a plan for executing a task"""

        system_prompt = """You are an expert task planner. Create clear, actionable plans for AI agents.
Break down complex tasks into specific, manageable steps.
Consider dependencies, potential blockers, and success criteria."""

        messages = [
            {
                "role": "user",
                "content": f"""Create a detailed execution plan for this task:

Task: {task_title}
Description: {task_description}
Agent Role: {agent_role}

Provide a numbered list of steps, each with:
- What to do
- Expected outcome
- Potential challenges

Keep the plan practical and achievable.""",
            }
        ]

        return (
            await self.generate(
                messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=1500,
            )
            or "Plan generation failed - proceed with basic execution"
        )

    async def generate_task_summary(
        self,
        task_title: str,
        task_description: str,
        agent_name: str,
        success: bool,
        actions_taken: List[str],
        results: str,
    ) -> str:
        """Generate a task completion summary"""

        status = "Successfully completed" if success else "Failed to complete"

        messages = [
            {
                "role": "user",
                "content": f"""Generate a brief summary for the human boss:

Task: {task_title}
Agent: {agent_name}
Status: {status}

Actions taken:
{chr(10).join(f"- {a}" for a in actions_taken)}

Results:
{results}

Keep it concise, professional, and highlight key outcomes.""",
            }
        ]

        return (
            await self.generate(
                messages,
                system_prompt="You are a helpful assistant that summarizes task completions.",
                temperature=0.5,
                max_tokens=500,
            )
            or f"{status}: {task_title}"
        )

    async def generate_agent_response(
        self,
        agent_name: str,
        agent_role: str,
        agent_soul: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """Generate streaming response from agent to user message"""

        context_str = json.dumps(context, indent=2)

        system_prompt = f"""You are {agent_name}, a {agent_role}.

Your personality:
{agent_soul[:500]}

Current context:
{context_str}

Respond as the agent would. Be helpful, direct, and professional.
If you need to take actions, format them as: [ACTION] ACTION_TYPE key: value"""

        messages = [{"role": "user", "content": user_message}]

        async for chunk in self.generate_with_stream(
            messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000,
        ):
            yield chunk


llm_service = LLMService()
