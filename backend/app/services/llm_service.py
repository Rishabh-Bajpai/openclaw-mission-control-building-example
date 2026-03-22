"""
LLM Service for OpenClaw Mission Control

This service provides a unified interface for interacting with Large Language Models (LLMs).
It supports any OpenAI-compatible API, including:
- OpenAI (GPT-4, GPT-3.5)
- Local models (LM Studio, Ollama)
- Self-hosted (vLLM, TGI)

Features:
--------
- Async API calls for non-blocking operations
- Streaming responses for real-time output
- System prompt injection
- Automatic retry on failure
- Configurable temperature and token limits

Usage Examples:
--------------
Basic generation:
```python
llm = LLMService()
response = await llm.generate([
    {"role": "user", "content": "Hello!"}
])
```

Streaming response:
```python
async for chunk in llm.generate_with_stream(messages):
    print(chunk, end="", flush=True)
```

Custom configuration:
```python
llm = LLMService(
    api_url="http://localhost:1234/v1/chat/completions",
    api_key=None,  # No auth for local
    model="my-custom-model"
)
```

Extension Points:
----------------
1. Add new LLM providers:
   - Implement provider-specific logic in generate()
   - Handle different API formats

2. Add caching:
   - Cache frequent prompts
   - Use Redis or in-memory cache

3. Add prompt templates:
   - Pre-built prompts for common tasks
   - Template variables and substitution

4. Add token counting:
   - Use tiktoken or similar
   - Prevent context overflow

See Also:
---------
- app/core/config.py - API configuration
- app/api/meetings.py - Uses LLM for standup generation
- app/services/workspace_manager.py - Generates agent files
"""

