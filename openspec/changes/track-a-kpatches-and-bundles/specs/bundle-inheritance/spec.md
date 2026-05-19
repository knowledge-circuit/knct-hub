## ADDED Requirements

### Requirement: Layered kpatch resolution
For every hook request, the system SHALL produce the set of effective kpatches for the target project by flattening three layers in order: (1) community bundles imported into the project's org, (2) the org's `default_bundles`, (3) the project's `attached_bundles`. Within and across layers, order SHALL be preserved as encountered; duplicate kpatch ids SHALL be deduplicated keeping the first occurrence.

#### Scenario: Three layers merged in order
- **GIVEN** the project's org has imported community bundle `community-essentials`
- **AND** the org's `default_bundles` is `["team-style"]`
- **AND** the project's `attached_bundles` is `["payments-specific"]`
- **WHEN** a hook request resolves the project's effective kpatches
- **THEN** the result iterates kpatches from `community-essentials`, then `team-style`, then `payments-specific`, with duplicates removed by first occurrence

### Requirement: Project-level disable
The system SHALL exclude any kpatch from the resolved set whose id appears in the project's `disabled_kpatch_ids[]`.

#### Scenario: Disabled kpatch dropped
- **GIVEN** an inherited bundle includes kpatch `commit-conventions`
- **AND** the project's `disabled_kpatch_ids` is `["commit-conventions"]`
- **THEN** the resolved set does not contain `commit-conventions`

### Requirement: Project-level override
The system SHALL allow a project to define `overridden_kpatches[]` — kpatch records keyed by an id that also appears in an inherited bundle. When resolving, the project-level kpatch body and triggers SHALL replace the inherited kpatch entirely.

#### Scenario: Override replaces inherited kpatch
- **GIVEN** an inherited bundle includes kpatch `commit-conventions` with body A and two triggers
- **AND** the project has an override for `commit-conventions` with body B and one trigger
- **WHEN** a hook fires
- **THEN** body B and the one project-level trigger are used, body A and the inherited triggers do not contribute

### Requirement: Resolution feeds the trigger engine
The system SHALL pass only the effective kpatch set (and their effective triggers, including overrides) to the trigger engine for the hook request. Kpatches outside the effective set SHALL NOT be evaluated.

#### Scenario: Disabled kpatch's triggers never evaluated
- **GIVEN** a kpatch is disabled at the project level
- **WHEN** a hook event arrives that would otherwise match one of its triggers
- **THEN** the trigger does not contribute its kpatch and is not evaluated
