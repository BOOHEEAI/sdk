# 薄荷科学.ai SDK

薄荷科学.ai 多语言 SDK，提供统一的 API 调用接口。

官方网站：https://ai.boohee.com/

## 支持语言

| 语言 | 目录 | 包名 | 最低版本 |
|------|------|------|----------|
| Python | [python/](./python) | `boohee-sdk` (PyPI) | Python 3.7+ |
| Go | [go/](./go) | `github.com/BOOHEEAI/sdk/go` | Go 1.18+ |
| Java | [java/](./java) | `com.boohee.ai:boohee-sdk` (Maven) | Java 8+ |
| Node.js | [nodejs/](./nodejs) | `@boohee/sdk` (npm) | Node 18+ |

## 安装

各语言的安装与使用方式，请参阅对应目录下的 README：

- [Python SDK](./python/README.md)
- [Go SDK](./go/README.md)
- [Java SDK](./java/README.md)
- [Node.js SDK](./nodejs/README.md)

## 认证模式

SDK 支持两种认证模式：

### API Key 模式

适用于服务端调用，使用 API Key 进行认证。

### Access Token 模式

适用于需要用户授权的场景，使用 RSA 签名获取 Access Token。

## 使用示例

### Python

```python
from boohee_sdk import BooheeClient, AuthMode, BaseReq

class FoodSearchReq(BaseReq):
    def get_method(self): return 'GET'
    def get_url(self): return '/open-apis/v1/food/search'
    def get_query_params(self): return {'keyword': 'apple'}

client = BooheeClient(api_key='your_api_key', auth_mode=AuthMode.API_KEY)
resp = client.execute(FoodSearchReq())

if resp.is_success():
    print(resp.data)
```

### Go

```go
import (
    "fmt"
    "net/url"

    boohee "github.com/BOOHEEAI/sdk/go"
)

type FoodSearchReq struct{}

func (r *FoodSearchReq) Method() boohee.HttpMethod {
    return boohee.MethodGet
}

func (r *FoodSearchReq) URL() string {
    return "/open-apis/v1/food/search"
}

func (r *FoodSearchReq) QueryParams() url.Values {
    return url.Values{"keyword": {"apple"}}
}

func (r *FoodSearchReq) Body() any {
    return nil
}

client, _ := boohee.NewClient(boohee.ClientConfig{
    AuthMode: boohee.AuthModeAPIKey,
    APIKey:   "your_api_key",
})
resp, _ := client.Execute(&FoodSearchReq{})

if resp.IsSuccess() {
    fmt.Println(resp.Data)
}
```

### Java

```java
import com.boohee.ai.*;

BooheeClient client = BooheeClient.builder()
    .authMode(AuthMode.API_KEY)
    .apiKey("your_api_key")
    .build();

BaseResp resp = client.execute(new BaseReq() {
    public HttpMethod getMethod() { return HttpMethod.GET; }
    public String getUrl() { return "/open-apis/v1/food/search"; }
    public Map<String, Object> getQueryParams() {
        return Map.of("keyword", "apple");
    }
});

if (resp.isSuccess()) {
    System.out.println(resp.getData());
}
```

### Node.js

```typescript
import { BooheeClient, AuthMode, HttpMethod, Request } from '@boohee/sdk';

class FoodSearchReq implements Request {
  getMethod() { return HttpMethod.GET; }
  getUrl() { return '/open-apis/v1/food/search'; }
  getQueryParams() { return { keyword: 'apple' }; }
}

const client = new BooheeClient({
  authMode: AuthMode.API_KEY,
  apiKey: 'your_api_key',
});

const resp = await client.execute(new FoodSearchReq());
if (resp.isSuccess()) {
  console.log(resp.data);
}
```

## 流式接口

所有 SDK 均支持 SSE 流式接口：

```python
# Python
for chunk in client.execute_stream(req):
    print(chunk)
```

```go
// Go
client.ExecuteStream(req, func(data string) {
    fmt.Println(data)
})
```

```java
// Java
client.executeStream(req, chunk -> {
    System.out.println(chunk);
});
```

```typescript
// Node.js
for await (const chunk of client.executeStream(req)) {
    console.log(chunk);
}
```

## 开发

各语言的详细文档和开发指南请参阅对应目录下的 README。

```bash
# Python
cd python && pip install -e . && pytest tests/ -v

# Go
cd go && go test ./... -v

# Java
cd java && mvn test

# Node.js
cd nodejs && npm install && npm test
```

## License

MIT
