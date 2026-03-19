import type {
  Assignment,
  Duty,
  DutyDetail,
  PaginatedResponse,
  Person,
  PersonListItem,
  Rule,
  SolverRunResponse,
  StatsResponse,
  Tag,
  TagSummary,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Tags
export const fetchTags = () => request<Tag[]>("/tags");
export const createTag = (data: { name: string; color?: string | null }) =>
  request<Tag>("/tags", { method: "POST", body: JSON.stringify(data) });
export const deleteTag = (id: number) =>
  request<void>(`/tags/${id}`, { method: "DELETE" });
export const fetchTagSummary = (id: number) =>
  request<TagSummary>(`/tags/${id}/summary`);

// People
export const fetchPeople = (params?: {
  limit?: number;
  offset?: number;
  q?: string;
  tag_id?: number;
  count_since?: string;
  sort_by?: string;
}) => {
  const qs = new URLSearchParams();
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  if (params?.q) qs.set("q", params.q);
  if (params?.tag_id != null) qs.set("tag_id", String(params.tag_id));
  if (params?.count_since) qs.set("count_since", params.count_since);
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  const q = qs.toString();
  return request<PaginatedResponse<PersonListItem>>(`/people${q ? `?${q}` : ""}`);
};
export const fetchPerson = (id: number, countSince?: string) => {
  const qs = countSince ? `?count_since=${countSince}` : "";
  return request<PersonListItem>(`/people/${id}${qs}`);
};
export const createPerson = (data: {
  name: string;
  external_id?: string | null;
}) => request<Person>("/people", { method: "POST", body: JSON.stringify(data) });
export const updatePerson = (
  id: number,
  data: { name?: string; external_id?: string | null },
) =>
  request<Person>(`/people/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deletePerson = (id: number) =>
  request<void>(`/people/${id}`, { method: "DELETE" });
export const addPersonTag = (personId: number, tag: Tag) =>
  request<Person>(`/people/${personId}/tags`, {
    method: "POST",
    body: JSON.stringify(tag),
  });
export const removePersonTag = (personId: number, tagId: number) =>
  request<Person>(`/people/${personId}/tags/${tagId}`, { method: "DELETE" });
export const importPeopleCsv = async (file: File): Promise<Person[]> => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/people/import`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
};

// Duties
export const fetchDuties = (params?: {
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
  q?: string;
  tag_id?: number;
}) => {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  if (params?.q) qs.set("q", params.q);
  if (params?.tag_id != null) qs.set("tag_id", String(params.tag_id));
  const q = qs.toString();
  return request<PaginatedResponse<Duty>>(`/duties${q ? `?${q}` : ""}`);
};
export const fetchDuty = (id: number) => request<DutyDetail>(`/duties/${id}`);
export const createDuty = (data: {
  name: string;
  date: string;
  headcount?: number;
  duration_days?: number;
  difficulty?: number;
}) => request<Duty>("/duties", { method: "POST", body: JSON.stringify(data) });
export const updateDuty = (
  id: number,
  data: { name?: string; date?: string; headcount?: number; duration_days?: number; difficulty?: number },
) =>
  request<Duty>(`/duties/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteDuty = (id: number) =>
  request<void>(`/duties/${id}`, { method: "DELETE" });
export const addDutyTag = (dutyId: number, tag: Tag) =>
  request<Duty>(`/duties/${dutyId}/tags`, {
    method: "POST",
    body: JSON.stringify(tag),
  });
export const removeDutyTag = (dutyId: number, tagId: number) =>
  request<Duty>(`/duties/${dutyId}/tags/${tagId}`, { method: "DELETE" });

// Rules
export const fetchRules = (params?: { tag_id?: number }) => {
  const qs = new URLSearchParams();
  if (params?.tag_id != null) qs.set("tag_id", String(params.tag_id));
  const q = qs.toString();
  return request<Rule[]>(`/rules${q ? `?${q}` : ""}`);
};
export const createRule = (data: {
  name: string;
  rule_type: string;
  person_tag_id?: number | null;
  duty_tag_id?: number | null;
  priority?: number;
  cooldown_days?: number | null;
  cooldown_duty_tag_id?: number | null;
}) => request<Rule>("/rules", { method: "POST", body: JSON.stringify(data) });
export const updateRule = (
  id: number,
  data: Partial<{
    name: string;
    rule_type: string;
    person_tag_id: number | null;
    duty_tag_id: number | null;
    priority: number;
    cooldown_days: number | null;
    cooldown_duty_tag_id: number | null;
  }>,
) =>
  request<Rule>(`/rules/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteRule = (id: number) =>
  request<void>(`/rules/${id}`, { method: "DELETE" });

// Assignments
export const fetchAssignments = (params?: {
  date_from?: string;
  date_to?: string;
  person_id?: number;
  duty_id?: number;
  limit?: number;
  offset?: number;
}) => {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  if (params?.person_id != null) qs.set("person_id", String(params.person_id));
  if (params?.duty_id != null) qs.set("duty_id", String(params.duty_id));
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const q = qs.toString();
  return request<PaginatedResponse<Assignment>>(`/assignments${q ? `?${q}` : ""}`);
};
export const createAssignment = (data: {
  person_id: number;
  duty_id: number;
}) =>
  request<Assignment>("/assignments", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const deleteAssignment = (id: number) =>
  request<void>(`/assignments/${id}`, { method: "DELETE" });

// Stats
export const fetchStats = (params?: { date_from?: string; date_to?: string }) => {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  const q = qs.toString();
  return request<StatsResponse>(`/stats${q ? `?${q}` : ""}`);
};

// Solver
export const runSolver = (opts?: {
  countSince?: string;
  algorithm?: string;
  iterations?: number;
}) =>
  request<SolverRunResponse>("/solver/run", {
    method: "POST",
    body: JSON.stringify({
      ...(opts?.countSince && { count_since: opts.countSince }),
      ...(opts?.algorithm && { algorithm: opts.algorithm }),
      ...(opts?.iterations != null && { iterations: opts.iterations }),
    }),
  });
export const acceptSolver = (
  assignments: { person_id: number; duty_id: number }[],
) =>
  request<{ accepted: number }>("/solver/accept", {
    method: "POST",
    body: JSON.stringify({ assignments }),
  });
