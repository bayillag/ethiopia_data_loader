# -*- coding: utf-8 -*-
"""
World Bank Client for Ethiopia Data Loader.

Provides access to World Bank Development Indicators API for Ethiopia.
"""

import json
import os
import tempfile
from datetime import datetime

from qgis.PyQt.QtCore import QUrl, QObject, pyqtSignal
from qgis.core import QgsBlockingNetworkRequest, QgsMessageLog, Qgis
from qgis.PyQt.QtNetwork import QNetworkRequest


class WorldBankClient(QObject):
    """Client for accessing World Bank Development Indicators API."""

    # World Bank API endpoint
    API_URL = "https://api.worldbank.org/v2"

    # Ethiopia country code
    ETHIOPIA_CODE = "ETH"

    # Indicator categories with relevant indicators
    INDICATOR_CATEGORIES = {
        'Population': {
            'SP.POP.TOTL': 'Population, total',
            'SP.POP.GROW': 'Population growth (annual %)',
            'SP.URB.TOTL': 'Urban population',
            'SP.URB.TOTL.IN.ZS': 'Urban population (% of total)',
            'SP.RUR.TOTL': 'Rural population',
            'SP.POP.DPND': 'Age dependency ratio',
            'SP.DYN.LE00.IN': 'Life expectancy at birth'
        },
        'Economy': {
            'NY.GDP.MKTP.CD': 'GDP (current US$)',
            'NY.GDP.MKTP.KD.ZG': 'GDP growth (annual %)',
            'NY.GDP.PCAP.CD': 'GDP per capita (current US$)',
            'NY.GNP.PCAP.CD': 'GNI per capita (current US$)',
            'FP.CPI.TOTL.ZG': 'Inflation, consumer prices (annual %)',
            'SL.UEM.TOTL.ZS': 'Unemployment (% of labor force)',
            'NE.EXP.GNFS.ZS': 'Exports of goods and services (% of GDP)',
            'NE.IMP.GNFS.ZS': 'Imports of goods and services (% of GDP)'
        },
        'Health': {
            'SH.DYN.MORT': 'Mortality rate, under-5 (per 1,000)',
            'SH.DYN.NMRT': 'Mortality rate, neonatal (per 1,000)',
            'SP.DYN.IMRT.IN': 'Mortality rate, infant (per 1,000)',
            'SH.STA.MMRT': 'Maternal mortality ratio (per 100,000)',
            'SH.MED.BEDS.ZS': 'Hospital beds (per 1,000 people)',
            'SH.MED.PHYS.ZS': 'Physicians (per 1,000 people)',
            'SH.XPD.CHEX.PC.CD': 'Health expenditure per capita (US$)',
            'SH.IMM.MEAS': 'Immunization, measles (% of children)',
            'SH.H2O.SMDW.ZS': 'Access to safe drinking water (%)',
            'SH.STA.SMSS.ZS': 'Access to sanitation (%)'
        },
        'Education': {
            'SE.ADT.LITR.ZS': 'Literacy rate, adult (%)',
            'SE.PRM.ENRR': 'School enrollment, primary (% gross)',
            'SE.SEC.ENRR': 'School enrollment, secondary (% gross)',
            'SE.TER.ENRR': 'School enrollment, tertiary (% gross)',
            'SE.PRM.CMPT.ZS': 'Primary completion rate (%)',
            'SE.XPD.TOTL.GD.ZS': 'Government expenditure on education (% of GDP)',
            'SE.PRM.TCHR': 'Primary school teachers',
            'SE.SEC.TCHR': 'Secondary school teachers'
        },
        'Infrastructure': {
            'EG.ELC.ACCS.ZS': 'Access to electricity (%)',
            'EG.ELC.ACCS.RU.ZS': 'Access to electricity, rural (%)',
            'EG.ELC.ACCS.UR.ZS': 'Access to electricity, urban (%)',
            'IT.NET.USER.ZS': 'Internet users (% of population)',
            'IT.CEL.SETS.P2': 'Mobile cellular subscriptions (per 100)',
            'IS.AIR.PSGR': 'Air transport, passengers',
            'IS.RRS.TOTL.KM': 'Rail lines (total route-km)'
        },
        'Environment': {
            'AG.LND.FRST.ZS': 'Forest area (% of land area)',
            'AG.LND.AGRI.ZS': 'Agricultural land (% of land area)',
            'AG.LND.ARBL.ZS': 'Arable land (% of land area)',
            'EN.ATM.CO2E.PC': 'CO2 emissions (metric tons per capita)',
            'ER.H2O.FWST.ZS': 'Annual freshwater withdrawals (%)',
            'AG.LND.TOTL.K2': 'Land area (sq. km)'
        },
        'Poverty & Inequality': {
            'SI.POV.NAHC': 'Poverty headcount ratio at national poverty lines (%)',
            'SI.POV.DDAY': 'Poverty headcount ratio at $2.15/day (%)',
            'SI.POV.GINI': 'Gini index',
            'SI.DST.FRST.20': 'Income share held by lowest 20%',
            'SI.DST.10TH.10': 'Income share held by highest 10%'
        },
        'Agriculture': {
            'AG.PRD.FOOD.XD': 'Food production index',
            'AG.PRD.CROP.XD': 'Crop production index',
            'AG.PRD.LVSK.XD': 'Livestock production index',
            'AG.YLD.CREL.KG': 'Cereal yield (kg per hectare)',
            'NV.AGR.TOTL.ZS': 'Agriculture, value added (% of GDP)',
            'SL.AGR.EMPL.ZS': 'Employment in agriculture (%)'
        },
        'Conflict & Fragility': {
            'VC.BTL.DETH': 'Battle-related deaths',
            'VC.IDP.TOTL.HE': 'Internally displaced persons',
            'SM.POP.REFG': 'Refugee population by country of asylum',
            'SM.POP.REFG.OR': 'Refugee population by country of origin',
            'VC.IHR.PSRC.P5': 'Intentional homicides (per 100,000)'
        }
    }

    # Signals
    data_loaded = pyqtSignal(dict)  # indicator data
    indicators_loaded = pyqtSignal(list)  # available indicators
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self):
        """Initialize the World Bank client."""
        super().__init__()
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'sudan_worldbank_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_categories(self):
        """Get list of indicator categories."""
        return list(self.INDICATOR_CATEGORIES.keys())

    def get_indicators_by_category(self, category):
        """Get indicators for a category."""
        indicators = self.INDICATOR_CATEGORIES.get(category, {})
        return [{'id': k, 'name': v} for k, v in indicators.items()]

    def get_all_indicators(self):
        """Get all indicators as a flat list."""
        indicators = []
        for category, cat_indicators in self.INDICATOR_CATEGORIES.items():
            for ind_id, ind_name in cat_indicators.items():
                indicators.append({
                    'id': ind_id,
                    'name': ind_name,
                    'category': category
                })
        return indicators

    def fetch_indicator(self, indicator_id, start_year=None, end_year=None):
        """
        Fetch data for a specific indicator for Sudan.

        :param indicator_id: World Bank indicator ID
        :param start_year: Start year (optional)
        :param end_year: End year (optional)
        :returns: Dictionary with indicator data
        """
        # Default to last 30 years
        if not end_year:
            end_year = datetime.now().year
        if not start_year:
            start_year = end_year - 30

        self.progress_update.emit(f"Fetching {indicator_id}...")

        url = f"{self.API_URL}/country/{self.SUDAN_CODE}/indicator/{indicator_id}"
        url += f"?format=json&date={start_year}:{end_year}&per_page=500"

        request = QNetworkRequest(QUrl(url))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            self.error_occurred.emit(f"API request failed: {blocking.errorMessage()}")
            return None

        try:
            content = bytes(blocking.reply().content())
            response = json.loads(content)

            # World Bank API returns [metadata, data] array
            if isinstance(response, list) and len(response) >= 2:
                metadata = response[0]
                data_points = response[1] or []

                # Parse data
                result = {
                    'indicator_id': indicator_id,
                    'indicator_name': '',
                    'country': 'Sudan',
                    'country_code': self.SUDAN_CODE,
                    'data': []
                }

                for point in data_points:
                    if not result['indicator_name'] and point.get('indicator'):
                        result['indicator_name'] = point['indicator'].get('value', '')

                    value = point.get('value')
                    year = point.get('date')

                    if value is not None and year:
                        result['data'].append({
                            'year': int(year),
                            'value': float(value)
                        })

                # Sort by year
                result['data'].sort(key=lambda x: x['year'])
                self.data_loaded.emit(result)
                return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.error_occurred.emit(f"Failed to parse response: {str(e)}")
            return None

        return None

    def fetch_multiple_indicators(self, indicator_ids, start_year=None, end_year=None):
        """
        Fetch data for multiple indicators.

        :param indicator_ids: List of indicator IDs
        :param start_year: Start year
        :param end_year: End year
        :returns: Dictionary mapping indicator IDs to their data
        """
        results = {}
        for ind_id in indicator_ids:
            data = self.fetch_indicator(ind_id, start_year, end_year)
            if data:
                results[ind_id] = data
        return results

    def search_indicators(self, query):
        """
        Search for indicators by keyword.

        :param query: Search query
        :returns: List of matching indicators
        """
        self.progress_update.emit(f"Searching indicators: {query}...")

        url = f"{self.API_URL}/indicator?format=json&q={query}&per_page=100"

        request = QNetworkRequest(QUrl(url))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            self.error_occurred.emit(f"Search failed: {blocking.errorMessage()}")
            return []

        try:
            content = bytes(blocking.reply().content())
            response = json.loads(content)

            if isinstance(response, list) and len(response) >= 2:
                indicators_data = response[1] or []
                indicators = []

                for ind in indicators_data:
                    indicators.append({
                        'id': ind.get('id', ''),
                        'name': ind.get('name', ''),
                        'source': ind.get('source', {}).get('value', ''),
                        'topic': ind.get('topics', [{}])[0].get('value', '') if ind.get('topics') else ''
                    })

                self.indicators_loaded.emit(indicators)
                return indicators

        except (json.JSONDecodeError, KeyError) as e:
            self.error_occurred.emit(f"Failed to parse search results: {str(e)}")

        return []

    def get_statistics(self, indicator_data):
        """
        Calculate statistics for indicator data.

        :param indicator_data: Data dict from fetch_indicator
        :returns: Statistics dictionary
        """
        if not indicator_data or not indicator_data.get('data'):
            return {}

        values = [d['value'] for d in indicator_data['data']]
        years = [d['year'] for d in indicator_data['data']]

        stats = {
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'latest': indicator_data['data'][-1] if indicator_data['data'] else None,
            'earliest': indicator_data['data'][0] if indicator_data['data'] else None,
            'data_points': len(values),
            'year_range': f"{min(years)} - {max(years)}" if years else "N/A"
        }

        # Calculate trend (simple linear)
        if len(values) >= 2:
            first_half = sum(values[:len(values)//2]) / (len(values)//2)
            second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            if first_half > 0:
                change_pct = ((second_half - first_half) / first_half) * 100
                stats['trend'] = 'increasing' if change_pct > 5 else ('decreasing' if change_pct < -5 else 'stable')
                stats['trend_pct'] = change_pct

        return stats

    def export_to_csv(self, indicator_data, filename=None):
        """
        Export indicator data to CSV.

        :param indicator_data: Data dict from fetch_indicator
        :param filename: Output filename (optional)
        :returns: File path
        """
        if not filename:
            ind_id = indicator_data.get('indicator_id', 'unknown').replace('.', '_')
            filename = f"worldbank_{ind_id}_sudan.csv"

        filepath = os.path.join(self.cache_dir, filename)

        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Country', 'Country Code', 'Indicator ID', 'Indicator Name', 'Year', 'Value'
            ])

            for point in indicator_data.get('data', []):
                writer.writerow([
                    indicator_data.get('country', 'Sudan'),
                    indicator_data.get('country_code', 'SDN'),
                    indicator_data.get('indicator_id', ''),
                    indicator_data.get('indicator_name', ''),
                    point.get('year'),
                    point.get('value')
                ])

        return filepath

    def clear_cache(self):
        """Clear the cache directory."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
