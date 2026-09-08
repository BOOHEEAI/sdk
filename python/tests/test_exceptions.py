import pytest
from boohee_sdk.exceptions import BooheeException, AuthenticationError, APIError, NetworkError


def test_boohee_exception_base():
    """测试基础异常"""
    exc = BooheeException("test error")
    assert str(exc) == "test error"
    assert isinstance(exc, Exception)


def test_authentication_error():
    """测试认证错误"""
    exc = AuthenticationError("invalid signature")
    assert str(exc) == "invalid signature"
    assert isinstance(exc, BooheeException)


def test_api_error():
    """测试 API 错误"""
    exc = APIError(401, "invalid access_token")
    assert exc.code == 401
    assert exc.message == "invalid access_token"
    assert "API Error 401: invalid access_token" in str(exc)
    assert isinstance(exc, BooheeException)


def test_network_error():
    """测试网络错误"""
    exc = NetworkError("connection timeout")
    assert str(exc) == "connection timeout"
    assert isinstance(exc, BooheeException)
