from dataclasses import dataclass, field
from datetime import date

from app.models import RuleType
from app.services.solver import SolverResult, solve_assignments


# Plain data objects that mimic the SA models for solver testing — avoids SA instrumentation.
@dataclass
class FakeTag:
    id: int
    name: str
    color: str | None = None


@dataclass
class FakePerson:
    id: int
    name: str
    tags: list[FakeTag] = field(default_factory=list)
    external_id: str | None = None
    assignments: list = field(default_factory=list)


@dataclass
class FakeDuty:
    id: int
    name: str
    date: date
    headcount: int = 1
    duration_days: int = 1
    difficulty: float = 1.0
    tags: list[FakeTag] = field(default_factory=list)
    assignments: list = field(default_factory=list)


@dataclass
class FakeRule:
    id: int
    name: str
    rule_type: str
    person_tag_id: int | None = None
    duty_tag_id: int | None = None
    priority: int = 0
    cooldown_days: int | None = None
    cooldown_duty_tag_id: int | None = None
    person_tag: FakeTag | None = None
    duty_tag: FakeTag | None = None
    cooldown_duty_tag: FakeTag | None = None


@dataclass
class FakeAssignment:
    person_id: int
    duty: FakeDuty
    is_manual: bool = False


def test_basic_assignment():
    """Solver assigns people to duties and returns SolverResult."""
    people = [FakePerson(1, "Alice"), FakePerson(2, "Bob")]
    duties = [FakeDuty(1, "Guard A", date(2026, 3, 20))]
    result = solve_assignments(people, duties, [], [])
    assert isinstance(result, SolverResult)
    assert len(result.proposed) == 1
    assert result.proposed[0][1].id == 1


def test_headcount():
    """Solver fills headcount correctly."""
    people = [FakePerson(i, f"P{i}") for i in range(1, 5)]
    duties = [FakeDuty(1, "Guard", date(2026, 3, 20), headcount=3)]
    result = solve_assignments(people, duties, [], [])
    assert len(result.proposed) == 3


def test_deny_rule():
    """Deny rule excludes tagged people from tagged duties."""
    night_tag = FakeTag(1, "night")
    exempt_tag = FakeTag(2, "exempt:night")

    alice = FakePerson(1, "Alice", tags=[exempt_tag])
    bob = FakePerson(2, "Bob")

    duty = FakeDuty(1, "Night Watch", date(2026, 3, 20), tags=[night_tag])
    rule = FakeRule(1, "No exempt at night", RuleType.deny, person_tag_id=2, duty_tag_id=1)

    result = solve_assignments([alice, bob], [duty], [rule], [])
    assert len(result.proposed) == 1
    assert result.proposed[0][0].name == "Bob"


def test_deny_rule_exclusion_reason():
    """Deny rule populates exclusion reason with rule name."""
    night_tag = FakeTag(1, "night")
    exempt_tag = FakeTag(2, "exempt:night")

    alice = FakePerson(1, "Alice", tags=[exempt_tag])
    duty = FakeDuty(1, "Night Watch", date(2026, 3, 20), tags=[night_tag])
    rule = FakeRule(1, "No exempt at night", RuleType.deny, person_tag_id=2, duty_tag_id=1)

    result = solve_assignments([alice], [duty], [rule], [])
    assert len(result.proposed) == 0
    exclusions = result.exclusions[(1, 1)]
    assert len(exclusions) == 1
    assert exclusions[0].rule_name == "No exempt at night"
    assert exclusions[0].rule_type == "deny"
    assert "Denied by" in exclusions[0].reason


def test_allow_rule():
    """Allow rule creates whitelist — only matching people eligible."""
    sgt_tag = FakeTag(1, "rank:sergeant")
    officer_tag = FakeTag(2, "officer-duty")

    alice = FakePerson(1, "Alice", tags=[sgt_tag])
    bob = FakePerson(2, "Bob")

    duty = FakeDuty(1, "Officer Duty", date(2026, 3, 20), tags=[officer_tag])
    rule = FakeRule(1, "Only sergeants", RuleType.allow, person_tag_id=1, duty_tag_id=2)

    result = solve_assignments([alice, bob], [duty], [rule], [])
    assert len(result.proposed) == 1
    assert result.proposed[0][0].name == "Alice"


def test_allow_rule_exclusion_reason():
    """Allow rule populates exclusion reason for excluded person."""
    sgt_tag = FakeTag(1, "rank:sergeant")
    officer_tag = FakeTag(2, "officer-duty")

    bob = FakePerson(2, "Bob")
    duty = FakeDuty(1, "Officer Duty", date(2026, 3, 20), tags=[officer_tag])
    rule = FakeRule(1, "Only sergeants", RuleType.allow, person_tag_id=1, duty_tag_id=2)

    result = solve_assignments([bob], [duty], [rule], [])
    exclusions = result.exclusions[(2, 1)]
    assert len(exclusions) == 1
    assert exclusions[0].rule_name == "Only sergeants"
    assert exclusions[0].rule_type == "allow"
    assert "allow list" in exclusions[0].reason


