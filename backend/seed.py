"""Seed script: populates the database with realistic military-style test data via the API."""

import random
from datetime import date, timedelta

import httpx

BASE = "http://127.0.0.1:8000/api"

# ---------------------------------------------------------------------------
# Tag definitions
# ---------------------------------------------------------------------------

PERSON_TAGS = [
    # Gender (mutually exclusive)
    ("man", "#3b82f6"),
    ("woman", "#ec4899"),
    # Personal
    ("married", "#f59e0b"),
    ("religious", "#8b5cf6"),
    ("parent", "#10b981"),
    # Medical / physical
    ("allergic-to-dust", "#ef4444"),
    ("cant-carry-weight", "#f97316"),
    ("color-blind", "#6b7280"),
    ("glasses", "#64748b"),
    # Certifications
    ("firing-range-certified", "#16a34a"),
    ("combat-medic", "#06b6d4"),
    ("heavy-vehicle-license", "#7c3aed"),
    ("radio-operator", "#0ea5e9"),
    ("explosives-certified", "#dc2626"),
    # NCO ranks (mutually exclusive with CO ranks)
    ("rank:corporal", "#a3a3a3"),
    ("rank:sergeant", "#78716c"),
    ("rank:staff-sergeant", "#57534e"),
    ("rank:sergeant-major", "#44403c"),
    # CO ranks (mutually exclusive with NCO ranks)
    ("rank:2nd-lieutenant", "#fbbf24"),
    ("rank:lieutenant", "#f59e0b"),
    ("rank:captain", "#d97706"),
    ("rank:major", "#b45309"),
    ("rank:colonel", "#92400e"),
]

DUTY_TAGS = [
    ("guard", "#22c55e"),
    ("armed-guard", "#15803d"),
    ("night-shift", "#1e3a5f"),
    ("weekend", "#6366f1"),
    ("warehouse", "#a16207"),
    ("kitchen", "#ea580c"),
    ("patrol", "#0d9488"),
    ("foreign-mission", "#7c3aed"),
    ("medical-station", "#06b6d4"),
    ("command-post", "#b45309"),
    ("firing-range", "#dc2626"),
    ("vehicle-maintenance", "#4b5563"),
    ("communications", "#0ea5e9"),
    ("training", "#8b5cf6"),
]

# Ranks grouped for mutual exclusion
NCO_RANKS = ["rank:corporal", "rank:sergeant", "rank:staff-sergeant", "rank:sergeant-major"]
CO_RANKS = ["rank:2nd-lieutenant", "rank:lieutenant", "rank:captain", "rank:major", "rank:colonel"]
ALL_RANKS = NCO_RANKS + CO_RANKS

# Tags that are mutually exclusive
GENDER_TAGS = ["man", "woman"]

# ---------------------------------------------------------------------------
# Duty templates
# ---------------------------------------------------------------------------

DUTY_TEMPLATES = [
    {"name": "Gate Guard", "tags": ["guard"], "headcount": (2, 4), "duration": (1, 1), "difficulty": (1.0, 1.0)},
    {"name": "Armed Perimeter Guard", "tags": ["armed-guard", "guard"], "headcount": (2, 3), "duration": (1, 1), "difficulty": (1.5, 1.5)},
    {"name": "Night Watch", "tags": ["guard", "night-shift"], "headcount": (2, 4), "duration": (1, 1), "difficulty": (1.5, 2.0)},
    {"name": "Weekend Gate Duty", "tags": ["guard", "weekend"], "headcount": (3, 5), "duration": (2, 2), "difficulty": (1.0, 1.5)},
    {"name": "Warehouse Inventory", "tags": ["warehouse"], "headcount": (3, 6), "duration": (1, 2), "difficulty": (1.0, 1.5)},
    {"name": "Kitchen Duty", "tags": ["kitchen"], "headcount": (4, 8), "duration": (1, 1), "difficulty": (1.0, 1.0)},
    {"name": "Patrol Route Alpha", "tags": ["patrol"], "headcount": (2, 4), "duration": (1, 1), "difficulty": (1.5, 2.0)},
    {"name": "Foreign Deployment", "tags": ["foreign-mission"], "headcount": (5, 10), "duration": (14, 30), "difficulty": (2.0, 3.0)},
    {"name": "Medical Station Coverage", "tags": ["medical-station"], "headcount": (1, 2), "duration": (1, 1), "difficulty": (1.0, 1.5)},
    {"name": "Command Post Watch", "tags": ["command-post"], "headcount": (1, 2), "duration": (1, 1), "difficulty": (1.0, 1.0)},
    {"name": "Firing Range Supervision", "tags": ["firing-range"], "headcount": (2, 3), "duration": (1, 1), "difficulty": (1.0, 1.5)},
    {"name": "Vehicle Maintenance Detail", "tags": ["vehicle-maintenance"], "headcount": (2, 4), "duration": (1, 2), "difficulty": (1.0, 1.5)},
    {"name": "Radio Watch", "tags": ["communications", "night-shift"], "headcount": (1, 2), "duration": (1, 1), "difficulty": (1.0, 1.5)},
    {"name": "Training Exercise", "tags": ["training"], "headcount": (10, 20), "duration": (1, 3), "difficulty": (1.5, 2.5)},
    {"name": "Weekend Patrol", "tags": ["patrol", "weekend"], "headcount": (3, 5), "duration": (2, 2), "difficulty": (1.5, 2.0)},
]

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

