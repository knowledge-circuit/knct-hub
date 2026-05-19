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

export type Org = {
  id: string;
  name: string;
  created_at: string;
  default_bundles: string[];
};

export type OrgMember = {
  user_id: string;
  role: "owner" | "admin" | "member";
  created_at: string;
};

export type Kpatch = {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  body: string;
  keywords: string[];
  created_at: string;
  updated_at: string;
};

export type Trigger = {
  id: number;
  kpatch_org_id: string;
  kpatch_id: string;
  event: "session_start" | "user_prompt" | "pre_tool_use";
  prompt_contains: string[] | null;
  path_match: string | null;
  once_per_session: boolean;
};

export type Bundle = {
  id: string;
  org_id: string;
  name: string;
  version: string;
  kpatch_ids: string[];
  created_at: string;
  updated_at: string;
};

export type Project = {
  slug: string;
  org_id: string;
  created_at: string;
  access_mode: "org" | "invite_only";
  members: string[];
  attached_bundles: string[];
  disabled_kpatch_ids: string[];
  overridden_kpatches: unknown[];
};

export const api = {
  // Orgs
  listOrgs: () => http<Org[]>("/orgs"),
  getOrg: (org: string) => http<Org>(`/orgs/${org}`),
  createOrg: (id: string, name: string) =>
    http<Org>("/orgs", { method: "POST", body: JSON.stringify({ id, name }) }),
  setDefaultBundles: (org: string, bundles: string[]) =>
    http<Org>(`/orgs/${org}/default-bundles`, {
      method: "PUT",
      body: JSON.stringify({ default_bundles: bundles }),
    }),
  listMembers: (org: string) => http<OrgMember[]>(`/orgs/${org}/members`),
  setMemberRole: (org: string, userId: string, role: string) =>
    http<{ user_id: string; role: string }>(
      `/orgs/${org}/members/${userId}`,
      { method: "PUT", body: JSON.stringify({ role }) },
    ),
  removeMember: (org: string, userId: string) =>
    http<void>(`/orgs/${org}/members/${userId}`, { method: "DELETE" }),

  // Kpatches
  listKpatches: (org: string) => http<Kpatch[]>(`/orgs/${org}/kpatches`),
  getKpatch: (org: string, id: string) =>
    http<Kpatch>(`/orgs/${org}/kpatches/${id}`),
  upsertKpatch: (
    org: string,
    id: string,
    body: { name: string; description: string | null; body: string; keywords: string[] },
  ) =>
    http<Kpatch>(`/orgs/${org}/kpatches/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteKpatch: (org: string, id: string) =>
    http<void>(`/orgs/${org}/kpatches/${id}`, { method: "DELETE" }),
  importKpatch: (org: string, md: string) =>
    http<{ kpatch: Kpatch; trigger: Trigger | null }>(
      `/orgs/${org}/kpatches/import`,
      { method: "POST", body: md, headers: { "content-type": "text/markdown" } },
    ),

  // Triggers
  listTriggers: (org: string, kpatchId: string) =>
    http<Trigger[]>(`/orgs/${org}/kpatches/${kpatchId}/triggers`),
  createTrigger: (
    org: string,
    kpatchId: string,
    body: Omit<Trigger, "id" | "kpatch_org_id" | "kpatch_id">,
  ) =>
    http<Trigger>(`/orgs/${org}/kpatches/${kpatchId}/triggers`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateTrigger: (
    org: string,
    kpatchId: string,
    triggerId: number,
    body: Omit<Trigger, "id" | "kpatch_org_id" | "kpatch_id">,
  ) =>
    http<Trigger>(`/orgs/${org}/kpatches/${kpatchId}/triggers/${triggerId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteTrigger: (org: string, kpatchId: string, triggerId: number) =>
    http<void>(`/orgs/${org}/kpatches/${kpatchId}/triggers/${triggerId}`, {
      method: "DELETE",
    }),

  // Bundles
  listBundles: (org: string) => http<Bundle[]>(`/orgs/${org}/bundles`),
  getBundle: (org: string, id: string) =>
    http<Bundle>(`/orgs/${org}/bundles/${id}`),
  upsertBundle: (
    org: string,
    id: string,
    body: { name: string; version: string; kpatch_ids: string[] },
  ) =>
    http<Bundle>(`/orgs/${org}/bundles/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteBundle: (org: string, id: string) =>
    http<void>(`/orgs/${org}/bundles/${id}`, { method: "DELETE" }),

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
  setAttachedBundles: (slug: string, bundles: string[]) =>
    http<Project>(`/projects/${slug}/attached-bundles`, {
      method: "PUT",
      body: JSON.stringify({ attached_bundles: bundles }),
    }),
  setDisabledKpatches: (slug: string, ids: string[]) =>
    http<Project>(`/projects/${slug}/disabled-kpatches`, {
      method: "PUT",
      body: JSON.stringify({ disabled_kpatch_ids: ids }),
    }),
  setOverriddenKpatches: (slug: string, overrides: unknown[]) =>
    http<Project>(`/projects/${slug}/overridden-kpatches`, {
      method: "PUT",
      body: JSON.stringify({ overridden_kpatches: overrides }),
    }),

  // Community (read-only stub — backend lands in group 3+)
  listCommunityBundles: () =>
    http<Bundle[]>("/community/bundles").catch(() => [] as Bundle[]),
  importCommunityBundle: (org: string, bundleId: string) =>
    http<{ ok: boolean }>(`/orgs/${org}/community-imports`, {
      method: "POST",
      body: JSON.stringify({ bundle_id: bundleId }),
    }),
};
