from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsPrintLayout,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsRuleBasedRenderer
)
from PyQt5.QtGui import QColor, QFont


def remove_existing_layer(project, layer_name):
    """
    Remove an existing layer from a QGIS project by its name.

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance where the layer may exist.
    layer_name : str
        The name of the layer to remove if it exists.

    Returns
    -------
    bool
        True if a layer was found and removed; False otherwise.

    Notes
    -----
    - If multiple layers share the same name, only the first encountered will be removed.
    - This function is useful for ensuring a fresh state before adding a new layer.
    """
    for layer in project.mapLayers().values():
        if layer.name() == layer_name:
            project.removeMapLayer(layer)
            print(f"Removed existing layer: {layer_name}")
            return True
    return False


def replace_layer_with_raster(project, layer_name, xyz_url, zmin=0, zmax=19):
    """
    Replace (or add) a raster (XYZ) layer in the project using the specified connection parameters.

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance where the layer will be added.
    layer_name : str
        Name to assign to the new raster layer (and to remove any old layer with this name).
    xyz_url : str
        The URL template for an XYZ tile source (e.g., Bing, OSM).
        Example: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    zmin : int, optional
        Minimum zoom level (default is 0).
    zmax : int, optional
        Maximum zoom level (default is 19).

    Returns
    -------
    QgsRasterLayer or None
        The newly added raster layer if valid; otherwise None.

    Notes
    -----
    - This function uses an XYZ tile connection string with the format "type=xyz&url=...&zmin=...&zmax=...".
    - If a layer with the same name already exists, it will be removed before adding the new one.
    """
    # Remove old layer if present
    remove_existing_layer(project, layer_name)

    # Build the XYZ connection string
    connection_str = f"type=xyz&url={xyz_url}&zmin={zmin}&zmax={zmax}"
    # Create a raster layer and add it to the project
    raster_layer = QgsRasterLayer(connection_str, layer_name, "wms")
    if raster_layer.isValid():
        project.addMapLayer(raster_layer)
        print(f"Successfully loaded raster layer: {layer_name}")
        return raster_layer
    else:
        print(f"Error: Could not load raster layer: {layer_name}")
        return None

def transform_layer_crs(layer, target_epsg, project):
    """
    Transform all features of a vector layer into a target CRS.

    Parameters
    ----------
    layer : QgsVectorLayer
        The source layer whose geometries will be transformed.
    target_epsg : str
        The EPSG code (e.g., "EPSG:4326" or "EPSG:3857") of the target CRS.
    project : QgsProject
        The QGIS project (used to retrieve a transform context).

    Returns
    -------
    None
        The layer’s features are updated in-place.

    Notes
    -----
    - Modifies geometry in-place using `layer.dataProvider().changeGeometryValues()`.
    - Useful when you need to unify the coordinate systems of multiple layers.
    """
    if not layer.isValid():
        print("Layer is invalid. Cannot transform CRS.")
        return

    source_crs = layer.crs()
    target_crs = QgsCoordinateReferenceSystem(target_epsg)
    if source_crs == target_crs:
        print(f"Layer already in {target_epsg}; no transformation needed.")
        return

    transform_context = project.transformContext()
    coord_transform = QgsCoordinateTransform(source_crs, target_crs, transform_context)

    update_map = {}
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom:
            geom.transform(coord_transform)
            update_map[feature.id()] = geom
    if update_map:
        layer.dataProvider().changeGeometryValues(update_map)
        print(f"Transformed layer '{layer.name()}' from {source_crs.authid()} to {target_crs.authid()}.")
    else:
        print("No geometry updated; possibly empty layer.")


def set_layer_opacity(layer, opacity=0.5):
    """
    Set the opacity (transparency) for a layer.

    Parameters
    ----------
    layer : QgsMapLayer
        The QGIS layer (vector or raster) for which to set opacity.
    opacity : float, optional
        Opacity value, ranging from 0.0 (fully transparent) to 1.0 (fully opaque).
        Default is 0.5 (50% opacity).

    Returns
    -------
    None

    Notes
    -----
    - QGIS typically interprets 0.0 as completely see-through and 1.0 as no transparency.
    - For vector layers, symbol or rule-based renderers can have separate opacity settings too.
    """
    if not layer.isValid():
        print(f"Cannot set opacity; layer '{layer.name()}' is invalid.")
        return
    layer.setOpacity(opacity)
    print(f"Set opacity of layer '{layer.name()}' to {opacity}.")


