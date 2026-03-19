import datetime as _dt
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Assignment, Duty, Person
from app.schemas import (
    DailyWorkload,
    PointsBucket,
    StatsResponse,
)

router = APIRouter(prefix="/stats", tags=["stats"])

NUM_BUCKETS = 10
TOP_N = 10


@router.get("", response_model=StatsResponse)
async def get_stats(
    date_from: _dt.date | None = None,
    date_to: _dt.date | None = None,
    db: AsyncSession = Depends(get_db),
):
    today = _dt.date.today()
    if date_from is None:
        date_from = today - _dt.timedelta(days=30)
    if date_to is None:
        date_to = today + _dt.timedelta(days=30)

    # A duty is "active" in the range if its span overlaps [date_from, date_to]:
    #   duty.date <= date_to AND duty.date + duration_days - 1 >= date_from
    # Using julianday for SQLite date arithmetic.
    def _active_in_range():
        return [
            Duty.date <= date_to,
            func.julianday(Duty.date) + Duty.duration_days - 1 >= func.julianday(date_from),
        ]

    # 1. Per-person points in date range
    points_q = (
        select(
            Assignment.person_id,
            func.sum(Duty.duration_days * Duty.difficulty).label("points"),
            func.count(Assignment.id).label("cnt"),
        )
        .join(Duty, Assignment.duty_id == Duty.id)
        .where(*_active_in_range())
        .group_by(Assignment.person_id)
    )
    points_result = await db.execute(points_q)
    person_stats: dict[int, tuple[float, int]] = {}
    for row in points_result:
        person_stats[row.person_id] = (float(row.points), row.cnt)

    # 2. Total personnel
    total_personnel = (await db.execute(select(func.count(Person.id)))).scalar_one()

    # KPIs from person_stats
    total_points = sum(pts for pts, _ in person_stats.values())
    active_personnel = len(person_stats)

    # 3. Fill rate: total slots vs filled assignments in range
    slots_q = (
        select(func.coalesce(func.sum(Duty.headcount), 0))
        .where(*_active_in_range())
    )
    total_slots = (await db.execute(slots_q)).scalar_one()

    filled_q = (
        select(func.count(Assignment.id))
        .join(Duty, Assignment.duty_id == Duty.id)
        .where(*_active_in_range())
    )
    total_filled = (await db.execute(filled_q)).scalar_one()

    fill_rate = total_filled / total_slots if total_slots > 0 else 0.0

    # 4. Upcoming unfilled: duties in next 7 days with assignment_count < headcount
    upcoming_start = today
    upcoming_end = today + _dt.timedelta(days=7)
    asgn_count_sub = (
        select(
            Assignment.duty_id,
            func.count(Assignment.id).label("asgn_cnt"),
        )
        .group_by(Assignment.duty_id)
        .subquery()
    )
    upcoming_q = (
        select(func.count())
        .select_from(Duty)
        .outerjoin(asgn_count_sub, Duty.id == asgn_count_sub.c.duty_id)
        .where(
            Duty.date <= upcoming_end,
            func.julianday(Duty.date) + Duty.duration_days - 1 >= func.julianday(upcoming_start),
            func.coalesce(asgn_count_sub.c.asgn_cnt, 0) < Duty.headcount,
        )
    )
    upcoming_unfilled = (await db.execute(upcoming_q)).scalar_one()

    # 5. Daily workload: duties in range spread across duration_days
    duties_in_range = (
        await db.execute(
            select(Duty.id, Duty.date, Duty.headcount, Duty.duration_days)
            .where(*_active_in_range())
        )
    ).all()

    duty_ids = [d.id for d in duties_in_range]
    asgn_per_duty: dict[int, int] = defaultdict(int)
    if duty_ids:
        asgn_counts = await db.execute(
            select(Assignment.duty_id, func.count(Assignment.id))
            .where(Assignment.duty_id.in_(duty_ids))
            .group_by(Assignment.duty_id)
        )
        for duty_id, cnt in asgn_counts:
            asgn_per_duty[duty_id] = cnt

    daily_demand: dict[_dt.date, int] = defaultdict(int)
    daily_filled: dict[_dt.date, int] = defaultdict(int)
    for d in duties_in_range:
        filled = asgn_per_duty.get(d.id, 0)
        for offset in range(d.duration_days):
            day = d.date + _dt.timedelta(days=offset)
            if date_from <= day <= date_to:
                daily_demand[day] += d.headcount
                daily_filled[day] += filled

    all_days = set(daily_demand.keys()) | set(daily_filled.keys())
    daily_workload = sorted(
        [
            DailyWorkload(date=day, demand=daily_demand.get(day, 0), filled=daily_filled.get(day, 0))
            for day in all_days
        ],
        key=lambda w: w.date,
    )

    # 6. Points distribution — bucket into NUM_BUCKETS equal-width bins
    # Include 0-point people for full population visibility
    zero_count = total_personnel - len(person_stats)
    all_points = [pts for pts, _ in person_stats.values()] + [0.0] * zero_count
    points_distribution = _bucket_points(all_points)

    return StatsResponse(
        total_points=total_points,
        fill_rate=fill_rate,
        active_personnel=active_personnel,
        total_personnel=total_personnel,
        upcoming_unfilled=upcoming_unfilled,
        points_distribution=points_distribution,
        daily_workload=daily_workload,
        top_loaded=[],
        bottom_loaded=[],
    )


def _bucket_points(values: list[float]) -> list[PointsBucket]:
    if not values:
        return []

    min_val = min(values)
    max_val = max(values)

    if min_val == max_val:
        return [PointsBucket(range_min=min_val, range_max=max_val, count=len(values))]

    width = (max_val - min_val) / NUM_BUCKETS
    buckets: list[PointsBucket] = []
    for i in range(NUM_BUCKETS):
        lo = min_val + i * width
        hi = min_val + (i + 1) * width
        count = sum(1 for v in values if (lo <= v < hi) or (i == NUM_BUCKETS - 1 and v == hi))
        buckets.append(PointsBucket(range_min=round(lo, 2), range_max=round(hi, 2), count=count))
    return buckets
