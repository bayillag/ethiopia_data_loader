# -*- coding: utf-8 -*-
"""
Anomaly Detection for Ethiopia Data Loader.

Detects unusual patterns and outliers in Ethiopian datasets (Population, IDPs, ACLED, etc.).
Optimized for QGIS 4.x.
"""

import math
import re
from qgis.core import QgsProject, QgsVectorLayer, QgsGeometry


class EthiopiaAnomalyDetector:
    """Detects anomalies and outliers in Ethiopian geospatial and humanitarian data."""

    def __init__(self):
        """Initialize the Ethiopia anomaly detector."""
        pass

    def detect_outliers_zscore(self, values, threshold=2.0):
        """
        Detect outliers using Z-score method.
        Useful for detecting unusual population spikes in Woredas or Zones.
        """
        if not values or len(values) < 3:
            return []

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            return []

        outliers = []
        for i, value in enumerate(values):
            zscore = (value - mean) / std
            if abs(zscore) > threshold:
                outliers.append({
                    'index': i,
                    'value': value,
                    'zscore': zscore,
                    'type': 'high' if zscore > 0 else 'low'
                })

        return outliers

    def detect_outliers_iqr(self, values, multiplier=1.5):
        """
        Detect outliers using Interquartile Range (IQR) method.
        Robust against extreme data errors.
        """
        if not values or len(values) < 4:
            return []

        sorted_values = sorted(values)
        n = len(sorted_values)

        q1_idx = n // 4
        q3_idx = 3 * n // 4

        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        outliers = []
        for i, value in enumerate(values):
            if value < lower_bound:
                outliers.append({
                    'index': i, 'value': value, 'bound': lower_bound, 'type': 'low'
                })
            elif value > upper_bound:
                outliers.append({
                    'index': i, 'value': value, 'bound': upper_bound, 'type': 'high'
                })

        return outliers

    def detect_spatial_anomalies(self, layer, field_name):
        """
        Detect features with anomalous attribute values (e.g. outlier population in a Zone).
        """
        if not layer or field_name not in [f.name() for f in layer.fields()]:
            return {'error': 'Invalid layer or field'}

        values_with_ids = []
        for feature in layer.getFeatures():
            value = feature[field_name]
            try:
                numeric_value = float(value) if value is not None else None
                if numeric_value is not None:
                    values_with_ids.append({
                        'id': feature.id(),
                        'value': numeric_value,
                        'geometry': feature.geometry()
                    })
            except (ValueError, TypeError):
                continue

        if not values_with_ids:
            return {'error': 'No numeric values found'}

        values = [v['value'] for v in values_with_ids]
        zscore_outliers = self.detect_outliers_zscore(values)
        iqr_outliers = self.detect_outliers_iqr(values)

        anomalies = []
        outlier_indices = set(o['index'] for o in zscore_outliers + iqr_outliers)

        for idx in outlier_indices:
            if idx < len(values_with_ids):
                feature_data = values_with_ids[idx]
                # QGIS 4.x centroid access
                centroid = None
                if feature_data['geometry'] and not feature_data['geometry'].isEmpty():
                    centroid = feature_data['geometry'].centroid().asPoint()

                anomalies.append({
                    'feature_id': feature_data['id'],
                    'value': feature_data['value'],
                    'location': centroid
                })

        return {
            'field': field_name,
            'total_features': len(values_with_ids),
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
            'statistics': {
                'mean': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
        }

    def detect_data_quality_issues(self, layer):
        """
        Detect potential data quality issues specific to Ethiopia COD-AB data.
        Includes checks for ET P-Codes.
        """
        if not layer:
            return {'error': 'Invalid layer'}

        issues = []
        null_geom_count = 0
        invalid_geom_count = 0
        pcode_issue_count = 0
        
        # Regex for Ethiopian P-Codes (e.g., ET04, ET0401, ET040101)
        pcode_pattern = re.compile(r'^ET\d{2,6}$')

        for feature in layer.getFeatures():
            # Geometry Checks
            geom = feature.geometry()
            if geom.isNull():
                null_geom_count += 1
            elif not geom.isGeosValid():
                invalid_geom_count += 1
            
            # Ethiopia-Specific P-Code Validation
            # Checks common HDX fields like 'ADM1_PCODE', 'ADM2_PCODE', 'ADM3_PCODE'
            for field in layer.fields():
                fname = field.name().upper()
                if 'PCODE' in fname:
                    val = str(feature[field.name()])
                    if val and val != 'NULL' and not pcode_pattern.match(val):
                        pcode_issue_count += 1

        if null_geom_count > 0:
            issues.append({'type': 'null_geometry', 'count': null_geom_count, 'severity': 'high', 
                           'description': f'{null_geom_count} features have missing geometry'})

        if invalid_geom_count > 0:
            issues.append({'type': 'invalid_geometry', 'count': invalid_geom_count, 'severity': 'high', 
                           'description': f'{invalid_geom_count} features have invalid topology'})
                           
        if pcode_issue_count > 0:
            issues.append({'type': 'invalid_pcode', 'count': pcode_issue_count, 'severity': 'medium', 
                           'description': f'{pcode_issue_count} features have non-standard Ethiopian P-Codes'})

        # Check for null attribute values
        for field in layer.fields():
            null_count = 0
            for feature in layer.getFeatures():
                val = feature[field.name()]
                if val is None or str(val).strip() == '' or str(val).lower() == 'null':
                    null_count += 1

            if null_count > 0:
                pct = (null_count / layer.featureCount()) * 100
                severity = 'high' if pct > 50 else ('medium' if pct > 20 else 'low')
                issues.append({
                    'type': 'null_attributes',
                    'field': field.name(),
                    'count': null_count,
                    'percentage': pct,
                    'severity': severity,
                    'description': f'{null_count} nulls ({pct:.1f}%) in "{field.name()}"'
                })

        return {
            'layer': layer.name(),
            'issue_count': len(issues),
            'issues': sorted(issues, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['severity']])
        }

    def detect_temporal_anomalies(self, events, date_field='date', value_field='count'):
        """
        Detect anomalies in temporal event data (e.g. ACLED Ethiopia conflict spikes).
        """
        if not events:
            return {'error': 'No events provided'}

        by_date = {}
        for event in events:
            date = str(event.get(date_field, ''))
            value = event.get(value_field, 1)
            by_date[date] = by_date.get(date, 0) + value

        if len(by_date) < 5:
            return {'error': 'Insufficient data for temporal trend analysis'}

        sorted_dates = sorted(by_date.keys())
        values = [by_date[d] for d in sorted_dates]

        outliers = self.detect_outliers_zscore(values, threshold=2.5)

        anomalous_dates = []
        for outlier in outliers:
            idx = outlier['index']
            anomalous_dates.append({
                'date': sorted_dates[idx],
                'value': outlier['value'],
                'type': outlier['type'],
                'description': f"{'Spike' if outlier['type'] == 'high' else 'Drop'} detected on {sorted_dates[idx]}"
            })

        return {
            'total_dates': len(sorted_dates),
            'anomaly_count': len(anomalous_dates),
            'anomalies': anomalous_dates
        }
