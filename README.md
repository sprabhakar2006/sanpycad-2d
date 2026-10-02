# SanPyCAD 2D Sketch

A small, focused, freeform 2D profile sketcher. Click to draw lines,
arcs, circles, and rectangles; round any corner with a real fillet;
then export the finished outline as a plain Python point list, ready
to paste into a SanPyCAD script (`polygon(sec)`, `prism(sec, path)`,
`cr2dt(...)`, etc.).

Every curve you draw is computed by **ocad.py itself** -- the
same 2D functions (`arc_2p`, `arc_3p`, `circle`, `fillet3points`,
`corner_radius`) that back SanPyCAD's own scripts -- not reimplemented
in JavaScript. The canvas only sends click coordinates to the backend
and draws back whatever real point list ocad.py returns, so an
exported profile behaves exactly like one built by hand-writing those
same function calls.

## Install

Grab the build for your machine from the
[latest release](../../releases/latest), unzip it, and open it. Each
download carries its own Python and every library it needs -- nothing
to install.

| Platform | Download | Open it |
|---|---|---|
| macOS (Apple Silicon) | `SanPyCAD-2D-mac-arm64.zip` | double-click `SanPyCAD-2D.app` |
| Windows 10/11 (x64) | `SanPyCAD-2D-win-x64.zip` | open the folder, double-click `SanPyCAD-2D.exe` |

**First launch on macOS** shows "SanPyCAD-2D cannot be opened because
the developer cannot be verified" -- the app is not notarized by
Apple. Right-click the app → **Open** → **Open**, once. Every launch
after that is a normal double-click.

**First launch on Windows** may show a SmartScreen banner for the same
reason: **More info** → **Run anyway**.

