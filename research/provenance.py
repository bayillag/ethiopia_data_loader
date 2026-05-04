# -*- coding: utf-8 -*-
"""
Data Provenance Tracking for Ethiopia Data Loader.

Tracks data lineage and transformations for reproducibility.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from qgis.core import QgsProject, QgsVectorLayer


class ProvenanceTracker:
    """Tracks data provenance and lineage."""

    def __init__(self):
        """Initialize the provenance tracker."""
        self.records = []
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_start = datetime.now()

    def record_data_load(self, layer_name, source, metadata=None):
        """
        Record a data load event.

        :param layer_name: Name of the loaded layer
        :param source: Data source (file path, URL, API)
        :param metadata: Optional metadata dictionary
        """
        record = {
            'event_type': 'data_load',
            'timestamp': datetime.now().isoformat(),
            'layer_name': layer_name,
            'source': source,
            'metadata': metadata or {}
        }

        # Calculate checksum if it's a file
        if isinstance(source, str) and Path(source).exists():
            record['checksum'] = self._calculate_checksum(source)

        self.records.append(record)
        return record

    def record_transformation(self, input_layers, output_layer, operation, parameters=None):
        """
        Record a data transformation.

        :param input_layers: List of input layer names
        :param output_layer: Output layer name
        :param operation: Name of the operation
        :param parameters: Operation parameters
        """
        record = {
            'event_type': 'transformation',
            'timestamp': datetime.now().isoformat(),
            'input_layers': input_layers if isinstance(input_layers, list) else [input_layers],
            'output_layer': output_layer,
            'operation': operation,
            'parameters': parameters or {}
        }

        self.records.append(record)
        return record

    def record_filter(self, layer_name, expression, result_count):
        """
        Record a filter/query operation.

        :param layer_name: Name of the filtered layer
        :param expression: Filter expression
        :param result_count: Number of features after filter
        """
        record = {
            'event_type': 'filter',
            'timestamp': datetime.now().isoformat(),
            'layer_name': layer_name,
            'expression': expression,
            'result_count': result_count
        }

        self.records.append(record)
        return record

    def record_export(self, layer_name, output_path, format, feature_count):
        """
        Record a data export.

        :param layer_name: Name of exported layer
        :param output_path: Export file path
        :param format: Export format
        :param feature_count: Number of features exported
        """
        record = {
            'event_type': 'export',
            'timestamp': datetime.now().isoformat(),
            'layer_name': layer_name,
            'output_path': output_path,
            'format': format,
            'feature_count': feature_count
        }

        if output_path and Path(output_path).exists():
            record['checksum'] = self._calculate_checksum(output_path)

        self.records.append(record)
        return record

    def record_api_call(self, api_name, endpoint, parameters, result_count):
        """
        Record an API data fetch.

        :param api_name: Name of the API (HDX, ACLED, etc.)
        :param endpoint: API endpoint used
        :param parameters: Request parameters
        :param result_count: Number of records returned
        """
        record = {
            'event_type': 'api_call',
            'timestamp': datetime.now().isoformat(),
            'api_name': api_name,
            'endpoint': endpoint,
            'parameters': self._sanitize_parameters(parameters),
            'result_count': result_count
        }

        self.records.append(record)
        return record

    def get_layer_lineage(self, layer_name):
        """
        Get the complete lineage of a layer.

        :param layer_name: Name of the layer
        :returns: List of related provenance records
        """
        lineage = []

        # Find all records related to this layer
        for record in self.records:
            if record.get('layer_name') == layer_name:
                lineage.append(record)
            elif record.get('output_layer') == layer_name:
                lineage.append(record)
                # Also include input layer lineage
                for input_layer in record.get('input_layers', []):
                    lineage.extend(self.get_layer_lineage(input_layer))

        return lineage

    def generate_methodology_report(self):
        """
        Generate a methodology report from provenance records.

        :returns: Methodology report dictionary
        """
        # Group by event type
        data_sources = []
        transformations = []
        filters = []
        exports = []

        for record in self.records:
            event_type = record.get('event_type')
            if event_type == 'data_load':
                data_sources.append(record)
            elif event_type == 'api_call':
                data_sources.append(record)
            elif event_type == 'transformation':
                transformations.append(record)
            elif event_type == 'filter':
                filters.append(record)
            elif event_type == 'export':
                exports.append(record)

        report = {
            'session_id': self.session_id,
            'session_start': self.session_start.isoformat(),
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'data_sources_count': len(data_sources),
                'transformations_count': len(transformations),
                'filters_count': len(filters),
                'exports_count': len(exports)
            },
            'data_sources': data_sources,
            'processing_steps': transformations + filters,
            'outputs': exports,
            'methodology_text': self._generate_methodology_text(
                data_sources, transformations, filters, exports
            )
        }

        return report

    def export_provenance(self, output_path, format='json'):
        """
        Export provenance records to file.

        :param output_path: Output file path
        :param format: Export format (json, txt)
        :returns: Success message
        """
        if format == 'json':
            data = {
                'session_id': self.session_id,
                'session_start': self.session_start.isoformat(),
                'exported_at': datetime.now().isoformat(),
                'records': self.records
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format == 'txt':
            report = self.generate_methodology_report()

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Data Provenance Report\n")
                f.write(f"{'=' * 50}\n\n")
                f.write(f"Session ID: {self.session_id}\n")
                f.write(f"Session Start: {self.session_start}\n")
                f.write(f"Report Generated: {datetime.now()}\n\n")
                f.write(report['methodology_text'])

        return f"Provenance exported to {output_path}"

    def clear_records(self):
        """Clear all provenance records."""
        self.records = []
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_start = datetime.now()

    def get_reproducibility_script(self):
        """
        Generate a Python script to reproduce the workflow.

        :returns: Python script string
        """
        script = '''# -*- coding: utf-8 -*-
"""
Auto-generated reproducibility script
Session: {session_id}
Generated: {generated_at}
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsFeatureRequest

