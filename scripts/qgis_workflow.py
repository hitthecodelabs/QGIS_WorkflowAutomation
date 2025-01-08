import os
import zipfile
from glob import glob

# Import main QGIS Python APIs
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsRuleBasedRenderer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsLayoutPoint,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemPicture
)
from PyQt5.QtGui import QColor, QFont

# ------------------------------------------------------------------
# 1. Basic QGIS Helper Functions
# ------------------------------------------------------------------

def remove_existing_layer(project, layer_name):
    """
    Removes a layer from the QGIS project if it exists.

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance where layers are loaded.
    layer_name : str
        The name of the layer to remove from the project.

    Returns
    -------
    None
        This function removes the layer if found; otherwise, does nothing.
    """
    for layer in project.mapLayers().values():
        if layer.name() == layer_name:
            project.removeMapLayer(layer)
            print(f"Existing '{layer_name}' layer removed.")
            return


def read_kmz_with_qgis(file_path):
    """
    Loads a vector layer from a KMZ or KML file using QGIS.

    Parameters
    ----------
    file_path : str
        The path to the KMZ or KML file. 
        Example: "/path/to/file.kmz" or "/path/to/file.kml"

    Returns
    -------
    QgsVectorLayer or None
        The loaded vector layer if successful; None otherwise.

    Notes
    -----
    - If the file is a KMZ, the function extracts it to 'temp_kml' 
      directory, then looks for the first '.kml' file within.
    - Make sure you have write permissions in the current working directory
      for KMZ extraction.
    """
    # If it's a KMZ, extract its KML
    if file_path.endswith('.kmz'):
        with zipfile.ZipFile(file_path, 'r') as kmz:
            kmz.extractall('temp_kml')
        # Assume we only want the first .kml found
        file_path = glob('temp_kml/*.kml')[0]

    layer = QgsVectorLayer(file_path, "MyLayer", "ogr")
    if not layer.isValid():
        print(f"Error loading layer from {file_path}")
        return None

    print(f"Loaded vector layer from {file_path}")
    return layer


def load_raster_layer(project, layer_name, url):
    """
    Loads an XYZ-based raster layer if it does not already exist in the project.

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance where the layer will be added.
    layer_name : str
        A user-friendly name to assign to the layer.
    url : str
        The URL template for the XYZ tile source.
        Example: "https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"

    Returns
    -------
    QgsRasterLayer or None
        The loaded raster layer if successful; None otherwise.

    Notes
    -----
    - If a layer with the same name already exists, that layer is re-used.
    - Sets minimum zoom (zmin=0) and maximum zoom (zmax=19) in the connection string.
    """
    # Check if the layer is already loaded
    for lyr in project.mapLayers().values():
        if lyr.name() == layer_name:
            print(f"'{layer_name}' layer already loaded.")
            return lyr

    # Build an XYZ connection string
    connection_str = f"type=xyz&url={url}&zmin=0&zmax=19"
    # Create a raster layer using the built connection string
    raster_lyr = QgsRasterLayer(connection_str, layer_name, "wms")
    if raster_lyr.isValid():
        project.addMapLayer(raster_lyr)
        print(f"Successfully loaded raster layer: {layer_name}")
    else:
        print(f"Error: Could not load raster layer: {layer_name}")
        raster_lyr = None

    return raster_lyr


def load_polygon_layer(project, polygon_path):
    """
    Loads a polygon from a KML (or other OGR-supported file), 
    applies a fill symbol, and adds it to the QGIS project.

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance where the layer will be added.
    polygon_path : str
        The path to the polygon file (e.g., KML).

    Returns
    -------
    QgsVectorLayer or None
        The loaded polygon layer if successful; None otherwise.

    Notes
    -----
    - If a layer named "PolygonLayer" already exists, it will be removed first.
    - The layer is styled with a semi-transparent fill and outline.
    """
    # Remove old copy
    remove_existing_layer(project, "PolygonLayer")

    # Load polygon
    polygon_layer = QgsVectorLayer(polygon_path, "PolygonLayer", "ogr")
    if not polygon_layer.isValid():
        print("Error loading polygon layer.")
        return None
    
    # Configure fill color and outline
    symbol = QgsFillSymbol.createSimple({
        'color': '#DBAA00',
        'outline_color': 'black',
        'outline_width': '0.95'
    })
    polygon_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    # Set some transparency
    polygon_layer.setOpacity(0.40)
    project.addMapLayer(polygon_layer)
    print("Polygon layer loaded and styled.")
    return polygon_layer


