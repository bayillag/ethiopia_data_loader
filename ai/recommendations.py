# -*- coding: utf-8 -*-
"""
Recommendation Engine for Ethiopia Data Loader.

Provides smart data recommendations and contextual suggestions.
"""

from datetime import datetime
from qgis.core import QgsProject, QgsVectorLayer, QgsRectangle


class RecommendationEngine:
    """Engine for generating smart data recommendations."""

    # Dataset relationships for "users who loaded X also loaded Y"
    DATASET_ASSOCIATIONS = {
        'admin_boundaries': ['health_facilities', 'education', 'population'],
        'admin1': ['admin2', 'settlements', 'roads'],
        'admin2': ['admin1', 'health_facilities', 'settlements'],
        'health_facilities': ['admin_boundaries', 'roads', 'population'],
        'education': ['admin_boundaries', 'population', 'roads'],
        'settlements': ['admin_boundaries', 'roads', 'population'],
        'roads': ['settlements', 'health_facilities', 'admin_boundaries'],
        'water_bodies': ['settlements', 'admin_boundaries'],
        'fire': ['admin_boundaries', 'settlements', 'vegetation'],
        'satellite': ['admin_boundaries', 'fire', 'vegetation']
    }

    # Contextual tips for different data types
    CONTEXTUAL_TIPS = {
        'admin_boundaries': [
            "Use 'Select by Location' to find features within specific states",
            "Try the 'Dissolve' tool to merge localities by state",
            "Enable labels to show state/locality names"
        ],
        'health_facilities': [
            "Buffer health facilities to analyze service coverage",
            "Use 'Count Points in Polygon' to see facility distribution",
            "Join population data to assess healthcare access"
        ],
        'conflict': [
            "Filter by date to analyze temporal patterns",
            "Use heat map styling to visualize conflict density",
            "Export filtered data for time-series analysis"
        ],
        'displacement': [
            "Compare with conflict data to understand causes",
            "Analyze proximity to settlements and services",
            "Track changes over time with temporal filtering"
        ],
        'satellite': [
            "Use band combinations for different analysis types",
            "Compare dates for change detection",
            "Calculate NDVI for vegetation analysis"
        ]
    }

    def __init__(self):
        """Initialize the recommendation engine."""
        self.user_history = []
        self.session_start = datetime.now()

    def record_action(self, action_type, details=None):
        """
        Record user action for learning.

        :param action_type: Type of action (load, filter, zoom, etc.)
        :param details: Dictionary with action details
        """
        self.user_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action_type,
            'details': details or {}
        })

        # Keep history manageable
        if len(self.user_history) > 100:
            self.user_history = self.user_history[-100:]

    def get_dataset_recommendations(self, loaded_datasets):
        """
        Get dataset recommendations based on what's already loaded.

        :param loaded_datasets: List of loaded dataset names/types
        :returns: List of recommendation dictionaries
        """
        recommendations = []
        already_loaded = set(d.lower() for d in loaded_datasets)

        # Find associated datasets
        suggested = set()
        for dataset in loaded_datasets:
            dataset_key = self._normalize_dataset_name(dataset)
            if dataset_key in self.DATASET_ASSOCIATIONS:
                for associated in self.DATASET_ASSOCIATIONS[dataset_key]:
                    if associated not in already_loaded:
                        suggested.add(associated)

        # Convert to recommendations
        for dataset in suggested:
            recommendations.append({
                'type': 'dataset',
                'name': self._format_dataset_name(dataset),
                'reason': f"Commonly used with {', '.join(loaded_datasets[:2])}",
                'priority': self._get_dataset_priority(dataset, loaded_datasets)
            })

        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'], reverse=True)

        return recommendations[:5]  # Top 5

    def get_contextual_tips(self, current_context):
        """
        Get contextual tips based on current activity.

        :param current_context: Dictionary describing current context
        :returns: List of relevant tips
        """
        tips = []

        # Check active layer type
        active_layer = current_context.get('active_layer')
        if active_layer:
            layer_type = self._detect_layer_type(active_layer)
            if layer_type in self.CONTEXTUAL_TIPS:
                tips.extend(self.CONTEXTUAL_TIPS[layer_type])

        # Check for specific conditions
        if current_context.get('has_selection'):
            tips.append("Use 'Zoom to Selection' to focus on selected features")
            tips.append("Export selected features using 'Save Selected Features As...'")

        if current_context.get('is_filtered'):
            tips.append("Clear filter to see all features again")
            tips.append("Save filter as a definition query for reuse")

        if current_context.get('zoom_level') == 'overview':
            tips.append("Zoom in to see more detailed features")
            tips.append("Use state boundaries for navigation")

        if current_context.get('zoom_level') == 'detail':
            tips.append("Consider loading higher resolution data for this area")
            tips.append("Enable OSM basemap for additional context")

        return tips[:5]  # Top 5 tips

    def get_analysis_suggestions(self, layers):
        """
        Suggest analyses based on loaded layers.

        :param layers: List of QgsVectorLayer objects
        :returns: List of analysis suggestion dictionaries
        """
        suggestions = []
        layer_types = [self._detect_layer_type(l.name()) for l in layers if l]

        # Point + Polygon = Count Points in Polygon
        has_points = any(l.geometryType() == 0 for l in layers if l and l.isValid())
        has_polygons = any(l.geometryType() == 2 for l in layers if l and l.isValid())

        if has_points and has_polygons:
            suggestions.append({
                'analysis': 'Count Points in Polygon',
                'description': 'Count point features within each polygon',
                'tool': 'processing:countpointsinpolygon',
                'relevance': 0.9
            })

        # Conflict data = Heat map
        if 'conflict' in layer_types:
            suggestions.append({
                'analysis': 'Heat Map Visualization',
                'description': 'Create heat map of conflict events',
                'tool': 'heatmap_style',
                'relevance': 0.85
            })
            suggestions.append({
                'analysis': 'Temporal Analysis',
                'description': 'Analyze conflict trends over time',
                'tool': 'temporal_controller',
                'relevance': 0.8
            })

        # Health facilities = Service area
        if 'health_facilities' in layer_types:
            suggestions.append({
                'analysis': 'Service Area Analysis',
                'description': 'Buffer health facilities to show coverage',
                'tool': 'processing:buffer',
                'relevance': 0.85
            })

        # Admin boundaries = Statistics
        if 'admin_boundaries' in layer_types or 'admin1' in layer_types:
            suggestions.append({
                'analysis': 'Zonal Statistics',
                'description': 'Calculate statistics per administrative unit',
                'tool': 'processing:zonalstatistics',
                'relevance': 0.75
            })

        # Multiple layers = Spatial Join
        if len(layers) >= 2:
            suggestions.append({
                'analysis': 'Spatial Join',
                'description': 'Join attributes based on spatial relationship',
                'tool': 'processing:joinattributesbylocation',
                'relevance': 0.7
            })

        # Sort by relevance
        suggestions.sort(key=lambda x: x['relevance'], reverse=True)

        return suggestions[:5]

    def get_workflow_suggestions(self, user_goal=None):
        """
        Suggest workflows based on user goal or current state.

        :param user_goal: Optional string describing user's goal
        :returns: List of workflow suggestions
        """
        workflows = {
            'humanitarian_assessment': {
                'name': 'Humanitarian Needs Assessment',
                'steps': [
                    'Load Admin 2 (localities) boundaries',
                    'Load health facilities and education data',
                    'Download recent conflict events',
                    'Generate statistics per locality',
                    'Create thematic maps showing needs',
                    'Export report with findings'
                ],
                'keywords': ['humanitarian', 'needs', 'assessment', 'crisis']
            },
            'conflict_analysis': {
                'name': 'Conflict Analysis',
                'steps': [
                    'Load ACLED conflict data',
                    'Filter by date range of interest',
                    'Create heat map visualization',
                    'Analyze by state using zonal statistics',
                    'Identify hotspots and trends',
                    'Generate conflict report'
                ],
                'keywords': ['conflict', 'violence', 'security', 'acled']
            },
            'population_mapping': {
                'name': 'Population Distribution Mapping',
                'steps': [
                    'Load Admin 1 and Admin 2 boundaries',
                    'Add population data from World Bank',
                    'Create choropleth map by population',
                    'Calculate population density',
                    'Add settlement points for context',
                    'Export publication-ready map'
                ],
                'keywords': ['population', 'demographics', 'census', 'density']
            },
            'service_coverage': {
                'name': 'Service Coverage Analysis',
                'steps': [
                    'Load health/education facility points',
                    'Create buffer zones (e.g., 5km, 10km)',
                    'Load settlement/population data',
                    'Calculate population within service areas',
                    'Identify underserved areas',
                    'Recommend new facility locations'
                ],
                'keywords': ['health', 'education', 'facilities', 'coverage', 'access']
            },
            'environmental_monitoring': {
                'name': 'Environmental Monitoring',
                'steps': [
                    'Load satellite imagery (Sentinel)',
                    'Check NASA FIRMS for active fires',
                    'Calculate vegetation indices (NDVI)',
                    'Compare with historical data',
                    'Identify areas of change',
                    'Generate environmental report'
                ],
                'keywords': ['environment', 'fire', 'vegetation', 'satellite', 'ndvi']
            }
        }

        # Match workflows to user goal
        if user_goal:
            goal_lower = user_goal.lower()
            matched = []
            for key, workflow in workflows.items():
                score = sum(1 for kw in workflow['keywords'] if kw in goal_lower)
                if score > 0:
                    matched.append((score, workflow))

            if matched:
                matched.sort(key=lambda x: x[0], reverse=True)
                return [m[1] for m in matched]

        # Return all workflows if no specific goal
        return list(workflows.values())

    def suggest_next_action(self, current_state):
        """
        Suggest the next action based on current plugin state.

        :param current_state: Dictionary describing current state
        :returns: Suggested action dictionary
        """
        layers_loaded = current_state.get('layers_loaded', 0)
        has_sudan_data = current_state.get('has_sudan_data', False)
        last_action = current_state.get('last_action')

        if not has_sudan_data:
            return {
                'action': 'load_data',
                'message': 'Start by loading Sudan administrative boundaries',
                'priority': 'high'
            }

        if layers_loaded == 1:
            return {
                'action': 'add_more_data',
                'message': 'Add more layers to enable spatial analysis',
                'priority': 'medium'
            }

        if last_action == 'load_conflict':
            return {
                'action': 'create_heatmap',
                'message': 'Create a heat map to visualize conflict density',
                'priority': 'medium'
            }

        if last_action == 'filter':
            return {
                'action': 'export_or_analyze',
                'message': 'Export filtered results or perform analysis',
                'priority': 'low'
            }

        return {
            'action': 'explore',
            'message': 'Try the Analysis Tools menu for more options',
            'priority': 'low'
        }

    def get_learning_resources(self, topic=None):
        """
        Get relevant learning resources.

        :param topic: Optional topic to filter resources
        :returns: List of resource dictionaries
        """
        resources = [
            {
                'title': 'Sudan Administrative Divisions',
                'description': 'Understanding Sudan\'s 18 states and localities',
                'type': 'documentation',
                'topic': 'admin_boundaries'
            },
            {
                'title': 'Working with Conflict Data',
                'description': 'Best practices for analyzing ACLED data',
                'type': 'tutorial',
                'topic': 'conflict'
            },
            {
                'title': 'Creating Thematic Maps',
                'description': 'How to style and label Sudan maps effectively',
                'type': 'tutorial',
                'topic': 'styling'
            },
            {
                'title': 'Spatial Analysis in QGIS',
                'description': 'Using Processing tools for Sudan data',
                'type': 'tutorial',
                'topic': 'analysis'
            },
            {
                'title': 'Humanitarian Data Standards',
                'description': 'OCHA COD and HDX data standards',
                'type': 'documentation',
                'topic': 'humanitarian'
            },
            {
                'title': 'Satellite Imagery Analysis',
                'description': 'Using Sentinel data for Sudan monitoring',
                'type': 'tutorial',
                'topic': 'satellite'
            }
        ]

        if topic:
            topic_lower = topic.lower()
            return [r for r in resources if topic_lower in r.get('topic', '').lower()]

        return resources

    def _normalize_dataset_name(self, name):
        """Normalize dataset name for matching."""
        name_lower = name.lower()

        # Map common variations to standard names
        mappings = {
            'admin 1': 'admin1',
            'admin 2': 'admin2',
            'states': 'admin1',
            'localities': 'admin2',
            'health': 'health_facilities',
            'schools': 'education',
            'acled': 'conflict',
            'idp': 'displacement',
            'firms': 'fire',
            'sentinel': 'satellite'
        }

        for pattern, standard in mappings.items():
            if pattern in name_lower:
                return standard

        # Generic categorization
        if 'admin' in name_lower or 'boundar' in name_lower:
            return 'admin_boundaries'
        if 'road' in name_lower:
            return 'roads'
        if 'water' in name_lower:
            return 'water_bodies'
        if 'settlement' in name_lower or 'populated' in name_lower:
            return 'settlements'

        return name_lower.replace(' ', '_')

    def _format_dataset_name(self, name):
        """Format dataset name for display."""
        return name.replace('_', ' ').title()

    def _get_dataset_priority(self, dataset, loaded):
        """Calculate priority for dataset recommendation."""
        # Base priorities
        priorities = {
            'admin_boundaries': 0.9,
            'admin1': 0.85,
            'admin2': 0.85,
            'conflict': 0.8,
            'health_facilities': 0.75,
            'population': 0.75,
            'roads': 0.7,
            'settlements': 0.7
        }

        priority = priorities.get(dataset, 0.5)

        # Boost if strongly associated
        for l in loaded:
            l_norm = self._normalize_dataset_name(l)
            if l_norm in self.DATASET_ASSOCIATIONS:
                if dataset in self.DATASET_ASSOCIATIONS[l_norm][:2]:
                    priority += 0.1

        return min(1.0, priority)

    def _detect_layer_type(self, layer_name):
        """Detect layer type from name."""
        if isinstance(layer_name, QgsVectorLayer):
            layer_name = layer_name.name()

        return self._normalize_dataset_name(layer_name)