def test_cooldown_rule():
    """Cooldown prevents assignment within cooldown_days of previous assignment."""
    weekend_tag = FakeTag(1, "weekend")

    alice = FakePerson(1, "Alice")
    bob = FakePerson(2, "Bob")

    past_duty = FakeDuty(100, "Past Weekend", date(2026, 3, 18), tags=[weekend_tag])
    past_assignment = FakeAssignment(1, past_duty)

    new_duty = FakeDuty(1, "Weekend Duty", date(2026, 3, 20), tags=[weekend_tag])
    rule = FakeRule(1, "Weekend cooldown", RuleType.cooldown, duty_tag_id=1, cooldown_days=7, cooldown_duty_tag_id=1)

    result = solve_assignments([alice, bob], [new_duty], [rule], [past_assignment])
    assert len(result.proposed) == 1
    assert result.proposed[0][0].name == "Bob"


def test_cooldown_exclusion_reason():
    """Cooldown populates exclusion reason with remaining days."""
    weekend_tag = FakeTag(1, "weekend")
    alice = FakePerson(1, "Alice")

    past_duty = FakeDuty(100, "Past Weekend", date(2026, 3, 18), tags=[weekend_tag])
    past_assignment = FakeAssignment(1, past_duty)

    new_duty = FakeDuty(1, "Weekend Duty", date(2026, 3, 20), tags=[weekend_tag])
    rule = FakeRule(1, "Weekend cooldown", RuleType.cooldown, duty_tag_id=1, cooldown_days=7, cooldown_duty_tag_id=1)

    result = solve_assignments([alice], [new_duty], [rule], [past_assignment])
    exclusions = result.exclusions[(1, 1)]
    assert len(exclusions) == 1
    assert exclusions[0].rule_type == "cooldown"
    assert "5 days remain" in exclusions[0].reason


def test_same_date_constraint():
    """Person can't be assigned to two duties on the same date."""
    alice = FakePerson(1, "Alice")
    d1 = FakeDuty(1, "Guard A", date(2026, 3, 20))
    d2 = FakeDuty(2, "Guard B", date(2026, 3, 20))

    result = solve_assignments([alice], [d1, d2], [], [])
    assert len(result.proposed) == 1


def test_fairness():
    """Solver distributes duties fairly across people."""
    people = [FakePerson(i, f"P{i}") for i in range(1, 5)]
    duties = [FakeDuty(i, f"D{i}", date(2026, 3, 20 + i % 10)) for i in range(1, 5)]

    result = solve_assignments(people, duties, [], [])
    assert len(result.proposed) == 4
    assigned_people = {r[0].id for r in result.proposed}
    assert len(assigned_people) == 4


def test_empty_inputs():
    """Solver handles empty inputs gracefully."""
    result = solve_assignments([], [], [], [])
    assert isinstance(result, SolverResult)
    assert result.proposed == []

    result = solve_assignments([FakePerson(1, "A")], [], [], [])
    assert result.proposed == []

    result = solve_assignments([], [FakeDuty(1, "D", date(2026, 3, 20))], [], [])
    assert result.proposed == []


def test_duty_points_basic():
    """duty_points sums duration_days * difficulty from historical assignments."""
    alice = FakePerson(1, "Alice")
    bob = FakePerson(2, "Bob")

    past_duty = FakeDuty(100, "Long Duty", date(2026, 3, 10), duration_days=3, difficulty=2.0)
    past_assignment = FakeAssignment(1, past_duty)

    new_duty = FakeDuty(1, "Guard", date(2026, 3, 25))
    result = solve_assignments([alice, bob], [new_duty], [], [past_assignment])

    assert result.duty_points[1] == 6.0  # 3 * 2.0
    assert result.duty_points[2] == 0.0


def test_duty_points_count_since():
    """count_since filters which assignments count toward duty_points."""
    alice = FakePerson(1, "Alice")

    old_duty = FakeDuty(100, "Old Duty", date(2026, 1, 1), duration_days=5)
    recent_duty = FakeDuty(101, "Recent Duty", date(2026, 3, 10), duration_days=2)
    old_assignment = FakeAssignment(1, old_duty)
    recent_assignment = FakeAssignment(1, recent_duty)

    new_duty = FakeDuty(1, "Guard", date(2026, 3, 25))
    result = solve_assignments([alice], [new_duty], [], [old_assignment, recent_assignment], count_since=date(2026, 3, 1))

    assert result.duty_points[1] == 2.0  # only recent_duty counts