def create_basic_marker_layer(
    project, 
    layer_name, 
    point_geometry, 
    layer_crs="EPSG:4326", 
    marker_color="#DBAA00",
    marker_size=6.0
):
    """
    Create and add an in-memory point layer with a single marker feature.

    Parameters
    ----------
    project : QgsProject
        The QGIS project instance to which the layer will be added.
    layer_name : str
        A name for the memory layer.
    point_geometry : QgsPointXY
        The geometry (coordinate) where the single marker will be placed.
    layer_crs : str, optional
        The EPSG code for the in-memory layer (default "EPSG:4326").
    marker_color : str, optional
        Color of the marker in hex format (default "#DBAA00").
    marker_size : float, optional
        Marker size in points (default 6.0).

    Returns
    -------
    QgsVectorLayer or None
        The created memory layer if successful; None otherwise.

    Notes
    -----
    - Removes any existing layer with the same name before creating this one.
    - The marker is styled with a star shape, but you can substitute any QgsSimpleMarkerSymbolLayerBase shape.
    """
    remove_existing_layer(project, layer_name)

    # Create an in-memory point layer
    uri = f"Point?crs={layer_crs}"
    memory_layer = QgsVectorLayer(uri, layer_name, "memory")
    if not memory_layer.isValid():
        print(f"Could not create in-memory layer '{layer_name}'.")
        return None

    # Add a single feature at the provided geometry
    dp = memory_layer.dataProvider()
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(point_geometry))
    dp.addFeatures([feat])

    # Configure symbol (star shape, custom color/size)
    symbol = QgsMarkerSymbol()
    symbol.deleteSymbolLayer(0)  # Remove default circle
    star_layer = QgsSimpleMarkerSymbolLayer(
        shape=QgsSimpleMarkerSymbolLayerBase.Star,
        size=marker_size,
        color=QColor(marker_color)
    )
    symbol.appendSymbolLayer(star_layer)
    memory_layer.setRenderer(QgsSingleSymbolRenderer(symbol))

    project.addMapLayer(memory_layer)
    print(f"Marker layer '{layer_name}' created at {point_geometry}.")
    return memory_layer


def add_frame_to_layout(layout, margin_mm=1.0, outline_width_mm=0.65):
    """
    Add a rectangular frame around an entire layout.

    Parameters
    ----------
    layout : QgsPrintLayout
        The print layout where the frame will be added.
    margin_mm : float, optional
        The margin (in millimeters) from each page border. Default is 1.0 mm.
    outline_width_mm : float, optional
        The width (in millimeters) of the frame’s outline. Default is 0.65 mm.

    Returns
    -------
    QgsLayoutItemShape
        The newly created frame item for further customization if desired.

    Notes
    -----
    - The frame is drawn as a rectangle matching the page size minus the margins.
    - Its default fill is transparent, and only the outline is visible.
    """
    from qgis.core import QgsLayoutItemShape

    # Create the frame shape
    frame = QgsLayoutItemShape(layout)
    frame.setShapeType(QgsLayoutItemShape.Rectangle)
    layout.addLayoutItem(frame)

    # Determine the page size and set the rectangle's dimensions
    page = layout.pageCollection().page(0)
    frame_width = page.pageSize().width() - (2 * margin_mm)
    frame_height = page.pageSize().height() - (2 * margin_mm)

    # Position the frame with the given margins
    frame.attemptMove(QgsLayoutPoint(margin_mm, margin_mm, QgsUnitTypes.LayoutMillimeters))
    frame.attemptResize(QgsLayoutSize(frame_width, frame_height, QgsUnitTypes.LayoutMillimeters))

    # Frame appearance
    frame_symbol = QgsFillSymbol.createSimple({
        'outline_width': str(outline_width_mm),
        'outline_color': 'black',
        'color': 'transparent'
    })
    frame.setSymbol(frame_symbol)

    print(f"Added a rectangular frame to layout '{layout.name()}'.")
    return frame

def add_scale_bar(layout, linked_map, position, size, units, units_per_segment, segment_height=1.5, num_segments=2, font_family="Arial", font_size=8, style="Line Ticks Up", background_color=QColor("white")):
    """
    Adds a scale bar to a QGIS print layout.

    Parameters:
        layout (QgsPrintLayout): The layout where the scale bar will be added.
        linked_map (QgsLayoutItemMap): The map item to which the scale bar will be linked.
        position (QgsLayoutPoint): The position of the scale bar in the layout.
        size (QgsLayoutSize): The size of the scale bar.
        units (QgsUnitTypes.DistanceUnit): The distance units to be displayed (e.g., meters, kilometers).
        units_per_segment (float): The length of each segment of the scale bar in the specified units.
        segment_height (float, optional): Height of the scale bar segments in millimeters. Default is 1.5 mm.
        num_segments (int, optional): Number of segments on the right side of the scale bar. Default is 2.
        font_family (str, optional): Font family for the scale bar labels. Default is "Arial".
        font_size (int, optional): Font size for the scale bar labels. Default is 8.
        style (str, optional): Style of the scale bar (e.g., "Line Ticks Up"). Default is "Line Ticks Up".
        background_color (QColor, optional): Background color for the scale bar. Default is white.

    Returns:
        QgsLayoutItemScaleBar: The created scale bar item.

    Raises:
        ValueError: If the linked_map is not valid or if required parameters are missing.
    """
    # Validate input
    if not layout or not linked_map:
        raise ValueError("Both 'layout' and 'linked_map' must be provided.")

    # Create the scale bar item
    scale_bar = QgsLayoutItemScaleBar(layout)
    scale_bar.setStyle(style)  # Set the style (e.g., Line Ticks Up)
    scale_bar.setLinkedMap(linked_map)  # Link the scale bar to the map
    scale_bar.setUnits(units)  # Set the measurement units (e.g., meters, kilometers)
    scale_bar.setUnitsPerSegment(units_per_segment)  # Set segment length in units
    scale_bar.setUnitLabel("km" if units == QgsUnitTypes.DistanceKilometers else "m")  # Set unit label

    # Configure the appearance of the scale bar
    scale_bar.setNumberOfSegments(num_segments)  # Number of segments to the right of the center
    scale_bar.setNumberOfSegmentsLeft(0)  # No segments to the left of the center
    scale_bar.setHeight(segment_height)  # Height of the segments in millimeters
    scale_bar.setFont(QFont(font_family, font_size))  # Font family and size for labels

    # Enable background for better visibility
    scale_bar.setBackgroundEnabled(True)
    scale_bar.setBackgroundColor(background_color)

    # Add the scale bar to the layout
    layout.addLayoutItem(scale_bar)

    # Adjust the position and size of the scale bar
    scale_bar.attemptResize(size)
    scale_bar.attemptMove(position)

    return scale_bar

