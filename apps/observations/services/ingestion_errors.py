import traceback


class IngestionError(Exception):
    """Stop ingestion immediately and return this error to the API."""

    def __init__(self, message: str, *, row: int | None = None, function: str | None = None, line: int | None = None):
        self.row        = row
        self.function   = function
        self.line       = line
        super().__init__(message)

    def as_dict(self) -> dict:
        return {
            'row'         : self.row,
            'function'    : self.function or 'unknown',
            'line'        : self.line,
            'error'       : str(self),
        }


def raise_ingestion_error(message: str, *, row: int | None = None) -> None:
    frame = traceback.extract_stack()[-2]
    raise IngestionError(
        message,
        row=row,
        function=frame.name,
        line=frame.lineno,
    )
