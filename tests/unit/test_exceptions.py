"""Unit tests for the exception hierarchy."""

import pytest

from proxy_lm_studio.exceptions import (
    AppError,
    ConfigurationError,
    FileServeError,
    RouteError,
)


def test_app_error_default_message():
    err = AppError()
    assert str(err) == "Application error"


def test_app_error_custom_message():
    err = AppError("Something went wrong")
    assert str(err) == "Something went wrong"


def test_app_error_context_default_empty():
    err = AppError()
    assert err.context == {}


def test_app_error_context_stored():
    err = AppError(context={"key": "value", "code": 42})
    assert err.context == {"key": "value", "code": 42}


def test_route_error_is_app_error():
    err = RouteError()
    assert isinstance(err, AppError)
    assert str(err) == "Route matching error"


def test_file_serve_error_is_app_error():
    err = FileServeError()
    assert isinstance(err, AppError)
    assert str(err) == "File serve error"


def test_configuration_error_is_app_error():
    err = ConfigurationError()
    assert isinstance(err, AppError)
    assert str(err) == "Configuration error"


def test_exception_chaining():
    original = ValueError("original cause")
    with pytest.raises(FileServeError) as exc_info:
        try:
            raise original
        except ValueError as e:
            raise FileServeError("wrapped", context={"path": "/foo"}) from e
    assert exc_info.value.__cause__ is original
    assert exc_info.value.context == {"path": "/foo"}
