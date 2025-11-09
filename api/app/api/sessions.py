from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, generate_session_token
from app.models.user import User
from app.models.session import Session
from app.models.host import Host
from app.schemas.session import SessionCreate, SessionResponse, SessionShare
from app.schemas.common import SuccessResponse
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List user's active sessions."""
    sessions = await Session.get_user_active_sessions(
        db=db,
        user_id=str(current_user.id)
    )
    return [SessionResponse.from_orm(session) for session in sessions]


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new terminal session."""
    # Verify host exists and belongs to user
    host = await Host.get_by_id(db, session_data.host_id)
    if not host or host.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )

    # Generate session token
    session_token = generate_session_token()

    session = await Session.create(
        db=db,
        user_id=str(current_user.id),
        host_id=session_data.host_id,
        session_token=session_token,
        **session_data.dict(exclude={"host_id"})
    )
    return SessionResponse.from_orm(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get session by ID."""
    session = await Session.get_by_id(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return SessionResponse.from_orm(session)


@router.delete("/{session_id}")
async def end_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """End session."""
    session = await Session.get_by_id(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await session.end_session(db)
    return {"message": "Session ended successfully"}


@router.post("/{session_id}/share", response_model=SuccessResponse)
async def share_session(
    session_id: str,
    share_data: SessionShare,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Share session with other users."""
    session = await Session.get_by_id(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if not session.can_share:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session cannot be shared"
        )

    await session.share_with_users(
        db=db,
        user_ids=share_data.user_ids,
        permissions=share_data.permissions
    )

    return SuccessResponse(
        message="Session shared successfully",
        data={"shared_users": share_data.user_ids}
    )


@router.delete("/{session_id}/share/{user_id}")
async def revoke_session_access(
    session_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Revoke user access to shared session."""
    session = await Session.get_by_id(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await session.revoke_access(db, user_id)
    return {"message": "Access revoked successfully"}


@router.websocket("/ws/{session_token}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_token: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for terminal I/O."""
    await websocket.accept()

    # Get session by token
    session = await Session.get_by_token(db, session_token)
    if not session or not session.is_active:
        await websocket.close(code=4004)
        return

    # Set WebSocket ID
    await session.set_websocket_id(db, f"ws_{session.id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            # TODO: Forward data to SSH Gateway
            # For now, just echo back
            await websocket.send_text(f"Echo: {data}")

            # Update session activity
            await session.update_activity(db)

    except WebSocketDisconnect:
        # Clear WebSocket ID
        await session.clear_websocket_id(db)
        logger.info("WebSocket disconnected", session_id=session.id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session.id, error=str(e))
        await websocket.close()