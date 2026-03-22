import logging
import os
from typing import Optional, Dict, Any, TypedDict
from app.services.openclaw.gateway_rpc import (
    openclaw_call,
    GatewayConfig,
    ensure_session,
    send_message,
    get_chat_history,
    OpenClawGatewayError,
)
from app.core.config import settings
from app.core.rate_limit import is_rate_limit_error, extract_retry_seconds

logger = logging.getLogger(__name__)


class HeartbeatResult(TypedDict):
    success: bool
    rate_limited: bool
    retry_seconds: int
    error_message: str


class OpenClawGateway:
    """Client for interacting with OpenClaw Gateway WebSocket API"""

    def __init__(self):
        self.ws_url = settings.OPENCLAW_GATEWAY_URL
        self.token = settings.OPENCLAW_GATEWAY_TOKEN
        logger.info(f"OpenClawGateway initialized with URL: {self.ws_url}")
        logger.info(f"Token configured: {bool(self.token)}")

    def _get_config(self) -> GatewayConfig:
        """Get gateway config for RPC calls"""
        return GatewayConfig(
            url=self.ws_url,
            token=self.token,
            disable_device_pairing=False,
        )

    async def create_agent(
        self,
        name: str,
        workspace: str,
    ) -> Optional[Dict[str, Any]]:
        """Create an agent in OpenClaw Gateway"""
        logger.info(f"Creating agent in OpenClaw: {name} at workspace: {workspace}")
        try:
            result = await openclaw_call(
                "agents.create",
                {
                    "name": name,
                    "workspace": workspace,
                },
                config=self._get_config(),
            )
            logger.info(f"Agent create result: {result}")
            if result:
                logger.info(f"Agent created in OpenClaw: {name}")
                return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Gateway create agent failed: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def update_agent(
        self,
        agent_id: str,
        name: str,
        workspace: str,
    ) -> Optional[Dict[str, Any]]:
        """Update an agent in OpenClaw Gateway"""
        logger.info(f"Updating agent in OpenClaw: {agent_id}")
        try:
            result = await openclaw_call(
                "agents.update",
                {
                    "agentId": agent_id,
                    "name": name,
                    "workspace": workspace,
                },
                config=self._get_config(),
            )
            if result:
                logger.info(f"Agent updated in OpenClaw: {agent_id}")
                return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Gateway update agent failed: {e}")
            return None

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent from OpenClaw Gateway"""
        logger.info(f"Deleting agent from OpenClaw: {agent_id}")
        try:
            result = await openclaw_call(
                "agents.delete", {"agentId": agent_id}, config=self._get_config()
            )
            return result is not None
        except Exception as e:
            logger.error(f"Gateway delete agent failed: {e}")
            return False

    async def run_agent(
        self,
        agent_id: str,
        message: str = "Start working on your assigned tasks",
    ) -> Optional[Dict[str, Any]]:
        """Trigger an agent to run in OpenClaw via chat.send"""
        logger.info(f"Triggering OpenClaw agent run: {agent_id}")
        try:
            config = self._get_config()
            session_key = f"agent:{agent_id.lower()}:main"
            logger.info(f"Using session key: {session_key}")

            # Ensure session exists
            ensure_result = await ensure_session(
                session_key,
                config=config,
                label=f"Agent {agent_id} session",
            )
            logger.info(f"ensure_session result: {ensure_result}")

            # Send the message to trigger agent work
            result = await send_message(
                message,
                session_key=session_key,
                config=config,
                deliver=True,
            )
            logger.info(f"send_message result: {result}")
            if result:
                logger.info(f"OpenClaw agent run triggered: {agent_id}")
                return {"status": "ok", "result": result}
        except Exception as e:
            logger.error(f"Gateway run agent failed: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def send_chat_message(
        self,
        agent_id: str,
        message: str,
        is_from_user: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Send a chat message to an agent via OpenClaw"""
        logger.info(f"Sending chat message to agent {agent_id}: {message[:50]}...")
        try:
            config = self._get_config()
            session_key = f"agent:{agent_id}:main"

            # Ensure session exists
            await ensure_session(
                session_key,
                config=config,
                label=f"Agent {agent_id} session",
            )

            # Send the message
            result = await send_message(
                message,
                session_key=session_key,
                config=config,
                deliver=True,
            )
            return {"status": "ok", "result": result}
        except Exception as e:
            logger.error(f"Gateway send chat message failed: {e}")
            return None

    async def get_chat_history(
        self,
        agent_id: str,
        limit: int = 50,
    ):
        """Get chat history for an agent from OpenClaw"""
        try:
            # agent_id is already the full session key or agent name
            if agent_id.startswith("agent:"):
                session_key = agent_id
            else:
                session_key = f"agent:{agent_id}:main"
            result = await get_chat_history(
                session_key,
                config=self._get_config(),
                limit=limit,
            )
            return result  # Returns dict with 'messages' key
        except Exception as e:
            logger.error(f"Gateway get chat history failed: {e}")
            return {"messages": []}

    async def get_status(self) -> Dict[str, Any]:
        """Get OpenClaw Gateway status"""
        return await self.health_check()

    async def get_config(self) -> Optional[Dict[str, Any]]:
        """Get current gateway config"""
        try:
            result = await openclaw_call("config.get", {}, config=self._get_config())
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Gateway get config failed: {e}")
            return None

    async def add_agent_to_config(
        self,
        agent_name: str,
        workspace: str,
    ) -> bool:
        """Add an agent to the OpenClaw config (without heartbeat)"""
        logger.info(f"Adding agent to OpenClaw config: {agent_name}")
        try:
            config = self._get_config()

            # Create agent via agents.create endpoint
            result = await openclaw_call(
                "agents.create",
                {
                    "name": agent_name,
                    "workspace": workspace,
                },
                config=config,
            )
            logger.info(f"agents.create result: {result}")

            if result:
                logger.info(f"Agent {agent_name} added to OpenClaw config")
                return True

            logger.warning(f"agents.create returned falsy for {agent_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to add agent {agent_name} to config: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def set_agent_heartbeat(
        self,
        agent_name: str,
        heartbeat_minutes: int,
        workspace: str,
    ) -> HeartbeatResult:
        """Set heartbeat for an agent in the gateway config"""
        logger.info(f"Setting heartbeat for {agent_name}: {heartbeat_minutes}m")
        try:
            config = self._get_config()

            current_config = await openclaw_call("config.get", {}, config=config)
            if not current_config or not isinstance(current_config, dict):
                logger.error("Failed to get current config")
                return HeartbeatResult(
                    success=False,
                    rate_limited=False,
                    retry_seconds=0,
                    error_message="Failed to get current config",
                )

            base_hash = current_config.get("hash", "")

            # Extract the actual config from the nested structure
            actual_config = current_config.get("config", current_config)

            agents_list = actual_config.get("agents", {}).get("list", [])
            agent_found = False

            # Find the agent
            for idx, agent in enumerate(agents_list):
                if agent.get("name", "").lower() == agent_name.lower():
                    agent_found = True

                    if heartbeat_minutes <= 0:
                        # Disable heartbeat by removing the heartbeat key
                        if "heartbeat" in agent:
                            del agent["heartbeat"]
                            logger.info(f"Removed heartbeat config for {agent_name}")
                    else:
                        # Enable heartbeat
                        agent["heartbeat"] = {
                            "every": f"{heartbeat_minutes}m",
                            "includeReasoning": False,
                            "target": "none",
                        }
                        # Also update workspace and agentDir if they changed
                        if workspace:
                            agent["workspace"] = workspace
                            agent_dir = (
                                workspace.replace("/workspace", "/agent")
                                if workspace.endswith("/workspace")
                                else f"{workspace}/../agent"
                            )
                            agent["agentDir"] = agent_dir
                        logger.info(
                            f"Updated heartbeat config for {agent_name}: {heartbeat_minutes}m"
                        )
                    break

            # If agent not found and heartbeat > 0, create new entry
            if not agent_found and heartbeat_minutes > 0:
                agent_dir = (
                    workspace.replace("/workspace", "/agent")
                    if workspace.endswith("/workspace")
                    else f"{workspace}/../agent"
                )
                new_agent_entry = {
                    "id": agent_name.lower().replace(" ", "-"),
                    "name": agent_name,
                    "workspace": workspace,
                    "agentDir": agent_dir,
                    "heartbeat": {
                        "every": f"{heartbeat_minutes}m",
                        "includeReasoning": False,
                        "target": "none",
                    },
                }
                agents_list.append(new_agent_entry)
                actual_config["agents"]["list"] = agents_list
                logger.info(f"Added new agent entry with heartbeat for {agent_name}")

            import json as json_module

            raw_config = json_module.dumps(actual_config)

            logger.info(
                f"Calling config.apply with baseHash: {base_hash[:20] if base_hash else 'none'}..."
            )
            result = await openclaw_call(
                "config.apply",
                {
                    "raw": raw_config,
                    "baseHash": base_hash,
                },
                config=config,
            )
            logger.info(f"config.apply result type: {type(result)}, value: {result}")

            if result:
                logger.info(
                    f"Heartbeat {'disabled' if heartbeat_minutes <= 0 else 'set'} for {agent_name}: {heartbeat_minutes}m"
                )
                return HeartbeatResult(
                    success=True,
                    rate_limited=False,
                    retry_seconds=0,
                    error_message="",
                )

            return HeartbeatResult(
                success=False,
                rate_limited=False,
                retry_seconds=0,
                error_message="config.apply returned empty result",
            )
        except OpenClawGatewayError as e:
            error_msg = str(e)
            if is_rate_limit_error(error_msg):
                retry_seconds = extract_retry_seconds(error_msg)
                logger.warning(
                    f"RATE_LIMITED setting heartbeat for {agent_name}: wait {retry_seconds}s - {error_msg}"
                )
                return HeartbeatResult(
                    success=False,
                    rate_limited=True,
                    retry_seconds=retry_seconds,
                    error_message=error_msg,
                )
            logger.error(f"Gateway error setting heartbeat for {agent_name}: {e}")
            return HeartbeatResult(
                success=False,
                rate_limited=False,
                retry_seconds=0,
                error_message=error_msg,
            )
        except Exception as e:
            logger.error(f"Failed to set heartbeat for {agent_name}: {e}")
            import traceback

            traceback.print_exc()
            return HeartbeatResult(
                success=False,
                rate_limited=False,
                retry_seconds=0,
                error_message=str(e),
            )

    async def get_agent_heartbeat(self, agent_name: str) -> int:
        """Get the current heartbeat interval for an agent from OpenClaw config. Returns minutes, or 0 if not set."""
        try:
            config = self._get_config()
            current_config = await openclaw_call("config.get", {}, config=config)
            if not current_config or not isinstance(current_config, dict):
                return 0

            actual_config = current_config.get("config", current_config)
            agents_list = actual_config.get("agents", {}).get("list", [])

            for agent in agents_list:
                if agent.get("name", "").lower() == agent_name.lower():
                    heartbeat = agent.get("heartbeat")
                    if heartbeat:
                        every = heartbeat.get("every", "")
                        if every.endswith("m"):
                            return int(every.rstrip("m"))
                        elif every.endswith("h"):
                            return int(every.rstrip("h")) * 60
                        elif every.endswith("s"):
                            return max(1, int(every.rstrip("s")) // 60)
                        return int(every) if every.isdigit() else 0
                    return 0
            return 0
        except Exception:
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Check OpenClaw Gateway health via WebSocket"""
        try:
            config = self._get_config()
            result = await openclaw_call("health", {}, config=config)
            if result:
                return {
                    "connected": True,
                    "gateway_url": self.ws_url,
                    "token_configured": bool(self.token),
                    "status": result,
                    "error": None,
                }
            else:
                return {
                    "connected": False,
                    "gateway_url": self.ws_url,
                    "token_configured": bool(self.token),
                    "status": None,
                    "error": "Health check returned empty result",
                }
        except Exception as e:
            logger.error(f"Gateway health check failed: {e}")
            return {
                "connected": False,
                "gateway_url": self.ws_url,
                "token_configured": bool(self.token),
                "status": None,
                "error": str(e),
            }

    async def list_agents(self) -> Optional[list]:
        """List agents from OpenClaw Gateway"""
        try:
            config = self._get_config()
            result = await openclaw_call("health", {}, config=config)
            if result and isinstance(result, dict):
                agents = result.get("agents", [])
                return agents
            return []
        except Exception as e:
            logger.error(f"Gateway list agents failed: {e}")
            return None


openclaw = OpenClawGateway()
