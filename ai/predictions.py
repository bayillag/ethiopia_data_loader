# -*- coding: utf-8 -*-
"""
Prediction Engine for Ethiopia Data Loader.

Provides trend forecasting and risk assessment for Ethiopia data.
"""

import math
from datetime import datetime, timedelta
from qgis.core import QgsProject, QgsVectorLayer


class PredictionEngine:
    """Engine for predictive analytics on Ethiopia data."""

    def __init__(self):
        """Initialize the prediction engine."""
        pass

    def forecast_trend(self, time_series, periods_ahead=3):
        """
        Forecast future values using simple linear regression.

        :param time_series: List of (date_str, value) tuples or dicts
        :param periods_ahead: Number of periods to forecast
        :returns: Forecast dictionary with predictions and confidence
        """
        if not time_series or len(time_series) < 3:
            return {'error': 'Need at least 3 data points for forecasting'}

        # Extract values
        values = []
        for item in time_series:
            if isinstance(item, dict):
                values.append(item.get('value', 0))
            elif isinstance(item, (list, tuple)):
                values.append(item[1])
            else:
                values.append(float(item))

        n = len(values)
        x_values = list(range(n))

        # Calculate linear regression coefficients
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return {'error': 'Cannot calculate trend - no variance in x values'}

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Calculate R-squared for confidence
        y_pred = [slope * x + intercept for x in x_values]
        ss_res = sum((y - yp) ** 2 for y, yp in zip(values, y_pred))
        ss_tot = sum((y - y_mean) ** 2 for y in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Calculate standard error for confidence intervals
        if n > 2:
            std_error = math.sqrt(ss_res / (n - 2))
        else:
            std_error = 0

        # Generate forecasts
        forecasts = []
        for i in range(periods_ahead):
            x_new = n + i
            predicted = slope * x_new + intercept

            # Simple confidence interval (approximate)
            margin = 1.96 * std_error * math.sqrt(1 + 1/n + (x_new - x_mean)**2 / denominator) if denominator > 0 else 0

            forecasts.append({
                'period': i + 1,
                'predicted_value': max(0, predicted),  # Don't predict negative
                'lower_bound': max(0, predicted - margin),
                'upper_bound': predicted + margin,
                'confidence': max(0, min(1, r_squared))
            })

        # Determine trend direction
        if slope > 0.1:
            trend = 'increasing'
        elif slope < -0.1:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {
            'historical_count': n,
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'trend': trend,
            'trend_description': self._describe_trend(slope, r_squared),
            'forecasts': forecasts
        }

    def assess_conflict_risk(self, events, area_km2=None):
        """
        Assess conflict risk based on historical events.

        :param events: List of conflict event dictionaries
        :param area_km2: Optional area in km² for density calculation
        :returns: Risk assessment dictionary
        """
        if not events:
            return {
                'risk_level': 'unknown',
                'risk_score': 0,
                'factors': ['No historical data available']
            }

        # Count events and fatalities
        total_events = len(events)
        total_fatalities = sum(e.get('fatalities', 0) for e in events)

        # Calculate event density if area provided
        event_density = total_events / area_km2 if area_km2 and area_km2 > 0 else None

        # Analyze recent trend (last 30% of events)
        recent_count = max(1, len(events) // 3)
        recent_events = events[-recent_count:] if len(events) > 3 else events
        recent_fatalities = sum(e.get('fatalities', 0) for e in recent_events)

        # Calculate risk factors
        factors = []
        risk_score = 0

        # Factor 1: Event frequency
        if total_events >= 100:
            risk_score += 30
            factors.append('High number of historical events')
        elif total_events >= 50:
            risk_score += 20
            factors.append('Moderate number of historical events')
        elif total_events >= 10:
            risk_score += 10
            factors.append('Some historical events recorded')

        # Factor 2: Fatality rate
        fatality_rate = total_fatalities / total_events if total_events > 0 else 0
        if fatality_rate >= 5:
            risk_score += 30
            factors.append(f'High fatality rate ({fatality_rate:.1f} per event)')
        elif fatality_rate >= 2:
            risk_score += 20
            factors.append(f'Moderate fatality rate ({fatality_rate:.1f} per event)')
        elif fatality_rate >= 0.5:
            risk_score += 10
            factors.append(f'Low fatality rate ({fatality_rate:.1f} per event)')

        # Factor 3: Recent trend
        if recent_count > 0:
            recent_rate = recent_fatalities / recent_count
            if recent_rate > fatality_rate * 1.5:
                risk_score += 20
                factors.append('Recent escalation in severity')
            elif recent_rate < fatality_rate * 0.5:
                risk_score -= 10
                factors.append('Recent de-escalation observed')

        # Factor 4: Event density
        if event_density:
            if event_density > 1:
                risk_score += 20
                factors.append(f'High event density ({event_density:.2f} per km²)')
            elif event_density > 0.1:
                risk_score += 10
                factors.append(f'Moderate event density ({event_density:.3f} per km²)')

        # Determine risk level
        risk_score = max(0, min(100, risk_score))
        if risk_score >= 70:
            risk_level = 'high'
        elif risk_score >= 40:
            risk_level = 'moderate'
        elif risk_score >= 20:
            risk_level = 'low'
        else:
            risk_level = 'minimal'

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'total_events': total_events,
            'total_fatalities': total_fatalities,
            'fatality_rate': fatality_rate,
            'event_density': event_density,
            'factors': factors,
            'recommendations': self._get_risk_recommendations(risk_level)
        }

    def predict_displacement(self, population, conflict_intensity, distance_km):
        """
        Estimate potential displacement based on conflict intensity.

        :param population: Current population in area
        :param conflict_intensity: 0-1 scale of conflict intensity
        :param distance_km: Distance to nearest safe zone
        :returns: Displacement estimate dictionary
        """
        if population <= 0:
            return {'error': 'Invalid population'}

        # Simple displacement model
        # Base displacement rate increases with conflict intensity
        base_rate = 0.05 + (conflict_intensity * 0.45)  # 5-50% base rate

        # Distance factor - longer distances reduce displacement rate
        distance_factor = 1.0 / (1.0 + distance_km / 100)

        # Calculate estimates
        displacement_rate = base_rate * (0.5 + 0.5 * distance_factor)
        estimated_displaced = int(population * displacement_rate)

        # Confidence decreases with higher estimates
        confidence = max(0.3, 1 - displacement_rate)

        return {
            'population': population,
            'conflict_intensity': conflict_intensity,
            'displacement_rate': displacement_rate,
            'estimated_displaced': estimated_displaced,
            'lower_estimate': int(estimated_displaced * 0.7),
            'upper_estimate': int(estimated_displaced * 1.4),
            'confidence': confidence,
            'scenario': self._describe_displacement_scenario(conflict_intensity)
        }

    def calculate_hotspot_probability(self, layer, value_field, threshold_percentile=90):
        """
        Calculate probability of areas being hotspots.

        :param layer: QgsVectorLayer with numeric values
        :param value_field: Field name containing values to analyze
        :param threshold_percentile: Percentile above which is considered hotspot
        :returns: List of feature hotspot probabilities
        """
        if not layer or not layer.isValid():
            return {'error': 'Invalid layer'}

        if value_field not in [f.name() for f in layer.fields()]:
            return {'error': f'Field {value_field} not found'}

        # Collect values
        values_with_ids = []
        for feature in layer.getFeatures():
            try:
                value = float(feature[value_field]) if feature[value_field] is not None else 0
                values_with_ids.append({
                    'feature_id': feature.id(),
                    'value': value
                })
            except (ValueError, TypeError):
                continue

        if not values_with_ids:
            return {'error': 'No numeric values found'}

        # Calculate threshold
        sorted_values = sorted([v['value'] for v in values_with_ids])
        threshold_idx = int(len(sorted_values) * threshold_percentile / 100)
        threshold = sorted_values[min(threshold_idx, len(sorted_values) - 1)]

        # Calculate mean and std for probability
        mean_val = sum(v['value'] for v in values_with_ids) / len(values_with_ids)
        variance = sum((v['value'] - mean_val) ** 2 for v in values_with_ids) / len(values_with_ids)
        std_val = math.sqrt(variance) if variance > 0 else 1

        # Calculate probabilities
        hotspots = []
        for item in values_with_ids:
            z_score = (item['value'] - mean_val) / std_val if std_val > 0 else 0

            # Convert z-score to probability (simplified)
            probability = min(1.0, max(0.0, 0.5 + z_score * 0.2))

            is_hotspot = item['value'] >= threshold

            hotspots.append({
                'feature_id': item['feature_id'],
                'value': item['value'],
                'z_score': z_score,
                'probability': probability,
                'is_hotspot': is_hotspot
            })

        # Sort by probability
        hotspots.sort(key=lambda x: x['probability'], reverse=True)

        return {
            'total_features': len(hotspots),
            'threshold': threshold,
            'hotspot_count': sum(1 for h in hotspots if h['is_hotspot']),
            'mean': mean_val,
            'std': std_val,
            'hotspots': hotspots
        }

    def project_population_change(self, current_pop, growth_rate, years, displacement_factor=0):
        """
        Project population changes over time.

        :param current_pop: Current population
        :param growth_rate: Annual growth rate (e.g., 0.02 for 2%)
        :param years: Number of years to project
        :param displacement_factor: Annual displacement as fraction (0-1)
        :returns: Population projection dictionary
        """
        if current_pop <= 0:
            return {'error': 'Invalid population'}

        projections = []
        pop = current_pop

        for year in range(1, years + 1):
            # Apply growth
            pop = pop * (1 + growth_rate)

            # Apply displacement
            if displacement_factor > 0:
                pop = pop * (1 - displacement_factor)

            projections.append({
                'year': year,
                'projected_population': int(pop),
                'change_from_current': int(pop - current_pop),
                'percent_change': ((pop - current_pop) / current_pop) * 100
            })

        net_rate = growth_rate - displacement_factor

        return {
            'current_population': current_pop,
            'growth_rate': growth_rate,
            'displacement_factor': displacement_factor,
            'net_rate': net_rate,
            'projections': projections,
            'summary': self._summarize_population_projection(projections, net_rate)
        }

    def _describe_trend(self, slope, r_squared):
        """Generate human-readable trend description."""
        strength = 'strong' if r_squared > 0.7 else ('moderate' if r_squared > 0.4 else 'weak')

        if abs(slope) < 0.1:
            return f"Values are relatively stable ({strength} confidence)"
        elif slope > 0:
            return f"Values show {strength} upward trend"
        else:
            return f"Values show {strength} downward trend"

    def _get_risk_recommendations(self, risk_level):
        """Get recommendations based on risk level."""
        recommendations = {
            'high': [
                'Implement early warning systems',
                'Prepare evacuation plans',
                'Coordinate with humanitarian organizations',
                'Monitor situation closely'
            ],
            'moderate': [
                'Maintain situational awareness',
                'Review contingency plans',
                'Establish communication channels',
                'Track key indicators'
            ],
            'low': [
                'Continue routine monitoring',
                'Keep emergency contacts updated',
                'Participate in community resilience programs'
            ],
            'minimal': [
                'Standard monitoring recommended',
                'Review historical patterns periodically'
            ],
            'unknown': [
                'Gather more data for assessment',
                'Establish baseline monitoring'
            ]
        }
        return recommendations.get(risk_level, recommendations['unknown'])

    def _describe_displacement_scenario(self, intensity):
        """Describe displacement scenario based on intensity."""
        if intensity >= 0.8:
            return 'Severe conflict - mass displacement expected'
        elif intensity >= 0.6:
            return 'High conflict - significant displacement likely'
        elif intensity >= 0.4:
            return 'Moderate conflict - some displacement expected'
        elif intensity >= 0.2:
            return 'Low conflict - limited displacement'
        else:
            return 'Minimal conflict - displacement unlikely'

    def _summarize_population_projection(self, projections, net_rate):
        """Summarize population projection."""
        if not projections:
            return "No projections available"

        final = projections[-1]
        years = len(projections)

        if net_rate > 0.02:
            return f"Population expected to grow significantly, reaching {final['projected_population']:,} in {years} years"
        elif net_rate > 0:
            return f"Population expected to grow slowly, reaching {final['projected_population']:,} in {years} years"
        elif net_rate < -0.02:
            return f"Population expected to decline significantly to {final['projected_population']:,} in {years} years"
        elif net_rate < 0:
            return f"Population expected to decline slowly to {final['projected_population']:,} in {years} years"
        else:
            return f"Population expected to remain stable around {final['projected_population']:,}"
