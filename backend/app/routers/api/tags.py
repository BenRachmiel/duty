from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Rule, Tag, duty_tag, person_tag
from app.schemas import RuleOut, TagCreate, TagOut, TagSummaryOut

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).order_by(Tag.name))
    return result.scalars().all()


@router.get("/{tag_id}/summary", response_model=TagSummaryOut)
async def get_tag_summary(tag_id: int, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    people_count = (await db.execute(
        select(func.count()).where(person_tag.c.tag_id == tag_id)
    )).scalar_one()

    duties_count = (await db.execute(
        select(func.count()).where(duty_tag.c.tag_id == tag_id)
    )).scalar_one()

    rules_result = await db.execute(
        select(Rule)
        .options(selectinload(Rule.person_tag), selectinload(Rule.duty_tag), selectinload(Rule.cooldown_duty_tag))
        .where(or_(
            Rule.person_tag_id == tag_id,
            Rule.duty_tag_id == tag_id,
            Rule.cooldown_duty_tag_id == tag_id,
        ))
        .order_by(Rule.name)
    )
    rules = [RuleOut.model_validate(r) for r in rules_result.scalars().all()]

    return TagSummaryOut(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        people_count=people_count,
        duties_count=duties_count,
        rules=rules,
    )


@router.post("", response_model=TagOut, status_code=201)
async def create_tag(data: TagCreate, db: AsyncSession = Depends(get_db)):
    tag = Tag(name=data.name, color=data.color)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    await db.delete(tag)
    await db.commit()
