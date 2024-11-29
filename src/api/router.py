from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from telethon import TelegramClient
from fast_depends import Depends, inject
from typing import Optional
from pydantic import BaseModel, ConfigDict

from src.dependencies import Dependencies

router = APIRouter()


class MessageResponse(BaseModel):
    status: str
    message: str


@inject
async def verify_auth(request: Request) -> bool:
    # TODO: Implement proper authentication
    # This is a placeholder that always returns True
    return True


@router.get("/redirect/{path:path}")
@inject
async def redirect(
    path: str, request: Request, authenticated: bool = Depends(verify_auth)
) -> RedirectResponse:
    """
    Handles redirects for authenticated users.
    The path parameter captures the entire path after /redirect/
    """
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    return RedirectResponse(url=path)
