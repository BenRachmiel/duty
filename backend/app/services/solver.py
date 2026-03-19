import math
import random
from dataclasses import dataclass
from datetime import date as date_type

from app.models import Assignment, Duty, Person, Rule, RuleType


@dataclass
class Exclusion:
    rule_name: str
    rule_type: str
    reason: str


@dataclass
class SolverResult:
    proposed: list[tuple[Person, Duty]]
    exclusions: dict[tuple[int, int], list[Exclusion]]
    duty_points: dict[int, float]


def _duty_points(duty: Duty) -> float:
    duration = getattr(duty, "duration_days", 1) or 1
    difficulty = getattr(duty, "difficulty", 1.0) or 1.0
    return duration * difficulty


def _person_tag_ids(person: Person) -> set[int]:
    return {t.id for t in person.tags}


def _duty_tag_ids(duty: Duty) -> set[int]:
    return {t.id for t in duty.tags}


def _compute_eligibility(
    people: list[Person],
    duties: list[Duty],
    rules: list[Rule],
    existing_assignments: list[Assignment],
) -> dict[tuple[int, int], list[Exclusion]]:
    """Return {(person_id, duty_id): [exclusion reasons]}. Missing key = eligible."""

    sorted_rules = sorted(rules, key=lambda r: r.priority)
    allow_rules = [r for r in sorted_rules if r.rule_type == RuleType.allow]
    deny_rules = [r for r in sorted_rules if r.rule_type == RuleType.deny]
    cooldown_rules = [r for r in sorted_rules if r.rule_type == RuleType.cooldown and r.cooldown_days is not None]

    # Build assignment history: person_id -> list of (date, duty_tag_ids)
    history: dict[int, list[tuple[object, set[int]]]] = {}
    for a in existing_assignments:
        pid = a.person_id if hasattr(a, "person_id") else a.person.id
        d = a.duty
        entry = (d.date, _duty_tag_ids(d))
        history.setdefault(pid, []).append(entry)

    # Precompute tag sets
    person_tags: dict[int, set[int]] = {p.id: _person_tag_ids(p) for p in people}
    duty_tags: dict[int, set[int]] = {d.id: _duty_tag_ids(d) for d in duties}

    # Precompute which rules apply to each duty (by tag match)
    duty_allow_rules: dict[int, list[Rule]] = {}
    duty_deny_rules: dict[int, list[Rule]] = {}
    duty_cooldown_rules: dict[int, list[Rule]] = {}
    for d in duties:
        d_tags = duty_tags[d.id]
        duty_allow_rules[d.id] = [r for r in allow_rules if r.duty_tag_id is None or r.duty_tag_id in d_tags]
        duty_deny_rules[d.id] = [r for r in deny_rules if r.duty_tag_id is None or r.duty_tag_id in d_tags]
        duty_cooldown_rules[d.id] = [r for r in cooldown_rules if r.duty_tag_id is None or r.duty_tag_id in d_tags]

    duty_has_allow: dict[int, bool] = {}
    duty_allow_ptags: dict[int, set[int | None]] = {}
    duty_allow_names: dict[int, list[str]] = {}
    duty_deny_ptags: dict[int, list[tuple[str, int | None]]] = {}

    for d in duties:
        did = d.id
        d_allows = duty_allow_rules[did]
        duty_has_allow[did] = bool(d_allows)
        if d_allows:
            duty_allow_ptags[did] = {r.person_tag_id for r in d_allows}
            duty_allow_names[did] = [r.name for r in d_allows]
        duty_deny_ptags[did] = [(r.name, r.person_tag_id) for r in duty_deny_rules[did]]

    exclusions: dict[tuple[int, int], list[Exclusion]] = {}

    for person in people:
        pid = person.id
        p_tags = person_tags[pid]
        p_history = history.get(pid, [])
        for duty in duties:
            did = duty.id

            # Check allow rules
            if duty_has_allow[did]:
                allow_ptags = duty_allow_ptags[did]
                if None not in allow_ptags and not p_tags & allow_ptags:
                    exclusions[(pid, did)] = [
                        Exclusion(rn, "allow", f"Not in allow list for '{rn}'")
                        for rn in duty_allow_names[did]
                    ]
                    continue

            # Apply deny rules
            denied = False
            for rule_name, rule_ptag in duty_deny_ptags[did]:
                if rule_ptag is None or rule_ptag in p_tags:
                    exclusions[(pid, did)] = [Exclusion(rule_name, "deny", f"Denied by '{rule_name}'")]
                    denied = True
                    break
            if denied:
                continue

            # Apply cooldown rules
            if p_history:
                cooldown_hit = False
                for rule in duty_cooldown_rules[did]:
                    if rule.person_tag_id is not None and rule.person_tag_id not in p_tags:
                        continue
                    trigger_tag = rule.cooldown_duty_tag_id
                    for hist_date, hist_tags in p_history:
                        if trigger_tag is not None and trigger_tag not in hist_tags:
                            continue
                        days_diff = abs((duty.date - hist_date).days)
                        if days_diff < rule.cooldown_days:
                            remaining = rule.cooldown_days - days_diff
                            exclusions[(pid, did)] = [Exclusion(
                                rule.name, "cooldown",
                                f"Cooldown: {remaining} days remain from '{rule.name}'"
                            )]
                            cooldown_hit = True
                            break
                    if cooldown_hit:
                        break

    return exclusions


