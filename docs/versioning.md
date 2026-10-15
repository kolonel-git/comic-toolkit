# Versioning

[< Docs index](README.md)

Git tags follow `vMAJOR.MINOR.PATCH` and stay at `v0.x.y` until the first public release (`v1.0.0`).

- **MINOR** (`v0.8.0`, `v0.9.0`, ...): a finished phase of the [roadmap](roadmap.md), or a new tool or meaningful capability.
- **PATCH** (`v0.7.1`, ...): bug fixes, small behaviour tweaks, documentation-only releases.
- Tags are annotated (`git tag -a`) and sit on the commit that finishes that release, after README and CHANGELOG are updated.
- Work is done one feature per branch and merged by pull request; the tag goes on the merge that completes the phase.

Tags that exist:

| Tag | Contents |
|---|---|
| `v0.1.0` | Initial import: Single issue, Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Clean-up; light/dark themes; settings |
| `v0.1.1` | Backups stored as `.bak` |
| `v0.2.0` | Metadata extensions |
| `v0.3.0` | Shared library scan and the Library Audit tool |
| `v0.4.0` | Reading Order |
| `v0.4.2` | Renamer revamp (cards, a format per type, formatting options, year fixes); `v0.4.1` was not used |
| `v0.5.0` | ACEO sheets |
| `v0.5.1` | Layout and navigation quality-of-life pass |
| `v0.6.0` | Neo-brutalist UI redesign: hard shadows, custom toggles and sliders, folding option panels, clearer empty states and page flow |
| `v0.7.0` | Shared library folder, recent folders, keyboard layer, focus rings and Ctrl+K search bar |

Planned next, one release per phase of the [UI revamp](ui-revamp-plan.md) (a guide; merge or split as the work lands):

| Tag | Contents |
|---|---|
| `v0.8.0` | Phase 1: shared shell kit, Bulk folder and Library stats on the new layout (tagged) |
| `v0.9.0` | Phase 2: Metadata repair editor, Library audit, CBR to CBZ |
| `v0.10.0` | Phase 3: Single issue, Folder icons, Reading order, ACEO sheets |
| `v0.11.0` | Phase 4: Renamer and Add to library |
| `v0.12.0` | Phase 5: links pass, documentation clean-up, packaged Windows build |
| `v1.0.0` | First public release |

See the [roadmap](roadmap.md) for what each phase contains.
