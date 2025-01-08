def list_registered_map_sources():
    """
    List all registered map layers (e.g., Raster or Vector) in the current QGIS project.

    This function:
      1. Retrieves the QGIS project instance.
      2. Iterates through all map layers in the project.
      3. Prints out:
         - The type of each layer (Raster Layer, Vector Layer, or Other Layer).
         - The human-readable name of the layer.
         - The data source path or connection string for the layer.

    Usage:
      Call this function from the QGIS Python console or a Python script 
      running within the QGIS environment. For example:
          >>> list_registered_map_sources()

    Requirements:
      - QGIS Python API (qgis.core) must be available.
      - A valid QGIS project must be open (or created) if you want 
        meaningful results.

    Returns:
      None
        This function prints the information about each layer directly 
        to the console and does not return any value.
    """
    from qgis.core import QgsProject, QgsMapLayer

    # Obtain the instance of the current QGIS project
    project = QgsProject.instance()

    # Retrieve all layers that are registered with the project
    layers = project.mapLayers()

    print("Registered Map Sources:")
    # Loop through each layer (key: layer_id, value: layer object)
    for layer_id, layer in layers.items():
        layer_name = layer.name()    # The user-friendly name of the layer
        layer_source = layer.source()  # The source path or URI of the layer
        
        # Identify the layer type
        if layer.type() == QgsMapLayer.RasterLayer:
            layer_type = "Raster Layer"
        elif layer.type() == QgsMapLayer.VectorLayer:
            layer_type = "Vector Layer"
        else:
            layer_type = "Other Layer"
        
        # Print layer information
        print(f"{layer_type}: {layer_name}")
        print(f"  Source: {layer_source}\n")

  def list_registered_xyz_tiles():
    """
    List all XYZ tile connections (base map sources) currently registered in QGIS Settings.

    This function:
      1. Accesses the QGIS settings via QgsSettings.
      2. Iterates through all keys.
      3. Prints out:
         - Each tile connection name.
         - The corresponding URL for that tile.

    Usage:
      Call this function from the QGIS Python console or a Python script 
      running within the QGIS environment. For example:
          >>> list_registered_xyz_tiles()

    Requirements:
      - QGIS Python API (qgis.core) must be available.
      - The user must have one or more XYZ tiles previously added to QGIS.

    Returns:
      None
        This function prints the registered XYZ tiles directly to the console
        and does not return any value.
    """
    from qgis.core import QgsSettings

    # Access QGIS settings to find XYZ tile connections
    settings = QgsSettings()

    print("Registered XYZ Tiles:")

    # Check all keys in QGIS settings to find those related to XYZ tiles
    for key in settings.allKeys():
        # Each XYZ tile URL is stored under "qgis/connections-xyz/[NAME]/url"
        if key.startswith("qgis/connections-xyz/") and key.endswith("/url"):
            # Extract the tile name from the key (the substring after the second slash)
            tile_name = key.split("/")[2]
            # Retrieve the actual URL from QGIS settings
            tile_url = settings.value(key)
            
            print(f"Tile Name: {tile_name}")
            print(f"  URL: {tile_url}\n")

      def add_map_sources_to_qgis_settings():
    """
    Add predefined XYZ tile connections (map sources) to QGIS Settings.

    This function:
      1. Defines a dictionary of map sources, each with a name and a URL pattern.
      2. Iterates through each key-value pair (map source name and URL).
      3. Inserts the source into the QGIS Settings under "qgis/connections-xyz".
      4. Sets additional properties like minimum (zmin) and maximum (zmax) zoom levels.
      5. Prints a confirmation message for each added source.

    Usage:
      Call this function from the QGIS Python console or a Python script 
      running within the QGIS environment. For example:
          >>> add_map_sources_to_qgis_settings()

    Requirements:
      - QGIS Python API (qgis.core) must be available.
      - The user should have sufficient permissions to modify QGIS Settings.

    Returns:
      None
        This function prints a log of each added map source directly to 
        the console and does not return any value.
    """
    from qgis.core import QgsSettings

    # Dictionary of map sources and their URLs
    map_sources = {
        "Bing Aerial": "http://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1",
        "Bing VirtualEarth": "http://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1",
        "CartoDb Dark Matter (No Labels)": "http://basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png",
        "CartoDb Dark Matter": "http://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "CartoDb Positron (No Labels)": "http://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png",
        "CartoDb Positron": "http://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "Esri Boundaries Places": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        "Esri Gray (dark)": "http://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "Esri Gray (light)": "http://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "Esri Hillshade": "http://services.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
        "Esri National Geographic": "http://services.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}",
        "Esri Navigation Charts": "http://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}",
        "Esri Ocean": "https://services.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}",
        "Esri Physical Map": "https://services.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}",
        "Esri Satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Esri Shaded Relief": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}",
        "Esri Standard": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        "Esri Terrain": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",
        "Esri Topo World": "http://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "Esri Transportation": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
        "Google Maps": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "Google Roads": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "Google Satellite Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "Google Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "Google Terrain Hybrid": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
        "Google Terrain": "https://mt1.google.com/vt/lyrs=t&x={x}&y={y}&z={z}",
        "Mapzen Global Terrain": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
        "OpenStreetMap H.O.T.": "http://tile.openstreetmap.fr/hot/%7Bz%7D/%7Bx%7D/%7By%7D.png",
        "OpenStreetMap Standard": "http://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png",
        "OpenStreetMap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "OpenTopoMap": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        "Strava All": "https://heatmap-external-b.strava.com/tiles/all/bluered/{z}/{x}/{y}.png",
        "Strava Run": "https://heatmap-external-b.strava.com/tiles/run/bluered/{z}/{x}/{y}.png?v=19"
    }

    # Initialize QGIS settings
    settings = QgsSettings()
    # Base path under which XYZ connections are stored
    xyz_path = "qgis/connections-xyz/"

    # Iterate over predefined map sources and add them to QGIS
    for name, url in map_sources.items():
        # Create a path for each map source in the QGIS settings
        group = f"{xyz_path}{name}"
        # Set the URL key
        settings.setValue(f"{group}/url", url)
        # Set the minimum zoom level
        settings.setValue(f"{group}/zmin", 0)
        # Set the maximum zoom level
        settings.setValue(f"{group}/zmax", 22)
        
        # Print a confirmation message to the console
        print(f"Added: {name}")
