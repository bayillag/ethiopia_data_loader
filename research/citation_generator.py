# -*- coding: utf-8 -*-
"""
Citation Generator for Ethiopia Data Loader.

Generates academic citations for data sources in various formats.
"""

from datetime import datetime


class CitationGenerator:
    """Generates citations for data sources."""

    # Known data source metadata
    DATA_SOURCES = {
        'hdx_admin': {
            'title': 'Ethiopia - Subnational Administrative Boundaries',
            'author': 'OCHA ROWCA',
            'publisher': 'Humanitarian Data Exchange',
            'url': 'https://data.humdata.org/dataset/cod-ab-sdn',
            'type': 'dataset'
        },
        'hdx_health': {
            'title': 'Sudan Health Facilities',
            'author': 'World Health Organization',
            'publisher': 'Humanitarian Data Exchange',
            'url': 'https://data.humdata.org/',
            'type': 'dataset'
        },
        'worldbank': {
            'title': 'World Development Indicators',
            'author': 'World Bank',
            'publisher': 'World Bank Open Data',
            'url': 'https://data.worldbank.org/',
            'type': 'database'
        },
        'osm': {
            'title': 'OpenStreetMap',
            'author': 'OpenStreetMap Contributors',
            'publisher': 'OpenStreetMap Foundation',
            'url': 'https://www.openstreetmap.org/',
            'license': 'ODbL',
            'type': 'database'
        },
        'sentinel': {
            'title': 'Copernicus Sentinel Data',
            'author': 'European Space Agency',
            'publisher': 'Copernicus Open Access Hub',
            'url': 'https://scihub.copernicus.eu/',
            'type': 'imagery'
        },
        'firms': {
            'title': 'Fire Information for Resource Management System (FIRMS)',
            'author': 'NASA',
            'publisher': 'NASA Earthdata',
            'url': 'https://firms.modaps.eosdis.nasa.gov/',
            'type': 'dataset'
        }
    }

    def __init__(self):
        """Initialize the citation generator."""
        self.accessed_date = datetime.now()

    def generate_citation(self, source_id, format='apa'):
        """
        Generate a citation for a data source.

        :param source_id: ID of the data source
        :param format: Citation format (apa, bibtex, chicago, harvard, mla)
        :returns: Citation string
        """
        source = self.DATA_SOURCES.get(source_id)
        if not source:
            return self._generate_generic_citation(source_id, format)

        formatters = {
            'apa': self._format_apa,
            'bibtex': self._format_bibtex,
            'chicago': self._format_chicago,
            'harvard': self._format_harvard,
            'mla': self._format_mla
        }

        formatter = formatters.get(format.lower(), self._format_apa)
        return formatter(source, source_id)

    def generate_bibliography(self, source_ids, format='apa'):
        """
        Generate a bibliography for multiple sources.

        :param source_ids: List of source IDs
        :param format: Citation format
        :returns: Formatted bibliography string
        """
        citations = []
        for source_id in source_ids:
            citations.append(self.generate_citation(source_id, format))

        # Sort alphabetically
        citations.sort()

        if format == 'bibtex':
            return '\n\n'.join(citations)
        else:
            return '\n\n'.join(citations)

    def get_available_sources(self):
        """Get list of available data sources for citation."""
        return [
            {'id': k, 'title': v['title'], 'publisher': v['publisher']}
            for k, v in self.DATA_SOURCES.items()
        ]

    def add_custom_source(self, source_id, metadata):
        """
        Add a custom data source for citation.

        :param source_id: Unique identifier
        :param metadata: Dictionary with title, author, publisher, url, etc.
        """
        required_fields = ['title', 'author', 'publisher']
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required field: {field}")

        self.DATA_SOURCES[source_id] = metadata

    def _format_apa(self, source, source_id):
        """Format citation in APA 7th edition style."""
        year = datetime.now().year
        accessed = self.accessed_date.strftime('%B %d, %Y')

        author = source.get('author', 'Unknown')
        title = source.get('title', 'Untitled')
        publisher = source.get('publisher', '')
        url = source.get('url', '')
        doi = source.get('doi')

        citation = f"{author}. ({year}). {title}. {publisher}."

        if doi:
            citation += f" https://doi.org/{doi}"
        elif url:
            citation += f" Retrieved {accessed}, from {url}"

        return citation

    def _format_bibtex(self, source, source_id):
        """Format citation in BibTeX format."""
        year = datetime.now().year
        accessed = self.accessed_date.strftime('%Y-%m-%d')

        entry_type = 'misc' if source.get('type') == 'dataset' else 'online'

        bibtex = f"@{entry_type}{{{source_id},\n"
        bibtex += f"  author = {{{source.get('author', 'Unknown')}}},\n"
        bibtex += f"  title = {{{{{source.get('title', 'Untitled')}}}}},\n"
        bibtex += f"  publisher = {{{source.get('publisher', '')}}},\n"
        bibtex += f"  year = {{{year}}},\n"

        if source.get('doi'):
            bibtex += f"  doi = {{{source['doi']}}},\n"

        if source.get('url'):
            bibtex += f"  url = {{{source['url']}}},\n"
            bibtex += f"  urldate = {{{accessed}}},\n"

        bibtex = bibtex.rstrip(',\n') + "\n}"
        return bibtex

    def _format_chicago(self, source, source_id):
        """Format citation in Chicago style."""
        year = datetime.now().year
        accessed = self.accessed_date.strftime('%B %d, %Y')

        author = source.get('author', 'Unknown')
        title = source.get('title', 'Untitled')
        publisher = source.get('publisher', '')
        url = source.get('url', '')

        citation = f"{author}. \"{title}.\" {publisher}, {year}."

        if url:
            citation += f" Accessed {accessed}. {url}."

        return citation

    def _format_harvard(self, source, source_id):
        """Format citation in Harvard style."""
        year = datetime.now().year
        accessed = self.accessed_date.strftime('%d %B %Y')

        author = source.get('author', 'Unknown')
        title = source.get('title', 'Untitled')
        url = source.get('url', '')

        citation = f"{author} ({year}) {title}."

        if url:
            citation += f" Available at: {url} (Accessed: {accessed})."

        return citation

    def _format_mla(self, source, source_id):
        """Format citation in MLA 9th edition style."""
        accessed = self.accessed_date.strftime('%d %b. %Y')

        author = source.get('author', 'Unknown')
        title = source.get('title', 'Untitled')
        publisher = source.get('publisher', '')
        url = source.get('url', '')

        citation = f"{author}. \"{title}.\" {publisher},"

        if url:
            citation += f" {url}. Accessed {accessed}."

        return citation

    def _generate_generic_citation(self, source_id, format):
        """Generate a generic citation for unknown sources."""
        generic = {
            'title': source_id.replace('_', ' ').title(),
            'author': 'Unknown',
            'publisher': 'Unknown Publisher',
            'url': '',
            'type': 'dataset'
        }

        formatters = {
            'apa': self._format_apa,
            'bibtex': self._format_bibtex,
            'chicago': self._format_chicago,
            'harvard': self._format_harvard,
            'mla': self._format_mla
        }

        formatter = formatters.get(format.lower(), self._format_apa)
        return formatter(generic, source_id)

    def export_bibliography(self, source_ids, format='apa', output_path=None):
        """
        Export bibliography to file.

        :param source_ids: List of source IDs
        :param format: Citation format
        :param output_path: Optional file path (returns string if None)
        :returns: Bibliography string or success message
        """
        bibliography = self.generate_bibliography(source_ids, format)

        if output_path:
            extension = '.bib' if format == 'bibtex' else '.txt'
            if not output_path.endswith(extension):
                output_path += extension

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(bibliography)

            return f"Bibliography exported to {output_path}"

        return bibliography

    def get_data_license(self, source_id):
        """
        Get license information for a data source.

        :param source_id: Data source ID
        :returns: License dictionary or None
        """
        licenses = {
            'hdx_admin': {
                'name': 'Creative Commons Attribution for Intergovernmental Organisations',
                'short': 'CC BY-IGO',
                'url': 'https://creativecommons.org/licenses/by/3.0/igo/'
            },
            'osm': {
                'name': 'Open Database License',
                'short': 'ODbL',
                'url': 'https://opendatacommons.org/licenses/odbl/'
            },
            'acled': {
                'name': 'ACLED Terms of Use',
                'short': 'ACLED ToU',
                'url': 'https://acleddata.com/terms-of-use/'
            },
            'sentinel': {
                'name': 'Copernicus Sentinel Data Terms',
                'short': 'Copernicus',
                'url': 'https://scihub.copernicus.eu/twiki/do/view/SciHubWebPortal/TermsConditions'
            },
            'worldbank': {
                'name': 'Creative Commons Attribution 4.0 International',
                'short': 'CC BY 4.0',
                'url': 'https://creativecommons.org/licenses/by/4.0/'
            }
        }

        return licenses.get(source_id)

    def generate_acknowledgement(self, source_ids):
        """
        Generate an acknowledgement section for multiple sources.

        :param source_ids: List of source IDs used
        :returns: Acknowledgement text
        """
        acknowledgements = []

        for source_id in source_ids:
            source = self.DATA_SOURCES.get(source_id)
            if source:
                ack = f"{source['title']} data provided by {source['author']}"
                license_info = self.get_data_license(source_id)
                if license_info:
                    ack += f" under {license_info['short']} license"
                acknowledgements.append(ack)

        if not acknowledgements:
            return "Data sources: See references."

        text = "This work uses data from the following sources: "
        text += "; ".join(acknowledgements) + "."

        return text
