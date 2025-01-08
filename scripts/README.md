
# QGIS Automation Functions

This script contains three Python functions designed for use within a QGIS environment:

- **`list_registered_map_sources()`**
- **`list_registered_xyz_tiles()`**
- **`add_map_sources_to_qgis_settings()`**

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [1. List Registered Map Sources](#1-list-registered-map-sources)
  - [2. List Registered XYZ Tiles](#2-list-registered-xyz-tiles)
  - [3. Add Map Sources to QGIS Settings](#3-add-map-sources-to-qgis-settings)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

These functions allow you to:

1. Discover all loaded layers (raster, vector, or others) in the current QGIS project using `list_registered_map_sources()`.
2. View existing XYZ tiles configured in your QGIS settings using `list_registered_xyz_tiles()`.
3. Add a predefined list of base map sources to QGIS as XYZ tiles using `add_map_sources_to_qgis_settings()`.

## Prerequisites

- **QGIS**: You must have QGIS installed.
- **QGIS Python API (`qgis.core`)**: Make sure you are running in an environment where `qgis.core` is importable (e.g., QGIS Python console or a Python environment correctly configured with QGIS).

## Installation

1. Download or clone the script(s) containing these functions.
2. Open QGIS and switch to the Python Console (`Plugins > Python Console`).
3. Load the script into the console:

```python
import sys
sys.path.append('/path/to/your/script/folder')  # Adjust the path as needed
import qgis_automation  # or whatever the script filename is
```

Alternatively, you can copy and paste the function definitions directly into the QGIS Python Console.

## Usage

### 1. List Registered Map Sources

**Function Name**: `list_registered_map_sources()`

```python
from qgis_automation import list_registered_map_sources

list_registered_map_sources()
```

#### What it does:
- Prints a list of all map layers (Raster/Vector/Other) present in the current QGIS project.
- Displays each layer’s name and data source.

#### Example Output:

```
Registered Map Sources:
Vector Layer: roads
  Source: /path/to/shapefile.shp

Raster Layer: elevation
  Source: /path/to/raster.tif
```

---

### 2. List Registered XYZ Tiles

**Function Name**: `list_registered_xyz_tiles()`

```python
from qgis_automation import list_registered_xyz_tiles

list_registered_xyz_tiles()
```

#### What it does:
- Scans QGIS settings to find configured XYZ tile connections.
- Prints each tile’s name and the corresponding URL.

#### Example Output:

```
Registered XYZ Tiles:
Tile Name: OpenStreetMap
  URL: https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

---

### 3. Add Map Sources to QGIS Settings

**Function Name**: `add_map_sources_to_qgis_settings()`

```python
from qgis_automation import add_map_sources_to_qgis_settings

add_map_sources_to_qgis_settings()
```

#### What it does:
- Adds a predefined list of popular basemap sources (e.g., Google Maps, Esri, Bing) to QGIS as XYZ tiles.
- Sets default zoom levels (`zmin = 0`, `zmax = 22`) for each source.
- Prints a confirmation message for each newly added source.

#### Example Output:

```
Added: Google Satellite
Added: Bing Aerial
...
```

## Troubleshooting

### Imports Fail
- Ensure you are in the QGIS Python environment.
- Verify the script file path is added to `sys.path`.
- Confirm `qgis.core` is imported within the QGIS environment.

### No Layers or Tiles Listed
- Make sure your QGIS project has layers loaded or XYZ tiles configured before listing them.
- For XYZ tiles, confirm they exist in `QGIS > Settings > Options > XYZ Tiles` before calling `list_registered_xyz_tiles()`.

### Permission Issues
- Modifying QGIS settings might require appropriate file or system privileges.
- If you cannot write to QGIS settings, run QGIS with higher permissions or contact your system administrator.

## License

This project is provided under the MIT License. Feel free to modify and use the code as needed for your projects.
