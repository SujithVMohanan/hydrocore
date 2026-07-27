import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ExceptionHandler:

    @staticmethod
    def handle(exception):


        tb       = exception.__traceback__
        filename = tb.tb_frame.f_code.co_filename
        function = tb.tb_frame.f_code.co_name
        line     = tb.tb_lineno

        logger.exception(exception)

        return Response(
            {
                "status": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                # "message": f"Something went wrong in {function} at line {line}.",
                "error": str(exception)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )