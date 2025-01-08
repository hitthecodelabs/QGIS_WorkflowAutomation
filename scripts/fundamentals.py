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

