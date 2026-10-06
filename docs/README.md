# Documentation

Index of the Comic Toolkit docs. The project overview and quick start live in the [main README](../README.md).

| Document | What's in it |
|---|---|
| [Getting started](getting-started.md) | Install, requirements, the RAR extractor for `.cbr` files, where settings are saved |
| [The tools](tools.md) | What each tool does and its options: Single issue, Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Clean-up, Library audit |
| [Naming styles and templates](renamer-templates.md) | The eight Renamer presets and the custom template syntax |
| [Safety model](safety.md) | Previews, verified writes, the `Archive` folder, conflict handling |
| [Architecture](architecture.md) | Project layout and what each module is responsible for |
| [Manual tests](manual-tests.md) | Hands-on checks that need real comics, the real window or YACReader, with an expected result for each |
| [Known limitations](known-limitations.md) | What is untested, Windows-only, heuristic, or likely to surprise you |
| [Roadmap](roadmap.md) | Findings from the latest review and the ordered build plan |
| [Reading Order (planned)](reading-order.md) | Full specification of the planned reading-order tool |
| [Versioning](versioning.md) | Tag scheme (`v0.x.y`) and planned releases |
| [Changelog](CHANGELOG.md) | Timestamped record of every working session |

## Keeping the docs current

At the end of every working session:

- add a new timestamped block at the **top** of [CHANGELOG.md](CHANGELOG.md): what was done and why, decisions, changes by file,
  bugs found and fixed, and only the verification that was actually run;
- update whichever docs above describe behaviour that changed (usually [The tools](tools.md), [Known limitations](known-limitations.md)
  and [Roadmap](roadmap.md)), and the [main README](../README.md) if the overview changed.
