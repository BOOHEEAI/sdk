"""核心客户端"""
import time
import threading
from typing import Optional, Dict, Any, Union
import requests

from .auth import AuthMode, rsa_sign, build_signature_string
from .cache import TokenCache
from .exceptions import AuthenticationError, APIError, NetworkError
from .request import BaseReq, HttpMethod
from .response import BaseResp


class BooheeClient:
    """薄荷开放平台客户端"""

    DEFAULT_BASE_URL = "https://api.boohee.com"
    DEFAULT_TIMEOUT = 30
    TOKEN_REFRESH_BUFFER = 300

    def __init__(
        self,
        # Access Token 模式参数
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        private_key: Optional[str] = None,
        # API Key 模式参数
        api_key: Optional[str] = None,
        # 通用配置
        auth_mode: AuthMode = AuthMode.ACCESS_TOKEN,
        base_url: str = DEFAULT_BASE_URL,
        cache: Optional[TokenCache] = None,
        timeout: Union[int, float] = DEFAULT_TIMEOUT
    ):
        """
        初始化客户端

        Args:
            app_id: 应用 ID(Access Token 模式必需)
            app_key: 应用密钥(Access Token 模式必需)
            private_key: RSA 私钥 PEM 格式(Access Token 模式必需)
            api_key: API Key(API Key 模式必需)
            auth_mode: 认证模式,默认 ACCESS_TOKEN
            base_url: API 基础 URL
            cache: Token 缓存实现(可选)
            timeout: 请求超时时间(秒)
        """
        self.auth_mode = auth_mode
        self.base_url = base_url.rstrip('/')
        self.cache = cache
        self.timeout: Union[int, float] = timeout
        self._session = requests.Session()

        # Access Token 模式
        if auth_mode == AuthMode.ACCESS_TOKEN:
            if not app_id:
                raise ValueError("app_id is required for ACCESS_TOKEN mode")
            if not app_key:
                raise ValueError("app_key is required for ACCESS_TOKEN mode")
            if not private_key:
                raise ValueError("private_key is required for ACCESS_TOKEN mode")

            self.app_id = app_id
            self.app_key = app_key
            self.private_key = private_key
            self.api_key = None

            # Token 管理
            self._access_token: Optional[str] = None
            self._token_expires_at: float = 0
            self._token_lock = threading.Lock()

        # API Key 模式
        elif auth_mode == AuthMode.API_KEY:
            if not api_key:
                raise ValueError("api_key is required for API_KEY mode")

            self.api_key = api_key
            self.app_id = None
            self.app_key = None
            self.private_key = None

        else:
            raise ValueError(f"Invalid auth_mode: {auth_mode}")

    def execute(self, req: BaseReq, access_token: Optional[str] = None) -> BaseResp:
        """
        执行 BaseReq 请求

        开发者实现 `BaseReq` 子类后,通过本方法统一发起调用。
        内部会根据 `req.get_method()` 选择 GET / POST,
        并分别传入 query params 与 JSON body。

        Args:
            req: BaseReq 实例
            access_token: 可选,开发者自行获取的 token,传入后直接使用,
                          不传则走内部自动缓存和刷新逻辑

        Returns:
            BaseResp 响应对象
        """
        method = req.get_method()
        path = req.get_url()
        params = req.get_query_params()
        data = req.get_body()

        raw_response = self._request(method, path, params=params, json_data=data, access_token=access_token)
        return BaseResp(raw_response)

    def execute_stream(self, req: BaseReq, access_token: Optional[str] = None):
        """
        执行 SSE 流式请求

        返回一个生成器,逐块 yield SSE data 内容(字符串)。
        遇到 `data: [DONE]` 或连接关闭时结束。

        Args:
            req: BaseReq 实例
            access_token: 可选,开发者自行获取的 token

        Yields:
            每个 SSE event 的 data 字段内容(字符串)
        """
        method = req.get_method()
        path = req.get_url()
        params = req.get_query_params()
        data = req.get_body()

        url = f"{self.base_url}{path}"
        headers = self._get_headers(access_token=access_token)
        headers['Accept'] = 'text/event-stream'

        try:
            response = self._send_request_stream(method, url, params, data, headers)
            response.encoding = 'utf-8'
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data:'):
                    continue
                # 标准 SSE: 去掉 "data:" 前缀和一个可选的前导空格
                payload = line[5:]
                if payload.startswith(' '):
                    payload = payload[1:]
                yield payload
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Stream request failed: {str(e)}")

    def _request(
        self,
        method: HttpMethod,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        注意: 此方法不检查业务错误(code != 0),由 BaseResp.raise_for_error() 处理
        """
        url = f"{self.base_url}{path}"
        headers = self._get_headers(access_token=access_token)

        try:
            response = self._send_request(method, url, params, json_data, headers)

            # 直接返回响应体,不检查 HTTP 状态码
            # 业务错误由 BaseResp.raise_for_error() 根据 code 字段判断
            try:
                return response.json()
            except ValueError:
                # 如果响应不是 JSON,返回原始文本
                return {'code': -1, 'message': response.text, 'data': None}

        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}")

    def _send_request(
        self,
        method: HttpMethod,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> requests.Response:
        """发送 HTTP 请求的辅助方法"""
        if method == HttpMethod.GET:
            return self._session.get(url, params=params, headers=headers, timeout=self.timeout)
        elif method == HttpMethod.POST:
            return self._session.post(url, json=json_data, headers=headers, timeout=self.timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _send_request_stream(
        self,
        method: HttpMethod,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> requests.Response:
        """发送流式 HTTP 请求"""
        if method == HttpMethod.GET:
            return self._session.get(url, params=params, headers=headers, timeout=self.timeout, stream=True)
        elif method == HttpMethod.POST:
            return self._session.post(url, json=json_data, headers=headers, timeout=self.timeout, stream=True)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """
        获取请求头

        Args:
            access_token: 可选,开发者手动传入的 token,优先使用

        Returns:
            包含认证信息的请求头
        """
        headers: Dict[str, str] = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.auth_mode == AuthMode.ACCESS_TOKEN:
            token = access_token or self._get_access_token()
            headers['Authorization'] = f'Bearer {token}'
        elif self.auth_mode == AuthMode.API_KEY:
            headers['X-Api-Key'] = self.api_key

        return headers

    def fetch_access_token(self) -> Dict[str, Any]:
        """
        从服务端获取 access_token,返回原始数据

        底层接口,不做任何缓存。开发者可根据返回的 expires_in 自行实现缓存策略。
        仅在 ACCESS_TOKEN 模式下可用。

        Returns:
            包含 access_token 和 expires_in 的字典

        Raises:
            AuthenticationError: 获取失败时抛出
        """
        if self.auth_mode != AuthMode.ACCESS_TOKEN:
            raise AuthenticationError("fetch_access_token is only available in ACCESS_TOKEN mode")

        timestamp = int(time.time())
        signature_str = build_signature_string(self.app_id, self.app_key, timestamp)
        sign = rsa_sign(signature_str, self.private_key)

        payload = {
            'app_id': self.app_id,
            'timestamp': timestamp,
            'sign': sign
        }

        try:
            response = self._session.post(
                f"{self.base_url}/open-apis/v1/access_token",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )

            try:
                data = response.json()
            except ValueError:
                raise AuthenticationError(f"Invalid response format: {response.text}")

            code = data.get('code', -1)
            if code != 0:
                message = data.get('message', 'Unknown error')
                raise AuthenticationError(f"Failed to get access_token: code={code}, message={message}")

            return {
                'access_token': data['data']['access_token'],
                'expires_in': data['data']['expires_in']
            }

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    def _get_access_token(self) -> str:
        """
        获取 access_token(自动缓存和刷新)

        Returns:
            access_token 字符串
        """
        # 检查是否已缓存且未过期
        if self._access_token and time.time() < self._token_expires_at - self.TOKEN_REFRESH_BUFFER:
            return self._access_token

        # 尝试从缓存获取
        if self.cache:
            cached_token = self.cache.get(self.app_id)
            if cached_token:
                self._access_token = cached_token
                # 保守假设:cache 返回的 token 可能在 10 分钟内过期
                # 下次调用时会触发 API 刷新
                self._token_expires_at = time.time() + 600
                return self._access_token

        # 刷新 token
        with self._token_lock:
            # 双重检查,防止并发刷新
            if self._access_token and time.time() < self._token_expires_at - self.TOKEN_REFRESH_BUFFER:
                return self._access_token

            self._refresh_access_token()
            return self._access_token

    def _refresh_access_token(self):
        """
        调用 API 刷新 access_token(内部使用)

        实际调用 fetch_access_token 获取数据并更新内部缓存。
        """
        data = self.fetch_access_token()
        self._access_token = data['access_token']
        self._token_expires_at = time.time() + data['expires_in']
        if self.cache:
            self.cache.set(self.app_id, self._access_token, data['expires_in'])
