from typing import Optional
from boohee_sdk.cache import TokenCache


class MockTokenCache:
    """Mock 缓存实现用于测试"""

    def __init__(self):
        self.storage = {}

    def get(self, app_id: str) -> Optional[str]:
        return self.storage.get(app_id)

    def set(self, app_id: str, token: str, expires_in: int) -> None:
        self.storage[app_id] = token

    def delete(self, app_id: str) -> None:
        self.storage.pop(app_id, None)


def test_token_cache_interface():
    """测试 TokenCache 接口"""
    cache = MockTokenCache()

    # 初始为 None
    assert cache.get("app1") is None

    # 设置 token
    cache.set("app1", "token123", 86400)
    assert cache.get("app1") == "token123"

    # 删除 token
    cache.delete("app1")
    assert cache.get("app1") is None


def test_token_cache_protocol():
    """测试 MockTokenCache 符合 TokenCache Protocol"""
    from typing import Protocol

    cache = MockTokenCache()
    # MockTokenCache 实现了 TokenCache 的所有方法
    assert hasattr(cache, 'get')
    assert hasattr(cache, 'set')
    assert hasattr(cache, 'delete')
