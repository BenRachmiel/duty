import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Assignment, Duty, Person, Tag, person_tag
from app.schemas import PaginatedResponse, PersonCreate, PersonListOut, PersonOut, PersonUpdate, TagOut

router = APIRouter(prefix="/people", tags=["people"])


def _points_subquery(count_since: date | None = None):
    sq = (
        select(func.coalesce(func.sum(Duty.duration_days * Duty.difficulty), 0.0))
        .select_from(Assignment)
        .join(Duty, Assignment.duty_id == Duty.id)
        .where(Assignment.person_id == Person.id)
    )
    if count_since:
        sq = sq.where(Duty.date >= count_since)
    return sq.correlate(Person).scalar_subquery().label("points")


@router.get("", response_model=PaginatedResponse[PersonListOut])
async def list_people(
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
    tag_id: int | None = None,
    count_since: date | None = None,
    sort_by: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    base = select(Person)
    if q:
        base = base.where(Person.name.ilike(f"%{q}%"))
    if tag_id is not None:
        base = base.where(Person.id.in_(select(person_tag.c.person_id).where(person_tag.c.tag_id == tag_id)))

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    pts = _points_subquery(count_since)

    if sort_by == "points_asc":
        order = pts.asc()
    elif sort_by == "points_desc":
        order = pts.desc()
    else:
        order = Person.name

    query = (
        base.options(selectinload(Person.tags))
        .add_columns(pts)
        .order_by(order)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = []
    for person, points in result.all():
        items.append(PersonListOut(
            id=person.id,
            name=person.name,
            external_id=person.external_id,
            created_at=person.created_at,
            tags=[TagOut.model_validate(t) for t in person.tags],
            points=float(points),
        ))
    return PaginatedResponse(items=items, total=total)


@router.get("/{person_id}", response_model=PersonListOut)
async def get_person(
    person_id: int,
    count_since: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    pts = _points_subquery(count_since)
    result = await db.execute(
        select(Person, pts)
        .options(selectinload(Person.tags))
        .where(Person.id == person_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Person not found")
    person, points = row
    return PersonListOut(
        id=person.id,
        name=person.name,
        external_id=person.external_id,
        created_at=person.created_at,
        tags=[TagOut.model_validate(t) for t in person.tags],
        points=float(points),
    )


@router.post("", response_model=PersonOut, status_code=201)
async def create_person(data: PersonCreate, db: AsyncSession = Depends(get_db)):
    person = Person(name=data.name, external_id=data.external_id)
    db.add(person)
    await db.commit()
    await db.refresh(person, ["tags"])
    return person


@router.put("/{person_id}", response_model=PersonOut)
async def update_person(person_id: int, data: PersonUpdate, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id, options=[selectinload(Person.tags)])
    if not person:
        raise HTTPException(404, "Person not found")
    if data.name is not None:
        person.name = data.name
    if data.external_id is not None:
        person.external_id = data.external_id
    await db.commit()
    await db.refresh(person, ["tags"])
    return person


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    await db.delete(person)
    await db.commit()


@router.post("/{person_id}/tags", response_model=PersonOut)
async def add_person_tag(person_id: int, data: TagOut, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id, options=[selectinload(Person.tags)])
    if not person:
        raise HTTPException(404, "Person not found")
    tag = await db.get(Tag, data.id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    if tag not in person.tags:
        person.tags.append(tag)
        await db.commit()
        await db.refresh(person, ["tags"])
    return person


@router.delete("/{person_id}/tags/{tag_id}", response_model=PersonOut)
async def remove_person_tag(person_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id, options=[selectinload(Person.tags)])
    if not person:
        raise HTTPException(404, "Person not found")
    person.tags = [t for t in person.tags if t.id != tag_id]
    await db.commit()
    await db.refresh(person, ["tags"])
    return person


@router.post("/import", response_model=list[PersonOut])
async def import_csv(file: UploadFile, db: AsyncSession = Depends(get_db)):
    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    created = []
    for row in reader:
        name = row.get("name", "").strip()
        if not name:
            continue
        row_tags = []
        tags_str = row.get("tags", "")
        if tags_str:
            for tag_name in (t.strip() for t in tags_str.split(",") if t.strip()):
                result = await db.execute(select(Tag).where(Tag.name == tag_name))
                tag = result.scalar_one_or_none()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.add(tag)
                    await db.flush()
                row_tags.append(tag)
        person = Person(name=name, external_id=row.get("external_id", "").strip() or None, tags=row_tags)
        db.add(person)
        created.append(person)
    await db.commit()
    result = await db.execute(select(Person).options(selectinload(Person.tags)).order_by(Person.name))
    return result.scalars().all()