def calculate_area_and_centroid(polygon_layer, project):
    """
    Calculates the total area in hectares and the centroid of 
    the first feature in the given polygon layer.

    Parameters
    ----------
    polygon_layer : QgsVectorLayer
        The polygon layer from which to calculate area and centroid.
    project : QgsProject
        The QGIS project to retrieve transformation context and CRS info.

    Returns
    -------
    tuple of (float, QgsPointXY) or (None, None)
        Returns a tuple (area_hectares, centroid_point_utm) if successful;
        otherwise, returns (None, None).

    Notes
    -----
    - Uses EPSG:32717 (WGS 84 / UTM zone 17S) as an example of a projected CRS
      for area measurement. Adjust the CRS to match your region if needed.
    - Performs only the area calculation on the first feature in the layer.
    - The centroid is returned in the projected CRS (same as used for area).
    """
    # Example: transform from polygon's CRS to a projected CRS for area
    utm_crs = QgsCoordinateReferenceSystem("EPSG:32717")  # Example UTM zone
    transform_context = project.transformContext()
    
    try:
        transform_to_utm = QgsCoordinateTransform(polygon_layer.crs(), utm_crs, transform_context)
    except Exception as e:
        print(f"Error setting up transform: {e}")
        return None, None

    for feat in polygon_layer.getFeatures():
        geom = feat.geometry()
        if not geom:
            print("No geometry found in the feature.")
            continue
        
        transformed_geom = QgsGeometry(geom)
        # Transform geometry to UTM for area computation
        if transformed_geom.transform(transform_to_utm) != 0:
            print("Failed to transform geometry to UTM.")
            continue
        
        # Calculate area in hectares (1 hectare = 10,000 m^2)
        area_ha = transformed_geom.area() / 10000.0
        # Calculate centroid in projected CRS
        centroid_geom = transformed_geom.centroid()
        centroid_pt_utm = centroid_geom.asPoint()

        print(f"Area (ha): {area_ha}, Centroid (UTM): {centroid_pt_utm}")
        return area_ha, centroid_pt_utm
    
    return None, None


def create_marker_layer(project, centroid_point):
    """
    Creates and adds an in-memory point layer with a single marker 
    feature at a specified point location (centroid or otherwise).

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance where the new marker layer will be added.
    centroid_point : QgsPointXY
        The point at which to place the marker. 
        Typically the centroid from a polygon, but can be any point.

    Returns
    -------
    QgsVectorLayer or None
        The newly created memory layer with the marker symbol if successful;
        None otherwise.

    Notes
    -----
    - Removes any existing layer named "CentroidMarker" to avoid conflicts.
    - Uses a star-shaped marker symbol with customizable size/color. 
      Adapt for your styling needs.
    - Assumes EPSG:4326 for the memory layer’s CRS. Adjust as needed.
    """
    remove_existing_layer(project, "CentroidMarker")
    # Create an in-memory point layer with EPSG:4326
    marker_layer = QgsVectorLayer("Point?crs=EPSG:4326", "CentroidMarker", "memory")
    if not marker_layer.isValid():
        print("Could not create in-memory point layer.")
        return None

    # Add a feature at the given point
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(centroid_point))
    provider = marker_layer.dataProvider()
    provider.addFeature(feat)
    
    # Configure a basic star marker symbol
    symbol = QgsMarkerSymbol()
    symbol.deleteSymbolLayer(0)  # remove default circle layer
    star_layer = QgsSimpleMarkerSymbolLayer(
        shape=QgsSimpleMarkerSymbolLayerBase.Star,
        size=6.0,
        color=QColor("#DBAA00")
    )
    symbol.appendSymbolLayer(star_layer)
    # Apply the symbol to the layer
    marker_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    
    project.addMapLayer(marker_layer)
    print("Marker layer created at centroid.")
    return marker_layer

# ------------------------------------------------------------------
# 2. Example of Creating a Simple Print Layout
# ------------------------------------------------------------------

