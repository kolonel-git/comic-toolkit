# Naming styles and templates

[< Docs index](README.md)

Used by the Renamer. See [The tools](tools.md) for how the Renamer works.

## Naming presets

`Series 001 (2016)` · `Series #001 (2016)` · `Series v2 001 (2016)` · `Series Vol 2 #001 (2016)` ·
`Series - 001 - Title (2016)` · `Series 001 - Title` · `Series (2016) 001` · `Series 001`

## Custom templates

Custom templates use the tokens `{series}` `{volume}` `{issue}` `{year}` `{title}`. Wrap optional parts in `[ ]`:
the whole group disappears when any value inside it is empty, e.g. `{series}[ v{volume}][ #{issue}][ ({year})]`.
