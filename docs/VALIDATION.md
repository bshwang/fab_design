# Validation scope

The current add-on is FAB Scene Kit 0.4.0. Its real ZIP was installed and tested in Blender 4.3.0 under an isolated extension namespace. The SHA-256 is recorded in `dist/manifest.json` and `dist/SHA256SUMS.txt`. Bundled asset geometry remains at library version 0.3.0.

Phase 2 validation: 86 authoring checks, 99 existing assembly regression checks and 19 actual ZIP installation checks. This covered rotated/mm geometry measurement, local bindings, file/text round trips, actual Edit Mode outline capture, all six types and shapes, joint data, revision preservation, returned .blend geometry, embedded thumbnails, template placement, theme changes and save/reopen. Native Windows clipboard and the four-step authoring panel were also exercised in Blender.

Three synthetic AMMR iterations were rendered and inspected. The second and third addressed sparse functional detail, excessive mint coverage and ground contact. The final scene passed ten fresh-process reopening checks and was visually accepted alongside the existing cobot/person assets. No company CAD models were used. Guided geometry capture does not imply automatic semantic CAD simplification.

The new Author HTML manual contains four actual screenshots and one rendered image. Static image integrity and internal anchors passed; it needs no JavaScript or network. Browser layout has not been directly checked. The previous assembly manual and catalog remain available at version 0.3.0.

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
