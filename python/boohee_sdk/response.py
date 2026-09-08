"""响应包装类"""
from typing import Any, Dict, Optional


class BaseResp:
    """
    API 响应基类

    包装统一的响应结构: {code, message, now, data}
    """

    def __init__(self, raw: Dict[str, Any]):
        """
        初始化响应

        Args:
            raw: 原始响应字典
        """
        self._raw = raw
        self.code = raw.get('code', -1)
        self.message = raw.get('message', '')
        self.now = raw.get('now', 0)
        self._data = raw.get('data')

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        """
        获取 data 字段

        Returns:
            data 字典,如果不存在返回 None
        """
        return self._data

    def is_success(self) -> bool:
        """
        判断请求是否成功

        Returns:
            True 如果 code == 0
        """
        return self.code == 0

    def raise_for_error(self):
        """
        如果请求失败,抛出异常

        Raises:
            APIError: 如果 code != 0
        """
        if not self.is_success():
            from .exceptions import APIError
            raise APIError(self.code, self.message)

    def get(self, key: str, default: Any = None) -> Any:
        """
        从 data 中获取字段

        Args:
            key: 字段名
            default: 默认值

        Returns:
            字段值
        """
        if self._data is None:
            return default
        return self._data.get(key, default)

    def __repr__(self):
        return f"BaseResp(code={self.code}, message={self.message!r})"


__all__ = ['BaseResp']
