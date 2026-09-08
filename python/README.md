# 薄荷科学.ai Python SDK

## 安装

```bash
# 从源码安装
pip install -e .

# 或安装依赖后直接引用
pip install pycryptodome requests
```

然后在代码中引用：

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'path/to/sdk/python'))
from boohee_sdk import BooheeClient
```

## 快速开始

SDK 采用 `BaseReq` 接口模式:开发者通过继承 `BaseReq` 描述一次 API 调用
(URL、HTTP 方法、query / body),再交给 `BooheeClient.execute(req)` 统一执行。

### API Key 模式

```python
from typing import Dict, Any
from boohee_sdk import BooheeClient, AuthMode, BaseReq, HttpMethod

# 1. 定义请求类
class FoodSearchReq(BaseReq):
    def __init__(self, keyword: str, page: int = 1):
        self.keyword = keyword
        self.page = page

    def get_method(self) -> HttpMethod:
        return HttpMethod.GET

    def get_url(self) -> str:
        return '/open-apis/v1/food/search'

    def get_query_params(self) -> Dict[str, Any]:
        return {'keyword': self.keyword, 'page': self.page}

# 2. 初始化客户端
client = BooheeClient(
    api_key='your_api_key',
    auth_mode=AuthMode.API_KEY
)

# 3. 执行请求
req = FoodSearchReq('apple', page=1)
resp = client.execute(req)

# 检查是否成功
if resp.is_success():
    # 访问 data 字段
    foods = resp.data.get('foods', [])
    for food in foods:
        print(food['name'])
else:
    print(f"Error: {resp.message}")

# 或者使用 raise_for_error(失败会抛出 APIError)
resp.raise_for_error()
foods = resp.data.get('foods', [])
```

### Access Token 模式

```python
from boohee_sdk import BooheeClient, BaseReq

client = BooheeClient(
    app_id='your_app_id',
    app_key='your_app_key',
    private_key=open('private.pem').read()
)

# 复用上面的 FoodSearchReq
resp = client.execute(FoodSearchReq('apple'))
if resp.is_success():
    print(resp.data)
```

### `BaseReq` 接口

```python
class BaseReq(ABC):
    def get_method(self) -> HttpMethod:      # 必需:HttpMethod.GET 或 HttpMethod.POST
    def get_url(self) -> str:               # 必需:API 路径
    def get_query_params(self) -> Optional[Dict[str, Any]]:  # 可选,默认 None
    def get_body(self) -> Optional[Dict[str, Any]]:          # 可选,默认 None
```

只需继承并实现 `get_method` / `get_url`,其余按需重写。

### Token 缓存

```python
import redis
from boohee_sdk import BooheeClient

class RedisTokenCache:
    def __init__(self, redis_client):
        self.redis = redis_client

    def get(self, app_id):
        return self.redis.get(f"boohee:token:{app_id}")

    def set(self, app_id, token, expires_in):
        self.redis.setex(f"boohee:token:{app_id}", expires_in, token)

    def delete(self, app_id):
        self.redis.delete(f"boohee:token:{app_id}")

redis_client = redis.Redis(host='localhost', port=6379)
cache = RedisTokenCache(redis_client)

client = BooheeClient(
    app_id='your_app_id',
    app_key='your_app_key',
    private_key=open('private.pem').read(),
    cache=cache
)
```

## API 端点参考

过去 SDK 通过 `boohee_sdk.endpoints` 导出 63 个端点常量;自 v0.2.0 起,
端点常量已移至 `examples/endpoints_example.py` 作为参考清单,
建议直接在 `BaseReq.get_url()` 中写回需要的路径。

## 错误处理

SDK 提供两种错误处理方式:

### 1. 使用 `BaseResp.raise_for_error()`

```python
resp = client.execute(FoodSearchReq('apple'))
try:
    resp.raise_for_error()  # 如果 code != 0,抛出 APIError
    # 处理 resp.data ...
except APIError as e:
    print(f"API 错误 {e.code}: {e.message}")
```

### 2. 捕获网络/认证异常

```python
from boohee_sdk.exceptions import AuthenticationError, APIError, NetworkError

try:
    resp = client.execute(FoodSearchReq('apple'))
    resp.raise_for_error()
except AuthenticationError as e:
    print(f"认证失败: {e}")
except APIError as e:
    print(f"API 错误 {e.code}: {e.message}")
except NetworkError as e:
    print(f"网络错误: {e}")
```

## 开发

```bash
# 安装开发依赖
pip install -e .
pip install pytest

# 运行测试
pytest tests/ -v
```

## License

MIT
