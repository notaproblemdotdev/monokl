---
status: investigating
trigger: "Todoist work items not displaying in UI even though fetched and cached. 27 tasks cached, UI shows 'No work items'"
created: 2026-02-17
updated: 2026-02-17
---

## Current Focus

hypothesis: CONFIRMED - Protocol/Model attribute name mismatch. PieceOfWork protocol requires `piece_icon`/`piece_type` but models have `adapter_icon`/`adapter_type`. UI accesses `item.piece_icon` which fails, causing items to be skipped.
test: Examined models.py and sections.py, verified with Python test
expecting: AttributeError when accessing piece_icon on deserialized models - CONFIRMED
next_action: Document complete findings and fix recommendation

## Symptoms

expected: Todoist work items should display in UI after being fetched and cached
actual: UI shows "No work items" despite 27 tasks being fetched and cached
errors: Items silently skipped in UI (try/except catches AttributeError)
reproduction: Fetch Todoist items, they cache, but UI shows nothing
started: Unknown

## Eliminated

- Cache storage issue: Data is correctly stored and retrieved from database
- Serialization format: model_dump() correctly includes adapter_type field
- Deserialization method: _deserialize_single_work_item correctly routes to TodoistTask.model_validate()
- Todoist-specific issue: This affects ALL work item types (Jira, GitHub, Todoist)

## Evidence

- 2026-02-17: Examined work_store.py _deserialize_work_items (lines 314-342)
  - Correctly looks for adapter_type field in cached data
  - Correctly validates with TodoistTask.model_validate(item)
  
- 2026-02-17: Examined models.py
  - GitHubPieceOfWork (line 287-288): Has `adapter_icon: str = "🐙"` and `adapter_type: str = "github"`
  - JiraPieceOfWork (line 384-385): Has `adapter_icon: str = "🔴"` and `adapter_type: str = "jira"`
  - TodoistPieceOfWork (line 502-503): Has `adapter_icon: str = "📝"` and `adapter_type: str = "todoist"`
  - PieceOfWork protocol (line 59-60): Requires `piece_icon: str` and `piece_type: str`

- 2026-02-17: Examined sections.py
  - Line 627: `icon = item.piece_icon` - TRIES TO ACCESS piece_icon
  - Lines 647-649: try/except silently catches AttributeError and skips items
  - This causes ALL items to be skipped because none have `piece_icon` attribute

- 2026-02-17: Python test confirmed:
  - Created TodoistPieceOfWork instance: SUCCESS
  - Accessing adapter_icon: SUCCESS (returns "📝")
  - Accessing adapter_type: SUCCESS (returns "todoist")
  - Accessing piece_icon: AttributeError - 'TodoistPieceOfWork' object has no attribute 'piece_icon'

- 2026-02-17: LSP/type checker errors confirm:
  - "TodoistPieceOfWork" is incompatible with protocol "PieceOfWork"
  - "piece_icon" is not present
  - "piece_type" is not present
  - Same errors for GitHubPieceOfWork and JiraPieceOfWork

## Resolution

root_cause: ATTRIBUTE NAME MISMATCH between protocol and implementations.

The PieceOfWork protocol (lines 50-88 in models.py) defines required attributes:
- Line 59: `piece_icon: str`
- Line 60: `piece_type: str`

But ALL three model implementations use different names:
- GitHubPieceOfWork (lines 287-288): `adapter_icon`, `adapter_type`
- JiraPieceOfWork (lines 384-385): `adapter_icon`, `adapter_type`  
- TodoistPieceOfWork (lines 502-503): `adapter_icon`, `adapter_type`

When the UI (sections.py line 627) accesses `item.piece_icon`, it raises AttributeError because the attribute doesn't exist. The try/except block (lines 647-649) silently catches this and continues, skipping the item. Since ALL items have this problem, NO items are displayed.

The LSP/type checker has been flagging this as an error, but it was not fixed.

fix: Update the PieceOfWork protocol to match the implementation names.

File: src/monocli/models.py
Lines: 59-60 (in the PieceOfWork protocol)
Change:
```python
    # Adapter metadata
    piece_icon: str
    piece_type: str
```
To:
```python
    # Adapter metadata
    adapter_icon: str
    adapter_type: str
```

Also update sections.py line 627:
Change:
```python
icon = item.piece_icon
```
To:
```python
icon = item.adapter_icon
```

Rationale for this fix:
1. `adapter_icon`/`adapter_type` is already used consistently across ALL three model implementations
2. Only the protocol has the mismatched naming
3. This requires minimal changes (2 lines in models.py, 1 line in sections.py)
4. All existing code already expects `adapter_*` naming

files_changed:
- src/monocli/models.py: Change protocol attributes from piece_icon/piece_type to adapter_icon/adapter_type
- src/monocli/ui/sections.py: Change line 627 from piece_icon to adapter_icon

verification: After fix, work items should display correctly. The LSP errors about protocol incompatibility should also be resolved.
