from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Assignment, Duty, Person
from app.schemas import AssignmentCreate, AssignmentOut, PaginatedResponse

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=PaginatedResponse[AssignmentOut])
async def list_assignments(
    date_from: date | None = None,
    date_to: date | None = None,
    person_id: int | None = None,
    duty_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    base = select(Assignment).join(Duty).join(Person)
    if date_from:
        base = base.where(Duty.date >= date_from)
    if date_to:
        base = base.where(Duty.date <= date_to)
    if person_id is not None:
        base = base.where(Assignment.person_id == person_id)
    if duty_id is not None:
        base = base.where(Assignment.duty_id == duty_id)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    query = (
        base.options(
            selectinload(Assignment.person).selectinload(Person.tags),
            selectinload(Assignment.duty).selectinload(Duty.tags),
        )
        .order_by(Duty.date, Person.name)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    return PaginatedResponse(items=result.scalars().all(), total=total)


@router.post("", response_model=AssignmentOut, status_code=201)
async def create_assignment(data: AssignmentCreate, db: AsyncSession = Depends(get_db)):
    assignment = Assignment(person_id=data.person_id, duty_id=data.duty_id, is_manual=True)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment, ["person", "duty"])
    return assignment


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: int, db: AsyncSession = Depends(get_db)):
    assignment = await db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    await db.delete(assignment)
    await db.commit()
