# Versioning

[< Docs index](README.md)

Git tags follow `vMAJOR.MINOR.PATCH` and stay at `v0.x.y` until the first public release (`v1.0.0`).

- **MINOR** (`v0.2.0`, `v0.3.0`, ...): a new tool or a meaningful new capability.
- **PATCH** (`v0.1.1`, ...): bug fixes, small behaviour tweaks, documentation-only releases.
- Tags are annotated (`git tag -a`) and sit on the commit that finishes that release, after README and CHANGELOG are updated.

Tags that exist:

| Tag | Contents |
|---|---|
| `v0.1.0` | Initial import: Single issue, Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Clean-up; light/dark themes; settings |
| `v0.1.1` | Backups stored as `.bak` (roadmap item 0) |
| `v0.2.0` | Metadata extensions (roadmap item 1) |
| `v0.3.0` | Shared library scan and the Library Audit tool (roadmap items 2-3) |
| `v0.4.0` | Reading Order (roadmap item 4) |
| `v0.4.2` | Renamer revamp (cards, a format per type, formatting options, year fixes); `v0.4.1` was not used |
| `v0.5.0` | ACEO sheets |

Planned next (a guide; merge or split as the work lands):

| Tag | Contents |
|---|---|
| `v0.6.0` | Roadmap items 5-6: Stats dashboard and folder browser |
| `v0.7.0` | Roadmap item 7: downloads watcher and processing pipeline |
| `v0.8.0` | Roadmap item 8: packaged Windows build |
| `v1.0.0` | First public release |

See the [roadmap](roadmap.md) for what each planned release contains.
