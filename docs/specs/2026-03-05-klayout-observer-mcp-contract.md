# KLayout Observer MCP Contract

## Purpose

This document is the normative handoff contract for the MVP implementation. If the design brief and this contract conflict, follow this contract for implementation details.

## Fixed Implementation Choices

- Implement the server in Python only for MVP.
- Use Python 3.11 or newer.
- Use the official Python MCP SDK, but keep tool names and request or response payloads defined here even if SDK ergonomics differ.
- Use standalone KLayout Python modules for in-process layout work:
  - `klayout.db` for layout loading and geometry inspection
  - `klayout.lay` for deterministic rendering through `LayoutView`
- Use external KLayout batch mode only for DRC deck execution:
  - `klayout -b -r <script>`
- Do not implement GUI attach mode in MVP.
- Do not implement geometry editing in MVP.

## Runtime Configuration

Support these environment variables:

- `KLAYOUT_MCP_ARTIFACT_ROOT`
  - Default: `<repo>/.artifacts`
- `KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS`
  - Colon-separated list of readable roots for input GDS or OASIS files
- `KLAYOUT_MCP_ALLOWED_DRC_ROOTS`
  - Colon-separated list of readable roots for DRC scripts
- `KLAYOUT_MCP_SESSION_TTL_SECONDS`
  - Default: `3600`
- `KLAYOUT_BIN`
  - Default: `klayout`

Reject input paths outside the configured allowlists.

## Runtime Artifact Layout

Store runtime artifacts under:

```text
.artifacts/
  sessions/
    <session_id>/
      session.json
      renders/
        <render_id>.png
      drc/
        <run_id>/
          stdout.txt
          stderr.txt
          report.lyrdb
          markers.json
          crops/
```

All paths returned to callers must be absolute paths.

## Session Lifecycle

- `session_id` format: `ses_<12-char-lowercase-hex>`
- Session IDs are unique per process lifetime.
- A session is created only by `open_layout`.
- A session expires after `KLAYOUT_MCP_SESSION_TTL_SECONDS` of inactivity.
- Expired sessions are deleted lazily on the next server operation.
- `close_session` deletes the in-memory session plus its artifact directory.
- Shape IDs are stable only within the session that created them.

## Global Response Rules

- Tool responses must be structured JSON objects, not free-form prose.
- Coordinates provided by callers are in microns unless a field explicitly says otherwise.
- Output must include:
  - `dbu`
  - micron-scale values
  - dbu-scale values where measurement or bbox precision matters
- Collections must have deterministic ordering:
  - layers sorted by `layer`, then `datatype`
  - cells sorted by name
  - shapes sorted by `layer`, `kind`, then bbox coordinates
- Large responses must include explicit truncation metadata.

## Shared Types

### `MicronBox`

```json
{
  "left": 0.0,
  "bottom": 0.0,
  "right": 100.0,
  "top": 50.0
}
```

### `LayerRef`

```json
{
  "layer": 1,
  "datatype": 0,
  "name": "WG"
}
```

`name` is optional on input and optional on output.

### `ArtifactRef`

```json
{
  "kind": "render",
  "path": "/abs/path/to/file.png",
  "media_type": "image/png"
}
```

### `ShapeRef`

```json
{
  "id": "shp_8a4f6d2f",
  "kind": "path",
  "cell": "TOP",
  "instance_path": ["TOP", "MMI_LEFT"],
  "layer": {
    "layer": 1,
    "datatype": 0,
    "name": "WG"
  },
  "bbox_um": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 10.0,
    "top": 2.0
  }
}
```

`id` must be deterministic within a session for the same queried object. It does not need to be stable across sessions.

### `ErrorObject`

```json
{
  "code": "FILE_NOT_FOUND",
  "message": "Layout file does not exist",
  "details": {
    "path": "/abs/path/to/missing.gds"
  }
}
```

## Error Codes

Use these exact codes:

- `FILE_NOT_FOUND`
- `PATH_NOT_ALLOWED`
- `UNSUPPORTED_FORMAT`
- `TOP_CELL_NOT_FOUND`
- `SESSION_NOT_FOUND`
- `SESSION_EXPIRED`
- `INVALID_BOX`
- `INVALID_LAYER`
- `INVALID_TARGET`
- `QUERY_TOO_LARGE`
- `TOOL_LIMIT_EXCEEDED`
- `RENDER_FAILED`
- `DRC_SCRIPT_NOT_ALLOWED`
- `DRC_RUN_FAILED`
- `INTERNAL_ERROR`