import httpx
import json
import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for interacting with LLM APIs.

    Handles:
    - API authentication
    - Request formatting
    - Response parsing
    - Error handling
    - Streaming responses

    Attributes:
        api_url: Full URL to API endpoint (e.g., https://api.openai.com/v1/chat/completions)
        api_key: Bearer token for authentication
        model: Model identifier (e.g., gpt-4, gpt-3.5-turbo)

    Example:
        >>> llm = LLMService()
        >>> response = await llm.generate([{"role": "user", "content": "Hi"}])
        >>> print(response)
        'Hello! How can I help you today?'
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize LLM service with optional overrides.

        Args:
            api_url: Override default API URL
            api_key: Override default API key
            model: Override default model

        Note:
            If not provided, uses values from settings (app/core/config.py)
        """
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
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Example: [{"role": "user", "content": "Hello!"}]
            system_prompt: Optional system prompt to prepend
            temperature: Sampling temperature (0.0-2.0)
                        Lower = more deterministic
                        Higher = more creative
            max_tokens: Maximum tokens in response

        Returns:
            Generated text or None on error

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "What is 2+2?"}
            ... ]
            >>> response = await llm.generate(messages)
            >>> print(response)
            '2+2 equals 4.'
        """
        # Prepend system prompt if provided
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        # Setup request headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            # Bearer token authentication (OpenAI standard)
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Build request payload
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            # Make async HTTP request
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url, headers=headers, json=payload
                )
                response.raise_for_status()  # Raise on HTTP errors
                data = response.json()

                # Extract content from response
                # Standard OpenAI format: data.choices[0].message.content
                return (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
        except httpx.HTTPStatusError as e:
            # Log HTTP errors (4xx, 5xx)
            logger.error(
                f"LLM HTTP Error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            # Log any other errors
            logger.error(f"LLM Error: {str(e)}")
            return None

    async def generate_with_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.

        Yields response chunks as they become available.
        Use this for real-time output or long responses.

        Args:
            messages: List of message dicts
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            Text chunks as they arrive

        Example:
            >>> async for chunk in llm.generate_with_stream(messages):
            ...     print(chunk, end="", flush=True)
        """
        # Prepare messages
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        # Setup headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Enable streaming
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,  # Enable streaming
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Use streaming context manager
                async with client.stream(
                    "POST", self.api_url, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()

                    # Process SSE (Server-Sent Events) lines
                    async for line in response.aiter_lines():
                        # Skip non-data lines
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix

                            # Check for end marker
                            if data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                # Extract delta content from OpenAI format
                                content = (
                                    data.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                # Skip malformed JSON
                                continue
        except Exception as e:
            logger.error(f"LLM Streaming Error: {str(e)}")
            yield f"Error: {str(e)}"

    def parse_actions(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse action directives from LLM response.

        Agents can return structured actions in their responses.
        This parses common action formats:
        - ACTION:type|key:value|key:value
        - [ACTION] ACTION_TYPE key: value

        Args:
            response: Raw LLM response text

        Returns:
            List of action dictionaries:
            [{"type": "MOVE_TASK", "task_id": "123", "status": "review"}, ...]

        Example:
            >>> response = "[ACTION] MOVE_TASK task_id: 123 status: review"
            >>> actions = llm.parse_actions(response)
            >>> print(actions)
            [{'type': 'MOVE_TASK', 'task_id': '123', 'status': 'review'}]
        """
        actions = []
        lines = response.split("\n")

        for line in lines:
            line = line.strip()

            # Format 1: ACTION:type|key:value|key:value
            if line.startswith("ACTION:"):
                parts = line[7:].split("|")  # Remove "ACTION:" prefix
                action = {"type": parts[0].strip().upper()}
                for part in parts[1:]:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        action[key.strip().lower()] = value.strip()
                actions.append(action)

            # Format 2: [ACTION] ACTION_TYPE key: value
            elif line.startswith("[ACTION]"):
                import re

                match = re.search(r"\[ACTION\]\s*(\w+)(.*)", line)
                if match:
                    action_type = match.group(1).upper()
                    action = {"type": action_type}

                    # Extract key: value pairs
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
        """
        Generate agent workspace files using LLM.

        Creates custom SOUL.md, IDENTITY.md, AGENTS.md, MEMORY.md, USER.md
        based on agent's role and context.

        Falls back to defaults if LLM fails.

        Args:
            agent_name: Agent's name
            role: Job role/title
            team: Team name
            chief_name: Supervisor's name
            can_spawn_subagents: Permission to create sub-agents

        Returns:
            Dict with file contents:
            {
                "soul": "...",
                "identity": "...",
                "agents": "...",
                "memory": "...",
                "user": "..."
            }
        """
        # System prompt for file generation
        system_prompt = """You are an expert AI agent designer. You create detailed, realistic agent personality files.
Generate content that is:
- Specific to the agent's role and responsibilities
- Practical and actionable
- Consistent across all files
- Written in a professional tone

Output ONLY valid JSON with keys: soul, identity, agents, memory, user."""

        # Build context for generation
        role_context = f"""
Agent Name: {agent_name}
Role: {role}
Team: {team or "General"}
Chief: {chief_name or "None specified"}
Can Spawn Subagents: {"Yes" if can_spawn_subagents else "No"}
"""

        # Prompt for file generation
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

        # Generate with LLM
        result = await self.generate(
            messages,
            system_prompt=system_prompt,
            temperature=0.8,  # Higher temperature for creative generation
            max_tokens=4000,
        )

        # Fallback to defaults if LLM fails
        if not result:
            logger.warning("LLM generation failed, using default files")
            return self._get_default_files(agent_name, role, team)

        # Parse JSON response
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
        """
        Get default workspace file contents.

        Called when LLM generation fails or as fallback.

        Args:
            agent_name: Agent's name
            role: Job role
            team: Team name

        Returns:
            Dict with default file contents
        """
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
        """
        Generate an execution plan for a task.

        Uses LLM to break down task into actionable steps.

        Args:
            task_title: Short task title
            task_description: Detailed description
            agent_role: Agent's job role
            agent_soul: Agent's personality/values

        Returns:
            Structured plan as text
        """
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

        result = await self.generate(
            messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1500,
        )

        return result or "Plan generation failed - proceed with basic execution"

    async def generate_task_summary(
        self,
        task_title: str,
        task_description: str,
        agent_name: str,
        success: bool,
        actions_taken: List[str],
        results: str,
    ) -> str:
        """
        Generate a summary of task completion.

        Creates a human-readable summary for the operator.

        Args:
            task_title: Task name
            task_description: Task details
            agent_name: Agent who completed task
            success: Whether task succeeded
            actions_taken: List of actions performed
            results: Task results

        Returns:
            Brief summary text
        """
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

        result = await self.generate(
            messages,
            system_prompt="You are a helpful assistant that summarizes task completions.",
            temperature=0.5,  # Lower temperature for factual summary
            max_tokens=500,
        )

        return result or f"{status}: {task_title}"

    async def generate_agent_response(
        self,
        agent_name: str,
        agent_role: str,
        agent_soul: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from agent to user message.

        Used for real-time agent conversations.

        Args:
            agent_name: Agent's name
            agent_role: Agent's job role
            agent_soul: Agent's personality
            user_message: Message from user
            context: Additional context (tasks, recent messages, etc.)

        Yields:
            Response chunks as they arrive
        """
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


# Global singleton instance
# Usage: from app.services.llm_service import llm_service
llm_service = LLMService()
