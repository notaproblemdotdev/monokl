---
status: complete
phase: 03-dashboard-ui
source:
  - 03-01-SUMMARY.md
  - 03-02-SUMMARY.md
  - 03-03-SUMMARY.md
  - 03-04-SUMMARY.md
  - 03-05-SUMMARY.md
started: 2026-02-09T12:00:00Z
updated: 2026-02-09T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Dashboard Layout and Initial State
expected: Dashboard opens with two sections. MR section has "Opened by me" and "Assigned to me" subsections. Loading spinners appear briefly.
result: issue
reported: "I dont see merge requests on top. There are two columns 'opened by me' and 'assigned to me'"
severity: minor

### 2. Responsive Layout
expected: When terminal is wide (>=100 cols), MR subsections display side-by-side. When narrow (<100 cols), they stack vertically.
result: issue
reported: "spinners should be centered vertically and horizontally. right they are not."
severity: cosmetic

### 3. Loading State Resolution
expected: Loading spinners resolve to either data table, empty message, or error message within 5-10 seconds.
result: pass

### 4. Data Display Format
expected: Items display with Key + Title + Status. MRs show Author. Work Items show Priority and Assignee.
result: pass

### 5. Empty State Handling
expected: If no items found, section shows appropriate message like "No merge requests found".
result: pass

### 6. Error State Handling
expected: If CLI not installed or not authenticated, section shows error message without crashing.
result: pass

### 7. Tab Key Navigation
expected: Pressing Tab cycles focus: Assigned → Opened → Work Items → back to Assigned. Active section has colored border.
result: issue
reported: "opened by me and assigned to me should be switched, assigned should be on left, first"
severity: minor

### 8. j/k Navigation
expected: When section focused, 'j' moves down, 'k' moves up through items.
result: pass

### 9. Arrow Key Navigation
expected: Up/Down arrows work same as j/k for navigation.
result: pass

### 10. 'o' Key Opens Browser
expected: When item selected, pressing 'o' opens item URL in default browser.
result: issue
reported: "o doesnt work. switching with tab works"
severity: major

### 11. Section-Scoped Selection
expected: Selection is preserved per section when switching between them.
result: issue
reported: "doesnt pass. when i select item in opened by me, click tab twice and work items section is selected, arrows doesnt work in work items but in opened by me"
severity: major

### 12. Quit Application
expected: Pressing 'q' quits dashboard and returns to terminal.
result: issue
reported: "q doesnt work, ctrl + q works"
severity: major

### 13. UI Responsiveness
expected: Dashboard remains responsive during data fetching.
result: pass

### 14. Item Count in Title
expected: Section titles show item count when data loads: "Assigned to me (5)".
result: pass

## Summary

total: 14
passed: 0
issues: 0
pending: 14
skipped: 0

## Gaps

- truth: "Dashboard shows 'Merge Requests' section label/header clearly above the two subsections"
  status: failed
  reason: "User reported: I dont see merge requests on top. There are two columns 'opened by me' and 'assigned to me'"
  severity: minor
  test: 1
  artifacts: []
  missing: []

- truth: "Loading spinners are centered both vertically and horizontally within their sections"
  status: failed
  reason: "User reported: spinners should be centered vertically and horizontally. right they are not."
  severity: cosmetic
  test: 2
  artifacts: []
  missing: []

- truth: "MR subsections display in UI with 'Assigned to me' on the left (first) and 'Opened by me' on the right"
  status: failed
  reason: "User reported: opened by me and assigned to me should be switched, assigned should be on left, first (in UI display)"
  severity: minor
  test: 7
  artifacts: []
  missing: []

- truth: "Pressing 'o' key opens the selected item in the default browser"
  status: failed
  reason: "User reported: o doesnt work. switching with tab works"
  severity: major
  test: 10
  artifacts: []
  missing: []

- truth: "Keyboard navigation (arrows/j/k) works in the currently focused section after Tab switching"
  status: failed
  reason: "User reported: when select item in opened by me, click tab twice and work items section is selected, arrows doesnt work in work items but in opened by me"
  severity: major
  test: 11
  artifacts: []
  missing: []

- truth: "Pressing 'q' key quits the application"
  status: failed
  reason: "User reported: q doesnt work, ctrl + q works"
  severity: major
  test: 12
  artifacts: []
  missing: []

## Summary

total: 14
passed: 8
issues: 6
pending: 0
skipped: 0