## Tool Contracts

### `open_layout`

Request:

```json
{
  "path": "/abs/path/to/layout.gds",
  "top_cell": "TOP",
  "format": "gds"
}
```

Rules:

- `path` is required and must be absolute.
- Supported formats: `gds`, `gdsii`, `oas`, `oasis`.
- If `format` is omitted, infer from extension.
- If `top_cell` is omitted and the file has multiple top cells, choose the alphabetically first one and return the full list.

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "source": {
    "path": "/abs/path/to/layout.gds",
    "format": "gds",
    "sha256": "..."
  },
  "selected_top_cell": "TOP",
  "top_cells": ["TOP"],
  "dbu": 0.001,
  "bbox_um": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 1200.0,
    "top": 600.0
  },
  "bbox_dbu": {
    "left": 0,
    "bottom": 0,
    "right": 1200000,
    "top": 600000
  },
  "layer_count": 7,
  "artifact_root": "/abs/path/to/.artifacts/sessions/ses_a1b2c3d4e5f6"
}
```

### `close_session`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6"
}
```

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "closed": true,
  "artifact_dir_deleted": true
}
```

Closing an already-missing session should return:

```json
{
  "session_id": "ses_missing",
  "closed": false,
  "artifact_dir_deleted": false
}
```

### `list_cells`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "max_depth": 2
}
```

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "cells": [
    {
      "name": "TOP",
      "is_top": true,
      "bbox_um": {
        "left": 0.0,
        "bottom": 0.0,
        "right": 100.0,
        "top": 50.0
      },
      "child_instance_count": 4,
      "shape_count": 18
    }
  ]
}
```

### `describe_cell`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "cell": "TOP",
  "depth": 1
}
```

Response fields:

- `cell`
- `bbox_um`
- `bbox_dbu`
- `instances`
- `labels`
- `shape_counts_by_layer`
- `depth_used`

Each instance must include:

- `name`
- `child_cell`
- `array`
- `transform`
- `bbox_um`

### `list_layers`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6"
}
```

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "layers": [
    {
      "layer": 1,
      "datatype": 0,
      "name": "WG",
      "visible": true,
      "shape_count": 128
    }
  ]
}
```

### `query_region`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "box": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 20.0,
    "top": 10.0
  },
  "cell": "TOP",
  "layers": [
    {
      "layer": 1,
      "datatype": 0
    }
  ],
  "hierarchy_mode": "recursive",
  "max_shapes": 200,
  "max_instances": 100
}
```

Allowed `hierarchy_mode` values:

- `top`
- `recursive`
- `flattened`

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "box_um": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 20.0,
    "top": 10.0
  },
  "cell": "TOP",
  "hierarchy_mode": "recursive",
  "summary": {
    "shape_count": 3,
    "instance_count": 1,
    "text_count": 2
  },
  "shapes": [
    {
      "id": "shp_8a4f6d2f",
      "kind": "path",
      "cell": "TOP",
      "instance_path": ["TOP"],
      "layer": {
        "layer": 1,
        "datatype": 0,
        "name": "WG"
      },
      "bbox_um": {
        "left": 0.0,
        "bottom": 0.0,
        "right": 10.0,
        "top": 1.0
      },
      "point_count": 2,
      "path_width_um": 0.5
    }
  ],
  "instances": [],
  "texts": [],
  "truncation": {
    "shapes_dropped": 0,
    "instances_dropped": 0,
    "texts_dropped": 0
  }
}
```

### `measure_geometry`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "mode": "edge_gap",
  "target_ids": ["shp_a", "shp_b"]
}
```

Supported `mode` values and required target counts:

- `path_width`: 1
- `segment_length`: 1
- `centerline_distance`: 2
- `edge_gap`: 2
- `bend_radius_estimate`: 1
- `overlap`: 2
- `label_distance`: 2
- `port_spacing`: 2

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "mode": "edge_gap",
  "target_ids": ["shp_a", "shp_b"],
  "value_um": 0.35,
  "value_dbu": 350,
  "details": {
    "method": "edge_to_edge_bbox_or_polygon_distance"
  }
}
```

