import csv
import io
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone as dt_timezone
from typing import Iterator, TextIO

from django.db import transaction

from apps.basin.models import Basin
from apps.observations.models import MeasurementType, Observation
from apps.observations.services.ingestion_constants import (
    BATCH_SIZE,
    MEASUREMENT_RAINFALL,
    MEASUREMENT_TEMPERATURE,
    OBSERVATION_SOURCE,
    RAIN_COLUMN_MAP,
    RAIN_REQUIRED,
    RAIN_TIMESTAMP_FORMATS,
    TEMP_COLUMN_MAP,
    TEMP_REQUIRED,
    TEMP_TIMESTAMP_FORMATS,
)
from apps.observations.services.ingestion_errors import IngestionError, raise_ingestion_error
from apps.users.models import Users
from utils.cache import CacheManager

UTC = dt_timezone.utc
PROGRESS_EVERY = 25_000
logger = logging.getLogger(__name__)


def _log(message: str) -> None:
    """Write to logger and terminal so progress is always visible."""
    logger.info(message)
    print(f'[ingest] {message}', flush=True)


class IngestionService:

    @staticmethod
    def _resolve_user(user) -> Users | None:
        if user is None:
            return None
        if isinstance(user, Users):
            return user
        user_id = getattr(user, 'id', None)
        return Users.objects.filter(id=user_id).first() if user_id else None

    @classmethod
    def ingest_rainfall(cls, file_obj, auto_create_basins: bool = True, created_by=None) -> None:
        _log('ingest_rainfall started')
        cls._ingest_file(
            file_obj=file_obj,
            file_type='rainfall',
            measurement=MEASUREMENT_RAINFALL,
            column_map=RAIN_COLUMN_MAP,
            required_columns=RAIN_REQUIRED,
            timestamp_formats=RAIN_TIMESTAMP_FORMATS,
            auto_create_basins=auto_create_basins,
            created_by=cls._resolve_user(created_by),
        )
        _log('ingest_rainfall ended')

    @classmethod
    def ingest_temperature(cls, file_obj, auto_create_basins: bool = True, created_by=None) -> None:
        _log('ingest_temperature started')
        cls._ingest_file(
            file_obj=file_obj,
            file_type='temperature',
            measurement=MEASUREMENT_TEMPERATURE,
            column_map=TEMP_COLUMN_MAP,
            required_columns=TEMP_REQUIRED,
            timestamp_formats=TEMP_TIMESTAMP_FORMATS,
            auto_create_basins=auto_create_basins,
            created_by=cls._resolve_user(created_by),
        )
        _log('ingest_temperature ended')

    @classmethod
    def _ingest_file(
        cls,
        file_obj,
        file_type: str,
        measurement: dict,
        column_map: dict,
        required_columns: frozenset,
        timestamp_formats: tuple,
        auto_create_basins: bool,
        created_by: Users | None,
    ) -> None:
        rows = None
        basin_map = None
        observations = None
        measurement_type = None
        affected_basin_ids = None
        started = time.monotonic()

        try:
            _log(f'{file_type}: parsing CSV started')
            with cls._open_text(file_obj) as text_file:
                rows = cls._parse_csv_rows(
                    text_file,
                    file_type=file_type,
                    column_map=column_map,
                    required_columns=required_columns,
                    timestamp_formats=timestamp_formats,
                )
            _log(f'{file_type}: parsing CSV ended — {len(rows):,} rows')

            _log(f'{file_type}: loading measurement type + basins started')
            measurement_type = cls._get_measurement_type(
                measurement['name'], measurement['unit'], created_by,
            )
            basin_map = cls._prepare_basins(
                {csv_basin_id for csv_basin_id, _ts, _value in rows},
                auto_create_basins=auto_create_basins,
                created_by=created_by,
            )
            _log(f'{file_type}: basins ready — {len(basin_map):,} stations')

            _log(f'{file_type}: building observation objects started')
            observations = []
            affected_basin_ids = set()
            total_rows = len(rows)
            for index, (csv_basin_id, timestamp, value) in enumerate(rows, start=1):
                basin_pk = basin_map[csv_basin_id]
                observations.append(
                    Observation(
                        basin_id=basin_pk,
                        measurement_type_id=measurement_type.id,
                        timestamp=timestamp,
                        value=value,
                        source=OBSERVATION_SOURCE,
                        created_by=created_by,
                    )
                )
                affected_basin_ids.add(basin_pk)
                if index % PROGRESS_EVERY == 0:
                    _log(f'{file_type}: built {index:,} / {total_rows:,} objects...')
            _log(f'{file_type}: building observation objects ended')

            _log(f'{file_type}: bulk_create started ({len(observations):,} rows)')
            with transaction.atomic():
                Observation.objects.bulk_create(
                    observations,
                    batch_size=BATCH_SIZE,
                    ignore_conflicts=True,
                )
            _log(f'{file_type}: bulk_create ended')

            _log(f'{file_type}: cache invalidation started')
            for basin_pk in affected_basin_ids:
                CacheManager.invalidate_basin_cache(basin_pk)
            _log(f'{file_type}: cache invalidation ended')

            elapsed = round(time.monotonic() - started, 2)
            _log(f'{file_type}: completed successfully in {elapsed}s')

        except IngestionError as exc:
            _log(f'{file_type}: FAILED — {exc}')
            raise
        except Exception as exc:
            _log(f'{file_type}: FAILED — {exc}')
            raise_ingestion_error(str(exc))
        finally:
            del rows, basin_map, observations, measurement_type, affected_basin_ids

    @staticmethod
    @contextmanager
    def _open_text(file_obj) -> Iterator[TextIO]:
        if hasattr(file_obj, 'seek'):
            try:
                file_obj.seek(0)
            except Exception:
                pass

        if isinstance(file_obj, io.TextIOBase):
            yield file_obj
            return

        wrapper = io.TextIOWrapper(file_obj, encoding='utf-8-sig', newline='')
        try:
            yield wrapper
        finally:
            wrapper.detach()

    @classmethod
    def _parse_csv_rows(
        cls,
        text_file: TextIO,
        file_type: str,
        column_map: dict,
        required_columns: frozenset,
        timestamp_formats: tuple,
    ) -> list[tuple[str, datetime, float]]:
        reader = csv.reader(text_file)
        try:
            headers = next(reader)
        except StopIteration:
            raise_ingestion_error('CSV file is empty or missing a header row.')

        indexes = cls._column_indexes(headers, file_type, column_map, required_columns)
        dt_idx, value_idx, basin_idx = indexes

        rows: list[tuple[str, datetime, float]] = []
        for row_number, raw in enumerate(reader, start=2):
            if not raw or all(not (cell or '').strip() for cell in raw):
                continue
            if len(raw) <= max(dt_idx, value_idx, basin_idx):
                raise_ingestion_error('Incomplete CSV row.', row=row_number)

            timestamp = cls._parse_timestamp(raw[dt_idx], timestamp_formats, row_number)
            value = cls._parse_value(raw[value_idx], row_number)
            basin_id = (raw[basin_idx] or '').strip()
            if not basin_id:
                raise_ingestion_error('Missing basin.', row=row_number)

            rows.append((basin_id, timestamp, value))
            parsed = len(rows)
            if parsed % PROGRESS_EVERY == 0:
                _log(f'{file_type}: parsed {parsed:,} rows...')

        if not rows:
            raise_ingestion_error(f'No data rows found in {file_type} CSV.')
        return rows

    @staticmethod
    def _column_indexes(headers, file_type, column_map, required_columns) -> tuple[int, int, int]:
        normalized = [(h or '').strip().lower().replace(' ', '') for h in headers]
        missing = required_columns - set(normalized)
        if missing:
            raise_ingestion_error(
                f"Missing required columns for {file_type} CSV: {', '.join(sorted(missing))}"
            )
        try:
            return (
                normalized.index(column_map['datetime']),
                normalized.index(column_map['value']),
                normalized.index(column_map['basin']),
            )
        except ValueError:
            raise_ingestion_error(f'Missing mapped columns for {file_type} CSV.')

    @staticmethod
    def _parse_timestamp(raw: str, formats: tuple, row: int) -> datetime:
        value = (raw or '').strip()
        if not value:
            raise_ingestion_error('Missing datetime.', row=row)
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        raise_ingestion_error(f"Invalid datetime: '{raw}'", row=row)

    @staticmethod
    def _parse_value(raw: str, row: int) -> float:
        if raw is None or str(raw).strip() == '':
            raise_ingestion_error('Missing value.', row=row)
        try:
            return float(raw)
        except (TypeError, ValueError):
            raise_ingestion_error(f"Non-numeric value: '{raw}'", row=row)

    @staticmethod
    def _get_measurement_type(name: str, unit: str, created_by: Users | None) -> MeasurementType:
        mt, _ = MeasurementType.objects.get_or_create(
            name=name,
            defaults={'unit': unit, 'created_by': created_by},
        )
        return mt

    @classmethod
    def _prepare_basins(
        cls,
        csv_basin_ids: set[str],
        auto_create_basins: bool,
        created_by: Users | None,
    ) -> dict[str, int]:
        basin_map = dict(
            Basin.objects.filter(basin_id__in=csv_basin_ids).values_list('basin_id', 'id')
        )
        missing = csv_basin_ids - set(basin_map.keys())
        if not missing:
            return basin_map

        if not auto_create_basins:
            raise_ingestion_error(f"Unknown basin_id(s): {', '.join(sorted(missing))}")

        _log(f'creating {len(missing):,} missing basins...')
        Basin.objects.bulk_create(
            [
                Basin(
                    basin_id=csv_id,
                    name=f'Station {csv_id}',
                    metadata={'source': 'csv_ingest', 'csv_station_id': csv_id},
                    created_by=created_by,
                )
                for csv_id in missing
            ],
            ignore_conflicts=True,
        )
        basin_map.update(
            dict(Basin.objects.filter(basin_id__in=missing).values_list('basin_id', 'id'))
        )
        return basin_map
