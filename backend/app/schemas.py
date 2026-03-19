import datetime as _dt
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.models import RuleType


class SolverAlgorithm(StrEnum):
    greedy = "greedy"
    montecarlo = "montecarlo"
    annealing = "annealing"

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int


# Tags
class TagCreate(BaseModel):
    name: str
    color: str | None = None


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None


# People
class PersonCreate(BaseModel):
    name: str
    external_id: str | None = None


class PersonUpdate(BaseModel):
    name: str | None = None
    external_id: str | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    external_id: str | None
    created_at: _dt.datetime
    tags: list[TagOut]


class PersonListOut(PersonOut):
    points: float = 0.0


# Duties
class DutyCreate(BaseModel):
    name: str
    date: _dt.date
    headcount: int = 1
    duration_days: int = 1
    difficulty: float = 1.0


class DutyUpdate(BaseModel):
    name: str | None = None
    date: _dt.date | None = None
    headcount: int | None = None
    duration_days: int | None = None
    difficulty: float | None = None


class DutyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: _dt.date
    headcount: int
    duration_days: int
    difficulty: float
    created_at: _dt.datetime
    tags: list[TagOut]


class DutyDetailOut(DutyOut):
    assignment_count: int = 0


# Rules
class RuleCreate(BaseModel):
    name: str
    person_tag_id: int | None = None
    duty_tag_id: int | None = None
    rule_type: RuleType
    priority: int = 0
    cooldown_days: int | None = None
    cooldown_duty_tag_id: int | None = None


class RuleUpdate(BaseModel):
    name: str | None = None
    person_tag_id: int | None = None
    duty_tag_id: int | None = None
    rule_type: RuleType | None = None
    priority: int | None = None
    cooldown_days: int | None = None
    cooldown_duty_tag_id: int | None = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    person_tag_id: int | None
    duty_tag_id: int | None
    rule_type: RuleType
    priority: int
    cooldown_days: int | None
    cooldown_duty_tag_id: int | None
    person_tag: TagOut | None
    duty_tag: TagOut | None
    cooldown_duty_tag: TagOut | None


# Assignments
class AssignmentCreate(BaseModel):
    person_id: int
    duty_id: int


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    duty_id: int
    assigned_at: _dt.datetime
    is_manual: bool
    person: PersonOut
    duty: DutyOut


# Solver
class ProposedAssignment(BaseModel):
    person: PersonOut
    duty: DutyOut


class ExclusionReason(BaseModel):
    rule_name: str
    rule_type: str
    reason: str


class ExcludedPerson(BaseModel):
    person: PersonOut
    reasons: list[ExclusionReason]


class UnfilledDuty(BaseModel):
    duty: DutyOut
    excluded_people: list[ExcludedPerson]
    slots_needed: int


class SolverRunRequest(BaseModel):
    count_since: _dt.date | None = None
    algorithm: SolverAlgorithm = SolverAlgorithm.greedy
    iterations: int = 100


class SolverAcceptRequest(BaseModel):
    assignments: list[AssignmentCreate]


class SolverRunResponse(BaseModel):
    proposed: list[ProposedAssignment]
    unfilled: list[UnfilledDuty]
    duty_points: dict[int, float]


# Tag summary
class TagSummaryOut(BaseModel):
    id: int
    name: str
    color: str | None
    people_count: int
    duties_count: int
    rules: list[RuleOut]


# Stats
class PointsBucket(BaseModel):
    range_min: float
    range_max: float
    count: int


class DailyWorkload(BaseModel):
    date: _dt.date
    demand: int
    filled: int


class PersonWorkload(BaseModel):
    person_id: int
    name: str
    tags: list[TagOut]
    points: float
    assignment_count: int


class StatsResponse(BaseModel):
    total_points: float
    fill_rate: float
    active_personnel: int
    total_personnel: int
    upcoming_unfilled: int
    points_distribution: list[PointsBucket]
    daily_workload: list[DailyWorkload]
    top_loaded: list[PersonWorkload]
    bottom_loaded: list[PersonWorkload]
