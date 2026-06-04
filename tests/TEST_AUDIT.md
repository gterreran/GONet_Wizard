# GONet Wizard test-suite audit

This suite is being rebuilt around the current package architecture rather than the older CLI-only layout.

## Keep and maintain

- `test_loading.py`: high-value parser and `GONetFile.from_file` coverage using the Dolus fixture.
- `test_writing.py`: high-value writer coverage for TIFF/JPEG/FITS output.
- `test_operations.py`: compact and still relevant `GONetFile` arithmetic behavior.
- `test_show.py`: useful coverage of the modern `show` command and Plotly layout helpers.
- `test_cli_routing.py`: protects the command-only-to-GUI fallback behavior.
- `test_ui_bridge.py`: protects preview/window request normalization without launching a real UI.

## Newly added regression/architecture tests

- `test_regressions.py`
  - version fallback when installed distribution metadata is missing
  - package-resource availability for YAML/templates/static assets
  - `build_full_array --weights` parsing and CLI handoff
  - `GONetFileRaw.as_bayer_planes(inplace=True)` state/return behavior

- `test_extract_shapes.py`
  - shape registry dispatch
  - circle/annulus/path masks
  - angle normalization and validation behavior

- `test_extractor_pipeline.py`
  - extractor dependency ordering
  - extractor result merging/alignment
  - region statistics
  - final record assembly and NumPy serialization

- `test_dashboard_loaders.py`
  - dashboard loader registry
  - JSON/CSV long-format loading
  - schema coercion and time-boundary parsing

## Deprioritized for now

- `connect_commands/*`: remote-camera interaction is deferred/experimental and should not drive current coverage goals.
- Full Dash callback integration: these are valuable later, but unit tests should first cover the pure functions and data transformations that callbacks call.
- Window/webview launch behavior: keep smoke tests with mocks only; avoid launching real GUI windows in CI.

## Suggested next coverage targets

1. `GONet_utils/src/gonet/gonet_file_raw.py`
2. `GONet_utils/src/gonet/analysis_utils/full_array.py`
3. `GONet_utils/src/extractors/*.py`
4. `GONet_utils/src/extract_app/shapes/*.py`
5. `GONet_dashboard/src/hood/loaders/*.py`
6. Public CLI command handlers (`extract`, `build_full_array`, `show_meta`)

## Testing philosophy

Coverage percentage is a guide, not the target. Prefer tests that protect:

- current public behavior,
- scientific/data correctness,
- packaging/import behavior,
- previously found bugs,
- CLI/UI bridge contracts.
