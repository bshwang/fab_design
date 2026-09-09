# AW1 semantic brief (0.4.2)

AW1 is compact UTF-8 JSON for communicating modeling intent. It is not the FQ1 geometric capture format, an executable script, or an Advanced Author model recipe. The whole outgoing string must be at most **1000 UTF-16 code units**, including punctuation and whitespace. Exports use compact JSON with no BOM or trailing newline; oversized output is rejected rather than truncated.

| Key | Meaning |
| --- | --- |
| `v` | `AW1` |
| `type` | `AMMR`, `AMR`, `ARM`, `EQUIPMENT`, `HUMANOID`, `OHT` |
| `use` | User-entered purpose; required for export |
| `base` | `UNKNOWN`, `RECT`, `L`, `U`, `OTHER` |
| `size` | Overall `[X, Y, Z]` extent in meters; `null` without measurements |
| `open` | Optional open-area / outline description for L, U or Other |
| `arms` | For arm-bearing types: `"unknown"`, or one `[kind, axes]` pair per arm; kind is `UNKNOWN`, `ARTICULATED`, `SCARA`, `OTHER`; unknown axes are `null` |
| `keep` | Optional must-keep features, entered by the user |
| `flow` | Optional work sequence text |
| `move` | Optional user-described relationship, including component A/B names |
| `parts` | Enabled functional cards except those explicitly marked Omit |
| `frame` | When measured: `m;center XY,floor Z;-Y front,+Z up;current pose` |
| `roots` | Optional selected source-root names; never the full object hierarchy |

Each part contains `id` (local functional-card key) and `role` (user-editable name). Optional fields are `keep: true`, `note`, `at` (placement), `motion`, and `on` (mounting description). `d` gives measured extent and `p` the measured bounding-box center in the common export frame. A Describe Only card omits `d` and `p`; missing values must not be interpreted as zero.

Measurements use evaluated current-pose geometry after world transforms, frame orientation and unit conversion. The common origin is the overall XY bounding center and minimum Z. X/Y/Z extents are aligned to this frame. Numeric measurements use five significant digits. Bounds do not encode a concave L-shaped outline; the user's outline and open-area description supply that information. Joint states, vertices, faces, source paths and local binding identifiers are not part of AW1.

The wizard checks source review, purpose, optional measurement freshness and the character budget before export. It recomputes the geometry fingerprint when exporting measured values. Changing source geometry or pose requires Measure / Refresh All again, or disabling Include measurements.

[The 543-character synthetic example](../dist/FAB_Guided_Brief_Example_0.4.2.txt) has a mobile base, one articulated arm and a Cartesian handler. Only its base card is bound for part measurement; the other two cards are descriptive. No actual company CAD was used.

Full local draft JSON is a different format and can exceed the transfer budget. It preserves wizard fields and local source references for Save/Load Draft; it is not the AW1 text to send. Returned completed FAB Author assets continue to use the existing `.blend` library importer.