RULES = [
    # Allow rules (whitelist)
    {"name": "Armed guard requires firing range cert", "rule_type": "allow", "person_tag": "firing-range-certified", "duty_tag": "armed-guard"},
    {"name": "Medical station requires combat medic", "rule_type": "allow", "person_tag": "combat-medic", "duty_tag": "medical-station"},
    {"name": "Vehicle maintenance requires heavy vehicle license", "rule_type": "allow", "person_tag": "heavy-vehicle-license", "duty_tag": "vehicle-maintenance"},
    {"name": "Radio watch requires radio operator cert", "rule_type": "allow", "person_tag": "radio-operator", "duty_tag": "communications"},
    {"name": "Firing range requires certification", "rule_type": "allow", "person_tag": "firing-range-certified", "duty_tag": "firing-range"},
    {"name": "Command post requires officer rank", "rule_type": "allow", "person_tag": "rank:captain", "duty_tag": "command-post"},
    {"name": "Command post allows majors", "rule_type": "allow", "person_tag": "rank:major", "duty_tag": "command-post"},
    {"name": "Command post allows colonels", "rule_type": "allow", "person_tag": "rank:colonel", "duty_tag": "command-post"},

    # Deny rules
    {"name": "Dust allergy can't do warehouse", "rule_type": "deny", "person_tag": "allergic-to-dust", "duty_tag": "warehouse"},
    {"name": "Can't carry weight excludes warehouse", "rule_type": "deny", "person_tag": "cant-carry-weight", "duty_tag": "warehouse"},
    {"name": "Can't carry weight excludes patrol", "rule_type": "deny", "person_tag": "cant-carry-weight", "duty_tag": "patrol"},
    {"name": "Color blind can't do firing range", "rule_type": "deny", "person_tag": "color-blind", "duty_tag": "firing-range"},

    # Cooldown rules
    {"name": "No consecutive weekends", "rule_type": "cooldown", "duty_tag": "weekend", "cooldown_days": 7, "cooldown_duty_tag": "weekend"},
    {"name": "Night shift cooldown 3 days", "rule_type": "cooldown", "duty_tag": "night-shift", "cooldown_days": 3, "cooldown_duty_tag": "night-shift"},
    {"name": "Foreign mission cooldown 90 days", "rule_type": "cooldown", "duty_tag": "foreign-mission", "cooldown_days": 90, "cooldown_duty_tag": "foreign-mission"},
    {"name": "Kitchen duty cooldown 14 days", "rule_type": "cooldown", "duty_tag": "kitchen", "cooldown_days": 14, "cooldown_duty_tag": "kitchen"},
    {"name": "Patrol cooldown 2 days", "rule_type": "cooldown", "duty_tag": "patrol", "cooldown_days": 2, "cooldown_duty_tag": "patrol"},
]

# ---------------------------------------------------------------------------
# First names pool
# ---------------------------------------------------------------------------

FIRST_NAMES_M = [
    "James", "Robert", "John", "Michael", "David", "William", "Richard", "Joseph",
    "Thomas", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
    "Steven", "Andrew", "Paul", "Joshua", "Kenneth", "Kevin", "Brian", "George",
    "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob",
    "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
    "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank", "Alexander",
    "Patrick", "Jack", "Dennis", "Jerry", "Tyler",
]

FIRST_NAMES_F = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
    "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura",
    "Cynthia", "Kathleen", "Amy", "Angela", "Shirley", "Anna", "Brenda",
    "Pamela", "Emma", "Nicole", "Helen", "Samantha", "Katherine", "Christine",
    "Debra", "Rachel", "Carolyn", "Janet", "Catherine", "Maria", "Heather",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts",
]


