# 薄荷科学.ai Go SDK

## 安装

```bash
go get github.com/BOOHEEAI/sdk/go
```

## 快速开始

```go
package main

import (
    "fmt"
    "net/url"
    boohee "github.com/BOOHEEAI/sdk/go"
)

// 定义请求
type FoodSearchReq struct {
    Keyword string
}

func (r *FoodSearchReq) Method() boohee.HttpMethod { return boohee.MethodGet }
func (r *FoodSearchReq) URL() string               { return "/open-apis/v1/food/search" }
func (r *FoodSearchReq) QueryParams() url.Values {
    return url.Values{"keyword": {r.Keyword}}
}
func (r *FoodSearchReq) Body() any { return nil }

func main() {
    // API Key 模式
    client, err := boohee.NewClient(boohee.ClientConfig{
        AuthMode: boohee.AuthModeAPIKey,
        APIKey:   "your_api_key",
    })
    if err != nil {
        panic(err)
    }

    resp, err := client.Execute(&FoodSearchReq{Keyword: "apple"})
    if err != nil {
        panic(err)
    }

    if resp.IsSuccess() {
        fmt.Println("Success:", resp.Data)
    } else {
        fmt.Println("Error:", resp.Err())
    }
}
```

## Access Token 模式

```go
client, err := boohee.NewClient(boohee.ClientConfig{
    AppID:      "your_app_id",
    AppKey:     "your_app_key",
    PrivateKey: "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
})
```

## 自行管理 Token

```go
// 获取原始 token 数据
tokenInfo, err := client.FetchAccessToken()
// tokenInfo.AccessToken, tokenInfo.ExpiresIn

// 使用自行管理的 token
resp, err := client.Execute(req, boohee.WithAccessToken(tokenInfo.AccessToken))
```

## 流式接口

```go
// 回调方式
err := client.ExecuteStream(req, func(data string) {
    fmt.Println(data)
})
```

## Token 缓存

实现 `TokenCache` 接口自定义缓存策略：

```go
type TokenCache interface {
    Get(appID string) (string, bool)
    Set(appID, token string, expiresIn int64)
    Delete(appID string)
}
```

## 错误处理

```go
resp, err := client.Execute(req)
if err != nil {
    switch e := err.(type) {
    case *boohee.AuthenticationError:
        // 认证错误
    case *boohee.NetworkError:
        // 网络错误
    }
}

// 检查业务错误
if !resp.IsSuccess() {
    apiErr := resp.Err().(*boohee.APIError)
    fmt.Printf("code=%d, message=%s\n", apiErr.Code, apiErr.Message)
}
```

## 开发

```bash
go test ./... -v
```
