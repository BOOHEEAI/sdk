# 薄荷科学.ai Node.js SDK

## 安装

```bash
# 从源码安装
cd nodejs && npm install
```

要求 Node.js >= 18.0.0

## 快速开始

```typescript
import { BooheeClient, AuthMode, HttpMethod, Request } from './nodejs/src';

// 定义请求
class FoodSearchReq implements Request {
  private keyword: string;

  constructor(keyword: string) {
    this.keyword = keyword;
  }

  getMethod() { return HttpMethod.GET; }
  getUrl() { return '/open-apis/v1/food/search'; }
  getQueryParams() { return { keyword: this.keyword }; }
}

// API Key 模式
const client = new BooheeClient({
  authMode: AuthMode.API_KEY,
  apiKey: 'your_api_key',
});

const resp = await client.execute(new FoodSearchReq('apple'));

if (resp.isSuccess()) {
  console.log('Success:', resp.data);
} else {
  console.log('Error:', resp.message);
}
```

## Access Token 模式

```typescript
const client = new BooheeClient({
  appId: 'your_app_id',
  appKey: 'your_app_key',
  privateKey: '-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----',
});
```

## 自行管理 Token

```typescript
// 获取原始 token 数据
const tokenInfo = await client.fetchAccessToken();
// tokenInfo.accessToken, tokenInfo.expiresIn

// 使用自行管理的 token
const resp = await client.execute(req, { accessToken: tokenInfo.accessToken });
```

## 流式接口

```typescript
for await (const chunk of client.executeStream(req)) {
  console.log(chunk);
}
```

## Token 缓存

实现 `TokenCache` 接口自定义缓存策略：

```typescript
interface TokenCache {
  get(appId: string): string | null;
  set(appId: string, token: string, expiresIn: number): void;
  delete(appId: string): void;
}
```

## 错误处理

```typescript
import { AuthenticationError, ApiError, NetworkError } from '@boohee/sdk';

try {
  const resp = await client.execute(req);
  resp.raiseForError(); // 失败抛出 ApiError
} catch (e) {
  if (e instanceof AuthenticationError) {
    // 认证错误
  } else if (e instanceof ApiError) {
    // API 业务错误
    console.log(`code=${e.code}, message=${e.message}`);
  } else if (e instanceof NetworkError) {
    // 网络错误
  }
}
```

## 开发

```bash
npm install
npm run build
npm test
```
