from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Session
from app.schemas import SessionCreate, SessionDetail, SessionResponse, SessionUpdate

router = APIRouter(prefix="/api")


@router.post("/session", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_session),
):
    session = Session(title=body.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/history", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Session).order_by(Session.updated_at.desc()))
    return result.scalars().all()


@router.get("/session/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    ses = result.scalar_one_or_none()
    if ses is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ses


@router.delete("/session/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    ses = result.scalar_one_or_none()
    if ses is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    await db.delete(ses)
    await db.commit()


@router.patch("/session/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    ses = result.scalar_one_or_none()
    if ses is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if body.title is not None:
        ses.title = body.title
    await db.commit()
    await db.refresh(ses)
    return ses
