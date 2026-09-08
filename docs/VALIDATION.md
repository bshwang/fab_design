# Validation scope

The distributed add-on is the previously tested FAB Scene Kit 0.3.0 package. Its ZIP bytes are unchanged; the SHA-256 is recorded in `dist/manifest.json` and `dist/SHA256SUMS.txt`.

The original Blender 4.3.0 validation covered:

- 95 asset, people-proportion, replacement and preservation checks.
- 99 assembly and asset-loading checks.
- 55 cleanroom editing and UI behavior checks.
- 162 asset metadata, thumbnail and geometry-sharing checks.
- Reopening four asset review scenes and the Light/Dark example scenes in fresh Blender processes.
- Installing the ZIP, creating a template, adding an asset, rendering and saving/reopening a scene with no external linked libraries.

Publication checks compare every packaged file with the included source tree, validate the ZIP checksum and CRC, verify 52 asset records, 52 thumbnails and three templates, and parse the embedded HTML catalog data. These checks do not replace Blender visual inspection when models or code change.

The HTML catalog passed data integrity and JavaScript logic checks, including ID/Korean search, category filtering, selection changes and CSV generation. Browser layout, clipboard, download and print/PDF behavior have not been directly validated. The catalog distributed here is the generated HTML, with its version and images embedded, rather than a source template.

Other Blender versions and every possible layout/pose combination have not been validated. Illustrative model dimensions are not manufacturing specifications.

The Korean HTML user manual includes 11 actual Blender screenshots and three rendered images. Its inspection-cell example was rendered in Blender 4.3.0, inspected visually and reopened in a fresh process; ten scene checks passed. The manual passed 18 document/image integrity checks and eight JavaScript logic checks using inert unit doubles. Every embedded image matches its original source. The body, images and table of contents are present without JavaScript. Browser layout, native image-dialog behavior, browser storage policies and print/PDF pagination have not been directly validated because the validation session's browser security policy blocked local HTML navigation.
