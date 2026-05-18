const BASE = "/api/v1";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Project = { slug: string; created_at: string };

export type Skill = {
  id: string;
  name: string;
  description: string | null;
  body: string;
  keywords: string[];
};

export type Rule = {
  id: number;
  on_event: string;
  match: string | null;
  inject: string[];
  once_per_session: boolean;
};

export const api = {
  listProjects: () => http<Project[]>("/projects"),
  createProject: (slug: string) =>
    http<Project>("/projects", { method: "POST", body: JSON.stringify({ slug }) }),

  listSkills: (slug: string) => http<Skill[]>(`/projects/${slug}/skills`),
  upsertSkill: (slug: string, id: string, body: Omit<Skill, "id">) =>
    http<Skill>(`/projects/${slug}/skills/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteSkill: (slug: string, id: string) =>
    http<void>(`/projects/${slug}/skills/${id}`, { method: "DELETE" }),

  listRules: (slug: string) => http<Rule[]>(`/projects/${slug}/rules`),
  createRule: (slug: string, body: Omit<Rule, "id">) =>
    http<Rule>(`/projects/${slug}/rules`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateRule: (slug: string, id: number, body: Omit<Rule, "id">) =>
    http<Rule>(`/projects/${slug}/rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteRule: (slug: string, id: number) =>
    http<void>(`/projects/${slug}/rules/${id}`, { method: "DELETE" }),
};
