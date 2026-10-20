# Documentation

Index of the Comic Toolkit docs. The project overview and quick start live in the [main README](../README.md).

| Document | What's in it |
|---|---|
| [Packaging](packaging.md) | Building the double-click folder version, where settings and bundled files live, the `tools` folder for `.cbr` support |
| [Getting started](getting-started.md) | Install, requirements, the RAR extractor for `.cbr` files, where settings are saved |
| [The tools](tools.md) | What each tool does and its options: Single issue, Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Library audit, Reading order, ACEO sheets |
| [Naming styles and templates](renamer-templates.md) | Every Renamer option: template syntax, tokens, token formats, a format per type, text options, folders and how names are read |
| [Safety model](safety.md) | Previews, verified writes, the `Archive` folder, conflict handling |
| [Architecture](architecture.md) | Project layout and what each module is responsible for |
| [Manual tests](manual-tests.md) | Hands-on checks that need real comics, the real window or YACReader, with an expected result for each |
| [Known limitations](known-limitations.md) | What is untested, Windows-only, heuristic, or likely to surprise you |
| [Roadmap](roadmap.md) | The build order (the UI revamp, phase by phase), what is built, and future implementations |
| [UI revamp plan](ui-revamp-plan.md) | The agreed redesign of every page: shared segmented layout, per-tool changes, links between tools, future work |
| [Reading Order](reading-order.md) | How the reading-order tool works, its options, and how YACReader treats the result |
| [Versioning](versioning.md) | Tag scheme (`v0.x.y`), the tags that exist, and one planned release per roadmap phase |
| [Changelog](CHANGELOG.md) | Timestamped record of every working session |

## Keeping the docs current

At the end of every working session:

- add a new timestamped block at the **top** of [CHANGELOG.md](CHANGELOG.md): what was done and why, decisions, changes by file,
  bugs found and fixed, and only the verification that was actually run;
- update whichever docs above describe behaviour that changed (usually [The tools](tools.md), [Known limitations](known-limitations.md)
  and [Roadmap](roadmap.md)), and the [main README](../README.md) if the overview changed.
