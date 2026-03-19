from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Rule
from app.schemas import RuleCreate, RuleOut, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
async def list_rules(tag_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = (
        select(Rule)
        .options(selectinload(Rule.person_tag), selectinload(Rule.duty_tag), selectinload(Rule.cooldown_duty_tag))
    )
    if tag_id is not None:
        query = query.where(or_(
            Rule.person_tag_id == tag_id,
            Rule.duty_tag_id == tag_id,
            Rule.cooldown_duty_tag_id == tag_id,
        ))
    query = query.order_by(Rule.priority.desc(), Rule.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=RuleOut, status_code=201)
async def create_rule(data: RuleCreate, db: AsyncSession = Depends(get_db)):
    rule = Rule(
        name=data.name,
        rule_type=data.rule_type,
        person_tag_id=data.person_tag_id,
        duty_tag_id=data.duty_tag_id,
        priority=data.priority,
        cooldown_days=data.cooldown_days,
        cooldown_duty_tag_id=data.cooldown_duty_tag_id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule, ["person_tag", "duty_tag", "cooldown_duty_tag"])
    return rule


@router.put("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: int, data: RuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(
        Rule, rule_id,
        options=[selectinload(Rule.person_tag), selectinload(Rule.duty_tag), selectinload(Rule.cooldown_duty_tag)],
    )
    if not rule:
        raise HTTPException(404, "Rule not found")
    if data.name is not None:
        rule.name = data.name
    if data.rule_type is not None:
        rule.rule_type = data.rule_type
    if data.person_tag_id is not None:
        rule.person_tag_id = data.person_tag_id
    if data.duty_tag_id is not None:
        rule.duty_tag_id = data.duty_tag_id
    if data.priority is not None:
        rule.priority = data.priority
    if data.cooldown_days is not None:
        rule.cooldown_days = data.cooldown_days
    if data.cooldown_duty_tag_id is not None:
        rule.cooldown_duty_tag_id = data.cooldown_duty_tag_id
    await db.commit()
    await db.refresh(rule, ["person_tag", "duty_tag", "cooldown_duty_tag"])
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