For `overlap`, return:

- `value_um`: overlapping area in square microns
- `value_dbu`: overlapping area in square dbu

### `set_view`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "box": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 50.0,
    "top": 25.0
  },
  "cell": "TOP",
  "layers": [
    {
      "layer": 1,
      "datatype": 0
    }
  ]
}
```

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "view": {
    "cell": "TOP",
    "box_um": {
      "left": 0.0,
      "bottom": 0.0,
      "right": 50.0,
      "top": 25.0
    },
    "layers": [
      {
        "layer": 1,
        "datatype": 0
      }
    ]
  }
}
```

### `render_view`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "box": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 50.0,
    "top": 25.0
  },
  "cell": "TOP",
  "layers": [
    {
      "layer": 1,
      "datatype": 0
    }
  ],
  "image_size": {
    "width": 1200,
    "height": 800
  },
  "annotations": [
    {
      "kind": "shape_outline",
      "target_ids": ["shp_a"],
      "color": "#ff3b30"
    }
  ],
  "style": "light"
}
```

Allowed `style` values:

- `light`
- `dark`
- `mask`

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "render_id": "rnd_1234abcd",
  "box_um": {
    "left": 0.0,
    "bottom": 0.0,
    "right": 50.0,
    "top": 25.0
  },
  "image": {
    "kind": "render",
    "path": "/abs/path/to/.artifacts/sessions/ses_a1b2c3d4e5f6/renders/rnd_1234abcd.png",
    "media_type": "image/png"
  },
  "width": 1200,
  "height": 800,
  "style": "light"
}
```

### `run_drc_script`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "script_path": "/abs/path/to/deck.drc",
  "script_type": "ruby",
  "params": {
    "WG_MIN_SPACE": "0.2"
  }
}
```

Rules:

- `script_path` must be absolute and allowed by `KLAYOUT_MCP_ALLOWED_DRC_ROOTS`.
- The server must invoke KLayout in batch mode.
- The implementation must export a copy of the session layout into the session DRC run directory and run the deck against that copy.
- The DRC run must produce a `.lyrdb` or another machine-readable marker artifact.

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "run_id": "drc_ab12cd34",
  "script_path": "/abs/path/to/deck.drc",
  "script_type": "ruby",
  "return_code": 0,
  "marker_count": 4,
  "rule_counts": {
    "wg_min_space": 3,
    "pin_overlap": 1
  },
  "artifacts": [
    {
      "kind": "drc_report",
      "path": "/abs/path/to/report.lyrdb",
      "media_type": "application/octet-stream"
    }
  ]
}
```

### `extract_markers`

Request:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "run_id": "drc_ab12cd34",
  "include_crops": true,
  "crop_size_um": {
    "x": 20.0,
    "y": 20.0
  }
}
```

Response:

```json
{
  "session_id": "ses_a1b2c3d4e5f6",
  "run_id": "drc_ab12cd34",
  "markers": [
    {
      "rule": "wg_min_space",
      "box_um": {
        "left": 10.0,
        "bottom": 10.0,
        "right": 12.0,
        "top": 12.0
      },
      "crop": {
        "kind": "render",
        "path": "/abs/path/to/crops/marker_0001.png",
        "media_type": "image/png"
      }
    }
  ]
}
```

If `include_crops` is `false`, omit `crop`.

## Security Rules

- Never execute arbitrary shell from tool input.
- Never pass unvalidated paths to `subprocess` calls.
- Only allow layout files and DRC scripts from configured roots.
- Treat script parameters as data, not as shell fragments.
- Refuse to open symlink targets outside the allowlist roots.

## Determinism Rules

- Always serialize numeric outputs as JSON numbers, not strings.
- Always report microns rounded to 6 decimal places.
- Always report dbu integers when applicable.
- Always include truncation metadata when limits are applied, even if all drop counts are zero.
- Render output for identical input plus identical session state must be byte-stable when the environment is unchanged.

## Acceptance Criteria

The MVP handoff is implemented correctly only if:

- every tool listed here exists under the exact tool name
- every tool accepts the fields defined here
- every tool returns the required fields defined here
- errors use the exact codes listed here
- session cleanup works both explicitly and by TTL
- artifacts are written to the documented directory layout
