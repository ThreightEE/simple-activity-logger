import logging
import os

from typing import Callable
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class LogRequestPIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        pid: int = os.getpid()
        logger.info(f"MIDDLEWARE - PID {pid} - request {request.method} {request.path}")
        
        response: HttpResponse = self.get_response(request)
        return response
    