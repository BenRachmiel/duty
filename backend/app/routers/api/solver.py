from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Assignment, Duty, Person, Rule
from app.schemas import (
    ExcludedPerson,
    ExclusionReason,
    SolverAcceptRequest,
    SolverRunRequest,
    SolverRunResponse,
    UnfilledDuty,
)
from app.services.solver import solve_assignments

router = APIRouter(prefix="/solver", tags=["solver"])


@router.post("/run", response_model=SolverRunResponse)
async def run_solver(body: SolverRunRequest = SolverRunRequest(), db: AsyncSession = Depends(get_db)):

    people_result = await db.execute(select(Person).options(selectinload(Person.tags)))
    people = list(people_result.scalars().all())

    duties_result = await db.execute(
        select(Duty).options(selectinload(Duty.tags), selectinload(Duty.assignments))
    )
    all_duties = duties_result.scalars().all()
    duties = [d for d in all_duties if len(d.assignments) < d.headcount]

    rules_result = await db.execute(
        select(Rule).options(
            selectinload(Rule.person_tag),
            selectinload(Rule.duty_tag),
            selectinload(Rule.cooldown_duty_tag),
        )
    )
    rules = list(rules_result.scalars().all())

    assignments_result = await db.execute(
        select(Assignment).options(
            selectinload(Assignment.duty).selectinload(Duty.tags),
        )
    )
    existing_assignments = list(assignments_result.scalars().all())

    result = solve_assignments(
        people, duties, rules, existing_assignments,
        body.count_since, body.algorithm, body.iterations,
    )

    # Build unfilled list with exclusion reasons
    unfilled: list[UnfilledDuty] = []
    for duty in duties:
        already = len(duty.assignments)
        proposed_for_duty = sum(1 for _, d in result.proposed if d.id == duty.id)
        slots_needed = duty.headcount - already - proposed_for_duty
        if slots_needed <= 0:
            continue

        excluded_people: list[ExcludedPerson] = []
        for person in people:
            reasons = result.exclusions.get((person.id, duty.id), [])
            if reasons:
                excluded_people.append(ExcludedPerson(
                    person=person,
                    reasons=[ExclusionReason(rule_name=r.rule_name, rule_type=r.rule_type, reason=r.reason) for r in reasons],
                ))

        unfilled.append(UnfilledDuty(
            duty=duty,
            excluded_people=excluded_people,
            slots_needed=slots_needed,
        ))

    return SolverRunResponse(
        proposed=[{"person": p, "duty": d} for p, d in result.proposed],
        unfilled=unfilled,
        duty_points=result.duty_points,
    )


@router.post("/accept", status_code=201)
async def accept_solver(data: SolverAcceptRequest, db: AsyncSession = Depends(get_db)):
    created = []
    for item in data.assignments:
        assignment = Assignment(person_id=item.person_id, duty_id=item.duty_id, is_manual=False)
        db.add(assignment)
        created.append(assignment)
    await db.commit()
    return {"accepted": len(created)}
