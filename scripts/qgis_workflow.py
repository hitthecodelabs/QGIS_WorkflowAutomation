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
    """
    for layer in project.mapLayers().values():
        if layer.name() == layer_name:
            project.removeMapLayer(layer)
            print(f"Existing '{layer_name}' layer removed.")
            return

def read_kmz_with_qgis(file_path):
    """
    Loads a vector layer from a KMZ or KML file using QGIS.
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
    Loads an XYZ-based raster layer if it does not already exist.
    For example, Bing or Google Satellite layer.
    """
    # Check if the layer is already loaded
    for lyr in project.mapLayers().values():
        if lyr.name() == layer_name:
            print(f"'{layer_name}' layer already loaded.")
            return lyr

    # Build an XYZ connection string and load
    connection_str = f"type=xyz&url={url}&zmin=0&zmax=19"
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
    configures a basic fill symbol, and adds to project.
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
    polygon_layer.setOpacity(0.40)
    project.addMapLayer(polygon_layer)
    print("Polygon layer loaded and styled.")
    return polygon_layer

def calculate_area_and_centroid(polygon_layer, project):
    """
    Calculates the total area in hectares and the centroid of
    the first feature in the given polygon layer.
    """
    # Example: transform from polygon's CRS to a projected CRS for area
    utm_crs = QgsCoordinateReferenceSystem("EPSG:32717")  # Just an example
    transform_context = project.transformContext()
    try:
        transform_to_utm = QgsCoordinateTransform(polygon_layer.crs(), utm_crs, transform_context)
    except Exception as e:
        print(f"Error setting up transform: {e}")
        return None, None

    for feat in polygon_layer.getFeatures():
        geom = feat.geometry()
        if not geom:
            print("No geometry found.")
            continue
        
        transformed_geom = QgsGeometry(geom)
        if transformed_geom.transform(transform_to_utm) != 0:
            print("Failed to transform geometry.")
            continue
        
        # Calculate area in hectares
        area_ha = transformed_geom.area() / 10000.0
        # Centroid in projected CRS
        centroid_geom = transformed_geom.centroid()
        centroid_pt_utm = centroid_geom.asPoint()
        print(f"Area (ha): {area_ha}, Centroid (UTM): {centroid_pt_utm}")
        
        return area_ha, centroid_pt_utm
    return None, None

def create_marker_layer(project, centroid_point):
    """
    Creates and adds a memory layer with a single marker feature
    at a given point location.
    """
    remove_existing_layer(project, "CentroidMarker")
    marker_layer = QgsVectorLayer("Point?crs=EPSG:4326", "CentroidMarker", "memory")
    
    # Add a feature at the given point
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(centroid_point))
    marker_layer.dataProvider().addFeature(feat)
    
    # Configure a basic marker symbol
    symbol = QgsMarkerSymbol()
    symbol.deleteSymbolLayer(0)  # remove default
    star_layer = QgsSimpleMarkerSymbolLayer(
        shape=QgsSimpleMarkerSymbolLayerBase.Star,
        size=6.0,
        color=QColor("#DBAA00")
    )
    symbol.appendSymbolLayer(star_layer)
    marker_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    
    project.addMapLayer(marker_layer)
    print("Marker layer created at centroid.")
    return marker_layer

# ------------------------------------------------------------------
# 2. Example of Creating a Simple Print Layout
# ------------------------------------------------------------------

def create_simple_layout(project, polygon_layer, raster_layer):
    """
    Creates a very basic print layout with a single map item.
    """
    # Remove a layout with the same name if it exists
    layout_name = "MySimpleLayout"
    existing_layout = project.layoutManager().layoutByName(layout_name)
    if existing_layout:
        project.layoutManager().removeLayout(existing_layout)
        print(f"Removed existing layout: {layout_name}")
    
    # Create a new layout
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)
    project.layoutManager().addLayout(layout)

    # Add a label (title) for demonstration
    label = QgsLayoutItemLabel(layout)
    label.setText("My Simple Map")
    label.setFont(QFont("Arial", 16))
    label.adjustSizeToText()
    layout.addLayoutItem(label)
    label.attemptMove(QgsLayoutPoint(10, 10, QgsUnitTypes.LayoutMillimeters))
    
    # Create a map item
    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(20, 20, 100, 100)
    # Set layers that the map will show
    if raster_layer and polygon_layer:
        map_item.setLayers([raster_layer, polygon_layer])
    else:
        map_item.setLayers(project.mapLayers().values())

    # Adjust map extent to polygon
    if polygon_layer:
        ext = polygon_layer.extent()
        ext.scale(1.2)  # optional
        map_item.setExtent(ext)
    
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
    Demonstrates how to:
      - Load a polygon
      - Calculate area & centroid
      - Create a marker layer
      - Load a raster (e.g., Bing)
      - Create a simple layout
    """
    project = QgsProject.instance()
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

    # 4. Create Marker at Centroid
    #    Note: For simplicity, we are not doing a coordinate transform back to EPSG:4326
    #    If your data is in a different CRS, adapt as needed.
    marker_layer = create_marker_layer(project, centroid_point_utm)

    # 5. Create a Simple Layout for Export
    layout = create_simple_layout(project, polygon_layer, raster_layer)
    # You can programmatically export layout if needed:
    # exporter = QgsLayoutExporter(layout)
    # exporter.exportToPdf("output_map.pdf", QgsLayoutExporter.PdfExportSettings())
    print("Workflow complete.")

# If desired, call the main_demo function with a path to your polygon KML/KMZ.
# main_demo("path/to/your_polygon.kml")
