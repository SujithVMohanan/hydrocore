import json
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / 'full_project_data.json'
CREATED_AT = '2024-01-01T00:00:00Z'
UPDATED_AT = CREATED_AT

basins = [
    ('Narmada Basin', 'Central India'),
    ('Godavari Basin', 'South India'),
    ('Krishna Basin', 'South India'),
    ('Cauvery Basin', 'South India'),
    ('Brahmaputra Basin', 'North East India'),
    ('Ganges Basin', 'North India'),
    ('Yamuna Basin', 'North India'),
    ('Mahanadi Basin', 'East India'),
    ('Tapi Basin', 'West India'),
    ('Sabarmati Basin', 'West India'),
    ('Bhima Basin', 'South India'),
    ('Periyar Basin', 'South India'),
    ('Barak Basin', 'North East India'),
    ('Brahmani Basin', 'East India'),
    ('Baitarani Basin', 'East India'),
    ('Kosi Basin', 'North India'),
    ('Sutlej Basin', 'North India'),
    ('Netravati Basin', 'South India'),
    ('Ghaghara Basin', 'North India'),
    ('Subarnarekha Basin', 'East India'),
    ('Mahananda Basin', 'East India'),
    ('Sabarmati East Basin', 'West India'),
]

measurement_types = [
    ('Rainfall', 'mm'),
    ('Temperature', '°C'),
    ('Humidity', '%'),
    ('Wind Speed', 'km/h'),
    ('Solar Radiation', 'W/m²'),
    ('Pressure', 'hPa'),
    ('Soil Moisture', '%'),
    ('Evaporation', 'mm'),
    ('Water Level', 'm'),
    ('Flow Rate', 'm³/s'),
    ('Snow Depth', 'cm'),
    ('Cloud Cover', '%'),
    ('Dew Point', '°C'),
    ('Vapor Pressure', 'kPa'),
    ('Conductivity', 'µS/cm'),
    ('Turbidity', 'NTU'),
    ('pH', ''),
    ('Dissolved Oxygen', 'mg/L'),
    ('Chlorophyll', 'µg/L'),
    ('Visibility', 'km'),
    ('Battery Voltage', 'V'),
    ('Leaf Wetness', '%'),
    ('Soil Temperature', '°C'),
    ('Rain Rate', 'mm/hr'),
]

record_list = []

# Basins
for idx, (name, region) in enumerate(basins, start=1):
    record_list.append({
        'model': 'basin.basin',
        'pk': idx,
        'fields': {
            'basin_id': f'BSN-{1000 + idx}',
            'name': name,
            'metadata': {'region': region, 'type': 'river-catchment'},
            'created_at': CREATED_AT,
            'updated_at': UPDATED_AT,
            'created_by': None,
            'updated_by': None,
        },
    })

# Measurement types
for idx, (name, unit) in enumerate(measurement_types, start=1):
    record_list.append({
        'model': 'observations.measurementtype',
        'pk': idx,
        'fields': {
            'name': name,
            'unit': unit,
            'created_at': CREATED_AT,
            'updated_at': UPDATED_AT,
            'created_by': None,
            'updated_by': None,
        },
    })

# Observations
obs_pk = 1
rain_series = [5.2, 12.8, 18.4, 42.1, 78.6, 112.3, 94.5, 103.9, 63.2, 18.7, 9.3, 4.9]
temp_series = [23.7, 22.3, 26.2, 28.7, 32.1, 31.8, 30.2, 29.8, 26.4, 22.0, 17.8, 13.1]

