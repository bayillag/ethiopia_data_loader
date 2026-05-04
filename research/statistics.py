# -*- coding: utf-8 -*-
"""
Spatial Statistics for Ethiopia Data Loader.

Provides spatial autocorrelation and cluster analysis tools.
"""

import math
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsDistanceArea,
    QgsCoordinateReferenceSystem, QgsGeometry, QgsPointXY
)


class SpatialStatistics:
    """Spatial statistical analysis tools."""

    def __init__(self):
        """Initialize spatial statistics calculator."""
        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )
        self.distance_area.setEllipsoid('WGS84')

    def calculate_descriptive_stats(self, values):
        """
        Calculate descriptive statistics for a list of values.

        :param values: List of numeric values
        :returns: Statistics dictionary
        """
        if not values:
            return {'error': 'No values provided'}

        n = len(values)
        sorted_vals = sorted(values)

        # Basic stats
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std = math.sqrt(variance)

        # Median
        if n % 2 == 0:
            median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            median = sorted_vals[n // 2]

        # Quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1

        # Skewness (Pearson's moment coefficient)
        if std > 0:
            skewness = sum((x - mean) ** 3 for x in values) / (n * std ** 3)
        else:
            skewness = 0

        # Kurtosis
        if std > 0:
            kurtosis = sum((x - mean) ** 4 for x in values) / (n * std ** 4) - 3
        else:
            kurtosis = 0

        return {
            'count': n,
            'min': min(values),
            'max': max(values),
            'range': max(values) - min(values),
            'sum': sum(values),
            'mean': mean,
            'median': median,
            'variance': variance,
            'std': std,
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'coefficient_of_variation': (std / mean * 100) if mean != 0 else 0
        }

    def calculate_morans_i(self, layer, field_name, distance_threshold=None):
        """
        Calculate Moran's I spatial autocorrelation.

        :param layer: QgsVectorLayer with polygon or point features
        :param field_name: Field name for the attribute to analyze
        :param distance_threshold: Distance threshold for weights (km)
        :returns: Moran's I statistics dictionary
        """
        if not layer or not layer.isValid():
            return {'error': 'Invalid layer'}

        if field_name not in [f.name() for f in layer.fields()]:
            return {'error': f'Field {field_name} not found'}

        # Collect features with values and centroids
        features_data = []
        for feature in layer.getFeatures():
            try:
                value = float(feature[field_name]) if feature[field_name] is not None else None
                if value is not None:
                    geom = feature.geometry()
                    if geom and not geom.isEmpty():
                        centroid = geom.centroid().asPoint()
                        features_data.append({
                            'id': feature.id(),
                            'value': value,
                            'centroid': centroid
                        })
            except (ValueError, TypeError):
                continue

        n = len(features_data)
        if n < 3:
            return {'error': 'Need at least 3 features with valid values'}

        # Calculate mean
        values = [f['value'] for f in features_data]
        mean = sum(values) / n

        # Calculate deviations
        deviations = [v - mean for v in values]

        # Set default distance threshold if not provided
        if distance_threshold is None:
            # Use average nearest neighbor distance * 2
            total_dist = 0
            for i, f1 in enumerate(features_data):
                min_dist = float('inf')
                for j, f2 in enumerate(features_data):
                    if i != j:
                        dist = self._calculate_distance(f1['centroid'], f2['centroid'])
                        min_dist = min(min_dist, dist)
                total_dist += min_dist
            distance_threshold = (total_dist / n) * 2

        # Build spatial weights matrix and calculate Moran's I
        w_sum = 0
        numerator = 0

        for i, f1 in enumerate(features_data):
            for j, f2 in enumerate(features_data):
                if i != j:
                    dist = self._calculate_distance(f1['centroid'], f2['centroid'])
                    if dist <= distance_threshold:
                        w = 1  # Binary weights
                        w_sum += w
                        numerator += w * deviations[i] * deviations[j]

        # Calculate denominator (sum of squared deviations)
        denominator = sum(d ** 2 for d in deviations)

        if w_sum == 0 or denominator == 0:
            return {'error': 'Cannot calculate - no neighbors or no variance'}

        morans_i = (n / w_sum) * (numerator / denominator)

        # Calculate expected I under null hypothesis
        expected_i = -1 / (n - 1)

        # Calculate variance (simplified formula)
        variance_i = 1 / (n - 1)  # Simplified

        # Z-score
        z_score = (morans_i - expected_i) / math.sqrt(variance_i) if variance_i > 0 else 0

        # P-value approximation (two-tailed)
        p_value = self._normal_p_value(z_score)

        # Interpretation
        if morans_i > 0:
            if p_value < 0.05:
                interpretation = "Significant positive spatial autocorrelation (clustering)"
            else:
                interpretation = "Slight positive autocorrelation (not significant)"
        elif morans_i < 0:
            if p_value < 0.05:
                interpretation = "Significant negative spatial autocorrelation (dispersion)"
            else:
                interpretation = "Slight negative autocorrelation (not significant)"
        else:
            interpretation = "Random spatial pattern"

        return {
            'morans_i': morans_i,
            'expected_i': expected_i,
            'z_score': z_score,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'interpretation': interpretation,
            'n_features': n,
            'distance_threshold_km': distance_threshold
        }

    def calculate_getis_ord_gi(self, layer, field_name, distance_threshold=None):
        """
        Calculate Getis-Ord Gi* statistic for hot spot analysis.

        :param layer: QgsVectorLayer
        :param field_name: Field name to analyze
        :param distance_threshold: Distance threshold in km
        :returns: Dictionary with Gi* values for each feature
        """
        if not layer or not layer.isValid():
            return {'error': 'Invalid layer'}

        if field_name not in [f.name() for f in layer.fields()]:
            return {'error': f'Field {field_name} not found'}

        # Collect features
        features_data = []
        for feature in layer.getFeatures():
            try:
                value = float(feature[field_name]) if feature[field_name] is not None else None
                if value is not None:
                    geom = feature.geometry()
                    if geom and not geom.isEmpty():
                        centroid = geom.centroid().asPoint()
                        features_data.append({
                            'id': feature.id(),
                            'value': value,
                            'centroid': centroid
                        })
            except (ValueError, TypeError):
                continue

        n = len(features_data)
        if n < 3:
            return {'error': 'Need at least 3 features'}

        values = [f['value'] for f in features_data]
        mean = sum(values) / n
        s = math.sqrt(sum((v - mean) ** 2 for v in values) / n)

        if s == 0:
            return {'error': 'No variance in values'}

        # Set default distance threshold
        if distance_threshold is None:
            total_dist = 0
            for i, f1 in enumerate(features_data):
                min_dist = float('inf')
                for j, f2 in enumerate(features_data):
                    if i != j:
                        dist = self._calculate_distance(f1['centroid'], f2['centroid'])
                        min_dist = min(min_dist, dist)
                total_dist += min_dist
            distance_threshold = (total_dist / n) * 2

        # Calculate Gi* for each feature
        results = []
        hotspots = 0
        coldspots = 0

        for i, f1 in enumerate(features_data):
            # Sum of weighted values and weights
            sum_wj_xj = 0
            sum_wj = 0
            sum_wj_squared = 0

            for j, f2 in enumerate(features_data):
                dist = self._calculate_distance(f1['centroid'], f2['centroid'])
                if dist <= distance_threshold:
                    w = 1  # Binary weight
                    sum_wj_xj += w * f2['value']
                    sum_wj += w
                    sum_wj_squared += w ** 2

            # Calculate Gi*
            if sum_wj > 0:
                numerator = sum_wj_xj - mean * sum_wj
                denominator = s * math.sqrt(
                    (n * sum_wj_squared - sum_wj ** 2) / (n - 1)
                )

                if denominator > 0:
                    gi_star = numerator / denominator
                else:
                    gi_star = 0
            else:
                gi_star = 0

            # P-value
            p_value = self._normal_p_value(gi_star)

            # Classification
            if gi_star > 1.96:
                classification = 'hot_spot_99' if gi_star > 2.58 else 'hot_spot_95'
                hotspots += 1
            elif gi_star < -1.96:
                classification = 'cold_spot_99' if gi_star < -2.58 else 'cold_spot_95'
                coldspots += 1
            else:
                classification = 'not_significant'

            results.append({
                'feature_id': f1['id'],
                'value': f1['value'],
                'gi_star': gi_star,
                'p_value': p_value,
                'classification': classification
            })

        return {
            'n_features': n,
            'distance_threshold_km': distance_threshold,
            'hotspot_count': hotspots,
            'coldspot_count': coldspots,
            'not_significant_count': n - hotspots - coldspots,
            'results': results
        }

    def calculate_nearest_neighbor_index(self, layer):
        """
        Calculate Nearest Neighbor Index for point pattern analysis.

        :param layer: QgsVectorLayer with point features
        :returns: NNI statistics dictionary
        """
        if not layer or not layer.isValid():
            return {'error': 'Invalid layer'}

        if layer.geometryType() != 0:  # Not points
            return {'error': 'Layer must contain point features'}

        # Collect points
        points = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                points.append(geom.asPoint())

        n = len(points)
        if n < 2:
            return {'error': 'Need at least 2 points'}

        # Calculate nearest neighbor distances
        nn_distances = []
        for i, p1 in enumerate(points):
            min_dist = float('inf')
            for j, p2 in enumerate(points):
                if i != j:
                    dist = self._calculate_distance(p1, p2)
                    min_dist = min(min_dist, dist)
            nn_distances.append(min_dist)

        # Calculate observed mean distance
        observed_mean = sum(nn_distances) / n

        # Calculate study area (convex hull)
        extent = layer.extent()
        area_km2 = (extent.width() * extent.height() * 111 * 111)  # Approximate for EPSG:4326

        # Expected mean distance under random distribution
        density = n / area_km2
        expected_mean = 0.5 / math.sqrt(density) if density > 0 else 0

        # Nearest Neighbor Index
        nni = observed_mean / expected_mean if expected_mean > 0 else 0

        # Standard error
        se = 0.26136 / math.sqrt(n * density) if density > 0 else 0

        # Z-score
        z_score = (observed_mean - expected_mean) / se if se > 0 else 0

        # P-value
        p_value = self._normal_p_value(z_score)

        # Interpretation
        if nni < 1:
            if p_value < 0.05:
                interpretation = "Significant clustering (clustered pattern)"
            else:
                interpretation = "Slightly clustered (not significant)"
        elif nni > 1:
            if p_value < 0.05:
                interpretation = "Significant dispersion (dispersed pattern)"
            else:
                interpretation = "Slightly dispersed (not significant)"
        else:
            interpretation = "Random pattern"

        return {
            'n_points': n,
            'observed_mean_distance_km': observed_mean,
            'expected_mean_distance_km': expected_mean,
            'nearest_neighbor_index': nni,
            'z_score': z_score,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'interpretation': interpretation,
            'study_area_km2': area_km2
        }

    def calculate_central_tendency(self, layer):
        """
        Calculate central tendency measures for point features.

        :param layer: QgsVectorLayer with point features
        :returns: Central tendency statistics
        """
        if not layer or not layer.isValid():
            return {'error': 'Invalid layer'}

        # Collect points
        x_coords = []
        y_coords = []

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                if geom.type() == 0:  # Point
                    pt = geom.asPoint()
                else:
                    pt = geom.centroid().asPoint()
                x_coords.append(pt.x())
                y_coords.append(pt.y())

        n = len(x_coords)
        if n == 0:
            return {'error': 'No valid geometries'}

        # Mean center
        mean_x = sum(x_coords) / n
        mean_y = sum(y_coords) / n

        # Median center
        sorted_x = sorted(x_coords)
        sorted_y = sorted(y_coords)
        if n % 2 == 0:
            median_x = (sorted_x[n // 2 - 1] + sorted_x[n // 2]) / 2
            median_y = (sorted_y[n // 2 - 1] + sorted_y[n // 2]) / 2
        else:
            median_x = sorted_x[n // 2]
            median_y = sorted_y[n // 2]

        # Standard distance
        std_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_coords) / n)
        std_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_coords) / n)
        std_distance = math.sqrt(std_x ** 2 + std_y ** 2)

        # Standard distance in km (approximate for geographic coordinates)
        std_distance_km = std_distance * 111  # Rough conversion

        return {
            'n_features': n,
            'mean_center': {'x': mean_x, 'y': mean_y},
            'median_center': {'x': median_x, 'y': median_y},
            'std_x': std_x,
            'std_y': std_y,
            'standard_distance_degrees': std_distance,
            'standard_distance_km': std_distance_km,
            'extent': {
                'x_min': min(x_coords),
                'x_max': max(x_coords),
                'y_min': min(y_coords),
                'y_max': max(y_coords)
            }
        }

    def _calculate_distance(self, point1, point2):
        """Calculate distance between two points in km."""
        geom1 = QgsGeometry.fromPointXY(
            QgsPointXY(point1.x(), point1.y()) if hasattr(point1, 'x') else QgsPointXY(point1[0], point1[1])
        )
        geom2 = QgsGeometry.fromPointXY(
            QgsPointXY(point2.x(), point2.y()) if hasattr(point2, 'x') else QgsPointXY(point2[0], point2[1])
        )

        return self.distance_area.measureLine(geom1.asPoint(), geom2.asPoint()) / 1000

    def _normal_p_value(self, z):
        """
        Calculate two-tailed p-value from z-score (approximation).
        """
        # Approximation using error function
        x = abs(z) / math.sqrt(2)
        t = 1 / (1 + 0.3275911 * x)
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        erf = 1 - (a1 * t + a2 * t ** 2 + a3 * t ** 3 + a4 * t ** 4 + a5 * t ** 5) * math.exp(-x ** 2)

        p = 1 - erf
        return p  # Two-tailed
