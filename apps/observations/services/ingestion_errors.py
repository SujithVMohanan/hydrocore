import traceback


class IngestionRowError(Exception):
    """Row-level ingestion failure with a stable error code for API responses."""

    def __init__(self, code: str, message: str, field: str | None = None):
        self.code = code
        self.field = field
        super().__init__(message)


ERROR_LABELS = {
    'invalid_datetime': 'Invalid or unparseable datetime',
    'invalid_value': 'Non-numeric or missing value',
    'missing_basin': 'Missing basin identifier',
    'unknown_basin': 'Unknown basin identifier',
    'missing_column': 'Missing required CSV column',
    'row_processing': 'Unexpected row processing error',
}


def classify_error(exc: Exception) -> tuple[str, str, str | None]:
    if isinstance(exc, IngestionRowError):
        return exc.code, str(exc), exc.field

    message = str(exc)
    lower = message.lower()

    if 'datetime' in lower or 'date' in lower:
        return 'invalid_datetime', message, 'datetime'
    if 'non-numeric' in lower or 'missing value' in lower:
        return 'invalid_value', message, 'value'
    if 'unknown basin' in lower:
        return 'unknown_basin', message, 'basin'
    if 'missing basin' in lower:
        return 'missing_basin', message, 'basin'
    if 'missing required columns' in lower:
        return 'missing_column', message, None

    return 'row_processing', message, None


def format_row_error(exc: Exception, row: int | None = None) -> dict:
    """Build a simple error dict with function name, line number, and message."""
    frames = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
    frame = frames[-1] if frames else None
    return {
        'row': row,
        'function': frame.name if frame else 'unknown',
        'line': frame.lineno if frame else None,
        'error': str(exc),
    }
