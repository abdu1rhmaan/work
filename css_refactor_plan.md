# CSS REFACTOR PLAN

## Phase 0 — Safety & Snapshot
* **Exact Goal**: Secure a baseline to prevent any accidental visual or behavioral regressions.
* **Affected Files**: `styles.tcss`, all `.py` files containing UI components (for `DEFAULT_CSS`).
* **Patterns to Search For**: N/A for this phase.
* **Rules to Keep/Remove/Merge**: N/A for this phase.
* **How to Verify No Visual Change**: Take comprehensive screenshots of all application states (Dashboard, Windows, Modals, Hover States). Save a copy of the current `styles.tcss` as `styles_backup.tcss` or via Git branch.
* **Risk Level**: Low
* **Dependencies**: None.

## Phase 1 — Duplicate Selector Resolution
* **Exact Goal**: Eliminate multiple declarations of the same selector without altering the final computed styles.
* **Affected Files**: `styles.tcss`
* **Patterns to Search For**: 
  - `CustomButton` (Lines 104, 139)
  - `CustomButton:hover` (Lines 134, 1687)
  - `CustomButton:focus` (Lines 119, 1692)
  - `#days-header` (Lines 1175, 1728)
  - `.day-cell` (Lines 1210, 1739)
  - `#main-buttons` (Lines 25, 96)
* **Rules to Keep/Remove/Merge**:
  - Merge `#main-buttons` blocks. Keep `padding: 0 1` from line 25, use `margin-bottom: 1` from line 96.
  - Merge `CustomButton` blocks. Drop the background color in line 104 in favor of line 139.
  - Consolidate `#days-header`. Preserve the explicit `grid-columns` from line 1175, but use the colors and margins from line 1728.
  - Consolidate `.day-cell`. Keep all sizing from line 1210 and add `content-align` from line 1739.
* **How to Verify No Visual Change**: Restart application and inspect affected components (Buttons, Calendar grid, Dashboard layout). Computed styling should match the backup precisely.
* **Risk Level**: Medium (Cascading overrides mean sequence matters).
* **Dependencies**: Phase 0.

## Phase 2 — Conflict & !important Cleanup
* **Exact Goal**: Remove unnecessary `!important` flags and resolve priority wars between generic states and contextual wrappers.
* **Affected Files**: `styles.tcss`
* **Patterns to Search For**: `!important` tags, conflicting hover states like `CustomButton:hover` vs `.window-mode #main-buttons CustomButton:hover`.
* **Rules to Keep/Remove/Merge**:
  - Remove global `!important` from `CustomButton:hover` (Line 1687). Relies on natural specificity.
  - For `.window-mode` overriding hovers, ensure the selector specificity naturally outweighs child elements without needing `!important`.
  - Resolve `Input.-invalid` vs `Input:focus` border conflicts.
