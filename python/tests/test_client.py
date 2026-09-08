import pytest
import time
from unittest.mock import Mock, patch
from boohee_sdk import BooheeClient, AuthMode
from boohee_sdk.request import HttpMethod
from boohee_sdk.exceptions import APIError, NetworkError


def test_client_init_access_token_mode():
    """测试 Access Token 模式初始化"""
    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_key_pem'
    )
    assert client.auth_mode == AuthMode.ACCESS_TOKEN
    assert client.app_id == 'test_app'
    assert client.app_key == 'test_key'


def test_client_init_api_key_mode():
    """测试 API Key 模式初始化"""
    client = BooheeClient(
        api_key='test_api_key',
        auth_mode=AuthMode.API_KEY
    )
    assert client.auth_mode == AuthMode.API_KEY
    assert client.api_key == 'test_api_key'


def test_client_init_missing_params():
    """测试缺少必需参数"""
    with pytest.raises(ValueError, match="app_id is required"):
        BooheeClient(app_key='key', private_key='pem')

    with pytest.raises(ValueError, match="api_key is required"):
        BooheeClient(auth_mode=AuthMode.API_KEY)


def test_client_init_custom_base_url():
    """测试自定义 base_url"""
    client = BooheeClient(
        api_key='test_key',
        auth_mode=AuthMode.API_KEY,
        base_url='https://custom.api.com/'
    )
    assert client.base_url == 'https://custom.api.com'


def test_client_default_base_url():
    """测试默认 base_url"""
    client = BooheeClient(
        api_key='test_key',
        auth_mode=AuthMode.API_KEY
    )
    assert client.base_url == 'https://api.boohee.com'


def test_client_default_timeout():
    """测试默认 timeout"""
    client = BooheeClient(
        api_key='test_key',
        auth_mode=AuthMode.API_KEY
    )
    assert client.timeout == 30


def test_client_cache_parameter():
    """测试 cache 参数"""
    from boohee_sdk.cache import TokenCache

    class MockCache:
        def get(self, app_id): return None
        def set(self, app_id, token, expires_in): pass
        def delete(self, app_id): pass

    cache = MockCache()
    client = BooheeClient(
        app_id='test',
        app_key='key',
        private_key='pem',
        cache=cache
    )
    assert client.cache is cache


def test_client_invalid_auth_mode():
    """测试无效 auth_mode"""
    with pytest.raises(ValueError, match="Invalid auth_mode"):
        BooheeClient(auth_mode="invalid")


def test_client_token_management_init():
    """测试 Token 管理属性初始化"""
    import threading
    client = BooheeClient(
        app_id='test',
        app_key='key',
        private_key='pem'
    )
    assert client._access_token is None
    assert client._token_expires_at == 0
    assert isinstance(client._token_lock, type(threading.Lock()))


def test_client_api_key_mode_isolation():
    """测试 API Key 模式属性隔离"""
    client = BooheeClient(
        api_key='test_key',
        auth_mode=AuthMode.API_KEY
    )
    assert client.app_id is None
    assert client.app_key is None
    assert client.private_key is None


def test_client_empty_string_params():
    """测试空字符串参数被拒绝"""
    with pytest.raises(ValueError):
        BooheeClient(app_id='', app_key='key', private_key='pem')


def test_client_access_token_header():
    """测试 ACCESS_TOKEN 模式的 Header"""
    client = BooheeClient(
        app_id='test',
        app_key='key',
        private_key='pem'
    )
    # 设置一个未过期的 token
    client._access_token = 'test_token'
    client._token_expires_at = time.time() + 3600

    headers = client._get_headers()
    assert headers['Authorization'] == 'Bearer test_token'
    assert 'X-Api-Key' not in headers


def test_client_invalid_method():
    """测试不支持的 HTTP 方法"""
    client = BooheeClient(api_key='test_key', auth_mode=AuthMode.API_KEY)

    with pytest.raises(ValueError, match="Unsupported HTTP method"):
        client._request('DELETE', '/test')  # type: ignore[arg-type]


def test_token_refresh():
    """测试 Token 自动刷新"""
    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )

    with patch('requests.Session.post') as mock_post:
        # Mock AccessToken API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'now': 1722851989,
            'data': {
                'access_token': 'new_token',
                'expires_in': 86400
            }
        }
        mock_post.return_value = mock_response

        # Mock RSA 签名
        with patch('boohee_sdk.client.rsa_sign') as mock_sign:
            mock_sign.return_value = 'mock_signature'

            token = client._get_access_token()

            assert token == 'new_token'
            assert mock_post.called


def test_token_cache():
    """测试 Token 缓存"""

    class MockCache:
        def __init__(self):
            self.storage = {}
        def get(self, app_id):
            return self.storage.get(app_id)
        def set(self, app_id, token, expires_in):
            self.storage[app_id] = token
        def delete(self, app_id):
            self.storage.pop(app_id, None)

    cache = MockCache()
    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key',
        cache=cache
    )

    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'now': 1722851989,
            'data': {
                'access_token': 'cached_token',
                'expires_in': 86400
            }
        }
        mock_post.return_value = mock_response

        with patch('boohee_sdk.client.rsa_sign') as mock_sign:
            mock_sign.return_value = 'mock_signature'

            # 第一次获取,应该调用 API
            token1 = client._get_access_token()
            assert token1 == 'cached_token'
            assert cache.get('test_app') == 'cached_token'


