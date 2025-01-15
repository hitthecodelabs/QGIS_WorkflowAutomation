import os
import numpy as np
import geopandas as gpd

from qgis.core import (
    QgsPointXY,
    QgsFeature,
    QgsProject,
    QgsGeometry,
    QgsUnitTypes,
    QgsLineSymbol,
    QgsFillSymbol,
    QgsTextFormat,
    QgsLayoutSize,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsLayoutPoint,
    QgsPrintLayout,
    QgsMarkerSymbol,
    QgsLayoutItemMap,
    QgsLegendSettings,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsPalLayerSettings,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsRuleBasedRenderer,
    QgsCoordinateTransform,
    QgsSimpleMarkerSymbolLayer,
    QgsCoordinateReferenceSystem,
    QgsVectorLayerSimpleLabeling,
    QgsSimpleMarkerSymbolLayerBase,
    QgsLayoutMeasurement,
    QgsLayoutItemShape,
)
from pprint import pprint
from pyproj import Transformer
from shapely.geometry import Point
from scipy.optimize import curve_fit
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

def remove_existing_layer(project, layer_name):
    """
    Removes an existing layer from the project by its name.
    """
    for layer in project.mapLayers().values():
        if layer.name() == layer_name:
            project.removeMapLayer(layer)
            print(f"Removed existing layer: {layer_name}")
            break

def load_bing_layer(project, bing_layer_name, bing_url):
    """
    Loads the Bing Aerial layer, replacing any existing layer with the same name.
    """
    remove_existing_layer(project, bing_layer_name)
    bing_layer = QgsRasterLayer(f"type=xyz&url={bing_url}&zmin=0&zmax=19", bing_layer_name, "wms")
    if bing_layer.isValid():
        project.addMapLayer(bing_layer)
        print(f"Successfully loaded: {bing_layer_name} layer")
        return bing_layer
    else:
        print(f"Error: Could not load {bing_layer_name} layer")
        return None

def set_grid_intervals(polygon_area):
    """
    Calculates grid intervals based on the polygon area using a power-law model.
    """
    def power_law(area, k, b):
        return k * (area ** b)

    polygon_area_ha = polygon_area / 10000  # convert m² to hectares

    # Known data for fitting
    areas = np.array([0.1, 1.0, 4.5, 9.5, 35.0])     # in hectares
    intervals = np.array([0.0015, 0.001, 0.001, 0.00275, 0.00225])  # in degrees

    # Fit the data to the power-law model
    params, _ = curve_fit(power_law, areas, intervals, maxfev=20000)
    k, b = params

    # Calculate new intervals
    new_interval_x = power_law(polygon_area_ha, k, b)
    new_interval_y = power_law(polygon_area_ha, k, b)

    # Dynamically adjust intervals
    target_interval = 0.001
    adjustment_factor = 0.85
    new_interval_x = adjustment_factor * new_interval_x + (1 - adjustment_factor) * target_interval
    new_interval_y = adjustment_factor * new_interval_y + (1 - adjustment_factor) * target_interval

    # Clamp intervals
    lower_limit = 0.001
    upper_limit = 0.0011
    new_interval_x = max(lower_limit, min(new_interval_x, upper_limit))
    new_interval_y = max(lower_limit, min(new_interval_y, upper_limit))

    return new_interval_x, new_interval_y

def create_marker_layer(project, polygon_centroid_point):
    """
    Creates a marker layer at the centroid of the polygon.
    """
    remove_existing_layer(project, "Marker")

    marker_layer = QgsVectorLayer("Point?crs=EPSG:4326", "Marker", "memory")
    marker_provider = marker_layer.dataProvider()
    marker_feature = QgsFeature()
    marker_feature.setGeometry(QgsGeometry.fromPointXY(polygon_centroid_point))
    marker_provider.addFeatures([marker_feature])

    # Configure symbol
    symbol = QgsMarkerSymbol()
    symbol.deleteSymbolLayer(0)  # Remove default

    # Two DiamondStar symbols stacked
    diamond_star1 = QgsSimpleMarkerSymbolLayer(
        shape=QgsSimpleMarkerSymbolLayerBase.DiamondStar,
        size=5.5,
        color=QColor("#DBAA00")
    )
    diamond_star2 = QgsSimpleMarkerSymbolLayer(
        shape=QgsSimpleMarkerSymbolLayerBase.DiamondStar,
        size=4.4,
        color=QColor("#DBAA00")
    )
    diamond_star2.setAngle(45)  # 45° rotation for layering

    symbol.appendSymbolLayer(diamond_star2)
    symbol.appendSymbolLayer(diamond_star1)
    marker_layer.renderer().setSymbol(symbol)

    project.addMapLayer(marker_layer)
    marker_layer.triggerRepaint()
    print("Marker layer added and refreshed.")
    return marker_layer

