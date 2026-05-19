## ADDED Requirements

### Requirement: Scope-based resolution
For every hook request the system SHALL produce the effective set of kpatches for `(caller_org_id, project_slug, caller_user_id)` by:

1. Collecting every kpatch row matching one of the three scope tuples:
   - `(scope="org", org_id=caller_org_id)`
   - `(scope="project", org_id=caller_org_id, project_slug=project_slug)`
   - `(scope="member", org_id=caller_org_id, project_slug=project_slug, user_id=caller_user_id)`
2. Grouping by `slug` and keeping the row whose `scope` has the highest priority: **`member` > `project` > `org`**.
3. Dropping any row whose `disable` field is `true`.

The resulting list of kpatches (each carrying the triggers of the winning row) SHALL be passed to the trigger engine.

#### Scenario: Project-scope overrides org-scope
- **GIVEN** an org-scope kpatch `commit-conventions` with body `A` and one trigger
- **AND** a project-scope kpatch `commit-conventions` on project `web` with body `B` and two triggers, `disable=false`
- **WHEN** a hook fires on project `web`
- **THEN** the effective set contains the project-scope row only — body `B` and its two triggers — and the org-scope row does not contribute

#### Scenario: Project-scope disable suppresses an org kpatch
- **GIVEN** an org-scope kpatch `commit-conventions` with a body and triggers
- **AND** a project-scope kpatch `commit-conventions` on project `web` with `disable=true` and no triggers
- **WHEN** a hook fires on project `web`
- **THEN** the effective set is empty for that slug and no body or trigger from the org row is evaluated

#### Scenario: Member-scope wins over project-scope
- **GIVEN** a project-scope kpatch `commit-conventions` with body `B`
- **AND** a member-scope kpatch `commit-conventions` for `(project=web, user=u1)` with body `C`
- **WHEN** a hook fires on project `web` as user `u1`
- **THEN** the effective set contains the member-scope row only — body `C`

#### Scenario: No higher-scope row, lower-scope row included as-is
- **GIVEN** only a project-scope kpatch `payments-style` exists for project `web`
- **WHEN** a hook fires on project `web`
- **THEN** the effective set contains that kpatch with its triggers

### Requirement: Resolution feeds the trigger engine
The system SHALL pass only the effective kpatch set (and their effective triggers, including any per-scope variations) to the trigger engine for the hook request. Kpatches outside the effective set SHALL NOT be evaluated.

#### Scenario: Disabled kpatch's triggers never evaluated
- **GIVEN** an org-scope kpatch is shadowed by a project-scope row with `disable=true`
- **WHEN** a hook event arrives that would otherwise match one of the org-scope row's triggers
- **THEN** the trigger does not contribute its kpatch and is not evaluated