def add_html_info_table(layout, info_html, position, size, font_family="Arial", font_size=12):
    """
    Adds an HTML table with information to a QGIS print layout.

    Parameters:
        layout (QgsPrintLayout): The layout where the HTML table will be added.
        info_html (str): The HTML content to be displayed.
        position (QgsLayoutPoint): The position of the HTML table in the layout.
        size (QgsLayoutSize): The size of the HTML table.
        font_family (str, optional): Font family for the table content. Default is "Arial".
        font_size (int, optional): Font size for the table content. Default is 12.

    Returns:
        QgsLayoutItemLabel: The created HTML label item.

    Raises:
        ValueError: If the layout or info_html is not provided.
    """
    # Validate input
    if not layout or not info_html:
        raise ValueError("Both 'layout' and 'info_html' must be provided.")

    # Create the HTML label item
    label = QgsLayoutItemLabel(layout)
    label.setText(info_html)  # Set the HTML content
    label.setMode(QgsLayoutItemLabel.ModeHtml)  # Enable HTML rendering
    label.setFont(QFont(font_family, font_size))  # Set font family and size

    # Add the HTML label to the layout
    layout.addLayoutItem(label)

    # Adjust the position and size of the HTML label
    label.attemptResize(size)
    label.attemptMove(position)

    return label

# HTML Example Usage
# <div class="example-code">
# <p><b>Example:</b> Adding an HTML table to a QGIS layout.</p>
# <pre>
# info_html = """
# <div class='info-table'>
#     <table>
#         <tr><th>Property</th><th>Value</th></tr>
#         <tr><td>Name</td><td>Central Mall</td></tr>
#         <tr><td>District</td><td>Green District</td></tr>
#         <tr><td>Province</td><td>Central Province</td></tr>
#         <tr><td>Area</td><td>15000 m²</td></tr>
#     </table>
# </div>
# """
#
# table_position = QgsLayoutPoint(10, 50, QgsUnitTypes.LayoutMillimeters)
# table_size = QgsLayoutSize(100, 50, QgsUnitTypes.LayoutMillimeters)
#
# html_label = add_html_info_table(
#     layout=layout,
#     info_html=info_html,
#     position=table_position,
#     size=table_size,
#     font_family="Arial",
#     font_size=10
# )
# </pre>
# </div>

import os
os.chdir('/path/to/your/project/directory')

from fundamentals import (
    remove_existing_layer, 
    replace_layer_with_raster, 
    transform_layer_crs,
    set_layer_opacity,
    create_basic_marker_layer,
    add_frame_to_layout
)

project = QgsProject.instance()

# 1) Replace an existing layer with a new raster
replace_layer_with_raster(
    project, 
    # layer_name="OpenStreetMap", 
    # xyz_url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    # layer_name="Bing Aerial", 
    # xyz_url="http://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1",
    # layer_name="Esri Satellite", 
    # xyz_url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    layer_name="Esri Standard", 
    xyz_url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
)

# 2) Transform a layer to EPSG:3857
some_layer = project.mapLayersByName("Districts")[0]
transform_layer_crs(some_layer, "EPSG:3857", project)

# 3) Set partial opacity on a layer
set_layer_opacity(some_layer, 0.4)

# 4) Create a marker at a given coordinate
create_basic_marker_layer(
    project, 
    layer_name="MyMarker", 
    point_geometry=QgsPointXY(-74.0, 4.6), 
    marker_color="#FF0000", 
    marker_size=8.0
)

# 5) Add a frame to a layout (assuming the layout is already created)
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("DemoLayout")
project.layoutManager().addLayout(layout)
add_frame_to_layout(layout)
