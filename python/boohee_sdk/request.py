"""请求接口定义"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any


class HttpMethod(str, Enum):
    """HTTP 方法"""
    GET = 'GET'
    POST = 'POST'


class BaseReq(ABC):
    """
    请求基类

    开发者实现此类来定义 API 请求,通过 get_method / get_url /
    get_query_params / get_body 四个方法来描述一次 HTTP 调用,
    然后交给 `BooheeClient.execute(req)` 统一执行。
    """

    @abstractmethod
    def get_method(self) -> HttpMethod:
        """
        获取 HTTP 方法

        Returns:
            HttpMethod.GET 或 HttpMethod.POST
        """
        pass

    @abstractmethod
    def get_url(self) -> str:
        """
        获取 API 路径

        Returns:
            API 路径,如 '/open-apis/v1/food/search'
        """
        pass

    def get_query_params(self) -> Optional[Dict[str, Any]]:
        """
        获取查询参数(GET 请求使用)

        Returns:
            查询参数字典,默认为 None
        """
        return None

    def get_body(self) -> Optional[Dict[str, Any]]:
        """
        获取请求体(POST 请求使用)

        Returns:
            请求体字典,默认为 None
        """
        return None


__all__ = ['HttpMethod', 'BaseReq']
