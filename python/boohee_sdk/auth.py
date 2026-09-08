"""认证相关"""
import base64
from enum import Enum

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pss


class AuthMode(str, Enum):
    """认证模式"""
    ACCESS_TOKEN = 'access_token'
    API_KEY = 'api_key'

    def __str__(self) -> str:
        return self.value


def rsa_sign(plaintext: str, private_key_pem: str) -> str:
    """
    RSA-PSS + SHA256 签名

    Args:
        plaintext: 待签名的字符串
        private_key_pem: RSA 私钥 PEM 格式字符串

    Returns:
        Base64 编码的签名字符串
    """
    key = RSA.import_key(private_key_pem)
    h = SHA256.new(plaintext.encode("utf-8"))
    signature = pss.new(key).sign(h)
    return base64.b64encode(signature).decode("utf-8")


def build_signature_string(app_id: str, app_key: str, timestamp: int) -> str:
    """
    构造签名串

    格式: appKey + "app_id" + appId + "timestamp" + timestamp + appKey

    Args:
        app_id: 应用 ID
        app_key: 应用密钥
        timestamp: Unix 秒级时间戳

    Returns:
        签名字符串
    """
    return f"{app_key}app_id{app_id}timestamp{timestamp}{app_key}"


__all__ = ['AuthMode', 'rsa_sign', 'build_signature_string']