def generate_html_table(predio_info, mall_name, district, province, canton, parroquia, area, utm_centroid, decimal_centroid):
    """
    Generates an HTML table with information about the selected mall.
    """
    table_style = """<style>
        .container {
            font-family: 'Montserrat', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 5px;
            margin: 1px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 5px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        td:nth-child(2) {
            font-family: 'Source Code Pro', monospace;
        }
    </style>"""

    if not predio_info:
        # In case there's no predio_info found
        return table_style + f"""
        <div class="container">
            <table>
                <tr><th>Centro Comercial</th><th>{mall_name}</th></tr>
                <tr><td colspan="2">No predio data found.</td></tr>
            </table>
        </div>"""

    html_content = f"""
    <div class="container">
        <table>
            <tr><th>Centro Comercial</th><th>{mall_name}</th></tr>
            <tr><td>Código Catastral</td><td>{predio_info['Codigo_Cat']}</td></tr>
            <tr><td>Uso</td><td>{predio_info['Uso_de_Edi']}</td></tr>
            <tr><td>Área Registrada</td><td>{round(predio_info['Area_Escri'], 2)} m²</td></tr>
            <tr><td>Centroide (lat, lon)</td><td>{decimal_centroid[0]:.6f}, {decimal_centroid[1]:.6f}</td></tr>
            <tr><td>Lindero Este</td><td>{predio_info['Lindero_Es']}</td></tr>
            <tr><td>Lindero Norte</td><td>{predio_info['Lindero_No']}</td></tr>
            <tr><td>Lindero Oeste</td><td>{predio_info['Lindero_Oe']}</td></tr>
            <tr><td>Lindero Sur</td><td>{predio_info['Lindero_Su']}</td></tr>
        </table>
    </div>
    """
    return table_style + html_content

def add_info_table(layout, info_html):
    """
    Adds the HTML table of information to the QGIS layout.
    """
    label = QgsLayoutItemLabel(layout)
    label.setText(info_html)
    label.setFont(QFont("Arial", 12))
    label.adjustSizeToText()
    layout.addLayoutItem(label)
    label.setMode(QgsLayoutItemLabel.ModeHtml)
    label_size = QgsLayoutSize(103.283, 84.515, QgsUnitTypes.LayoutMillimeters)
    label.attemptResize(label_size)
    label_position = QgsLayoutPoint(13.875, 122.963, QgsUnitTypes.LayoutMillimeters)
    label.attemptMove(label_position)
    print("HTML table added with size and position adjustments.")