* **How to Verify No Visual Change**: Trigger hover and focus states heavily, especially when a window is mounted (`window-mode`). Verify buttons don't flash blue.
* **Risk Level**: High (Removing `!important` cascades unpredictably if DOM hierarchy isn't strict).
* **Dependencies**: Phase 1.

## Phase 3 — Layout Integrity Validation
* **Exact Goal**: Fix unsafe layout constraints that risk overflow or content clipping on irregular terminal sizes.
* **Affected Files**: `styles.tcss`, UI Python files establishing layout grids.
* **Patterns to Search For**: `width: 85%` with fixed `padding`/`margin` lacking `box-sizing: border-box`. Hardcoded `height` on list components inside flexible containers. `align` vs `absolute` positioning mixes.
* **Rules to Keep/Remove/Merge**:
  - Add `box-sizing: border-box;` to `.modal-dialog`, `#txn-details-dialog`, and `#add-order-dialog` to prevent their internal paddings from inflating the 85% width.
  - Convert `#expense-list` hardcoded `height: 10` to `max-height: 10; height: auto` or `height: 1fr` within a sized parent.
  - Enforce explicit grid columns (e.g., `grid-columns: 1fr 1fr;`) on `#main-buttons` instead of relying entirely on `grid-size: 2`.
* **How to Verify No Visual Change**: Resize the terminal aggressively. Observe `#expense-list` wrapping and Modal borders. Ensure no internal scrollbars appear on percentage-width modals.
* **Risk Level**: High (Layout logic shifts).
* **Dependencies**: Phase 2.

## Phase 4 — Dead CSS Removal
* **Exact Goal**: Remove styles referencing deleted or inactive UI components to declutter the file.
* **Affected Files**: `styles.tcss`
* **Patterns to Search For**: `#global-footer`, `.expense-row`, `.break-row`, `ShiftTimerDisplay` mappings, deprecated `#shifts-history-dialog` ID-specific overrides if generalized to `BaseWindow`.
* **Rules to Keep/Remove/Merge**:
  - Delete `.window-mode #global-footer` blocks.
  - Delete `.expense-row` and `.break-row` selectors entirely if a global search in `.py` files confirms zero usage.
* **How to Verify No Visual Change**: Visual appearance should be identical since these elements do not exist in the DOM.
* **Risk Level**: Low.
* **Dependencies**: Phase 1.

## Phase 5 — Specificity & Cascade Stabilization
* **Exact Goal**: Flatten overly complex CSS selectors to make future theming possible without specificity arms races.
* **Affected Files**: `styles.tcss`
* **Patterns to Search For**: Triple ID/Class chains like `#txn-details-dialog.txn-details-in #title`. Confusing state classes (`.has-shift` vs `.day-cell.has-shift`).
* **Rules to Keep/Remove/Merge**:
  - Simplify `#txn-details-dialog.txn-details-in #title` to `.txn-details-in #title` or ideally assign a specific class directly to the title widget.
  - Consolidate `.has-shift` styling onto a single class definition, rather than splitting properties between a generic `.has-shift` and a contextual `.day-cell.has-shift`. Let the DOM class handle the styling.
* **How to Verify No Visual Change**: Inspect Transaction Details headers and Calendar Shift indicators for correct background/text colors.
* **Risk Level**: Medium.
* **Dependencies**: Phase 2.

## Phase 6 — Textual Compatibility Audit
* **Exact Goal**: Clean up properties that are either invalid, poorly supported, or problematic in Textual.
* **Affected Files**: `styles.tcss`
* **Patterns to Search For**: `scrollbar-size: 0 0;`, `display: block;` (on non-block native widgets), extreme `tint:` usage over transparent backgrounds.
* **Rules to Keep/Remove/Merge**:
  - Consider replacing `scrollbar-size: 0 0;` with `overflow-y: hidden;` if scrolling is entirely disabled, or accept minimal scrollbars if scrolling is required.
  - Remove redundant `display: block;` from `BaseWindow` (Textual defaults most containers to block).
* **How to Verify No Visual Change**: Check scrolling capability on history lists. Ensure `BaseWindow` backgrounds render correctly without double opacity shifting.
* **Risk Level**: Low.
* **Dependencies**: Phase 5.

## Phase 7 — Performance Cleanup
* **Exact Goal**: Minimize rendering passes caused by universal selectors (`*`) and transparency logic.
* **Affected Files**: `styles.tcss`
* **Patterns to Search For**: `*:hover`, extensive use of `transparent` backgrounds.
* **Rules to Keep/Remove/Merge**:
  - Refactor `.window-mode #info-row *:hover` to target exactly the widgets that receive hover states natively (e.g., `#info-row Static:hover`). Universal selectors force full DOM tree traversal on every mouse movement.
  - Minimize `transparent` layers in deeply nested modal content areas if a solid color can be applied instead.
* **How to Verify No Visual Change**: App should behave identically. Monitor CPU usage during rapid mouse movement over the dashboard when a window is open to observe performance gains.
* **Risk Level**: Medium.
* **Dependencies**: Phase 5.

## Validation Strategy
* **Automated Checks**: Running `textual colors` or similar linters against the `.tcss` file if available.
* **Manual Verification Approach**:
    1. Start the application before changes, capture screenshots of Dashboard, Settings Modal, History List, Wallet, and Calendar.
    2. After *each phase*, restart the application.
    3. Perform side-by-side comparisons of the screenshots.
    4. Focus heavily on Hover/Focus interactions (Tab cycling, mouse roaming) after Phases 2 and 7.
    5. Test terminal resizing horizontally and vertically after Phase 3.

## Rollback Strategy
* Before starting, branch the Git repository or duplicate the `src/` folder.
* Keep a master copy of the original `styles.tcss`.
* If a visual regression is detected after applying a phase:
    1. Revert to the exact state before that specific phase.
    2. Do NOT attempt to brute-force a fix by adding `!important` tags.
    3. Re-evaluate why the specificity or cascade logic failed.
    4. If the generic fix cannot be isolated safely without visual disruption, abandon the specific rule consolidation and document the exception.