def test_fairness_with_points():
    """Solver balances by points (duration*difficulty), not raw count."""
    people = [FakePerson(i, f"P{i}") for i in range(1, 3)]

    # P1 already did a heavy duty (6 points)
    past_duty = FakeDuty(100, "Heavy", date(2026, 3, 10), duration_days=3, difficulty=2.0)
    past_assignment = FakeAssignment(1, past_duty)

    # Two new duties on different dates, 1 point each
    d1 = FakeDuty(1, "Light A", date(2026, 3, 25))
    d2 = FakeDuty(2, "Light B", date(2026, 3, 26))

    result = solve_assignments(people, [d1, d2], [], [past_assignment])
    assert len(result.proposed) == 2

    # P2 should get both since P1 already has 6 points — giving P2 both (2 pts)
    # is fairer than splitting (P1=7, P2=1)
    p2_assignments = [p for p, _ in result.proposed if p.id == 2]
    assert len(p2_assignments) == 2


def test_fairness_many_people():
    """With many people and few slots, solver spreads across people, not concentrating."""
    people = [FakePerson(i, f"P{i}") for i in range(1, 21)]  # 20 people
    # 10 duties on different dates, headcount 1 each
    duties = [FakeDuty(i, f"D{i}", date(2026, 3, i)) for i in range(1, 11)]

    result = solve_assignments(people, duties, [], [])
    assert len(result.proposed) == 10

    # Each person should get at most 1 duty (10 slots / 20 people)
    from collections import Counter
    counts = Counter(p.id for p, _ in result.proposed)
    assert max(counts.values()) == 1


# --- Algorithm variants ---


def test_montecarlo_basic():
    """Monte carlo runs multiple greedy passes and returns a valid result."""
    people = [FakePerson(i, f"P{i}") for i in range(1, 5)]
    duties = [FakeDuty(i, f"D{i}", date(2026, 3, 20 + i % 10)) for i in range(1, 5)]

    result = solve_assignments(people, duties, [], [], algorithm="montecarlo", iterations=5)
    assert len(result.proposed) == 4
    assigned_people = {p.id for p, _ in result.proposed}
    assert len(assigned_people) == 4


def test_montecarlo_respects_rules():
    """Monte carlo respects deny rules."""
    tag = FakeTag(1, "exempt")
    p1 = FakePerson(1, "Alice", tags=[tag])
    p2 = FakePerson(2, "Bob")
    duty = FakeDuty(1, "Night Watch", date(2026, 3, 20), tags=[tag])
    deny = FakeRule(1, "No exempt", RuleType.deny, person_tag_id=1, duty_tag_id=1)

    result = solve_assignments([p1, p2], [duty], [deny], [], algorithm="montecarlo", iterations=5)
    assert len(result.proposed) == 1
    assert result.proposed[0][0].id == 2


def test_annealing_basic():
    """Annealing produces a valid assignment."""
    people = [FakePerson(i, f"P{i}") for i in range(1, 5)]
    duties = [FakeDuty(i, f"D{i}", date(2026, 3, 20 + i % 10)) for i in range(1, 5)]

    result = solve_assignments(people, duties, [], [], algorithm="annealing", iterations=100)
    assert len(result.proposed) == 4
    assigned_people = {p.id for p, _ in result.proposed}
    assert len(assigned_people) == 4


def test_annealing_respects_rules():
    """Annealing respects deny rules."""
    tag = FakeTag(1, "exempt")
    p1 = FakePerson(1, "Alice", tags=[tag])
    p2 = FakePerson(2, "Bob")
    duty = FakeDuty(1, "Night Watch", date(2026, 3, 20), tags=[tag])
    deny = FakeRule(1, "No exempt", RuleType.deny, person_tag_id=1, duty_tag_id=1)

    result = solve_assignments([p1, p2], [duty], [deny], [], algorithm="annealing", iterations=100)
    assert len(result.proposed) == 1
    assert result.proposed[0][0].id == 2


def test_annealing_fairness():
    """Annealing should produce fair results comparable to greedy."""
    from collections import Counter
    people = [FakePerson(i, f"P{i}") for i in range(1, 21)]
    duties = [FakeDuty(i, f"D{i}", date(2026, 3, i)) for i in range(1, 11)]

    result = solve_assignments(people, duties, [], [], algorithm="annealing", iterations=500)
    assert len(result.proposed) == 10

    counts = Counter(p.id for p, _ in result.proposed)
    assert max(counts.values()) == 1