def filter_layers(selected_mall_name, malls_layer, districts_layer):
    """
    Filters the malls and districts layers to display only the selected mall and its district,
    while painting other districts gray. Also creates the Mall Polygon and a marker at its centroid.
    """
    selected_mall_feature = None
    for feature in malls_layer.getFeatures():
        if feature["Name"] == selected_mall_name:
            selected_mall_feature = feature
            break

    if not selected_mall_feature:
        print("Selected mall not found.")
        return

    selected_mall_geometry = selected_mall_feature.geometry()
    mall_centroid = selected_mall_geometry.centroid().asPoint()
    selected_district_name = None

    for feature in districts_layer.getFeatures():
        if selected_mall_geometry.within(feature.geometry()):
            selected_district_name = feature["DENOMINACI"]  # Adjust field name if needed
            break

    # District symbology (green for selected, gray for others)
    symbol_with_mall = QgsFillSymbol.createSimple({"color": "#006aff", "outline_width": "1.25", "outline_color": "#FFFFFF"})  
    symbol_with_mall.setOpacity(0.45)
    symbol_no_mall = QgsFillSymbol.createSimple({"color": "#006aff", "outline_width": "1.25", "outline_color": "#FFFFFF"})  
    symbol_no_mall.setOpacity(0.40)

    root_rule = QgsRuleBasedRenderer.Rule(None)

    # Rule for the selected district
    if selected_district_name:
        rule_with_mall = QgsRuleBasedRenderer.Rule(symbol_with_mall)
        rule_with_mall.setFilterExpression(f'"DENOMINACI" = \'{selected_district_name}\'')
        root_rule.appendChild(rule_with_mall)

    # Rule for other districts
    rule_no_mall = QgsRuleBasedRenderer.Rule(symbol_no_mall)
    rule_no_mall.setFilterExpression(f'"DENOMINACI" != \'{selected_district_name}\'')
    root_rule.appendChild(rule_no_mall)

    renderer = QgsRuleBasedRenderer(root_rule)
    districts_layer.setRenderer(renderer)
    districts_layer.triggerRepaint()

    # Filter the malls layer to show only the selected mall
    malls_layer.setSubsetString(f'"Name" = \'{selected_mall_name}\'')
    print(f"Displaying only '{selected_mall_name}' and painting its district '{selected_district_name}' green.")

    # Add the mall polygon as its own layer
    mall_polygon_layer, mall_info = create_mall_polygon_layer(QgsProject.instance(), selected_mall_feature, districts_layer)
    
    return mall_info

def create_mall_polygon_layer(project, selected_mall_feature, districts_layer):
    """
    Creates a layer to display the polygon of the selected mall.
    Also gathers info (area, centroid, etc.) for further usage.
    """
    remove_existing_layer(project, "Mall Polygon")
    mall_polygon_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Mall Polygon", "memory")
    provider = mall_polygon_layer.dataProvider()
    provider.addFeatures([selected_mall_feature])

    # Simple fill style
    symbol = QgsFillSymbol.createSimple({
        "color": "#f0f4f7",
        "outline_color": "black",
        "outline_width_unit": "MM",
        "outline_width": "0.20",
        "style": "dense5"
    })
    mall_polygon_layer.setRenderer(QgsRuleBasedRenderer(QgsRuleBasedRenderer.Rule(symbol)))
    project.addMapLayer(mall_polygon_layer)
    mall_polygon_layer.triggerRepaint()

    # Calculate area and centroid info
    transform_context = project.transformContext()
    utm_crs = QgsCoordinateReferenceSystem("EPSG:32717")  # example UTM zone
    wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")

    transform_to_utm = QgsCoordinateTransform(mall_polygon_layer.crs(), utm_crs, transform_context)
    transform_to_wgs84 = QgsCoordinateTransform(utm_crs, wgs84_crs, transform_context)

    geom = selected_mall_feature.geometry()
    transformed_geom = QgsGeometry(geom)
    transformed_geom.transform(transform_to_utm)
    polygon_area_m2 = transformed_geom.area()
    polygon_centroid_utm = transformed_geom.centroid()
    centroid_point_utm = polygon_centroid_utm.asPoint()
    utm_x, utm_y = centroid_point_utm.x(), centroid_point_utm.y()

    # Convert UTM centroid to WGS84
    polygon_centroid_utm.transform(transform_to_wgs84)
    centroid_point_wgs84 = polygon_centroid_utm.asPoint()
    lon_deg, lat_deg = centroid_point_wgs84.x(), polygon_centroid_utm.asPoint().y()

    mall_name = selected_mall_feature["Name"] if "Name" in selected_mall_feature.fields().names() else "Unknown"

    # Attempt to find district / province / canton / parroquia
    district_name = "Unknown"
    province_name = "Unknown"
    canton_name = "Unknown"
    parroquia_name = "Unknown"
    for feat in districts_layer.getFeatures():
        if geom.within(feat.geometry()):
            district_name = feat["DENOMINACI"] if "DENOMINACI" in feat.fields().names() else "Unknown"
            province_name = feat["PROV"] if "PROV" in feat.fields().names() else "Unknown"
            canton_name = feat["CANTON"] if "CANTON" in feat.fields().names() else "Unknown"
            parroquia_name = feat["PARROQUIA"].replace("PARROQUIA", "").strip() if "PARROQUIA" in feat.fields().names() else "Unknown"
            break

    print(f"Mall Name: {mall_name}")
    print(f"District: {district_name}")
    print(f"Province: {province_name}")
    print(f"Canton: {canton_name}")
    print(f"Parroquia: {parroquia_name}")
    print(f"Area: {polygon_area_m2:.2f} m2")
    print(f"Centroid (UTM): ({utm_x:.3f}, {utm_y:.3f})")
    print(f"Centroid (Decimal Degrees): ({lat_deg:.6f}, {lon_deg:.6f})")

    info = {
        "mall_name": mall_name,
        "district": district_name,
        "province": province_name,
        "canton": canton_name,
        "parroquia": parroquia_name,
        "area": polygon_area_m2,
        "utm_centroid": (utm_x, utm_y),
        "decimal_centroid": (lat_deg, lon_deg)
    }
    return mall_polygon_layer, info