def _compute_duty_points(
    people: list[Person],
    existing_assignments: list[Assignment],
    count_since: date_type | None,
) -> dict[int, float]:
    """Sum of (duration_days * difficulty) per person from historical assignments."""
    points: dict[int, float] = {p.id: 0.0 for p in people}
    for a in existing_assignments:
        pid = a.person_id if hasattr(a, "person_id") else a.person.id
        if pid not in points:
            continue
        if count_since and a.duty.date < count_since:
            continue
        points[pid] += _duty_points(a.duty)
    return points


def _violates_batch_cooldown(
    person_tag_ids: set[int],
    duty_date: object,
    duty_tags: set[int],
    cooldown_rules: list[Rule],
    batch_history: list[tuple[object, set[int]]],
) -> bool:
    """Check if assigning person to duty violates cooldown within the current batch."""
    for rule in cooldown_rules:
        if rule.person_tag_id is not None and rule.person_tag_id not in person_tag_ids:
            continue

        blocked_tag = rule.duty_tag_id
        trigger_tag = rule.cooldown_duty_tag_id

        if blocked_tag is not None and blocked_tag not in duty_tags:
            continue

        cooldown_days = rule.cooldown_days

        for hist_date, hist_tags in batch_history:
            if trigger_tag is not None and trigger_tag not in hist_tags:
                duty_triggers = trigger_tag is None or trigger_tag in duty_tags
                if duty_triggers:
                    hist_blocked = blocked_tag is None or blocked_tag in hist_tags
                    if hist_blocked and abs((duty_date - hist_date).days) < cooldown_days:
                        return True
                continue
            if abs((duty_date - hist_date).days) < cooldown_days:
                return True

    return False


# ---------------------------------------------------------------------------
# Precomputed context shared across algorithm runs
# ---------------------------------------------------------------------------

@dataclass
class _SolverCtx:
    """Precomputed data that all algorithms share. Built once per solve call."""
    all_pids: list[int]
    person_tags: dict[int, set[int]]
    duty_tags: dict[int, set[int]]
    duty_pts: dict[int, float]
    duty_dates: dict[int, object]
    duty_needed: dict[int, int]  # slots to fill per duty
    eligible_per_duty: dict[int, list[int]]
    sorted_duty_ids: list[int]  # most-constrained first
    cooldown_rules: list[Rule]


def _build_ctx(
    people: list[Person],
    duties: list[Duty],
    rules: list[Rule],
    exclusions: dict[tuple[int, int], list[Exclusion]],
) -> _SolverCtx:
    all_pids = [p.id for p in people]
    person_tags = {p.id: _person_tag_ids(p) for p in people}
    duty_tags = {d.id: _duty_tag_ids(d) for d in duties}
    duty_pts = {d.id: _duty_points(d) for d in duties}
    duty_dates = {d.id: d.date for d in duties}
    duty_needed = {d.id: d.headcount - len(d.assignments) for d in duties}
    cooldown_rules = [r for r in rules if r.rule_type == RuleType.cooldown and r.cooldown_days]

    eligible_per_duty: dict[int, list[int]] = {}
    for d in duties:
        did = d.id
        eligible_per_duty[did] = [pid for pid in all_pids if (pid, did) not in exclusions]

    sorted_duty_ids = sorted(
        [d.id for d in duties],
        key=lambda did: (len(eligible_per_duty[did]), -duty_pts[did]),
    )

    return _SolverCtx(
        all_pids=all_pids,
        person_tags=person_tags,
        duty_tags=duty_tags,
        duty_pts=duty_pts,
        duty_dates=duty_dates,
        duty_needed=duty_needed,
        eligible_per_duty=eligible_per_duty,
        sorted_duty_ids=sorted_duty_ids,
        cooldown_rules=cooldown_rules,
    )


