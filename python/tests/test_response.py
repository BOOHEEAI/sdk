"""BaseResp 响应包装类测试"""
from boohee_sdk.response import BaseResp
from boohee_sdk.exceptions import APIError


def test_base_resp_success():
    """测试成功响应"""
    raw = {
        'code': 0,
        'message': '成功',
        'now': 1722851989,
        'data': {
            'items': [{'date': '2024-01-01', 'value': 65.5}],
            'has_more': False
        }
    }

    resp = BaseResp(raw)
    assert resp.code == 0
    assert resp.message == '成功'
    assert resp.now == 1722851989
    assert resp.is_success() is True
    assert resp.data == {'items': [{'date': '2024-01-01', 'value': 65.5}], 'has_more': False}


def test_base_resp_error():
    """测试错误响应"""
    raw = {
        'code': 401,
        'message': 'invalid access_token',
        'now': 1722851989,
        'data': None
    }

    resp = BaseResp(raw)
    assert resp.code == 401
    assert resp.message == 'invalid access_token'
    assert resp.is_success() is False
    assert resp.data is None


def test_base_resp_raise_for_error():
    """测试 raise_for_error"""
    raw = {
        'code': 400,
        'message': 'invalid params',
        'now': 1722851989,
        'data': None
    }

    resp = BaseResp(raw)

    import pytest
    with pytest.raises(APIError) as exc_info:
        resp.raise_for_error()

    assert exc_info.value.code == 400
    assert exc_info.value.message == 'invalid params'


def test_base_resp_get():
    """测试 get 方法从 data 获取字段"""
    raw = {
        'code': 0,
        'message': '成功',
        'now': 1722851989,
        'data': {
            'items': [1, 2, 3],
            'total': 100
        }
    }

    resp = BaseResp(raw)
    assert resp.get('items') == [1, 2, 3]
    assert resp.get('total') == 100
    assert resp.get('not_exist', 'default') == 'default'


def test_base_resp_get_with_none_data():
    """测试 data 为 None 时的 get"""
    raw = {
        'code': 0,
        'message': '成功',
        'now': 1722851989,
        'data': None
    }

    resp = BaseResp(raw)
    assert resp.get('anything', 'default') == 'default'


def test_client_execute_returns_base_resp():
    """测试 execute 返回 BaseResp"""
    from unittest.mock import Mock, patch
    from boohee_sdk import BooheeClient, AuthMode, BaseReq

    class TestReq(BaseReq):
        def get_method(self):
            return 'GET'

        def get_url(self):
            return '/test'

    client = BooheeClient(api_key='test_key', auth_mode=AuthMode.API_KEY)

    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'message': '成功',
            'now': 1722851989,
            'data': {'result': 'test'}
        }
        mock_get.return_value = mock_response

        resp = client.execute(TestReq())

        assert isinstance(resp, BaseResp)
        assert resp.code == 0
        assert resp.is_success() is True
        assert resp.data == {'result': 'test'}
