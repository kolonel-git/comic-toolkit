# Versioning

[< Docs index](README.md)

Git tags follow `vMAJOR.MINOR.PATCH` and stay at `v0.x.y` until the first public release (`v1.0.0`).

- **MINOR** (`v0.2.0`, `v0.3.0`, ...): a new tool or a meaningful new capability.
- **PATCH** (`v0.1.1`, ...): bug fixes, small behaviour tweaks, documentation-only releases.
- Tags are annotated (`git tag -a`) and sit on the commit that finishes that release, after README and CHANGELOG are updated.

| Tag | Contents |
|---|---|
| `v0.1.0` | Initial import: Single issue, Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Clean-up; light/dark themes; settings |
| `v0.2.0` | Roadmap items 0-1: backup safety fix and Metadata extensions |
| `v0.3.0` | Roadmap items 2-3: shared library scan and the Library Audit tool |
| `v0.4.0` | Roadmap item 4: Reading Order |
| `v0.5.0` | Roadmap items 5-6: Stats dashboard and folder browser |
| `v0.6.0` | Roadmap item 7: downloads watcher and processing pipeline |
| `v0.7.0` | Roadmap item 8: packaged Windows build |
| `v1.0.0` | First public release |

The planned versions are a guide and can be merged or split as the work lands.

See the [roadmap](roadmap.md) for what each planned release contains.
