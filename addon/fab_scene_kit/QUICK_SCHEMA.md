# FQ1 geometric summary

UTF-8 JSON with exactly five keys: `v: "FQ1"`, `t` (Author type enum), `f` (nonempty features, up to 240 UTF-16 code units), `d` (XYZ overall dimensions in meters, six significant digits), `g` (concatenated fixed-width shape records). The complete serialized text is at most 1000 UTF-16 code units. No BOM/newline is emitted. This is lossy numeric envelope data, not compressed mesh data or an image.

Asset frame: +Z up, -Y front, origin at overall AABB center XY / minimum Z. Translation and reference orientation in the source scene stay local and are not transmitted. All decoded shapes are asset-absolute. `d` remains the original overall AABB even when small shapes are omitted.

Each record is exactly 19 ASCII characters: `B` (box) or `C` (local Z cylinder), followed by nine two-digit lowercase base-36 integers (alphabet 0-9a-z). Values are center XYZ, size XYZ, Euler XYZ. Let S = max(d) and q be an integer:

- Center: `(q * 2 / 1295 - 0.5) * S`, then subtract d.X/2 and d.Y/2 for X/Y. This is the envelope center measured from the original minimum corner, converted to floor-center coordinates.
- Size: `q * 2 / 1295 * S`, q >= 1. Center and size quantization steps are 2S/1295; rounding error is at most S/1295, before shape approximation.
- Rotation: q / 2 degrees, q in 0..719. XYZ Euler; rounding error <= 0.25 degrees per Euler angle.
- Decoding a C produces an elliptical cylinder with local diameters size.X/Y and height size.Z. A round envelope is a geometric heuristic, not a semantic wheel/joint claim.

`quick_spec.py` is the reference standard-library encoder/validator/decoder. `recipe(text)` expands into the existing fab.asset-brief schema, with generic OTHER roles, no inferred joints and blue guide materials. Imported strings are parsed and validated, never evaluated as code. Unknown versions/keys, duplicate keys, non-finite dimensions, illegal record characters and partial records are rejected.

Capture evaluates selected objects and descendants in the chosen frame, analyzes coincident-vertex connected components without mutating source topology, and fits world/PCA oriented bounds. Area-weighted surface samples reduce tessellation bias; connected concave forms split only when empty bounding volume falls substantially. Tiny components (<2.2% of overall longest dimension) are deprioritized by exclusion; remaining envelopes sort by volume and geometry. Duplicate envelopes are removed. Large shells, thin structures and complex curved forms can remain ambiguous. This is a starting point for human or external author interpretation, not an automatic styled CAD reconstruction.

Transfer sequence: select/type/features -> capture -> inspect local decoded guide -> manually transfer FQ1 -> decode/infer/model in FAB style -> return finished individual Author .blend or a full author recipe. Capture does not contact a server. Model-dependent ambiguities must be reported rather than silently asserted as real equipment details.
