const BASE = "/api/v1";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (init?.body && !headers["content-type"]) {
    headers["content-type"] = "application/json";
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return undefined as T;
  return res.json() as Promise<T>;
}

export type Scope = "org" | "project" | "member";

export type Org = { id: string; name: string; created_at: string };
export type OrgMember = {
  user_id: string;
  role: "owner" | "admin" | "member";
  created_at: string;
};

export type Kpatch = {
  pk_id: number;
  scope: Scope;
  org_id: string;
  project_slug: string | null;
  user_id: string | null;
  slug: string;
  disable: boolean;
  name: string;
  description: string | null;
  body: string;
  keywords: string[];
  created_at: string;
  updated_at: string;
};

export type KpatchInherited = Kpatch & {
  origin_scope: Scope;
  shadowed_at_current: boolean;
};

export type Trigger = {
  id: number;
  kpatch_id: number;
  event: "session_start" | "user_prompt" | "pre_tool_use";
  prompt_contains: string[] | null;
  path_match: string | null;
  once_per_session: boolean;
};

export type Project = {
  slug: string;
  org_id: string;
  created_at: string;
  access_mode: "org" | "invite_only";
  members: string[];
};

// ---- URL builders --------------------------------------------------------

function scopePrefix(org_id: string, project_slug?: string, user_id?: string): string {
  if (user_id && project_slug) {
    return `/orgs/${org_id}/projects/${project_slug}/members/${user_id}/kpatches`;
  }
  if (project_slug) return `/orgs/${org_id}/projects/${project_slug}/kpatches`;
  return `/orgs/${org_id}/kpatches`;
}

export type ScopeRef = {
  org_id: string;
  project_slug?: string;
  user_id?: string;
};

export const api = {
  // Orgs
  listOrgs: () => http<Org[]>("/orgs"),
  getOrg: (org: string) => http<Org>(`/orgs/${org}`),
  createOrg: (id: string, name: string) =>
    http<Org>("/orgs", { method: "POST", body: JSON.stringify({ id, name }) }),
  listMembers: (org: string) => http<OrgMember[]>(`/orgs/${org}/members`),
  setMemberRole: (org: string, userId: string, role: string) =>
    http<{ user_id: string; role: string }>(
      `/orgs/${org}/members/${userId}`,
      { method: "PUT", body: JSON.stringify({ role }) },
    ),
  removeMember: (org: string, userId: string) =>
    http<void>(`/orgs/${org}/members/${userId}`, { method: "DELETE" }),

  // Kpatches (scope-aware)
  listKpatches: (s: ScopeRef, includeInherited = false) => {
    const path = scopePrefix(s.org_id, s.project_slug, s.user_id);
    const q = includeInherited ? "?include_inherited=true" : "";
    return http<KpatchInherited[]>(`${path}${q}`);
  },
  getKpatch: (s: ScopeRef, slug: string) =>
    http<Kpatch>(`${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}`),
  upsertKpatch: (
    s: ScopeRef,
    slug: string,
    body: {
      name: string;
      description: string | null;
      body: string;
      keywords: string[];
      disable?: boolean;
    },
  ) =>
    http<Kpatch>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}`,
      { method: "PUT", body: JSON.stringify(body) },
    ),
  deleteKpatch: (s: ScopeRef, slug: string) =>
    http<void>(`${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}`, {
      method: "DELETE",
    }),
  setDisable: (s: ScopeRef, slug: string, disable: boolean) =>
    http<Kpatch>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}/disable`,
      { method: "PUT", body: JSON.stringify({ disable }) },
    ),
  importKpatch: (s: ScopeRef, md: string) =>
    http<{ kpatch: Kpatch; trigger: Trigger | null }>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/import`,
      { method: "POST", body: md, headers: { "content-type": "text/markdown" } },
    ),

  // Triggers (under kpatch URL)
  listTriggers: (s: ScopeRef, slug: string) =>
    http<Trigger[]>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}/triggers`,
    ),
  createTrigger: (
    s: ScopeRef,
    slug: string,
    body: Omit<Trigger, "id" | "kpatch_id">,
  ) =>
    http<Trigger>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}/triggers`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  updateTrigger: (
    s: ScopeRef,
    slug: string,
    triggerId: number,
    body: Omit<Trigger, "id" | "kpatch_id">,
  ) =>
    http<Trigger>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}/triggers/${triggerId}`,
      { method: "PUT", body: JSON.stringify(body) },
    ),
  deleteTrigger: (s: ScopeRef, slug: string, triggerId: number) =>
    http<void>(
      `${scopePrefix(s.org_id, s.project_slug, s.user_id)}/${slug}/triggers/${triggerId}`,
      { method: "DELETE" },
    ),

  // Projects
  listProjects: (org: string) => http<Project[]>(`/orgs/${org}/projects`),
  createProject: (org: string, slug: string) =>
    http<Project>(`/orgs/${org}/projects`, {
      method: "POST",
      body: JSON.stringify({ slug }),
    }),
  getProject: (slug: string) => http<Project>(`/projects/${slug}`),
  setProjectAccess: (
    slug: string,
    body: { access_mode?: string | null; members?: string[] | null },
  ) =>
    http<Project>(`/projects/${slug}/access`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};