def add_district_labels(districts_layer):
    """
    Configures and enables labeling for the districts layer.
    """
    if not districts_layer.isValid():
        print("Districts layer is invalid. Skipping label configuration.")
        return

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "DENOMINACI"
    label_settings.enabled = True
    
    font_size = 8.5

    text_format = QgsTextFormat()
    font = QFont("Noto Sans", font_size)
    font.setBold(True)
    text_format.setFont(font)
    text_format.setSize(font_size)
    label_settings.setFormat(text_format)

    label_settings.placement = QgsPalLayerSettings.Horizontal
    label_settings.quadOffset = QgsPalLayerSettings.QuadrantAboveLeft

    labeling = QgsVectorLayerSimpleLabeling(label_settings)
    districts_layer.setLabeling(labeling)
    districts_layer.setLabelsEnabled(True)
    districts_layer.triggerRepaint()
    print(f"Labels for districts configured with font size {font_size} and bold text.")

def add_images_to_layout(layout):
    """
    Adds images (logo and north arrows) to the layout.
    """
    # Logo
    image_item = QgsLayoutItemPicture(layout)
    image_item.setPicturePath('htcl_logo.png')
    image_item.attemptResize(QgsLayoutSize(54.569, 16.695, QgsUnitTypes.LayoutMillimeters))
    image_item.attemptMove(QgsLayoutPoint(241.670, 191.149, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(image_item)

    # North arrow (small)
    north_arrow2 = QgsLayoutItemPicture(layout)
    north_arrow2.setPicturePath('north_arrow1.png')
    north_arrow2.attemptResize(QgsLayoutSize(25.120, 21.499, QgsUnitTypes.LayoutMillimeters))
    north_arrow2.attemptMove(QgsLayoutPoint(187.579, 163.226, QgsUnitTypes.LayoutMillimeters))
    north_arrow2.setFrameStrokeColor(QColor(0, 0, 0))
    north_arrow2.setFrameStrokeWidth(QgsLayoutMeasurement(0.10, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(north_arrow2)

def add_footer_label(layout):
    """
    Adds a footer label to the layout.
    """
    label = QgsLayoutItemLabel(layout)
    label.setText("© 2025 Hit the Code Labs. All Rights Reserved.")
    label.setFont(QFont("Open Sans", 7))
    label.adjustSizeToText()
    label.setFontColor(QColor(128, 128, 128, 128))
    layout.addLayoutItem(label)
    label_size = QgsLayoutSize(85.279, 6.455, QgsUnitTypes.LayoutMillimeters)
    label.attemptResize(label_size)
    label.attemptMove(QgsLayoutPoint(3.0 , 204.289, QgsUnitTypes.LayoutMillimeters))

def add_title_label(layout, mall_name):
    """
    Adds a title label to the layout.
    """
    label = QgsLayoutItemLabel(layout)
    label.setText(f"Límites Distritales de Guayaquil".upper())
    font = QFont("Montserrat", 18)
    font.setBold(True)
    label.setFont(font)
    label.adjustSizeToText()
    label.setFontColor(QColor(0, 0, 0))
    label.setFrameEnabled(True)
    label.setFrameStrokeColor(QColor(0, 0, 0))
    label.setFrameStrokeWidth(QgsLayoutMeasurement(0.25, QgsUnitTypes.LayoutMillimeters))
    label.setFrameJoinStyle(Qt.BevelJoin)
    label.setHAlign(Qt.AlignHCenter)
    label.setVAlign(Qt.AlignVCenter)
    layout.addLayoutItem(label)
    label_size = QgsLayoutSize(61.245, 173.030, QgsUnitTypes.LayoutMillimeters)
    label.attemptResize(label_size)
    label.attemptMove(QgsLayoutPoint(228.774, 16.994, QgsUnitTypes.LayoutMillimeters))

# --------------------------------------------------------------------
# ONLY THE "map2" CODE BELOW
# --------------------------------------------------------------------
def create_district_map_layout(
    project,
    province_layer,
    marker_layer,
    ostr_layer,
    info_html,
    mall_info,
    predio_info
):
    """
    Creates a QGIS layout that displays:
      - A single map (district-level) with OSM or Bing (ost_layer),
      - The selected mall’s district in green,
      - A marker for the mall centroid,
      - Scale bar, label, images, footer, etc.
    Exports the layout to PDF and PNG.
    """

    layout_name = "District_Layout"
    mall_name = mall_info['mall_name']

    # Remove any existing layout with the same name
    manager = project.layoutManager()
    existing_layout = manager.layoutByName(layout_name)
    if existing_layout:
        manager.removeLayout(existing_layout)
        print(f"Removed existing layout: {layout_name}")

    # Create a new layout
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)
    manager.addLayout(layout)

    # ---------------------------------------------------------
    # Create the map showing the district + marker + OSM layer
    # ---------------------------------------------------------
    map2 = QgsLayoutItemMap(layout)
    map2.setRect(20, 20, 180, 180)
    map2.setFrameEnabled(True)
    map2.setFrameStrokeWidth(QgsLayoutMeasurement(0.25, QgsUnitTypes.LayoutMillimeters))

    # The layers to show in the district map
    map2.setLayers([province_layer, ostr_layer])

    # Zoom the map to the extent of province_layer (or districts_layer)
    if province_layer.isValid():
        map2_extent = province_layer.extent()
        map2_extent.scale(1.85)
        map2.setExtent(map2_extent)

    map2.attemptResize(QgsLayoutSize(211.496, 173.030, QgsUnitTypes.LayoutMillimeters))
    map2.attemptMove(QgsLayoutPoint(8.719, 16.994, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map2)

    # Label for OSM source
    osm_source_label = QgsLayoutItemLabel(layout)
    osm_source_label.setText("© OpenStreetMap contributors")
    osm_source_label.setFont(QFont("Lato", 7))
    osm_source_label.setFontColor(QColor(128, 128, 128))
    osm_source_label.adjustSizeToText()
    osm_source_label.attemptResize(QgsLayoutSize(40.107, 6.259, QgsUnitTypes.LayoutMillimeters))
    osm_source_label.attemptMove(QgsLayoutPoint(185.233, 190.850, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(osm_source_label)

    # Scale bar for map2
    scale_bar2 = QgsLayoutItemScaleBar(layout)
    scale_bar2.setStyle('Line Ticks Up')
    scale_bar2.setLinkedMap(map2)
    scale_bar2.setUnits(QgsUnitTypes.DistanceKilometers)
    scale_bar2.setUnitsPerSegment(2.5)
    scale_bar2.setUnitLabel("km")
    scale_bar2.setNumberOfSegments(2)
    scale_bar2.setNumberOfSegmentsLeft(0)
    scale_bar2.setBackgroundEnabled(True)
    scale_bar2.setBackgroundColor(QColor('white'))
    scale_bar2.setHeight(1.5)
    scale_bar2.setFont(QFont('Arial', 8))

    layout.addLayoutItem(scale_bar2)
    scale_bar2.attemptResize(QgsLayoutSize(34.399, 10.717, QgsUnitTypes.LayoutMillimeters))
    scale_bar2.attemptMove(QgsLayoutPoint(175.902, 28.080, QgsUnitTypes.LayoutMillimeters))

    # Add images, footer, title, and table
    add_images_to_layout(layout)
    add_footer_label(layout)
    add_title_label(layout, mall_name)
    # add_info_table(layout, info_html)

    # ---------------------------------------------------------
    # Export to PDF and PNG
    # ---------------------------------------------------------
    exporter = QgsLayoutExporter(layout)
    output_pdf = "District_Layout.pdf"
    output_png = "District_Layout.png"

    pdf_result = exporter.exportToPdf(output_pdf, QgsLayoutExporter.PdfExportSettings())
    if pdf_result == QgsLayoutExporter.Success:
        print(f"PDF successfully exported to {output_pdf}")
    else:
        print("Failed to export PDF.")

    png_result = exporter.exportToImage(output_png, QgsLayoutExporter.ImageExportSettings())
    if png_result == QgsLayoutExporter.Success:
        print(f"PNG successfully exported to {output_png}")
    else:
        print("Failed to export PNG.")


# --------------------------------------------------------------------
#  Below is an example usage outline:
# --------------------------------------------------------------------

# Path to your data
districts_file = "distritos_data.geojson"
malls_file = "Centros Comerciales.kml"

ostreet_layer_name = "OpenStreetMap"
ostreet_url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

bing_layer_name = "Bing Aerial"
bing_url = "https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"

google_layer_name = "Google Satellite Hybrid"
google_url = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"

# Load QGIS project instance
project = QgsProject.instance()

# Load OSM as "ost_layer" (we’ll just reuse the Bing function for convenience)
ost_layer = load_bing_layer(project, ostreet_layer_name, ostreet_url)
if ost_layer:
    print(f"OpenStreetMap layer loaded: {ostreet_layer_name}")

# Load the districts layer
remove_existing_layer(project, "Districts")
districts_layer = QgsVectorLayer(districts_file, "Districts", "ogr")
if not districts_layer.isValid():
    print("Failed to load districts layer.")
else:
    print("Districts layer loaded successfully.")
    project.addMapLayer(districts_layer)
    add_district_labels(districts_layer)

# Load the malls layer
remove_existing_layer(project, "Malls")
malls_layer = QgsVectorLayer(malls_file, "Malls", "ogr")
if not malls_layer.isValid():
    print("Failed to load malls layer.")
else:
    print("Malls layer loaded successfully.")
    project.addMapLayer(malls_layer)

# Example of selecting a mall
predefined_mall_index = 5  # pick which mall to highlight
mall_names = [feat["Name"] for feat in malls_layer.getFeatures()]
if 0 <= predefined_mall_index - 1 < len(mall_names):
    selected_mall_name = mall_names[predefined_mall_index - 1]
    print(f"Selected mall: {selected_mall_name}")
else:
    print("Invalid index for malls.")
    selected_mall_name = None

# Filter the layers to show only the selected mall/district
if selected_mall_name:
    mall_info = filter_layers(selected_mall_name, malls_layer, districts_layer)
else:
    mall_info = None

# Suppose we have some `predio_info` from your own logic/GeoDataFrame
predio_info = None  # or a dict if found

# Build your info_html
if mall_info:
    info_html = generate_html_table(
        predio_info,
        mall_info["mall_name"],
        mall_info["district"],
        mall_info["province"],
        mall_info["canton"],
        mall_info["parroquia"],
        mall_info["area"],
        mall_info["utm_centroid"],
        mall_info["decimal_centroid"]
    )
else:
    info_html = "No mall info"

# Get references to the layers you want for map2
province_layer = project.mapLayersByName("Districts")[0]
marker_layer = project.mapLayersByName("Marker")[0]
# ost_layer is already loaded above

# Finally, create and export ONLY map2 (the district-level map)
if mall_info:
    create_district_map_layout(
        project=project,
        province_layer=province_layer,
        marker_layer=marker_layer,
        # ostr_layer=ost_layer,
        ostr_layer=ost_layer,
        info_html=info_html,
        mall_info=mall_info,
        predio_info=predio_info
    )
print("District-level map created (map2 only).")
