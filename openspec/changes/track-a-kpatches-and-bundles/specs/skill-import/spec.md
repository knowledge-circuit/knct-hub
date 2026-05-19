## REMOVED Requirements

### Requirement: Skill markdown source format
**Reason**: Replaced by `kpatch-import`'s markdown format, which is structurally identical (frontmatter + body) and adds an optional `trigger` block.
**Migration**: Existing `.md` skill files import cleanly as kpatches without changes; the optional trigger block is purely additive.

### Requirement: Required and optional frontmatter fields
**Reason**: Same fields are required by `kpatch-import` (`id`, `name`) and same optional fields are accepted (`description`, `keywords`).
**Migration**: No action.

### Requirement: Import entry points in the dashboard
**Reason**: Re-stated under `kpatch-import` for the Kpatches page; the Skills page is removed.
**Migration**: The dashboard navigation entry "Skills" is renamed/replaced by "Kpatches"; the import UI moves with it.

### Requirement: Preview dialog with editable parsed fields
**Reason**: The preview dialog is preserved by `kpatch-import` in spirit, but the explicit dialog behavior is treated as implementation detail in Track A and not re-specified. If detailed dialog behavior is required, it will be added back in a follow-up spec.
**Migration**: The dashboard MAY keep the existing dialog implementation; it is no longer a normative requirement.

### Requirement: Silent upsert on conflict
**Reason**: Re-stated under `kpatch-import` as "Re-import preserves existing triggers"; upsert semantics on `id` collision are preserved.
**Migration**: No action; behavior is unchanged for collisions on `id`.

### Requirement: Inline parse-error feedback
**Reason**: Same UX is expected for the Kpatches import surface but is not re-specified as a normative requirement in Track A.
**Migration**: The dashboard MAY keep the existing inline error UX.