def main():
    client = httpx.Client(base_url=BASE, timeout=30)

    print("Seeding tags...")
    tag_map: dict[str, dict] = {}
    all_tags = PERSON_TAGS + DUTY_TAGS
    # Deduplicate
    seen = set()
    for name, color in all_tags:
        if name in seen:
            continue
        seen.add(name)
        resp = client.post("/tags", json={"name": name, "color": color})
        if resp.status_code == 201:
            tag_map[name] = resp.json()
        elif resp.status_code == 422:
            # Tag might already exist
            pass
    # Fetch all tags to fill in any that already existed
    for t in client.get("/tags").json():
        tag_map[t["name"]] = t
    print(f"  {len(tag_map)} tags ready")

    print("Seeding 500 people...")
    person_count = 500
    people = []
    used_names: set[str] = set()

    for i in range(person_count):
        # Pick gender
        is_male = random.random() < 0.65  # 65% male skew (military context)
        gender_tag = "man" if is_male else "woman"
        first_pool = FIRST_NAMES_M if is_male else FIRST_NAMES_F

        # Generate unique name
        for _ in range(50):
            first = random.choice(first_pool)
            last = random.choice(LAST_NAMES)
            full = f"{first} {last}"
            if full not in used_names:
                used_names.add(full)
                break
        else:
            full = f"{random.choice(first_pool)} {random.choice(LAST_NAMES)} {i}"
            used_names.add(full)

        resp = client.post("/people", json={"name": full, "external_id": f"SN-{10000 + i}"})
        person = resp.json()
        people.append(person)

        # Assign tags
        tags_to_assign: list[str] = [gender_tag]

        # Rank — 70% enlisted (NCO), 15% officer (CO), 15% no rank yet
        rank_roll = random.random()
        if rank_roll < 0.70:
            # NCO — weighted toward lower ranks
            weights = [0.35, 0.30, 0.25, 0.10]
            tags_to_assign.append(random.choices(NCO_RANKS, weights=weights, k=1)[0])
        elif rank_roll < 0.85:
            # CO — weighted toward lower officer ranks
            weights = [0.30, 0.30, 0.20, 0.15, 0.05]
            tags_to_assign.append(random.choices(CO_RANKS, weights=weights, k=1)[0])

        # Personal tags (independent probabilities)
        if random.random() < 0.35:
            tags_to_assign.append("married")
        if random.random() < 0.20:
            tags_to_assign.append("religious")
        if random.random() < 0.25 and "married" in tags_to_assign:
            tags_to_assign.append("parent")

        # Medical / physical
        if random.random() < 0.08:
            tags_to_assign.append("allergic-to-dust")
        if random.random() < 0.05:
            tags_to_assign.append("cant-carry-weight")
        if random.random() < 0.04:
            tags_to_assign.append("color-blind")
        if random.random() < 0.15:
            tags_to_assign.append("glasses")

        # Certifications (more common in higher ranks)
        has_rank = any(t.startswith("rank:") for t in tags_to_assign)
        cert_boost = 1.3 if has_rank else 1.0
        if random.random() < 0.30 * cert_boost:
            tags_to_assign.append("firing-range-certified")
        if random.random() < 0.08 * cert_boost:
            tags_to_assign.append("combat-medic")
        if random.random() < 0.12 * cert_boost:
            tags_to_assign.append("heavy-vehicle-license")
        if random.random() < 0.10 * cert_boost:
            tags_to_assign.append("radio-operator")
        if random.random() < 0.05 * cert_boost:
            tags_to_assign.append("explosives-certified")

        for tag_name in tags_to_assign:
            tag = tag_map.get(tag_name)
            if tag:
                client.post(f"/people/{person['id']}/tags", json=tag)

    print(f"  {len(people)} people created")

    print("Seeding duties...")
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=60)
    duties = []

    current = start_date
    while current <= end_date:
        is_weekend = current.weekday() in (4, 5)  # Friday, Saturday
        # Pick 3-6 duties per day, more on weekdays
        num_duties = random.randint(3, 6) if not is_weekend else random.randint(2, 4)

        templates = random.sample(DUTY_TEMPLATES, min(num_duties, len(DUTY_TEMPLATES)))
        for tmpl in templates:
            # Skip weekend-tagged duties on weekdays and vice versa
            if "weekend" in tmpl["tags"] and not is_weekend:
                continue
            if is_weekend and "weekend" not in tmpl["tags"] and random.random() < 0.5:
                continue

            hc = random.randint(*tmpl["headcount"])
            dur = random.randint(*tmpl["duration"])
            diff = round(random.uniform(*tmpl["difficulty"]), 1)

            resp = client.post("/duties", json={
                "name": tmpl["name"],
                "date": current.isoformat(),
                "headcount": hc,
                "duration_days": dur,
                "difficulty": diff,
            })
            if resp.status_code == 201:
                duty = resp.json()
                duties.append(duty)

                for tag_name in tmpl["tags"]:
                    tag = tag_map.get(tag_name)
                    if tag:
                        client.post(f"/duties/{duty['id']}/tags", json=tag)

        current += timedelta(days=1)

    print(f"  {len(duties)} duties created over {(end_date - start_date).days} days")

    print("Seeding rules...")
    rules_created = 0
    for rule_def in RULES:
        payload: dict = {
            "name": rule_def["name"],
            "rule_type": rule_def["rule_type"],
            "priority": 0,
        }
        if "person_tag" in rule_def:
            tag = tag_map.get(rule_def["person_tag"])
            if tag:
                payload["person_tag_id"] = tag["id"]
        if "duty_tag" in rule_def:
            tag = tag_map.get(rule_def["duty_tag"])
            if tag:
                payload["duty_tag_id"] = tag["id"]
        if "cooldown_days" in rule_def:
            payload["cooldown_days"] = rule_def["cooldown_days"]
        if "cooldown_duty_tag" in rule_def:
            tag = tag_map.get(rule_def["cooldown_duty_tag"])
            if tag:
                payload["cooldown_duty_tag_id"] = tag["id"]

        resp = client.post("/rules", json=payload)
        if resp.status_code == 201:
            rules_created += 1

    print(f"  {rules_created} rules created")
    print("Done!")


if __name__ == "__main__":
    main()
