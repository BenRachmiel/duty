"""Scale test for solver with 500 people x 195 duties."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.services.solver import solve_assignments


@dataclass
class FakeTag:
    id: int
    name: str = ""


@dataclass
class FakePerson:
    id: int
    name: str = ""
    tags: list = field(default_factory=list)


@dataclass
class FakeDuty:
    id: int
    name: str = ""
    date: object = None
    headcount: int = 1
    duration_days: int = 1
    difficulty: float = 1.0
    tags: list = field(default_factory=list)
    assignments: list = field(default_factory=list)


@dataclass
class FakeRule:
    id: int
    name: str = ""
    person_tag_id: int | None = None
    duty_tag_id: int | None = None
    rule_type: str = "deny"
    priority: int = 0
    cooldown_days: int | None = None
    cooldown_duty_tag_id: int | None = None


def test_solver_500_people_no_rules():
    """500 people, 195 duties across 60 days, no rules — should produce proposals."""
    people = [FakePerson(id=i, name=f"P{i}") for i in range(500)]
    duties = [
        FakeDuty(
            id=i,
            name=f"D{i}",
            date=date(2026, 3, 19) + timedelta(days=i % 60),
            headcount=3,
        )
        for i in range(195)
    ]

    result = solve_assignments(people, duties, [], [])
    # 195 duties * 3 headcount = 585 total slots
    assert len(result.proposed) == 585


def test_solver_500_people_with_allow_rules():
    """Simulate seed-like scenario with allow rules reducing eligibility."""
    cert_tag = FakeTag(id=1, name="firing-range-certified")
    fr_tag = FakeTag(id=2, name="firing-range")
    guard_tag = FakeTag(id=3, name="guard")

    # 100 people have the cert, 400 don't
    people = []
    for i in range(500):
        tags = [cert_tag] if i < 100 else []
        people.append(FakePerson(id=i, name=f"P{i}", tags=tags))

    duties = []
    for i in range(195):
        d = date(2026, 3, 19) + timedelta(days=i % 60)
        if i < 20:
            duties.append(FakeDuty(id=i, name=f"FR{i}", date=d, headcount=2, tags=[fr_tag]))
        else:
            duties.append(FakeDuty(id=i, name=f"G{i}", date=d, headcount=3, tags=[guard_tag]))

    rules = [
        FakeRule(id=1, name="FR requires cert", person_tag_id=1, duty_tag_id=2, rule_type="allow"),
    ]

    result = solve_assignments(people, duties, rules, [])
    # 20 FR duties * 2 + 175 guard duties * 3 = 40 + 525 = 565
    assert len(result.proposed) == 565
