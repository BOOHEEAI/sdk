"""SDK 异常定义"""


class BooheeException(Exception):
    """SDK 基础异常"""
    pass


class AuthenticationError(BooheeException):
    """认证失败(签名错误、token 无效等)"""
    pass


class APIError(BooheeException):
    """API 返回错误"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API Error {code}: {message}")


class NetworkError(BooheeException):
    """网络错误(超时、连接失败等)"""
    pass