def test_token_memory_cache_hit():
    """测试内存缓存命中"""
    client = BooheeClient(
        app_id='test',
        app_key='key',
        private_key='pem'
    )
    # 设置一个未过期的 token
    client._access_token = 'cached_token'
    client._token_expires_at = time.time() + 3600

    # 应该直接返回,不调用 API
    with patch('requests.Session.post') as mock_post:
        token = client._get_access_token()
        assert token == 'cached_token'
        assert not mock_post.called


def test_token_refresh_buffer():
    """测试 TOKEN_REFRESH_BUFFER 提前刷新"""
    client = BooheeClient(
        app_id='test',
        app_key='key',
        private_key='pem'
    )
    # 设置一个即将过期的 token(在 buffer 内)
    client._access_token = 'expiring_token'
    client._token_expires_at = time.time() + 200  # 小于 300 秒 buffer

    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'now': 1722851989,
            'data': {
                'access_token': 'new_token',
                'expires_in': 86400
            }
        }
        mock_post.return_value = mock_response

        with patch('boohee_sdk.client.rsa_sign', return_value='sig'):
            token = client._get_access_token()
            assert token == 'new_token'
            assert mock_post.called


def test_token_refresh_error():
    """测试 Token 刷新失败(通过 code 判断)"""
    from boohee_sdk.exceptions import AuthenticationError

    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )

    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200  # HTTP 200
        mock_response.json.return_value = {
            'code': 401,
            'message': 'invalid signature',
            'now': 1722851989
        }
        mock_post.return_value = mock_response

        with patch('boohee_sdk.client.rsa_sign', return_value='sig'):
            with pytest.raises(AuthenticationError) as exc_info:
                client._refresh_access_token()

            assert 'code=401' in str(exc_info.value)
            assert 'invalid signature' in str(exc_info.value)


def test_token_refresh_success():
    """测试 Token 刷新成功"""
    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )

    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'now': 1722851989,
            'data': {
                'access_token': 'new_token',
                'expires_in': 86400
            }
        }
        mock_post.return_value = mock_response

        with patch('boohee_sdk.client.rsa_sign', return_value='sig'):
            client._refresh_access_token()

            assert client._access_token == 'new_token'
            assert client._token_expires_at > 0


def test_fetch_access_token_returns_raw_data():
    """测试 fetch_access_token 返回原始数据"""
    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )

    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'data': {
                'access_token': 'raw_token',
                'expires_in': 7200
            }
        }
        mock_post.return_value = mock_response

        with patch('boohee_sdk.client.rsa_sign', return_value='sig'):
            result = client.fetch_access_token()

            assert result == {'access_token': 'raw_token', 'expires_in': 7200}


def test_fetch_access_token_does_not_update_internal_state():
    """测试 fetch_access_token 不更新内部缓存状态"""
    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )

    with patch('requests.Session.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'data': {
                'access_token': 'raw_token',
                'expires_in': 7200
            }
        }
        mock_post.return_value = mock_response

        with patch('boohee_sdk.client.rsa_sign', return_value='sig'):
            client.fetch_access_token()

            # 内部状态不应被更新
            assert client._access_token is None
            assert client._token_expires_at == 0


def test_execute_with_access_token():
    """测试 execute 传入 access_token 参数"""
    from boohee_sdk.request import BaseReq

    class TestReq(BaseReq):
        def get_url(self): return '/test'
        def get_method(self): return HttpMethod.GET

    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )

    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'code': 0, 'data': {}}
        mock_get.return_value = mock_response

        client.execute(TestReq(), access_token='manual_token')

        # 验证请求头使用了手动传入的 token
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]['headers']['Authorization'] == 'Bearer manual_token'


def test_execute_without_access_token_uses_internal():
    """测试 execute 不传 access_token 时走内部逻辑"""
    from boohee_sdk.request import BaseReq

    class TestReq(BaseReq):
        def get_url(self): return '/test'
        def get_method(self): return HttpMethod.GET

    client = BooheeClient(
        app_id='test_app',
        app_key='test_key',
        private_key='test_private_key'
    )
    client._access_token = 'internal_token'
    client._token_expires_at = time.time() + 3600

    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'code': 0, 'data': {}}
        mock_get.return_value = mock_response

        client.execute(TestReq())

        call_kwargs = mock_get.call_args
        assert call_kwargs[1]['headers']['Authorization'] == 'Bearer internal_token'


def test_fetch_access_token_rejects_api_key_mode():
    """测试 fetch_access_token 在 API Key 模式下抛出错误"""
    from boohee_sdk.exceptions import AuthenticationError

    client = BooheeClient(
        api_key='test_key',
        auth_mode=AuthMode.API_KEY
    )

    with pytest.raises(AuthenticationError, match="only available in ACCESS_TOKEN mode"):
        client.fetch_access_token()


def test_execute_stream():
    """测试 execute_stream SSE 流式请求"""
    from boohee_sdk.request import BaseReq

    class StreamReq(BaseReq):
        def get_url(self): return '/stream'
        def get_method(self): return HttpMethod.GET

    client = BooheeClient(
        api_key='test_key',
        auth_mode=AuthMode.API_KEY
    )

    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'id:1',
            'data:{"content": "hello"}',
            '',
            'id:2',
            'data:{"content": " world", "end": true}',
            '',
        ]
        mock_get.return_value = mock_response

        chunks = list(client.execute_stream(StreamReq()))

        assert len(chunks) == 2
        assert chunks[0] == '{"content": "hello"}'
        assert chunks[1] == '{"content": " world", "end": true}'
