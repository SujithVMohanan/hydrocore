import csv
import io
import logging
import time
from collections import Counter
from datetime import datetime, timezone as dt_timezone
from typing import Any, BinaryIO, Callable, TextIO

from django.db import transaction
from django.utils import timezone

from apps.basin.models import Basin
from apps.observations.models import MeasurementType, Observation
from apps.observations.services.ingestion_constants import (
    BATCH_SIZE,
    MAX_ERRORS_IN_RESPONSE,
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
from apps.observations.services.ingestion_errors import (
    ERROR_LABELS,
    IngestionRowError,
    classify_error,
    format_row_error,
)
from apps.users.models import Users
from utils.cache import CacheManager

logger = logging.getLogger(__name__)


class IngestionService:

    @staticmethod
    def _resolve_user(user) -> Users | None:
        if user is None:
            return None
        if isinstance(user, Users):
            return user
        user_id = getattr(user, 'id', None)
        if user_id:
            return Users.objects.filter(id=user_id).first()
        return None

    @classmethod
    def ingest_rainfall(
        cls,
        file_obj: BinaryIO,
        auto_create_basins: bool = True,
        created_by: Users | None = None,
    ) -> dict[str, Any]:
        created_by = cls._resolve_user(created_by)
        measurement_type = cls._get_or_create_measurement_type(
            MEASUREMENT_RAINFALL['name'], MEASUREMENT_RAINFALL['unit'], created_by,
        )
        return cls._ingest_stream(
            file_obj=file_obj,
            file_type='rainfall',
            measurement_type=measurement_type,
            column_map=RAIN_COLUMN_MAP,
            parse_timestamp=cls._parse_rainfall_timestamp,
            auto_create_basins=auto_create_basins,
            created_by=created_by,
        )

    @classmethod
    def ingest_temperature(
        cls,
        file_obj: BinaryIO,
        auto_create_basins: bool = True,
        created_by: Users | None = None,
    ) -> dict[str, Any]:
        created_by = cls._resolve_user(created_by)
        measurement_type = cls._get_or_create_measurement_type(
            MEASUREMENT_TEMPERATURE['name'], MEASUREMENT_TEMPERATURE['unit'], created_by,
        )
        return cls._ingest_stream(
            file_obj=file_obj,
            file_type='temperature',
            measurement_type=measurement_type,
            column_map=TEMP_COLUMN_MAP,
            parse_timestamp=cls._parse_temperature_timestamp,
            auto_create_basins=auto_create_basins,
            created_by=created_by,
        )

    @classmethod
    def build_overall_summary(cls, file_summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
        totals = Counter()
        merged_error_summary: Counter = Counter()
        duration = 0.0

        for summary in file_summaries.values():
            totals['rows_read'] += summary.get('rows_read', 0)
            totals['rows_inserted'] += summary.get('rows_inserted', 0)
            totals['rows_updated'] += summary.get('rows_updated', 0)
            totals['rows_ingested'] += summary.get('rows_ingested', 0)
            totals['rows_not_inserted'] += summary.get('rows_not_inserted', 0)
            totals['errors_count'] += summary.get('errors_count', 0)
            duration += summary.get('duration_seconds', 0)
            for code, count in summary.get('error_summary', {}).items():
                merged_error_summary[code] += count

        overall = {
            'files_processed': list(file_summaries.keys()),
            'rows_read': totals['rows_read'],
            'rows_ingested': totals['rows_ingested'],
            'rows_inserted': totals['rows_inserted'],
            'rows_updated': totals['rows_updated'],
            'rows_not_inserted': totals['rows_not_inserted'],
            'errors_count': totals['errors_count'],
            'error_summary': dict(sorted(merged_error_summary.items())),
            'main_error': cls._build_main_error(merged_error_summary),
            'duration_seconds': round(duration, 2),
        }
        return overall

    @classmethod
    def build_response_message(cls, overall: dict[str, Any]) -> str:
        errors_count = overall.get('errors_count', 0)
        rows_ingested = overall.get('rows_ingested', 0)

        if errors_count == 0:
            return 'Ingestion completed successfully.'
        if rows_ingested == 0:
            return f'Ingestion failed: no rows were saved ({errors_count} errors).'
        return f'Ingestion completed with {errors_count} row errors.'

    @classmethod
    def build_simple_response(cls, file_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        overall = cls.build_overall_summary(file_results)
        inserted = overall['rows_inserted']
        updated = overall['rows_updated']
        failed = overall['rows_not_inserted']
        saved = overall['rows_ingested']

        errors: list[dict] = []
        for file_type, summary in file_results.items():
            for err in summary.get('errors', []):
                errors.append({
                    'file': file_type,
                    'row': err.get('row'),
                    'function': err.get('function'),
                    'line': err.get('line'),
                    'error': err.get('error'),
                })
            if summary.get('errors_truncated'):
                errors.append({
                    'file': file_type,
                    'row': None,
                    'function': 'IngestionService._ingest_stream',
                    'line': None,
                    'error': (
                        f"{summary['errors_count']} total errors; "
                        f"showing first {len(summary.get('errors', []))} only."
                    ),
                })

        if failed == 0:
            message = f'Successfully inserted {inserted} rows and updated {updated} rows.'
            success = True
        elif saved == 0:
            message = f'Ingestion failed. {failed} rows could not be saved.'
            success = False
        else:
            message = (
                f'Partially completed: inserted {inserted}, '
                f'updated {updated}, failed {failed}.'
            )
            success = True

        return {
            'success': success,
            'message': message,
            'data': {
                'rows_inserted': inserted,
                'rows_updated': updated,
                'rows_failed': failed,
                'rows_saved': saved,
            },
            'errors': errors,
        }

    @classmethod
    def _ingest_stream(
        cls,
        file_obj: BinaryIO,
        file_type: str,
        measurement_type: MeasurementType,
        column_map: dict[str, str],
        parse_timestamp: Callable[[str], datetime],
        auto_create_basins: bool,
        created_by: Users | None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        error_counts: Counter = Counter()
        summary: dict[str, Any] = {
            'file_type': file_type,
            'rows_read': 0,
            'rows_inserted': 0,
            'rows_updated': 0,
            'rows_skipped_error': 0,
            'errors': [],
        }

        basin_cache: dict[str, Basin] = {}
        affected_basin_pks: set[int] = set()
        batch: list[Observation] = []

        reader, _fieldnames = cls._open_csv_stream(file_obj)
        cls._validate_required_columns(_fieldnames, file_type)

        for row_number, raw_row in enumerate(reader, start=2):
            summary['rows_read'] += 1

            try:
                row = cls._normalize_row(raw_row)
                timestamp = parse_timestamp(row[column_map['datetime']])
                value = cls._parse_value(row[column_map['value']])
                basin = cls._resolve_basin(
                    csv_basin_id=str(row[column_map['basin']]).strip(),
                    basin_cache=basin_cache,
                    auto_create_basins=auto_create_basins,
                    created_by=created_by,
                )

                batch.append(
                    Observation(
                        basin=basin,
                        measurement_type=measurement_type,
                        timestamp=timestamp,
                        value=value,
                        source=OBSERVATION_SOURCE,
                        created_by=created_by,
                    )
                )
                affected_basin_pks.add(basin.pk)

                if len(batch) >= BATCH_SIZE:
                    inserted, updated = cls._flush_batch(batch, measurement_type.id)
                    summary['rows_inserted'] += inserted
                    summary['rows_updated'] += updated
                    batch.clear()

            except Exception as exc:
                summary['rows_skipped_error'] += 1
                error_counts[classify_error(exc)[0]] += 1

                if len(summary['errors']) < MAX_ERRORS_IN_RESPONSE:
                    summary['errors'].append(format_row_error(exc, row_number))
                logger.warning('[%s ingest] row %s skipped: %s', file_type, row_number, exc)

        if batch:
            inserted, updated = cls._flush_batch(batch, measurement_type.id)
            summary['rows_inserted'] += inserted
            summary['rows_updated'] += updated
            batch.clear()

        summary['basins_affected'] = sorted(
            b.basin_id for b in basin_cache.values() if b.pk in affected_basin_pks
        )
        summary['duration_seconds'] = round(time.monotonic() - started, 2)

        for basin_pk in affected_basin_pks:
            CacheManager.invalidate_basin_cache(basin_pk)

        cls._finalize_summary(summary, error_counts)
        logger.info('[%s ingest complete] %s', file_type, summary)
        return summary

    @classmethod
    def _finalize_summary(cls, summary: dict[str, Any], error_counts: Counter) -> None:
        summary['rows_ingested'] = summary['rows_inserted'] + summary['rows_updated']
        summary['rows_not_inserted'] = summary['rows_skipped_error']
        summary['errors_count'] = summary['rows_skipped_error']
        summary['error_summary'] = dict(sorted(error_counts.items()))
        summary['main_error'] = cls._build_main_error(error_counts)
        summary['errors_truncated'] = summary['errors_count'] > len(summary['errors'])

    @staticmethod
    def _build_main_error(error_counts: Counter) -> dict[str, Any] | None:
        if not error_counts:
            return None
        code, count = error_counts.most_common(1)[0]
        return {
            'code': code,
            'label': ERROR_LABELS.get(code, code),
            'count': count,
        }

    @staticmethod
    def _open_csv_stream(file_obj: BinaryIO):
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        text_stream: TextIO = io.TextIOWrapper(file_obj, encoding='utf-8-sig', newline='')
        reader = csv.DictReader(text_stream)
        return reader, reader.fieldnames

    @classmethod
    @transaction.atomic
    def _flush_batch(cls, batch: list[Observation], measurement_type_id: int) -> tuple[int, int]:
        """Insert new rows and bulk_update existing ones (MySQL-compatible upsert)."""
        if not batch:
            return 0, 0

        now = timezone.now()
        existing_map = cls._fetch_existing_map(batch, measurement_type_id)

        to_create: list[Observation] = []
        to_update: list[Observation] = []

        for obs in batch:
            key = (obs.basin_id, obs.timestamp)
            db_obs = existing_map.get(key)
            if db_obs:
                db_obs.value = obs.value
                db_obs.source = obs.source
                db_obs.updated_at = now
                to_update.append(db_obs)
            else:
                obs.updated_at = now
                to_create.append(obs)

        if to_create:
            Observation.objects.bulk_create(to_create, batch_size=BATCH_SIZE)

        if to_update:
            Observation.objects.bulk_update(
                to_update,
                ['value', 'source', 'updated_at'],
                batch_size=BATCH_SIZE,
            )

        return len(to_create), len(to_update)

    @staticmethod
    def _fetch_existing_map(
        batch: list[Observation],
        measurement_type_id: int,
    ) -> dict[tuple[int, datetime], Observation]:
        basin_ids = {obs.basin_id for obs in batch}
        ts_min = min(obs.timestamp for obs in batch)
        ts_max = max(obs.timestamp for obs in batch)

        existing = Observation.objects.filter(
            basin_id__in=basin_ids,
            measurement_type_id=measurement_type_id,
            timestamp__gte=ts_min,
            timestamp__lte=ts_max,
        )

        return {(o.basin_id, o.timestamp): o for o in existing}

    @staticmethod
    def _get_or_create_measurement_type(name: str, unit: str, created_by: Users | None) -> MeasurementType:
        mt, _ = MeasurementType.objects.get_or_create(
            name=name,
            defaults={'unit': unit, 'created_by': created_by},
        )
        return mt

    @classmethod
    def _resolve_basin(
        cls,
        csv_basin_id: str,
        basin_cache: dict[str, Basin],
        auto_create_basins: bool,
        created_by: Users | None,
    ) -> Basin:
        if not csv_basin_id:
            raise IngestionRowError('missing_basin', 'Missing basin', field='basin')

        cached = basin_cache.get(csv_basin_id)
        if cached:
            return cached

        basin = Basin.objects.filter(basin_id=csv_basin_id).first()
        if basin:
            basin_cache[csv_basin_id] = basin
            return basin

        if not auto_create_basins:
            raise IngestionRowError(
                'unknown_basin',
                f"Unknown basin_id '{csv_basin_id}'",
                field='basin',
            )

        basin = Basin(
            basin_id=csv_basin_id,
            name=f'Station {csv_basin_id}',
            metadata={'source': 'csv_ingest', 'csv_station_id': csv_basin_id},
            created_by=created_by,
        )
        basin.save()
        basin_cache[csv_basin_id] = basin
        return basin

    @staticmethod
    def _parse_rainfall_timestamp(raw: str):
        raw = (raw or '').strip()
        if not raw:
            raise IngestionRowError('invalid_datetime', 'Missing datetime', field='datetime')
        for fmt in RAIN_TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(raw, fmt)
                return timezone.make_aware(dt, timezone=dt_timezone.utc)
            except ValueError:
                continue
        raise IngestionRowError('invalid_datetime', f"Invalid rainfall datetime: '{raw}'", field='datetime')

    @staticmethod
    def _parse_temperature_timestamp(raw: str):
        raw = (raw or '').strip()
        if not raw:
            raise IngestionRowError('invalid_datetime', 'Missing datetime', field='datetime')
        for fmt in TEMP_TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(raw, fmt)
                return timezone.make_aware(dt, timezone=dt_timezone.utc)
            except ValueError:
                continue
        raise IngestionRowError('invalid_datetime', f"Invalid temperature datetime: '{raw}'", field='datetime')

    @staticmethod
    def _parse_value(raw: str) -> float:
        if raw is None or str(raw).strip() == '':
            raise IngestionRowError('invalid_value', 'Missing value', field='value')
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise IngestionRowError('invalid_value', f"Non-numeric value: '{raw}'", field='value') from exc

    @staticmethod
    def _normalize_row(raw_row: dict[str, str | None]) -> dict[str, str]:
        return {
            (key or '').strip().lower().replace(' ', ''): (value or '').strip()
            for key, value in raw_row.items()
        }

    @classmethod
    def _validate_required_columns(cls, fieldnames: list[str] | None, file_type: str) -> None:
        if not fieldnames:
            raise IngestionRowError('missing_column', 'CSV file is empty or missing a header row.')

        normalized = {(name or '').strip().lower().replace(' ', '') for name in fieldnames}
        required = RAIN_REQUIRED if file_type == 'rainfall' else TEMP_REQUIRED
        missing = required - normalized
        if missing:
            raise IngestionRowError(
                'missing_column',
                f"Missing required columns for {file_type} CSV: {', '.join(sorted(missing))}",
            )
