from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Assignment, Duty, Tag, duty_tag
from app.schemas import DutyCreate, DutyDetailOut, DutyOut, DutyUpdate, PaginatedResponse, TagOut

router = APIRouter(prefix="/duties", tags=["duties"])


@router.get("", response_model=PaginatedResponse[DutyOut])
async def list_duties(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
    tag_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    base = select(Duty)
    if date_from:
        base = base.where(Duty.date >= date_from)
    if date_to:
        base = base.where(Duty.date <= date_to)
    if q:
        base = base.where(Duty.name.ilike(f"%{q}%"))
    if tag_id is not None:
        base = base.where(Duty.id.in_(select(duty_tag.c.duty_id).where(duty_tag.c.tag_id == tag_id)))

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    query = base.options(selectinload(Duty.tags)).order_by(Duty.date, Duty.name).offset(offset).limit(limit)
    result = await db.execute(query)
    return PaginatedResponse(items=result.scalars().all(), total=total)


@router.get("/{duty_id}", response_model=DutyDetailOut)
async def get_duty(duty_id: int, db: AsyncSession = Depends(get_db)):
    duty = await db.get(Duty, duty_id, options=[selectinload(Duty.tags)])
    if not duty:
        raise HTTPException(404, "Duty not found")
    count_result = await db.execute(
        select(func.count()).where(Assignment.duty_id == duty_id)
    )
    assignment_count = count_result.scalar_one()
    return DutyDetailOut(
        id=duty.id,
        name=duty.name,
        date=duty.date,
        headcount=duty.headcount,
        duration_days=duty.duration_days,
        difficulty=duty.difficulty,
        created_at=duty.created_at,
        tags=[TagOut.model_validate(t) for t in duty.tags],
        assignment_count=assignment_count,
    )


@router.post("", response_model=DutyOut, status_code=201)
async def create_duty(data: DutyCreate, db: AsyncSession = Depends(get_db)):
    duty = Duty(name=data.name, date=data.date, headcount=data.headcount, duration_days=data.duration_days, difficulty=data.difficulty)
    db.add(duty)
    await db.commit()
    await db.refresh(duty, ["tags"])
    return duty


@router.put("/{duty_id}", response_model=DutyOut)
async def update_duty(duty_id: int, data: DutyUpdate, db: AsyncSession = Depends(get_db)):
    duty = await db.get(Duty, duty_id, options=[selectinload(Duty.tags)])
    if not duty:
        raise HTTPException(404, "Duty not found")
    if data.name is not None:
        duty.name = data.name
    if data.date is not None:
        duty.date = data.date
    if data.headcount is not None:
        duty.headcount = data.headcount
    if data.duration_days is not None:
        duty.duration_days = data.duration_days
    if data.difficulty is not None:
        duty.difficulty = data.difficulty
    await db.commit()
    await db.refresh(duty, ["tags"])
    return duty


@router.delete("/{duty_id}", status_code=204)
async def delete_duty(duty_id: int, db: AsyncSession = Depends(get_db)):
    duty = await db.get(Duty, duty_id)
    if not duty:
        raise HTTPException(404, "Duty not found")
    await db.delete(duty)
    await db.commit()


@router.post("/{duty_id}/tags", response_model=DutyOut)
async def add_duty_tag(duty_id: int, data: TagOut, db: AsyncSession = Depends(get_db)):
    duty = await db.get(Duty, duty_id, options=[selectinload(Duty.tags)])
    if not duty:
        raise HTTPException(404, "Duty not found")
    tag = await db.get(Tag, data.id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    if tag not in duty.tags:
        duty.tags.append(tag)
        await db.commit()
        await db.refresh(duty, ["tags"])
    return duty


@router.delete("/{duty_id}/tags/{tag_id}", response_model=DutyOut)
async def remove_duty_tag(duty_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    duty = await db.get(Duty, duty_id, options=[selectinload(Duty.tags)])
    if not duty:
        raise HTTPException(404, "Duty not found")
    duty.tags = [t for t in duty.tags if t.id != tag_id]
    await db.commit()
    await db.refresh(duty, ["tags"])
    return duty
