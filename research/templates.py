# -*- coding: utf-8 -*-
"""
Project Templates for Ethiopia Data Loader.

Pre-configured analysis workflows and project templates.
"""

from datetime import datetime


class ProjectTemplates:
    """Manages analysis workflow templates."""

    # Available templates
    TEMPLATES = {
        'humanitarian_assessment': {
            'name': 'Humanitarian Needs Assessment',
            'description': 'Comprehensive assessment of humanitarian needs in Ethiopia',
            'category': 'humanitarian',
            'required_data': [
                'admin_boundaries',
                'health_facilities',
                'education_facilities'
            ],
            'optional_data': [
                'population',
                'roads',
                'settlements'
            ],
            'workflow': [
                {
                    'step': 1,
                    'name': 'Load Administrative Boundaries',
                    'description': 'Load Admin 1 (states) and Admin 2 (localities) boundaries',
                    'action': 'load_admin_boundaries',
                    'parameters': {'levels': [1, 2]}
                },
                {
                    'step': 2,
                    'name': 'Load Service Infrastructure',
                    'description': 'Load health facilities and educational institutions',
                    'action': 'load_hdx_datasets',
                    'parameters': {'types': ['health', 'education']}
                },
                {
                    'step': 3,
                    'name': 'Calculate Service Coverage',
                    'description': 'Buffer health facilities to analyze coverage',
                    'action': 'run_buffer_analysis',
                    'parameters': {'distance_km': 10}
                },
                {
                    'step': 4,
                    'name': 'Generate Statistics',
                    'description': 'Calculate statistics per locality',
                    'action': 'run_zonal_statistics',
                    'parameters': {}
                },
                {
                    'step': 5,
                    'name': 'Create Thematic Maps',
                    'description': 'Apply humanitarian color schemes',
                    'action': 'apply_humanitarian_style',
                    'parameters': {}
                },
                {
                    'step': 6,
                    'name': 'Generate Report',
                    'description': 'Create humanitarian assessment report',
                    'action': 'generate_report',
                    'parameters': {'template': 'humanitarian'}
                }
            ],
            'outputs': [
                'Thematic maps by locality',
                'Service coverage analysis',
                'Conflict hotspot map',
                'Humanitarian needs report'
            ]
        },

        'population_mapping': {
            'name': 'Population Distribution Mapping',
            'description': 'Map and analyze population distribution across Sudan',
            'category': 'demographics',
            'required_data': [
                'admin_boundaries',
                'population_data'
            ],
            'optional_data': [
                'settlements',
                'roads'
            ],
            'workflow': [
                {
                    'step': 1,
                    'name': 'Load Administrative Boundaries',
                    'description': 'Load Admin 1 and Admin 2 boundaries',
                    'action': 'load_admin_boundaries',
                    'parameters': {'levels': [1, 2]}
                },
                {
                    'step': 2,
                    'name': 'Load Population Data',
                    'description': 'Load World Bank population indicators',
                    'action': 'load_worldbank_data',
                    'parameters': {'indicators': ['SP.POP.TOTL']}
                },
                {
                    'step': 3,
                    'name': 'Join Population to Boundaries',
                    'description': 'Join population data to admin units',
                    'action': 'join_attributes',
                    'parameters': {}
                },
                {
                    'step': 4,
                    'name': 'Calculate Density',
                    'description': 'Calculate population density per km²',
                    'action': 'calculate_density',
                    'parameters': {}
                },
                {
                    'step': 5,
                    'name': 'Create Choropleth Map',
                    'description': 'Style boundaries by population',
                    'action': 'create_choropleth',
                    'parameters': {'field': 'population'}
                },
                {
                    'step': 6,
                    'name': 'Generate Charts',
                    'description': 'Create population distribution charts',
                    'action': 'create_charts',
                    'parameters': {'types': ['bar', 'pie']}
                }
            ],
            'outputs': [
                'Population choropleth map',
                'Population density map',
                'Distribution charts',
                'Statistical summary'
            ]
        },

        'service_coverage': {
            'name': 'Service Coverage Analysis',
            'description': 'Analyze health and education service coverage',
            'category': 'development',
            'required_data': [
                'admin_boundaries',
                'health_facilities',
                'education_facilities'
            ],
            'optional_data': [
                'population',
                'roads',
                'settlements'
            ],
            'workflow': [
                {
                    'step': 1,
                    'name': 'Load Base Data',
                    'description': 'Load boundaries and facility locations',
                    'action': 'load_service_data',
                    'parameters': {}
                },
                {
                    'step': 2,
                    'name': 'Create Service Buffers',
                    'description': 'Buffer facilities at 5km, 10km, 15km',
                    'action': 'create_service_buffers',
                    'parameters': {'distances': [5, 10, 15]}
                },
                {
                    'step': 3,
                    'name': 'Calculate Coverage',
                    'description': 'Identify areas within/outside coverage',
                    'action': 'calculate_coverage',
                    'parameters': {}
                },
                {
                    'step': 4,
                    'name': 'Identify Gaps',
                    'description': 'Find underserved areas',
                    'action': 'identify_service_gaps',
                    'parameters': {}
                },
                {
                    'step': 5,
                    'name': 'Suggest Locations',
                    'description': 'Recommend new facility locations',
                    'action': 'suggest_locations',
                    'parameters': {}
                },
                {
                    'step': 6,
                    'name': 'Generate Report',
                    'description': 'Create coverage analysis report',
                    'action': 'generate_report',
                    'parameters': {'template': 'coverage'}
                }
            ],
            'outputs': [
                'Service coverage maps',
                'Gap analysis map',
                'Recommended locations',
                'Coverage statistics',
                'Analysis report'
            ]
        },

        'environmental_monitoring': {
            'name': 'Environmental Monitoring',
            'description': 'Monitor environmental changes using satellite data',
            'category': 'environment',
            'required_data': [
                'admin_boundaries',
                'satellite_imagery'
            ],
            'optional_data': [
                'fire_data',
                'water_bodies'
            ],
            'workflow': [
                {
                    'step': 1,
                    'name': 'Load Boundaries',
                    'description': 'Load area of interest boundaries',
                    'action': 'load_admin_boundaries',
                    'parameters': {'levels': [1]}
                },
                {
                    'step': 2,
                    'name': 'Load Satellite Data',
                    'description': 'Download Sentinel-2 imagery',
                    'action': 'load_sentinel_data',
                    'parameters': {'cloud_cover': 20}
                },
                {
                    'step': 3,
                    'name': 'Check Fire Data',
                    'description': 'Load NASA FIRMS active fire data',
                    'action': 'load_firms_data',
                    'parameters': {'days': 7}
                },
                {
                    'step': 4,
                    'name': 'Calculate NDVI',
                    'description': 'Calculate vegetation index',
                    'action': 'calculate_ndvi',
                    'parameters': {}
                },
                {
                    'step': 5,
                    'name': 'Compare Dates',
                    'description': 'Detect changes between dates',
                    'action': 'change_detection',
                    'parameters': {}
                },
                {
                    'step': 6,
                    'name': 'Generate Report',
                    'description': 'Create environmental monitoring report',
                    'action': 'generate_report',
                    'parameters': {'template': 'environment'}
                }
            ],
            'outputs': [
                'Satellite imagery mosaics',
                'NDVI maps',
                'Fire detection map',
                'Change detection results',
                'Monitoring report'
            ]
        },
    }

    def __init__(self):
        """Initialize project templates manager."""
        self.custom_templates = {}

    def get_available_templates(self):
        """
        Get list of all available templates.

        :returns: List of template summaries
        """
        templates = []

        for template_id, template in self.TEMPLATES.items():
            templates.append({
                'id': template_id,
                'name': template['name'],
                'description': template['description'],
                'category': template['category'],
                'steps': len(template['workflow'])
            })

        for template_id, template in self.custom_templates.items():
            templates.append({
                'id': template_id,
                'name': template['name'],
                'description': template.get('description', ''),
                'category': template.get('category', 'custom'),
                'steps': len(template.get('workflow', []))
            })

        return templates

    def get_template(self, template_id):
        """
        Get a specific template by ID.

        :param template_id: Template identifier
        :returns: Template dictionary or None
        """
        if template_id in self.TEMPLATES:
            return self.TEMPLATES[template_id]
        elif template_id in self.custom_templates:
            return self.custom_templates[template_id]
        return None

    def get_templates_by_category(self, category):
        """
        Get templates filtered by category.

        :param category: Category name (humanitarian, security, etc.)
        :returns: List of matching templates
        """
        matching = []

        for template_id, template in self.TEMPLATES.items():
            if template.get('category') == category:
                matching.append({
                    'id': template_id,
                    **template
                })

        for template_id, template in self.custom_templates.items():
            if template.get('category') == category:
                matching.append({
                    'id': template_id,
                    **template
                })

        return matching

    def get_workflow_steps(self, template_id):
        """
        Get workflow steps for a template.

        :param template_id: Template identifier
        :returns: List of workflow steps
        """
        template = self.get_template(template_id)
        if template:
            return template.get('workflow', [])
        return []

    def get_required_data(self, template_id):
        """
        Get required data for a template.

        :param template_id: Template identifier
        :returns: List of required data types
        """
        template = self.get_template(template_id)
        if template:
            return template.get('required_data', [])
        return []

    def create_custom_template(self, template_id, name, description, workflow,
                                category='custom', required_data=None,
                                optional_data=None, outputs=None):
        """
        Create a custom template.

        :param template_id: Unique template identifier
        :param name: Template name
        :param description: Template description
        :param workflow: List of workflow step dictionaries
        :param category: Template category
        :param required_data: List of required data types
        :param optional_data: List of optional data types
        :param outputs: List of expected outputs
        """
        self.custom_templates[template_id] = {
            'name': name,
            'description': description,
            'category': category,
            'required_data': required_data or [],
            'optional_data': optional_data or [],
            'workflow': workflow,
            'outputs': outputs or [],
            'created_at': datetime.now().isoformat()
        }

    def export_template(self, template_id, output_path):
        """
        Export a template to JSON file.

        :param template_id: Template to export
        :param output_path: Output file path
        :returns: Success message
        """
        import json

        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        export_data = {
            'id': template_id,
            'exported_at': datetime.now().isoformat(),
            **template
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return f"Template exported to {output_path}"

    def import_template(self, input_path):
        """
        Import a template from JSON file.

        :param input_path: Input file path
        :returns: Imported template ID
        """
        import json

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        template_id = data.pop('id', None) or f"imported_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data.pop('exported_at', None)

        self.custom_templates[template_id] = data

        return template_id

    def generate_workflow_checklist(self, template_id):
        """
        Generate a printable workflow checklist.

        :param template_id: Template identifier
        :returns: Checklist string
        """
        template = self.get_template(template_id)
        if not template:
            return "Template not found"

        checklist = f"WORKFLOW CHECKLIST: {template['name']}\n"
        checklist += "=" * 50 + "\n\n"
        checklist += f"Description: {template['description']}\n\n"

        checklist += "REQUIRED DATA:\n"
        for data in template.get('required_data', []):
            checklist += f"  [ ] {data.replace('_', ' ').title()}\n"

        checklist += "\nOPTIONAL DATA:\n"
        for data in template.get('optional_data', []):
            checklist += f"  [ ] {data.replace('_', ' ').title()}\n"

        checklist += "\nWORKFLOW STEPS:\n"
        for step in template.get('workflow', []):
            checklist += f"  [ ] Step {step['step']}: {step['name']}\n"
            checklist += f"      {step['description']}\n"

        checklist += "\nEXPECTED OUTPUTS:\n"
        for output in template.get('outputs', []):
            checklist += f"  [ ] {output}\n"

        checklist += f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"

        return checklist
