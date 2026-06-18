class AppError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError): ...


class PermissionDeniedError(AppError): ...


class AuthenticationError(AppError): ...


class ConflictError(AppError): ...
