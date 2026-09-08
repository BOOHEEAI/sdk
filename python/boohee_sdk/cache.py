"""Token 缓存接口"""
from typing import Protocol, Optional


class TokenCache(Protocol):
    """
    Token 缓存接口

    开发者可以实现此接口来自定义 token 存储方式
    """

    def get(self, app_id: str) -> Optional[str]:
        """
        获取缓存的 token

        Args:
            app_id: 应用 ID

        Returns:
            缓存的 token,如果不存在或已过期返回 None
        """
        ...

    def set(self, app_id: str, token: str, expires_in: int) -> None:
        """
        缓存 token

        Args:
            app_id: 应用 ID
            token: access_token
            expires_in: 过期时间(秒)
        """
        ...

    def delete(self, app_id: str) -> None:
        """
        删除缓存的 token

        Args:
            app_id: 应用 ID
        """
        ...


__all__ = ['TokenCache']
