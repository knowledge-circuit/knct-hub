## REMOVED Requirements

### Requirement: Skill record shape
**Reason**: Skills are replaced by kpatches owned by orgs rather than projects. See `kpatch-store` for the new record shape — same `id`, `name`, `description`, `body`, `keywords` fields, but keyed by `(org_id, id)` instead of `(project_slug, id)`.
**Migration**: The Alembic revision copies each `skills` row into a new `kpatches` row under the default `solo` org for self-hosted hubs. Cloud deployments will be re-seeded from scratch.

### Requirement: Skill CRUD endpoints
**Reason**: Per-project skill endpoints are removed; kpatches are managed under `/api/v1/orgs/{org}/kpatches`.
**Migration**: Update CLI and dashboard to use the org-scoped endpoints. The dashboard's Skills page becomes the Kpatches page.
