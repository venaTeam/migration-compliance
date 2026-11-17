"""Adapter mapping errors."""


class MappingError(Exception):
    """Raised when a Grafana rule cannot be mapped to the standard."""

    def __init__(self, reason_code: str, message: str):
        self.reason_code = reason_code
        self.message = message
        super().__init__(message)