Prefer to run from the source instead? See
[Running from source](#running-from-source).

## Running from source

```
pip install -r requirements.txt
python3 app.py
```

This opens a desktop window (via `pywebview`) if it's installed, or
your default browser otherwise -- the geometry backend is the same
local server either way, started automatically with no separate step
needed. Python 3.10 or newer (the geometry library uses `match`
statements).

## Using it

- **Pan/zoom**: scroll (or Space+drag, or the middle mouse button) to
  pan; hold a real `Ctrl`/`Cmd` key while scrolling to zoom instead.
  Zoom requires an actual tracked keyboard press of Control/Cmd, not
  just a wheel event that happens to report `ctrlKey: true` -- WebKit
  (this app's macOS backend) reports a trackpad pinch as exactly that
  kind of wheel event with no real Control key involved, which used to
  mean incidental trackpad contact during ordinary clicking could
  silently satisfy the check and zoom the view with no scroll or
  keypress the user could point to, compounding a little further with
  every click and no way back short of Zoom to fit. Requiring a real
  keyboard press closes that gap, at the cost of no longer supporting
  a deliberate trackpad pinch to zoom (this app is mouse-first; a
  wheel with `Ctrl`/`Cmd` held is the supported zoom gesture). If the
  view ever ends up stuck/zoomed weirdly, **Zoom to fit** (bottom of
  the left toolbar, under View) recenters and rescales to whatever's
  currently drawn. Separately, this app's own zoom is not the app
  window's *native* zoom -- a stray pinch/gesture signal landing
  anywhere outside the canvas (the toolbar, the sidebar) used to have
  nothing stopping it from triggering the OS/webview's own native page
  zoom instead, which has no in-app undo; the app now blocks that
  everywhere on the page, not just on the canvas. And any interaction
  that's "armed" by a keydown/mousedown (panning, Space-to-pan, box
  select) is now automatically cleared if the app window loses focus
  before the matching keyup/mouseup arrives -- e.g. switching to the
  inspector or another app mid-drag -- so a stuck flag from that can't
  silently keep nudging the view or swallow the next click.
- **Line** (`L`): click to place points one at a time. Or type an
  exact length + angle in the box that appears and click *Add point*
  to place the next vertex precisely instead of by eye.
- **Arc (2pt+radius)** (`A`): click 2 points (start, then end) for a
  standalone arc, or -- with a line already in progress -- just click
  the end point to continue that line as an arc. Either way, set a
  radius and pick clockwise/counter-clockwise afterward, plus **Short
  arc**/**Long arc** -- any radius big enough to span the 2 points has
  two valid arcs joining them (the short way around and the long way
  around, `arc_2p`/`arc_long_2p`); short is the default.
- In any numeric entry box (radius, distance, angle, length/breadth,
  etc.), pressing **Enter** submits it -- no need to click the button.
- **Arc (3 clicks)** (`3`): click any 3 points to fit a standalone arc
  through them (`arc_3p`).
- **Circle** (`C`): click a center, then click again (or type a
  radius) to set its size. Circles are their own separate entity --
  handy for holes.
- **Rectangle** (`R`): click two opposite corners.
- **Round corner** (`F`): click a corner of the shape you're currently
  drawing, of any already-finished shape, the point where two separate
  finished lines/polylines happen to meet (e.g. two lines drawn
  end-to-end rather than as one continuous chain), or the start point
  of a shape you closed manually (clicked back on its own start point
  and finished with Enter/Esc instead of Close) -- then set a radius --
  replaces that sharp corner with a real fillet arc (`fillet3points`),
  merging shapes / cleaning up the closure into one entity where
  needed. If the corner's two edges are themselves circular arcs rather
  than straight lines -- e.g. the pointed tip of a lens/vesica shape
  made of 2 overlapping circles -- this is detected automatically and
  `two_cir_tarc_internal` is used instead, fitting the fillet tangent
  to the actual circles the arcs lie on. A straight-line fillet there
  would only match the two edges' tangent direction at the corner, not
  their curvature, letting it cut back across the originals and
  self-intersect for anything but a tiny radius.
- **Close shape** (`X`) / **Finish (open)** (`Enter` or `Esc`):
  finalizes the shape you're currently drawing (closed loop or open
  polyline) and starts a fresh one -- a single stray click with nothing
  else placed is dropped rather than saved as a shapeless 1-point
  entity. `Esc` also finishes the active shape (same as `Enter`)
  whenever nothing else is pending -- when a
  multi-click tool (Rectangle, Arc-3pt, Move, etc.) is mid-click,
  `Esc` instead just cancels that one step. Undo (`Cmd/Ctrl+Z`) and
  Redo work across the whole sketch.
- **Export**: turns every finished shape (plus whatever's still in
  progress) into one or more `sec = [[x, y], ...]`-style Python lists
  in the panel on the right -- copy and paste straight into a script.
  Multiple shapes (e.g. an outer profile plus circles for holes) come
  out as `sec`, `sec2`, `sec3`, ... Hatch lines export as a list of
  2-point segments; dimensions are on-screen annotations only and
  aren't exported.
- **Save as PDF**: saves the whole sketch -- every shape, hatch,
  dimension, and text label -- as a real vector PDF (not a screenshot),
  fitted to a US Letter page and downloaded straight to your browser's
  downloads folder. Built entirely in the browser, no extra install
  needed.

### Selecting and editing existing shapes

- **Select** (`V`): click a shape to select it (Shift-click to
  add/remove more); selected shapes highlight and also list under
  *Finished entities* in the sidebar, where you can click an entry to
  select it or use its `x` to delete it. `Delete`/`Backspace` removes
  whatever's currently selected. Dragging on empty space instead draws
  a selection box -- drag left-to-right for a **window** box (only
  shapes entirely inside it get selected, drawn solid blue) or
  right-to-left for a **crossing** box (anything the box touches at
  all, even just grazing it, gets selected too, drawn dashed cyan) --
  the standard AutoCAD convention. Releasing the mouse without moving
  it just clears the selection, same as clicking empty space always
  has.
- **Properties** (sidebar, appears when exactly one shape is selected):
  edit its own dimensions directly as numbers instead of dragging --
  Radius for a circle, Length/Breadth for an axis-aligned rectangle,
  Length/Angle for a straight 2-point line. Click directly on a rounded
  corner (made with Round Corner) to select that specific corner too --
  its Fillet radius becomes editable, re-running the fillet at the new
  radius in place; click a different rounded corner on the same shape
  to switch to editing that one instead. Type a value and press Enter
  or click away to apply. A shape that's been rotated, or isn't one of
  these simple cases (an arc, a multi-point polyline with no rounded
  corner clicked, ...), shows a note instead -- reshape it with
  Trim/Fillet/Chamfer, or move it with Move/Rotate.
- **Move** (`M`): with shape(s) selected, click a base point then a
  destination point.
- **Rotate** (`T`): click a center point, then type a rotation angle.
- **Mirror** (`I`): click two points to define the mirror line, then
  choose whether to keep the original or replace it.
- **Copy** (`Y`): click a base point, then click as many destinations
  as you like (each click drops another copy) -- `Esc` when done.
- **Rotate array** (`Z`): with shape(s) selected, click a pivot point
  -- inside the shape, outside it, anywhere -- then set the angle per
  copy and how many copies to create. The original stays put; copies
  land at 1x, 2x, 3x, ... that angle around the pivot (e.g. 60 degrees
  x 5 copies fills a full circle with 6 shapes total, evenly spaced).
- **Linear array** (`0`): with shape(s) selected, click 2 points to
  set a direction, then set the exact pitch (spacing between copies)
  and how many copies to create along that direction -- the pitch
  field starts pre-filled with the distance you just clicked, but
  overwrite it for a precise value.
- **Offset** (`O`): click a shape, then type a distance (try a
  negative number if it offsets to the wrong side) -- creates a new
  offset copy alongside the original, via `ocad.py`'s own
  `offset()`/`path_offset()`.
- **Chamfer** (`H`): the straight-cut sibling of Round corner -- click
  a corner, then set how far back along each edge to cut.
- **Trim** (`G`): click the piece of a shape you want removed, bounded
  by wherever it crosses other shapes -- ordinary AutoCAD TRIM
  semantics (click what should disappear, not what should stay).
- **Difference** (`D`): click the shape to keep, then the shape to cut
  it with. Since this app has no real polygon-boolean library
  available, the cut is computed by rasterizing both shapes to a fine
  grid and re-tracing the result's contour -- accurate enough for
  sketching, but corners come back very slightly rounded/faceted
  rather than perfectly sharp.
- **Hatch lines** (`K`): select one or more shapes first (a profile
  plus a circle "hole" inside it works too -- the hole is excluded
  automatically), switch to Hatch, then set an angle and spacing.

### Tangent & hull

Every tool in this section accepts a rounded corner (fillet arc) on a
shape anywhere a circle is asked for, not just standalone circle
entities -- click near the arc the same way you would a circle. This
works because the underlying tangent math only needs 3 spread-out
points to fit a circle, so a small arc is just as valid an input as a
full circle.

- **Two-circle tangent** (`4`): click 2 circles or rounded corners,
  then pick a side -- draws the straight external tangent line joining
  them (`twoCircleTangentPoints`).
- **Two-circle cross tangent** (`5`): click 2 circles or rounded
  corners, then pick a direction -- draws the crossing (internal)
  tangent line between them (`twoCircleCrossTangent`).
- **Two-circle tangent arc** (`6`): click 2 circles or rounded corners,
  then set a radius and side -- draws an arc tangent to both
  (`two_cir_tarc`). Too small a radius can't reach between them -- if
  you get an error, try a bigger radius or the other side.
- **Point-to-circle tangent** (`P`): click a point outside a circle,
  then click the circle or a rounded corner -- draws the tangent line
  from that point to it (`p_cir_t`).
- **Circle/line tangent** (`7`): click a circle or rounded corner, then
  click an existing drawn line, then pick a side -- draws a new line
  the same length as the one you clicked, tangent to it and parallel
  to the reference line (`cir_line_tangent`).
- **Convex hull** (`8`): select one or more shapes first (Select tool,
  Shift-click for more), switch to Convex hull, then generate -- draws
  the convex hull polygon around every point in the selection
  (`convex_hull`).
- **Concave hull** (`9`): same as Convex hull, but traces a tighter,
  concave outline instead (`concave_hull`) -- needs at least 6 points
  total across the selection; falls back with an error on smaller or
  too-clustered point sets (try Convex hull instead).
- **Bezier curve** (`S`): click a series of control points, then
  `Enter` to draw the smooth curve through them (`bezier`) -- `Esc`
  cancels the curve instead of finishing it, unlike other draw tools.

### Dimensions

- **Linear** (`J`): click 2 points to measure between, then a 3rd
  point to place the dimension line's offset. Select it afterward and
  use the **Measure** toggle in Properties to switch between the true
  point-to-point Distance and axis-only **dx** (horizontal) or **dy**
  (vertical) separation -- the dimension line redraws horizontal or
  vertical accordingly, AutoCAD-style. This also works on
  Center-to-center/Center-to-edge/Edge-to-edge dimensions, since
  they're the same underlying dimension type.
- **Radius** (`U`): click a circle or a rounded corner to label its
  radius. Select it afterward and use the **Leader** toggle in
  Properties to switch between Inside (leader runs from the center out
  to the edge, the default) and Outside (leader runs from the edge
  outward to wherever you drag it) -- useful when the circle or fillet
  is too small to fit the line and label inside it comfortably.
- **Center-to-center** (`N`): click 2 centers -- each can be a circle
  or a rounded corner (click near its center mark) -- then a 3rd point
  to place the dimension line -- measures the distance between them.
- **Center-to-edge** (`E`): click a center (a circle, or a rounded
  corner), then click an edge -- measures the shortest distance from
  that center to the edge.
- **Edge-to-edge** (`B`): click one edge, then another -- measures the
  shortest distance between them (0 if they cross).
- **Angle** (`Q`): click one edge, then another that crosses it, then
  click to size the angle arc -- labels the angle between them.
- Every dimension can be dragged back into place at any time, in any
  tool: click and drag its dimension/leader line to move it (for
  Angle, this resizes the arc).
- Circles show a small crosshair at their center at all times, and so
  does every rounded corner (fillet) on any shape -- both are always
  visible and are what Center-to-center/Center-to-edge click on to
  identify which center is meant, especially when a shape has more
  than one rounded corner.

### Text and label positioning

- **Text** (`W`): click a point and type a label.
- Every dimension's number and every Text label can be dragged
  independently of the dimension line/leader it belongs to -- click
  and drag the text itself to move just the label (handy when two
  numbers land too close together, or a label needs to move out of
  the way). This works in any tool, not just Select.
- Drag the small square handle at a label's bottom-right corner to
  grow or shrink its text size.

Pan by holding **Space** and dragging (works in every tool, and is the
most reliable option on a trackpad), or with Shift+drag or the middle
mouse button -- in the Select tool, Shift+drag pans while a plain
Shift+click still toggles a shape in/out of the selection as usual.
Zoom with the scroll wheel. Grid snapping is on by default (adjustable
grid size in the toolbar) and always snaps to nearby existing points
first, so chained segments join up exactly.

## Files

- `SanPyCAD-2D.app` (macOS) / `SanPyCAD-2D.exe` (Windows) -- the
  self-contained bundle from [Install](#install), no command line, no
  Python to install.
- `app.py` -- desktop-window launcher the bundle runs under the hood
  (same pywebview-or-browser pattern as SanPyCAD's own `app.py`).
- `packaging/build_bundle.py` -- builds that bundle; see
  [Building the bundle](#building-the-bundle) below.
- `backend/server.py` -- small stdlib-only HTTP backend (no Flask
  needed, matching SanPyCAD's own philosophy) exposing the routes the
  canvas calls (`/api/arc2p`, `/api/arc3p`, `/api/circle`,
  `/api/fillet_corner`, `/api/corner_radius`, `/api/offset_shape`,
  `/api/chamfer_corner`, `/api/difference`, `/api/trim`, `/api/hatch`,
  `/api/two_circle_tangent`, `/api/two_circle_cross_tangent`,
  `/api/two_circle_tangent_arc`, `/api/point_circle_tangent`,
  `/api/circle_line_tangent`, `/api/convex_hull`, `/api/concave_hull`,
  `/api/bezier_curve`, `/api/export`).
- `backend/ocad.py` -- the real geometry engine (copied from
  SanPyCAD; only its 2D functions are used here).
- `backend/geom_ops.py` -- the AutoCAD-style editing operations that
  ocad.py has no equivalent for (Difference, Trim, Hatch,
  Chamfer); Offset and Fillet instead reuse ocad.py's own
  `offset()`/`path_offset()`/`fillet3points()` directly.
- `frontend/index.html` -- the whole UI: canvas, toolbar, and export
  panel, in one file.

## Building the bundle

```bash
pip install pyinstaller
python packaging/build_bundle.py
```

This produces `dist/SanPyCAD-2D.app` (macOS) or `dist/SanPyCAD-2D/`
(Windows, Linux) plus a zip of it, with Python and every dependency
inside. On macOS you can also just double-click
`Build and Launch SanPyCAD-2D.command`, which does this and opens the
result in one step.

PyInstaller cannot cross-compile, so each platform's bundle has to be
built on that platform. `.github/workflows/build-installers.yml` runs
this same script on GitHub's macOS and Windows runners: push a `v*` tag
and the finished bundles are attached to a release automatically, or
start it by hand from the **Actions** tab.

`SanPyCAD-2D.log` in `~/Library/Application Support/SanPyCAD-2D`
(macOS) or `%APPDATA%\SanPyCAD-2D` (Windows) holds the console output
of the last session -- the first place to look if something misbehaves.

## License

[MIT](LICENSE).
