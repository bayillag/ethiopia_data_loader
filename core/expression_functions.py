# -*- coding: utf-8 -*-
"""
Custom QGIS Expression Functions for Sudan Data Loader.

Provides Sudan-specific expression functions for use in field calculator,
labeling, and styling.

Note: Functions use register=False to prevent crashes during import.
Call register_functions() during plugin initGui() to activate them.
"""

from qgis.core import (
    QgsExpression, QgsProject, QgsVectorLayer,
    QgsDistanceArea, QgsCoordinateReferenceSystem,
    qgsfunction
)


# Sudan state data lookup
SUDAN_STATES = {
    'SD01': {'name_en': 'Northern', 'name_ar': 'الشمالية', 'capital': 'Dongola'},
    'SD02': {'name_en': 'River Nile', 'name_ar': 'نهر النيل', 'capital': 'Ed Damer'},
    'SD03': {'name_en': 'Red Sea', 'name_ar': 'البحر الأحمر', 'capital': 'Port Sudan'},
    'SD04': {'name_en': 'Kassala', 'name_ar': 'كسلا', 'capital': 'Kassala'},
    'SD05': {'name_en': 'Gedaref', 'name_ar': 'القضارف', 'capital': 'Gedaref'},
    'SD06': {'name_en': 'Khartoum', 'name_ar': 'الخرطوم', 'capital': 'Khartoum'},
    'SD07': {'name_en': 'Gezira', 'name_ar': 'الجزيرة', 'capital': 'Wad Madani'},
    'SD08': {'name_en': 'White Nile', 'name_ar': 'النيل الأبيض', 'capital': 'Rabak'},
    'SD09': {'name_en': 'Sennar', 'name_ar': 'سنار', 'capital': 'Singa'},
    'SD10': {'name_en': 'Blue Nile', 'name_ar': 'النيل الأزرق', 'capital': 'Ed Damazin'},
    'SD11': {'name_en': 'North Kordofan', 'name_ar': 'شمال كردفان', 'capital': 'El Obeid'},
    'SD12': {'name_en': 'South Kordofan', 'name_ar': 'جنوب كردفان', 'capital': 'Kadugli'},
    'SD13': {'name_en': 'West Kordofan', 'name_ar': 'غرب كردفان', 'capital': 'El Fula'},
    'SD14': {'name_en': 'North Darfur', 'name_ar': 'شمال دارفور', 'capital': 'El Fasher'},
    'SD15': {'name_en': 'West Darfur', 'name_ar': 'غرب دارفور', 'capital': 'El Geneina'},
    'SD16': {'name_en': 'Central Darfur', 'name_ar': 'وسط دارفور', 'capital': 'Zalingei'},
    'SD17': {'name_en': 'South Darfur', 'name_ar': 'جنوب دارفور', 'capital': 'Nyala'},
    'SD18': {'name_en': 'East Darfur', 'name_ar': 'شرق دارفور', 'capital': 'Ed Daein'}
}


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_state_name(pcode, feature, parent):
    """
    Get Sudan state name from P-Code.

    <h4>Syntax</h4>
    <code>sudan_state_name(pcode)</code>

    <h4>Arguments</h4>
    <ul>
        <li><code>pcode</code> - State P-Code (e.g., 'SD01', 'SD06')</li>
    </ul>

    <h4>Example</h4>
    <code>sudan_state_name('SD06')</code> returns 'Khartoum'
    """
    if pcode and str(pcode).upper() in SUDAN_STATES:
        return SUDAN_STATES[str(pcode).upper()]['name_en']
    return None


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_state_name_ar(pcode, feature, parent):
    """
    Get Sudan state Arabic name from P-Code.

    <h4>Syntax</h4>
    <code>sudan_state_name_ar(pcode)</code>

    <h4>Arguments</h4>
    <ul>
        <li><code>pcode</code> - State P-Code (e.g., 'SD01', 'SD06')</li>
    </ul>

    <h4>Example</h4>
    <code>sudan_state_name_ar('SD06')</code> returns 'الخرطوم'
    """
    if pcode and str(pcode).upper() in SUDAN_STATES:
        return SUDAN_STATES[str(pcode).upper()]['name_ar']
    return None


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_state_capital(pcode, feature, parent):
    """
    Get Sudan state capital from P-Code.

    <h4>Syntax</h4>
    <code>sudan_state_capital(pcode)</code>

    <h4>Arguments</h4>
    <ul>
        <li><code>pcode</code> - State P-Code (e.g., 'SD01', 'SD06')</li>
    </ul>

    <h4>Example</h4>
    <code>sudan_state_capital('SD06')</code> returns 'Khartoum'
    """
    if pcode and str(pcode).upper() in SUDAN_STATES:
        return SUDAN_STATES[str(pcode).upper()]['capital']
    return None


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_locality_count(state_name, feature, parent):
    """
    Count localities in a Sudan state.

    <h4>Syntax</h4>
    <code>sudan_locality_count(state_name)</code>

    <h4>Arguments</h4>
    <ul>
        <li><code>state_name</code> - State name in English</li>
    </ul>

    <h4>Example</h4>
    <code>sudan_locality_count('Khartoum')</code> returns count of localities
    """
    # Find Admin 2 layer
    admin2_layer = None
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            name = layer.name().lower()
            if ('admin 2' in name or 'localities' in name) and 'sudan' in name:
                admin2_layer = layer
                break

    if not admin2_layer or not state_name:
        return 0

    count = 0
    state_lower = str(state_name).lower()

    for f in admin2_layer.getFeatures():
        for field_name in ['ADM1_EN', 'admin1Name_en', 'state']:
            if field_name in [fld.name() for fld in admin2_layer.fields()]:
                value = f[field_name]
                if value and state_lower in str(value).lower():
                    count += 1
                    break

    return count


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_area_km2(feature, parent):
    """
    Calculate area in square kilometers (ellipsoidal).

    <h4>Syntax</h4>
    <code>sudan_area_km2()</code>

    <h4>Description</h4>
    Calculates the area of the current feature using ellipsoidal
    measurement for accurate results.

    <h4>Example</h4>
    <code>sudan_area_km2()</code> returns area in km²
    """
    geom = feature.geometry()
    if not geom or geom.isEmpty():
        return 0

    # Set up distance calculator
    da = QgsDistanceArea()
    da.setSourceCrs(
        QgsCoordinateReferenceSystem('EPSG:4326'),
        QgsProject.instance().transformContext()
    )
    da.setEllipsoid('WGS84')

    area_m2 = da.measureArea(geom)
    return area_m2 / 1_000_000  # Convert to km²


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_perimeter_km(feature, parent):
    """
    Calculate perimeter in kilometers (ellipsoidal).

    <h4>Syntax</h4>
    <code>sudan_perimeter_km()</code>

    <h4>Description</h4>
    Calculates the perimeter of the current feature using ellipsoidal
    measurement for accurate results.

    <h4>Example</h4>
    <code>sudan_perimeter_km()</code> returns perimeter in km
    """
    geom = feature.geometry()
    if not geom or geom.isEmpty():
        return 0

    da = QgsDistanceArea()
    da.setSourceCrs(
        QgsCoordinateReferenceSystem('EPSG:4326'),
        QgsProject.instance().transformContext()
    )
    da.setEllipsoid('WGS84')

    perimeter_m = da.measurePerimeter(geom)
    return perimeter_m / 1000  # Convert to km


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_is_darfur(state_name, feature, parent):
    """
    Check if a state is in Darfur region.

    <h4>Syntax</h4>
    <code>sudan_is_darfur(state_name)</code>

    <h4>Arguments</h4>
    <ul>
        <li><code>state_name</code> - State name to check</li>
    </ul>

    <h4>Example</h4>
    <code>sudan_is_darfur('North Darfur')</code> returns True
    """
    darfur_states = ['North Darfur', 'South Darfur', 'West Darfur',
                     'Central Darfur', 'East Darfur']

    if state_name:
        for ds in darfur_states:
            if ds.lower() in str(state_name).lower():
                return True
    return False


