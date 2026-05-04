# -*- coding: utf-8 -*-
"""
Anomaly Detection for Ethiopia Data Loader.

Detects unusual patterns and outliers in Ethiopia data.
"""

import math
from qgis.core import QgsProject, QgsVectorLayer


class AnomalyDetector:
    """Detects anomalies and outliers in Ethiopia data."""

    def __init__(self):
        """Initialize the anomaly detector."""
        pass

    def detect_outliers_zscore(self, values, threshold=2.0):
        """
        Detect outliers using Z-score method.

        :param values: List of numeric values
        :param threshold: Z-score threshold (default 2.0)
        :returns: List of (index, value, zscore) tuples for outliers
        """
        if not values or len(values) < 3:
            return []

        # Calculate mean and standard deviation
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

        :param values: List of numeric values
        :param multiplier: IQR multiplier (default 1.5)
        :returns: List of outlier dictionaries
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
                    'index': i,
                    'value': value,
                    'bound': lower_bound,
                    'type': 'low'
                })
            elif value > upper_bound:
                outliers.append({
                    'index': i,
                    'value': value,
                    'bound': upper_bound,
                    'type': 'high'
                })

        return outliers

    def detect_spatial_anomalies(self, layer, field_name):
        """
        Detect features with anomalous attribute values.

        :param layer: QgsVectorLayer
        :param field_name: Field name to analyze
        :returns: Anomaly report dictionary
        """
        if not layer or field_name not in [f.name() for f in layer.fields()]:
            return {'error': 'Invalid layer or field'}

        # Collect values with feature IDs
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

        # Detect outliers using both methods
        zscore_outliers = self.detect_outliers_zscore(values)
        iqr_outliers = self.detect_outliers_iqr(values)

        # Map back to features
        anomalies = []
        outlier_indices = set(o['index'] for o in zscore_outliers + iqr_outliers)

        for idx in outlier_indices:
            if idx < len(values_with_ids):
                feature_data = values_with_ids[idx]
                anomalies.append({
                    'feature_id': feature_data['id'],
                    'value': feature_data['value'],
                    'location': (
                        feature_data['geometry'].centroid().asPoint()
                        if feature_data['geometry'] else None
                    )
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
        Detect potential data quality issues in a layer.

        :param layer: QgsVectorLayer
        :returns: Quality report dictionary
        """
        if not layer:
            return {'error': 'Invalid layer'}

        issues = []

        # Check for null geometries
        null_geom_count = 0
        invalid_geom_count = 0
        empty_geom_count = 0

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom is None:
                null_geom_count += 1
            elif geom.isEmpty():
                empty_geom_count += 1
            elif not geom.isGeosValid():
                invalid_geom_count += 1

        if null_geom_count > 0:
            issues.append({
                'type': 'null_geometry',
                'count': null_geom_count,
                'severity': 'high',
                'description': f'{null_geom_count} features have no geometry'
            })

        if empty_geom_count > 0:
            issues.append({
                'type': 'empty_geometry',
                'count': empty_geom_count,
                'severity': 'medium',
                'description': f'{empty_geom_count} features have empty geometry'
            })

        if invalid_geom_count > 0:
            issues.append({
                'type': 'invalid_geometry',
                'count': invalid_geom_count,
                'severity': 'high',
                'description': f'{invalid_geom_count} features have invalid geometry'
            })

        # Check for null attribute values
        for field in layer.fields():
            null_count = 0
            for feature in layer.getFeatures():
                if feature[field.name()] is None or str(feature[field.name()]).strip() == '':
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
                    'description': f'{null_count} null values ({pct:.1f}%) in field "{field.name()}"'
                })

        return {
            'layer': layer.name(),
            'total_features': layer.featureCount(),
            'issue_count': len(issues),
            'issues': sorted(issues, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['severity']])
        }

    def detect_temporal_anomalies(self, events, date_field='date', value_field='count'):
        """
        Detect anomalies in temporal event data.

        :param events: List of event dictionaries
        :param date_field: Field name for date
        :param value_field: Field name for value to analyze
        :returns: Anomaly report
        """
        if not events:
            return {'error': 'No events provided'}

        # Group by date
        by_date = {}
        for event in events:
            date = event.get(date_field, '')
            value = event.get(value_field, 1)

            if date not in by_date:
                by_date[date] = 0
            by_date[date] += value

        if len(by_date) < 5:
            return {'error': 'Not enough data points for temporal analysis'}

        # Sort by date and get values
        sorted_dates = sorted(by_date.keys())
        values = [by_date[d] for d in sorted_dates]

        # Detect outliers
        outliers = self.detect_outliers_zscore(values, threshold=2.5)

        anomalous_dates = []
        for outlier in outliers:
            idx = outlier['index']
            if idx < len(sorted_dates):
                anomalous_dates.append({
                    'date': sorted_dates[idx],
                    'value': outlier['value'],
                    'type': outlier['type'],
                    'description': f"{'Unusually high' if outlier['type'] == 'high' else 'Unusually low'} activity on {sorted_dates[idx]}"
                })

        return {
            'total_dates': len(sorted_dates),
            'anomaly_count': len(anomalous_dates),
            'anomalies': anomalous_dates,
            'date_range': {
                'start': sorted_dates[0] if sorted_dates else None,
                'end': sorted_dates[-1] if sorted_dates else None
            }
        }