# ---------------------------------------------------------------------------
# Core greedy — returns list of (person_id, duty_id) pairs
# ---------------------------------------------------------------------------

def _greedy_core(
    ctx: _SolverCtx,
    duty_points_hist: dict[int, float],
) -> list[tuple[int, int]]:
    """Run one greedy pass. Returns (person_id, duty_id) pairs."""
    running_points = dict(duty_points_hist)
    date_occupied: dict[int, set] = {}
    batch_history: dict[int, list[tuple[object, set[int]]]] = {}
    proposed: list[tuple[int, int]] = []

    for did in ctx.sorted_duty_ids:
        needed = ctx.duty_needed[did]
        if needed <= 0:
            continue

        d_tags = ctx.duty_tags[did]
        d_date = ctx.duty_dates[did]
        d_pts = ctx.duty_pts[did]
        candidates = []

        for pid in ctx.eligible_per_duty[did]:
            occupied = date_occupied.get(pid)
            if occupied is not None and d_date in occupied:
                continue
            if ctx.cooldown_rules:
                p_batch = batch_history.get(pid)
                if p_batch and _violates_batch_cooldown(
                    ctx.person_tags[pid], d_date, d_tags, ctx.cooldown_rules, p_batch
                ):
                    continue
            candidates.append(pid)

        random.shuffle(candidates)
        candidates.sort(key=lambda pid: running_points.get(pid, 0.0))

        for pid in candidates[:needed]:
            proposed.append((pid, did))
            running_points[pid] = running_points.get(pid, 0.0) + d_pts
            date_occupied.setdefault(pid, set()).add(d_date)
            batch_history.setdefault(pid, []).append((d_date, d_tags))

    return proposed


def _score(proposed: list[tuple[int, int]], duty_points_hist: dict[int, float], duty_pts: dict[int, float]) -> float:
    """Score = max points any person accumulates. Lower is better (fairer)."""
    pts = dict(duty_points_hist)
    for pid, did in proposed:
        pts[pid] = pts.get(pid, 0.0) + duty_pts[did]
    return max(pts.values()) if pts else 0.0


# ---------------------------------------------------------------------------
# Algorithm: greedy (single pass)
# ---------------------------------------------------------------------------

def _algo_greedy(
    ctx: _SolverCtx,
    duty_points_hist: dict[int, float],
    _iterations: int,
) -> list[tuple[int, int]]:
    return _greedy_core(ctx, duty_points_hist)


# ---------------------------------------------------------------------------
# Algorithm: monte carlo (repeated greedy, keep best)
# ---------------------------------------------------------------------------

def _algo_montecarlo(
    ctx: _SolverCtx,
    duty_points_hist: dict[int, float],
    iterations: int,
) -> list[tuple[int, int]]:
    best: list[tuple[int, int]] = []
    best_score = float("inf")

    for _ in range(max(1, iterations)):
        proposed = _greedy_core(ctx, duty_points_hist)
        s = _score(proposed, duty_points_hist, ctx.duty_pts)
        if s < best_score or (s == best_score and len(proposed) > len(best)):
            best_score = s
            best = proposed

    return best


# ---------------------------------------------------------------------------
# Algorithm: simulated annealing (start from greedy, swap to improve fairness)
# ---------------------------------------------------------------------------

