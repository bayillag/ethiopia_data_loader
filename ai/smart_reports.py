# -*- coding: utf-8 -*-
"""
Smart Reports Generator for Sudan Data Loader.

Generates AI-assisted summaries and insights from Sudan data.
"""

from datetime import datetime
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsDistanceArea,
    QgsCoordinateReferenceSystem, QgsFeatureRequest
)


class SmartReportGenerator:
    """Generates intelligent reports and summaries from Sudan data."""

    def __init__(self):
        """Initialize the report generator."""
        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )
        self.distance_area.setEllipsoid('WGS84')

    def generate_area_summary(self, layer, name_field=None):
        """
        Generate a summary of an area from layer data.

        :param layer: QgsVectorLayer
        :param name_field: Optional field name for feature names
        :returns: Summary dictionary
        """
        if not layer or not layer.isValid():
            return None

        # Detect name field if not provided
        if not name_field:
            for candidate in ['ADM1_EN', 'ADM2_EN', 'name', 'NAME']:
                if candidate in [f.name() for f in layer.fields()]:
                    name_field = candidate
                    break

        # Collect statistics
        features_data = []
        total_area = 0

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue

            area_km2 = self.distance_area.measureArea(geom) / 1_000_000
            total_area += area_km2

            name = feature[name_field] if name_field else f"Feature {feature.id()}"

            features_data.append({
                'name': str(name) if name else 'Unnamed',
                'area_km2': area_km2,
                'centroid': geom.centroid().asPoint()
            })

        # Sort by area
        features_data.sort(key=lambda x: x['area_km2'], reverse=True)

        return {
            'layer_name': layer.name(),
            'feature_count': len(features_data),
            'total_area_km2': total_area,
            'average_area_km2': total_area / len(features_data) if features_data else 0,
            'largest': features_data[0] if features_data else None,
            'smallest': features_data[-1] if features_data else None,
            'features': features_data,
            'generated_at': datetime.now().isoformat()
        }

    def generate_state_profile(self, state_name):
        """
        Generate a comprehensive profile for a Sudan state.

        :param state_name: State name
        :returns: Profile dictionary
        """
        profile = {
            'state_name': state_name,
            'generated_at': datetime.now().isoformat(),
            'area_km2': 0,
            'locality_count': 0,
            'localities': [],
            'insights': []
        }

        # Find Admin 1 layer for state info
        admin1_layer = self._find_layer('admin 1', 'states')
        if admin1_layer:
            for feature in admin1_layer.getFeatures():
                for field in ['ADM1_EN', 'admin1Name_en', 'name']:
                    if field in [f.name() for f in admin1_layer.fields()]:
                        if feature[field] and state_name.lower() in str(feature[field]).lower():
                            geom = feature.geometry()
                            if geom:
                                profile['area_km2'] = self.distance_area.measureArea(geom) / 1_000_000

                            # Get Arabic name if available
                            for ar_field in ['ADM1_AR', 'admin1Name_ar']:
                                if ar_field in [f.name() for f in admin1_layer.fields()]:
                                    profile['arabic_name'] = feature[ar_field]
                                    break
                            break

        # Find Admin 2 layer for localities
        admin2_layer = self._find_layer('admin 2', 'localities')
        if admin2_layer:
            for feature in admin2_layer.getFeatures():
                for field in ['ADM1_EN', 'admin1Name_en']:
                    if field in [f.name() for f in admin2_layer.fields()]:
                        if feature[field] and state_name.lower() in str(feature[field]).lower():
                            profile['locality_count'] += 1

                            # Get locality name
                            for name_field in ['ADM2_EN', 'admin2Name_en', 'name']:
                                if name_field in [f.name() for f in admin2_layer.fields()]:
                                    loc_name = feature[name_field]
                                    if loc_name:
                                        profile['localities'].append(str(loc_name))
                                    break
                            break

        # Generate insights
        profile['insights'] = self._generate_insights(profile)

        return profile

    def generate_comparison_report(self, features_or_states):
        """
        Generate a comparison report between states or features.

        :param features_or_states: List of state names or features
        :returns: Comparison dictionary
        """
        comparison = {
            'items': [],
            'summary': {},
            'generated_at': datetime.now().isoformat()
        }

        for item in features_or_states:
            if isinstance(item, str):
                # It's a state name
                profile = self.generate_state_profile(item)
                comparison['items'].append({
                    'name': item,
                    'area_km2': profile.get('area_km2', 0),
                    'locality_count': profile.get('locality_count', 0)
                })
            else:
                # It's a feature
                geom = item.geometry()
                comparison['items'].append({
                    'name': str(item['ADM1_EN'] if 'ADM1_EN' in item.fields().names() else item.id()),
                    'area_km2': self.distance_area.measureArea(geom) / 1_000_000 if geom else 0
                })

        # Calculate summary
        if comparison['items']:
            areas = [i['area_km2'] for i in comparison['items']]
            comparison['summary'] = {
                'total_area': sum(areas),
                'average_area': sum(areas) / len(areas),
                'largest': max(comparison['items'], key=lambda x: x['area_km2']),
                'smallest': min(comparison['items'], key=lambda x: x['area_km2'])
            }

        return comparison

    def generate_trend_analysis(self, data_series, time_field='date'):
        """
        Analyze trends in time-series data.

        :param data_series: List of data points with timestamps
        :param time_field: Field name for timestamp
        :returns: Trend analysis dictionary
        """
        if not data_series:
            return {'error': 'No data provided'}

        # Sort by time
        sorted_data = sorted(data_series, key=lambda x: x.get(time_field, ''))

        # Calculate basic statistics
        values = [d.get('value', 0) for d in sorted_data if 'value' in d]

        if not values:
            return {'error': 'No numeric values found'}

        analysis = {
            'data_points': len(values),
            'first_date': sorted_data[0].get(time_field, 'Unknown'),
            'last_date': sorted_data[-1].get(time_field, 'Unknown'),
            'min_value': min(values),
            'max_value': max(values),
            'mean_value': sum(values) / len(values),
            'trend': 'stable'
        }

        # Determine trend
        if len(values) >= 3:
            first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
            second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

            change_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg else 0
            analysis['change_percent'] = change_pct

            if change_pct > 10:
                analysis['trend'] = 'increasing'
                analysis['trend_description'] = f"Values have increased by approximately {abs(change_pct):.1f}%"
            elif change_pct < -10:
                analysis['trend'] = 'decreasing'
                analysis['trend_description'] = f"Values have decreased by approximately {abs(change_pct):.1f}%"
            else:
                analysis['trend'] = 'stable'
                analysis['trend_description'] = "Values have remained relatively stable"

        return analysis

    def _generate_insights(self, profile):
        """Generate text insights from profile data."""
        insights = []

        area = profile.get('area_km2', 0)
        localities = profile.get('locality_count', 0)

        if area > 0:
            # Compare to Sudan total (approximately 1,886,000 km²)
            sudan_total = 1_886_000
            percentage = (area / sudan_total) * 100
            insights.append(f"Covers approximately {percentage:.1f}% of Sudan's total area")

        if localities > 0:
            avg_locality_area = area / localities if area and localities else 0
            insights.append(f"Contains {localities} localities")
            if avg_locality_area > 0:
                insights.append(f"Average locality size: {avg_locality_area:,.0f} km²")

        # Regional classification
        state_name = profile.get('state_name', '').lower()
        if 'darfur' in state_name:
            insights.append("Located in the Darfur region of western Sudan")
        elif 'kordofan' in state_name:
            insights.append("Located in the Kordofan region of central Sudan")
        elif state_name in ['khartoum']:
            insights.append("Capital region containing Khartoum city")
        elif state_name in ['red sea', 'kassala', 'gedaref']:
            insights.append("Located in eastern Sudan")
        elif state_name in ['northern', 'river nile']:
            insights.append("Located in northern Sudan along the Nile")

        return insights

    def _find_layer(self, *keywords):
        """Find a Sudan layer by keywords."""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                name = layer.name().lower()
                if 'sudan' in name and any(kw in name for kw in keywords):
                    return layer
        return None

    def export_report_html(self, report_data, title="Sudan Data Report"):
        """
        Export report data as HTML.

        :param report_data: Report dictionary
        :param title: Report title
        :returns: HTML string
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #3498db; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        .stat {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .insight {{ background: #e8f4f8; padding: 10px; margin: 5px 0; border-left: 3px solid #3498db; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="footer">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""

        # Add content based on report type
        if 'state_name' in report_data:
            # State profile
            html += f"<h2>{report_data['state_name']}</h2>"

            if 'arabic_name' in report_data:
                html += f"<p><strong>Arabic:</strong> {report_data['arabic_name']}</p>"

            html += f"""
            <div class="stat">
                <strong>Area:</strong> {report_data.get('area_km2', 0):,.2f} km²<br>
                <strong>Localities:</strong> {report_data.get('locality_count', 0)}
            </div>
            """

            if report_data.get('insights'):
                html += "<h2>Insights</h2>"
                for insight in report_data['insights']:
                    html += f'<div class="insight">{insight}</div>'

            if report_data.get('localities'):
                html += "<h2>Localities</h2><ul>"
                for loc in report_data['localities'][:20]:
                    html += f"<li>{loc}</li>"
                if len(report_data['localities']) > 20:
                    html += f"<li>... and {len(report_data['localities']) - 20} more</li>"
                html += "</ul>"

        elif 'items' in report_data:
            # Comparison report
            html += "<h2>Comparison</h2>"
            html += "<table><tr><th>Name</th><th>Area (km²)</th></tr>"
            for item in report_data['items']:
                html += f"<tr><td>{item['name']}</td><td>{item.get('area_km2', 0):,.2f}</td></tr>"
            html += "</table>"

            if report_data.get('summary'):
                summary = report_data['summary']
                html += f"""
                <div class="stat">
                    <strong>Total Area:</strong> {summary.get('total_area', 0):,.2f} km²<br>
                    <strong>Largest:</strong> {summary.get('largest', {}).get('name', 'N/A')}<br>
                    <strong>Smallest:</strong> {summary.get('smallest', {}).get('name', 'N/A')}
                </div>
                """

        html += """
</body>
</html>"""

        return html
