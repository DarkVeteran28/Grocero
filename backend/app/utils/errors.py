"""HTTP errors that always serialise to the API error shape."""

from werkzeug.exceptions import HTTPException


class ApiError(HTTPException):
    code = 400

    def __init__(self, message="Request failed", status=400, details=None):
        super().__init__(description=message)
        self.message = message
        self.code = status
        self.details = {} if details is None else details


class ValidationError(ApiError):
    def __init__(self, message="Validation failed", details=None):
        super().__init__(message, 422, details or {})