def _algo_annealing(
    ctx: _SolverCtx,
    duty_points_hist: dict[int, float],
    iterations: int,
    exclusions: dict[tuple[int, int], list[Exclusion]] | None = None,
) -> list[tuple[int, int]]:
    if exclusions is None:
        exclusions = {}

    # Start from a greedy solution
    current = _greedy_core(ctx, duty_points_hist)
    if not current:
        return current

    current_score = _score(current, duty_points_hist, ctx.duty_pts)
    best = list(current)
    best_score = current_score

    # Build index structures for fast swaps
    # duty_id -> list of person_ids assigned
    duty_people: dict[int, list[int]] = {}
    person_duties: dict[int, list[int]] = {}
    for pid, did in current:
        duty_people.setdefault(did, []).append(pid)
        person_duties.setdefault(pid, []).append(did)

    # Build batch state
    date_occupied: dict[int, set] = {}
    batch_history: dict[int, list[tuple[object, set[int]]]] = {}
    for pid, did in current:
        date_occupied.setdefault(pid, set()).add(ctx.duty_dates[did])
        batch_history.setdefault(pid, []).append((ctx.duty_dates[did], ctx.duty_tags[did]))

    # Compute running points
    running_pts = dict(duty_points_hist)
    for pid, did in current:
        running_pts[pid] = running_pts.get(pid, 0.0) + ctx.duty_pts[did]

    t_start = 1.0
    t_end = 0.01
    n_iter = max(1, iterations)

    for i in range(n_iter):
        t = t_start * (t_end / t_start) ** (i / n_iter)

        # Pick the person with max points and try to swap one of their duties
        # with someone who has fewer points
        max_pid = max(running_pts, key=lambda pid: running_pts.get(pid, 0.0))
        max_duties = person_duties.get(max_pid, [])
        if not max_duties:
            continue

        swap_did = random.choice(max_duties)
        # Find an eligible replacement from people not currently assigned to this duty
        assigned_set = set(duty_people.get(swap_did, []))
        eligible = [pid for pid in ctx.eligible_per_duty[swap_did] if pid not in assigned_set and pid != max_pid]
        if not eligible:
            continue

        # Pick a candidate weighted toward low-points people
        random.shuffle(eligible)
        candidate = min(eligible[:20], key=lambda pid: running_pts.get(pid, 0.0))

        # Check validity: candidate must not violate date/cooldown constraints
        # Temporarily remove max_pid from batch state
        d_date = ctx.duty_dates[swap_did]
        d_tags = ctx.duty_tags[swap_did]

        # Check candidate date conflict
        cand_occupied = date_occupied.get(candidate, set())
        if d_date in cand_occupied:
            continue

        # Check candidate cooldown (excluding the assignment we're removing)
        cand_batch = batch_history.get(candidate, [])
        if ctx.cooldown_rules and cand_batch and _violates_batch_cooldown(
            ctx.person_tags[candidate], d_date, d_tags, ctx.cooldown_rules, cand_batch
        ):
            continue

        # Also check if max_pid's removal breaks cooldown for existing assignments
        # (removing an assignment can only relax constraints, never tighten them)

        # Compute score delta
        d_pts = ctx.duty_pts[swap_did]
        old_max_pts = running_pts.get(max_pid, 0.0)
        old_cand_pts = running_pts.get(candidate, 0.0)
        new_max_pts = old_max_pts - d_pts
        new_cand_pts = old_cand_pts + d_pts

        # Check if this improves the max (the objective)
        new_worst = max(new_max_pts, new_cand_pts)
        old_worst = old_max_pts  # max_pid was already the worst
        delta = new_worst - old_worst

        if delta < 0 or random.random() < math.exp(-delta / t):
            # Accept the swap
            # Update assignment lists
            dp = duty_people[swap_did]
            dp.remove(max_pid)
            dp.append(candidate)
            person_duties[max_pid].remove(swap_did)
            person_duties.setdefault(candidate, []).append(swap_did)

            # Update date_occupied
            date_occupied[max_pid].discard(d_date)
            date_occupied.setdefault(candidate, set()).add(d_date)

            # Update batch_history
            bh = batch_history[max_pid]
            for j, (hd, ht) in enumerate(bh):
                if hd == d_date and ht == d_tags:
                    bh.pop(j)
                    break
            batch_history.setdefault(candidate, []).append((d_date, d_tags))

            # Update points
            running_pts[max_pid] = new_max_pts
            running_pts[candidate] = new_cand_pts

            new_score = max(running_pts.values())
            if new_score < best_score:
                best_score = new_score
                best = [(pid, did) for did, pids in duty_people.items() for pid in pids]

    return best


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve_assignments(
    people: list[Person],
    duties: list[Duty],
    rules: list[Rule],
    existing_assignments: list[Assignment],
    count_since: date_type | None = None,
    algorithm: str = "greedy",
    iterations: int = 100,
) -> SolverResult:
    """Run solver with the specified algorithm."""
    empty = SolverResult([], {}, {p.id: 0.0 for p in people})
    if not people or not duties:
        return empty

    exclusions = _compute_eligibility(people, duties, rules, existing_assignments)
    duty_points_hist = _compute_duty_points(people, existing_assignments, count_since)

    ctx = _build_ctx(people, duties, rules, exclusions)

    if algorithm == "montecarlo":
        pairs = _algo_montecarlo(ctx, duty_points_hist, iterations)
    elif algorithm == "annealing":
        pairs = _algo_annealing(ctx, duty_points_hist, iterations, exclusions)
    else:
        pairs = _algo_greedy(ctx, duty_points_hist, iterations)

    person_map = {p.id: p for p in people}
    duty_map = {d.id: d for d in duties}
    proposed = [(person_map[pid], duty_map[did]) for pid, did in pairs]
    proposed.sort(key=lambda x: (x[1].date, x[0].name))

    return SolverResult(proposed, exclusions, duty_points_hist)
