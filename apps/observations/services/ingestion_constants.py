from django.conf import settings

_cfg = settings.INGESTION_SETTINGS

BATCH_SIZE                = _cfg['BATCH_SIZE']
MAX_ERRORS_IN_RESPONSE    = _cfg['MAX_ERRORS_IN_RESPONSE']

RAIN_REQUIRED             = _cfg['RAIN_REQUIRED_COLUMNS']
TEMP_REQUIRED             = _cfg['TEMP_REQUIRED_COLUMNS']

RAIN_COLUMN_MAP = {
    'datetime': 'datetime',
    'value': 'value',
    'basin': 'basin',
}

TEMP_COLUMN_MAP = {
    'datetime': 'datetime',
    'value': 'value',
    'basin': 'basin.id',
}

RAIN_TIMESTAMP_FORMATS = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d')
TEMP_TIMESTAMP_FORMATS = ('%d/%m/%Y %H:%M', '%d/%m/%Y')

MEASUREMENT_RAINFALL = {'name': 'Rainfall', 'unit': 'mm'}
MEASUREMENT_TEMPERATURE = {'name': 'Temperature', 'unit': '°C'}

OBSERVATION_SOURCE = 'CSV_Ingest'