@qgsfunction(args='auto', group='Sudan Data', referenced_columns=[], register=False)
def sudan_region(state_name, feature, parent):
    """
    Get the region for a Sudan state.

    <h4>Syntax</h4>
    <code>sudan_region(state_name)</code>

    <h4>Arguments</h4>
    <ul>
        <li><code>state_name</code> - State name</li>
    </ul>

    <h4>Returns</h4>
    One of: Northern, Eastern, Central, Kordofan, Darfur

    <h4>Example</h4>
    <code>sudan_region('Khartoum')</code> returns 'Central'
    """
    if not state_name:
        return None

    state_lower = str(state_name).lower()

    regions = {
        'Northern': ['northern', 'river nile'],
        'Eastern': ['red sea', 'kassala', 'gedaref'],
        'Central': ['khartoum', 'gezira', 'white nile', 'sennar', 'blue nile'],
        'Kordofan': ['north kordofan', 'south kordofan', 'west kordofan'],
        'Darfur': ['north darfur', 'south darfur', 'west darfur', 'central darfur', 'east darfur']
    }

    for region, states in regions.items():
        for state in states:
            if state in state_lower:
                return region

    return 'Unknown'


def register_functions():
    """Register all Sudan expression functions."""
    try:
        QgsExpression.registerFunction(sudan_state_name)
        QgsExpression.registerFunction(sudan_state_name_ar)
        QgsExpression.registerFunction(sudan_state_capital)
        QgsExpression.registerFunction(sudan_locality_count)
        QgsExpression.registerFunction(sudan_area_km2)
        QgsExpression.registerFunction(sudan_perimeter_km)
        QgsExpression.registerFunction(sudan_is_darfur)
        QgsExpression.registerFunction(sudan_region)
    except Exception:
        # Silently fail if registration fails
        pass


def unregister_functions():
    """Unregister all Sudan expression functions."""
    try:
        QgsExpression.unregisterFunction('sudan_state_name')
        QgsExpression.unregisterFunction('sudan_state_name_ar')
        QgsExpression.unregisterFunction('sudan_state_capital')
        QgsExpression.unregisterFunction('sudan_locality_count')
        QgsExpression.unregisterFunction('sudan_area_km2')
        QgsExpression.unregisterFunction('sudan_perimeter_km')
        QgsExpression.unregisterFunction('sudan_is_darfur')
        QgsExpression.unregisterFunction('sudan_region')
    except Exception:
        # Silently fail if unregistration fails
        pass
