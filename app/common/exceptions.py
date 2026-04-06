class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message="An error occurred", status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppException):
    def __init__(self, message="Validation failed"):
        super().__init__(message, status_code=400)


class AuthorizationError(AppException):
    def __init__(self, message="Not authorized"):
        super().__init__(message, status_code=403)


class NotFoundError(AppException):
    def __init__(self, message="Resource not found"):
        super().__init__(message, status_code=404)
