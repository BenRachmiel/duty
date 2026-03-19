export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface Tag {
  id: number;
  name: string;
  color: string | null;
}

export interface Person {
  id: number;
  name: string;
  external_id: string | null;
  created_at: string;
  tags: Tag[];
}

export interface Duty {
  id: number;
  name: string;
  date: string;
  headcount: number;
  duration_days: number;
  difficulty: number;
  created_at: string;
  tags: Tag[];
}

export type RuleType = "allow" | "deny" | "cooldown";

export interface Rule {
  id: number;
  name: string;
  person_tag_id: number | null;
  duty_tag_id: number | null;
  rule_type: RuleType;
  priority: number;
  cooldown_days: number | null;
  cooldown_duty_tag_id: number | null;
  person_tag: Tag | null;
  duty_tag: Tag | null;
  cooldown_duty_tag: Tag | null;
}

export interface Assignment {
  id: number;
  person_id: number;
  duty_id: number;
  assigned_at: string;
  is_manual: boolean;
  person: Person;
  duty: Duty;
}

export interface ProposedAssignment {
  person: Person;
  duty: Duty;
}

export interface ExclusionReason {
  rule_name: string;
  rule_type: string;
  reason: string;
}

export interface ExcludedPerson {
  person: Person;
  reasons: ExclusionReason[];
}

export interface UnfilledDuty {
  duty: Duty;
  excluded_people: ExcludedPerson[];
  slots_needed: number;
}

export interface SolverRunResponse {
  proposed: ProposedAssignment[];
  unfilled: UnfilledDuty[];
  duty_points: Record<number, number>;
}

export interface PersonListItem extends Person {
  points: number;
}

export interface DutyDetail extends Duty {
  assignment_count: number;
}

export interface TagSummary {
  id: number;
  name: string;
  color: string | null;
  people_count: number;
  duties_count: number;
  rules: Rule[];
}

// Stats
export interface PointsBucket {
  range_min: number;
  range_max: number;
  count: number;
}

export interface DailyWorkloadItem {
  date: string;
  demand: number;
  filled: number;
}

export interface PersonWorkload {
  person_id: number;
  name: string;
  tags: Tag[];
  points: number;
  assignment_count: number;
}

export interface StatsResponse {
  total_points: number;
  fill_rate: number;
  active_personnel: number;
  total_personnel: number;
  upcoming_unfilled: number;
  points_distribution: PointsBucket[];
  daily_workload: DailyWorkloadItem[];
  top_loaded: PersonWorkload[];
  bottom_loaded: PersonWorkload[];
}
