"""Moving a block of selected items inside an ordered list. No UI code.

An "order" is a list of item ids; `selected` is any collection of ids from it. Every function returns a new list and keeps
the selected items together, in the order they already have, so several issues dragged as one block arrive as one block.
"""
from __future__ import annotations


def move_block(order, selected, delta):
    """Shift every selected item one place up (delta -1) or down (+1), keeping their order relative to each
    other. Items already at the edge stay put, and the rest of the block still moves."""
    sel, out = set(selected), list(order)
    for i in (range(len(out)) if delta < 0 else range(len(out) - 1, -1, -1)):
        j = i + delta
        if out[i] in sel and 0 <= j < len(out) and out[j] not in sel:
            out[i], out[j] = out[j], out[i]
    return out


def send_to_edge(order, selected, top):
    """Move the selected items, as one block in their current order, to the very top (or bottom)."""
    sel = set(selected)
    items = [i for i in order if i in sel]
    rest = [i for i in order if i not in sel]
    return items + rest if top else rest + items


def drop_block(order, selected, target):
    """Move the selected items, as one block in their current order, to where `target` is: after it when
    dragging down, before it when dragging up. Dropping on a selected item changes nothing."""
    sel = set(selected)
    if target in sel or target not in order:
        return list(order)
    items = [i for i in order if i in sel]
    if not items:
        return list(order)
    rest = [i for i in order if i not in sel]
    at = rest.index(target) + (1 if order.index(target) > order.index(items[0]) else 0)
    return rest[:at] + items + rest[at:]


def insert_block(order, selected, boundary):
    """Move the selected items, as one block, to the gap `boundary` of the list as it is now: 0 is before the first item,
    len(order) after the last. A gap inside or next to the block leaves the list as it was."""
    sel = set(selected)
    items = [i for i in order if i in sel]
    if not items:
        return list(order)
    rest = [i for i in order if i not in sel]
    at = sum(1 for i in order[:max(0, min(boundary, len(order)))] if i not in sel)
    return rest[:at] + items + rest[at:]