def create_simple_layout(project, polygon_layer, raster_layer):
    """
    Creates and returns a basic print layout with a map item and a text label.

    Parameters
    ----------
    project : QgsProject
        The QGIS project that will hold the new layout.
    polygon_layer : QgsVectorLayer or None
        A polygon layer to display in the layout's map. 
        If None, the polygon layer is omitted from the map.
    raster_layer : QgsRasterLayer or None
        A raster layer (e.g., Bing Aerial) to display in the layout's map.
        If None, the raster layer is omitted from the map.

    Returns
    -------
    QgsPrintLayout
        The newly created layout with a map item and a label.

    Notes
    -----
    - Deletes any existing layout named "MySimpleLayout" to avoid duplicates.
    - Sets the extent of the map item to the polygon layer's extent if provided.
    - The layout is added to the project's layout manager automatically.
    - You can further customize map size, styling, scale, etc., as needed.
    """
    layout_name = "MySimpleLayout"
    # Remove existing layout (if it exists) with the same name
    existing_layout = project.layoutManager().layoutByName(layout_name)
    if existing_layout:
        project.layoutManager().removeLayout(existing_layout)
        print(f"Removed existing layout: {layout_name}")
    
    # Create a new layout
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()  # Optional step to set some default items
    layout.setName(layout_name)
    # Add the layout to the project
    project.layoutManager().addLayout(layout)

    # Add a label (title)
    label = QgsLayoutItemLabel(layout)
    label.setText("My Simple Map")
    label.setFont(QFont("Arial", 16))
    label.adjustSizeToText()
    layout.addLayoutItem(label)
    # Position the label
    label.attemptMove(QgsLayoutPoint(10, 10, QgsUnitTypes.LayoutMillimeters))
    
    # Create a map item
    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(20, 20, 100, 100)  # set a bounding rectangle
    
    # Determine which layers are displayed in the map
    if raster_layer and polygon_layer:
        map_item.setLayers([raster_layer, polygon_layer])
    else:
        # If one or both are None, default to all layers in the project
        map_item.setLayers(project.mapLayers().values())

    # Adjust the map extent based on polygon layer if available
    if polygon_layer:
        ext = polygon_layer.extent()
        ext.scale(1.2)  # example: zoom out slightly
        map_item.setExtent(ext)
    
    # Resize and position the map
    map_item.attemptResize(QgsLayoutSize(120, 80, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptMove(QgsLayoutPoint(10, 20, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map_item)

    print("A basic print layout was created with a map and a label.")
    return layout

# ------------------------------------------------------------------
# 3. Main (Demonstration) Workflow
# ------------------------------------------------------------------

def main_demo(polygon_kml_path):
    """
    Demonstrates a typical workflow of loading a polygon, calculating area,
    creating a marker at its centroid, loading a raster, and making a 
    simple print layout.

    Parameters
    ----------
    polygon_kml_path : str
        The path to the KML (or KMZ) file containing the polygon to be loaded.

    Returns
    -------
    None
        This function prints log messages showing the progress of each step.

    Workflow Steps
    -------------
    1. Load Bing raster layer.
    2. Load polygon layer (from KML/KMZ).
    3. Calculate area and centroid (in UTM).
    4. Create a marker at the centroid.
    5. Create a simple map layout containing both polygon and raster.

    Usage
    -----
    >>> project = QgsProject.instance()
    >>> main_demo("/path/to/your_polygon.kml")
    """
    project = QgsProject.instance()
    # Set project CRS to EPSG:4326 (WGS84) for demonstration
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    # 1. Load Raster (e.g., Bing)
    bing_layer_name = "Bing Aerial"
    bing_url = "https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"
    raster_layer = load_raster_layer(project, bing_layer_name, bing_url)

    # 2. Load Polygon Layer
    polygon_layer = load_polygon_layer(project, polygon_kml_path)
    if not polygon_layer:
        print("Cannot proceed without a valid polygon layer.")
        return

    # 3. Calculate Area & Centroid
    area_hectares, centroid_point_utm = calculate_area_and_centroid(polygon_layer, project)
    if area_hectares is None or centroid_point_utm is None:
        print("Cannot proceed without valid area and centroid.")
        return

    # 4. Create Marker at the centroid
    #    Note: The marker is created in EPSG:4326, but our centroid is in UTM.
    #    You may need to transform the UTM centroid back to EPSG:4326 or 
    #    create the marker layer with the UTM CRS. This depends on your workflow.
    marker_layer = create_marker_layer(project, centroid_point_utm)
    if not marker_layer:
        print("Marker layer creation failed.")
        return

    # 5. Create a Simple Layout for Export
    layout = create_simple_layout(project, polygon_layer, raster_layer)
    # Example: you could export this layout to a file
    # exporter = QgsLayoutExporter(layout)
    # result = exporter.exportToPdf("output_map.pdf", QgsLayoutExporter.PdfExportSettings())
    # if result == QgsLayoutExporter.Success:
    #     print("Layout exported to PDF successfully.")

    print("Workflow complete.")
