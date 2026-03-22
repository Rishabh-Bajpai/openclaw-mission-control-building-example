from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.services.openclaw_gateway import openclaw

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMSettingsUpdate(BaseModel):
    api_url: str
    api_key: str | None = None
    model: str


class SettingsResponse(BaseModel):
    llm_api_url: str
    llm_model: str
    debug: bool
    app_name: str
    openclaw_gateway_url: str
    openclaw_connected: bool


class OpenClawStatusResponse(BaseModel):
    connected: bool
    gateway_url: str
    token_configured: bool
    error: str | None = None


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    status = await openclaw.get_status()
    return {
        "llm_api_url": settings.LLM_API_URL,
        "llm_model": settings.LLM_MODEL,
        "debug": settings.DEBUG,
        "app_name": settings.APP_NAME,
        "openclaw_gateway_url": settings.OPENCLAW_GATEWAY_URL,
        "openclaw_connected": status.get("connected", False),
    }


@router.get("/llm")
async def get_llm_settings():
    return {
        "api_url": settings.LLM_API_URL,
        "api_key": settings.LLM_API_KEY if settings.LLM_API_KEY else "",
        "model": settings.LLM_MODEL,
        "note": "LLM is managed by OpenClaw. Configure in OpenClaw settings.",
    }


@router.put("/llm")
async def update_llm_settings(settings_update: LLMSettingsUpdate):
    return {
        "message": "Settings noted. OpenClaw manages its own LLM configuration.",
        "api_url": settings_update.api_url,
        "model": settings_update.model,
        "note": "Configure the actual LLM in OpenClaw's settings panel.",
    }


@router.get("/openclaw", response_model=OpenClawStatusResponse)
async def get_openclaw_status():
    status = await openclaw.get_status()
    return {
        "connected": status.get("connected", True),
        "gateway_url": settings.OPENCLAW_GATEWAY_URL,
        "token_configured": settings.OPENCLAW_GATEWAY_TOKEN is not None,
        "error": status.get("error"),
    }


@router.post("/openclaw/test")
async def test_openclaw_connection():
    status = await openclaw.get_status()
    if status.get("connected"):
        return {"message": "OpenClaw Gateway is connected", "status": status}
    else:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to OpenClaw Gateway at {settings.OPENCLAW_GATEWAY_URL}",
        )
