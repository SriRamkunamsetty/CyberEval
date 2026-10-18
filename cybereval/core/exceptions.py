"""
CyberEval - Core Domain Exceptions
"""

from fastapi import HTTPException, status


class CyberEvalException(Exception):
    """Base domain exception for CyberEval."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DatasetNotFoundError(CyberEvalException):
    pass


class ScenarioNotFoundError(CyberEvalException):
    pass


class EvaluationNotFoundError(CyberEvalException):
    pass


class ReleaseGateViolationError(CyberEvalException):
    pass


class ProviderAPIError(CyberEvalException):
    pass


class InvalidReferenceSchemaError(CyberEvalException):
    pass


def to_http_exception(exc: CyberEvalException) -> HTTPException:
    """Map domain exceptions to HTTPExceptions with safe, generic messages."""
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, (DatasetNotFoundError, ScenarioNotFoundError, EvaluationNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ReleaseGateViolationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        
    return HTTPException(
        status_code=status_code,
        detail={"error": exc.message, "details": exc.details}
    )
