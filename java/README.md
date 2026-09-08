# 薄荷科学.ai Java SDK

## 安装

从源码构建：

```bash
cd java && mvn package
```

然后在你的项目中引用生成的 jar 包，或直接拷贝 `src/main/java/com/boohee/ai` 到你的项目中。

Maven 依赖（发布后可用）：

```xml
<dependency>
    <groupId>com.boohee.ai</groupId>
    <artifactId>boohee-sdk</artifactId>
    <version>0.1.0</version>
</dependency>
```

## 快速开始

```java
import com.boohee.ai.*;

// 定义请求
class FoodSearchReq implements BaseReq {
    private String keyword;

    public FoodSearchReq(String keyword) {
        this.keyword = keyword;
    }

    @Override
    public HttpMethod getMethod() { return HttpMethod.GET; }

    @Override
    public String getUrl() { return "/open-apis/v1/food/search"; }

    @Override
    public Map<String, Object> getQueryParams() {
        return Map.of("keyword", keyword);
    }
}

// API Key 模式
BooheeClient client = BooheeClient.builder()
    .authMode(AuthMode.API_KEY)
    .apiKey("your_api_key")
    .build();

BaseResp resp = client.execute(new FoodSearchReq("apple"));

if (resp.isSuccess()) {
    System.out.println("Success: " + resp.getData());
} else {
    System.out.println("Error: " + resp.getMessage());
}
```

## Access Token 模式

```java
BooheeClient client = BooheeClient.builder()
    .appId("your_app_id")
    .appKey("your_app_key")
    .privateKey("-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----")
    .build();
```

## 自行管理 Token

```java
// 获取原始 token 数据
BooheeClient.TokenInfo tokenInfo = client.fetchAccessToken();
// tokenInfo.getAccessToken(), tokenInfo.getExpiresIn()

// 使用自行管理的 token
BaseResp resp = client.execute(req, tokenInfo.getAccessToken());
```

## 流式接口

```java
client.executeStream(req, chunk -> {
    System.out.println(chunk);
});
```

## Token 缓存

实现 `TokenCache` 接口自定义缓存策略：

```java
public interface TokenCache {
    String get(String appId);
    void set(String appId, String token, long expiresIn);
    void delete(String appId);
}
```

## 错误处理

```java
try {
    BaseResp resp = client.execute(req);
    resp.raiseForError(); // 失败抛出 ApiException
} catch (AuthenticationException e) {
    // 认证错误
} catch (ApiException e) {
    // API 业务错误
    System.out.printf("code=%d, message=%s%n", e.getCode(), e.getMessage());
} catch (NetworkException e) {
    // 网络错误
}
```

## 开发

```bash
mvn test
```