for basin_id in range(1, len(basins) + 1):
    rain_offset = ((basin_id - 1) % 5) * 2.2
    temp_offset = ((basin_id - 1) % 4) * 0.7 - ((basin_id - 1) // 6) * 0.4
    for month_idx in range(12):
        timestamp = f'2024-{month_idx + 1:02d}-01T00:00:00Z'
        record_list.append({
            'model': 'observations.observation',
            'pk': obs_pk,
            'fields': {
                'basin': basin_id,
                'measurement_type': 1,
                'timestamp': timestamp,
                'value': round(rain_series[month_idx] + rain_offset, 1),
                'source': 'fixture',
                'created_at': CREATED_AT,
                'updated_at': UPDATED_AT,
                'created_by': None,
                'updated_by': None,
            },
        })
        obs_pk += 1
        record_list.append({
            'model': 'observations.observation',
            'pk': obs_pk,
            'fields': {
                'basin': basin_id,
                'measurement_type': 2,
                'timestamp': timestamp,
                'value': round(temp_series[month_idx] + temp_offset, 1),
                'source': 'fixture',
                'created_at': CREATED_AT,
                'updated_at': UPDATED_AT,
                'created_by': None,
                'updated_by': None,
            },
        })
        obs_pk += 1

# Additional measurement observations for first 10 basins
extra_measurements = [3, 4, 5, 6, 7, 8, 9, 10]
for basin_id in range(1, 11):
    for idx, measurement_type in enumerate(extra_measurements, start=1):
        record_list.append({
            'model': 'observations.observation',
            'pk': obs_pk,
            'fields': {
                'basin': basin_id,
                'measurement_type': measurement_type,
                'timestamp': f'2024-01-{idx + 1:02d}T06:00:00Z',
                'value': round(12.0 + basin_id * 1.5 + idx * 1.3, 1),
                'source': 'fixture',
                'created_at': CREATED_AT,
                'updated_at': UPDATED_AT,
                'created_by': None,
                'updated_by': None,
            },
        })
        obs_pk += 1

# Rainfall events with 30 entries
event_pk = 1
base_start_dates = [
    '2024-01-05T03:00:00Z', '2024-01-18T04:00:00Z', '2024-02-10T05:00:00Z',
    '2024-02-28T03:00:00Z', '2024-03-15T02:00:00Z', '2024-03-30T22:00:00Z',
    '2024-04-18T09:00:00Z', '2024-04-27T07:00:00Z', '2024-05-22T08:00:00Z',
    '2024-05-14T05:00:00Z', '2024-06-08T11:00:00Z', '2024-06-19T19:00:00Z',
    '2024-07-10T10:00:00Z', '2024-07-29T21:00:00Z', '2024-08-12T14:00:00Z',
    '2024-08-25T13:00:00Z', '2024-09-18T02:00:00Z', '2024-09-28T06:00:00Z',
    '2024-10-20T18:00:00Z', '2024-11-08T06:00:00Z', '2024-11-25T06:00:00Z',
    '2024-12-02T12:00:00Z', '2024-12-18T18:00:00Z', '2024-12-29T04:00:00Z',
    '2024-06-14T08:00:00Z', '2024-07-06T15:00:00Z', '2024-08-28T18:00:00Z',
    '2024-09-07T11:00:00Z', '2024-10-16T16:00:00Z', '2024-11-03T10:00:00Z',
]

end_offsets = [24, 18, 30, 22, 28, 16, 24, 20, 12, 12, 10, 36, 18, 20, 24, 48, 16, 14, 20, 22, 15, 14, 18, 20, 26, 21, 19, 17, 25, 13]
peak_values = [
    12.5, 10.8, 15.2, 17.9, 22.4, 28.1, 18.9, 24.5, 14.8, 9.8,
    11.2, 7.5, 13.1, 16.3, 20.2, 18.5, 26.0, 31.1, 19.0, 23.4,
    14.2, 17.6, 21.8, 25.3, 13.9, 18.4, 29.5, 16.7, 22.2, 12.9,
]
total_volumes = [
    52.1, 40.6, 63.5, 81.4, 102.0, 76.8, 96.4, 88.0, 47.5, 31.2,
    28.4, 55.3, 64.8, 72.1, 98.3, 132.6, 91.0, 104.2, 82.5, 90.1,
    45.0, 55.4, 63.8, 78.2, 48.9, 59.1, 89.4, 72.7, 94.0, 53.6,
]

for idx, start_ts in enumerate(base_start_dates, start=1):
    basin_id = ((idx - 1) % len(basins)) + 1
    offset = end_offsets[idx - 1]
    peak = peak_values[idx - 1]
    volume = total_volumes[idx - 1]
    start_dt = datetime.fromisoformat(start_ts.replace('Z', ''))
    end_dt = start_dt + timedelta(hours=offset)
    record_list.append({
        'model': 'analytics.rainfallevent',
        'pk': event_pk,
        'fields': {
            'basin': basin_id,
            'start_timestamp': start_ts,
            'end_timestamp': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'duration_hours': offset,
            'peak_value': peak,
            'total_volume': volume,
            'min_dry_gap_used': 6,
            'is_cold_event': peak < 10,
            'created_at': CREATED_AT,
            'updated_at': UPDATED_AT,
            'created_by': None,
            'updated_by': None,
        },
    })
    event_pk += 1

OUTPUT_FILE.write_text(json.dumps(record_list, indent=2), encoding='utf-8')
print('Wrote', OUTPUT_FILE, 'with', len(record_list), 'records')