# Data Loading
'''.format(
            session_id=self.session_id,
            generated_at=datetime.now().isoformat()
        )

        for record in self.records:
            if record['event_type'] == 'data_load':
                script += f'''
# Load: {record['layer_name']}
# Source: {record['source']}
layer_{record['layer_name'].replace(' ', '_').lower()} = QgsVectorLayer(
    "{record['source']}",
    "{record['layer_name']}",
    "ogr"
)
QgsProject.instance().addMapLayer(layer_{record['layer_name'].replace(' ', '_').lower()})
'''

            elif record['event_type'] == 'filter':
                script += f'''
# Filter: {record['layer_name']}
# Expression: {record['expression']}
layer.setSubsetString("{record['expression']}")
'''

            elif record['event_type'] == 'transformation':
                script += f'''
# Transformation: {record['operation']}
# Input: {record['input_layers']}
# Output: {record['output_layer']}
# Parameters: {record['parameters']}
# Note: Run corresponding Processing algorithm
'''

        return script

    def _calculate_checksum(self, file_path):
        """Calculate MD5 checksum of a file."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None

    def _sanitize_parameters(self, parameters):
        """Remove sensitive information from parameters."""
        if not parameters:
            return {}

        sanitized = dict(parameters)
        sensitive_keys = ['key', 'password', 'token', 'secret', 'api_key', 'auth']

        for key in list(sanitized.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = '***REDACTED***'

        return sanitized

    def _generate_methodology_text(self, sources, transformations, filters, exports):
        """Generate human-readable methodology text."""
        text = "METHODOLOGY\n\n"

        # Data Sources section
        text += "1. DATA SOURCES\n"
        text += "-" * 30 + "\n"

        for i, source in enumerate(sources, 1):
            if source['event_type'] == 'data_load':
                text += f"{i}. {source['layer_name']}\n"
                text += f"   Source: {source['source']}\n"
                if source.get('checksum'):
                    text += f"   Checksum (MD5): {source['checksum']}\n"
            elif source['event_type'] == 'api_call':
                text += f"{i}. {source['api_name']} API\n"
                text += f"   Endpoint: {source['endpoint']}\n"
                text += f"   Records retrieved: {source['result_count']}\n"
            text += f"   Timestamp: {source['timestamp']}\n\n"

        # Processing section
        if transformations or filters:
            text += "\n2. DATA PROCESSING\n"
            text += "-" * 30 + "\n"

            for i, step in enumerate(transformations + filters, 1):
                if step['event_type'] == 'transformation':
                    text += f"{i}. {step['operation']}\n"
                    text += f"   Input: {', '.join(step['input_layers'])}\n"
                    text += f"   Output: {step['output_layer']}\n"
                    if step.get('parameters'):
                        text += f"   Parameters: {step['parameters']}\n"
                elif step['event_type'] == 'filter':
                    text += f"{i}. Filter applied to {step['layer_name']}\n"
                    text += f"   Expression: {step['expression']}\n"
                    text += f"   Result count: {step['result_count']}\n"
                text += f"   Timestamp: {step['timestamp']}\n\n"

        # Outputs section
        if exports:
            text += "\n3. OUTPUTS\n"
            text += "-" * 30 + "\n"

            for i, export in enumerate(exports, 1):
                text += f"{i}. {export['layer_name']}\n"
                text += f"   Format: {export['format']}\n"
                text += f"   Path: {export['output_path']}\n"
                text += f"   Features: {export['feature_count']}\n"
                if export.get('checksum'):
                    text += f"   Checksum (MD5): {export['checksum']}\n"
                text += f"   Timestamp: {export['timestamp']}\n\n"

        return text
