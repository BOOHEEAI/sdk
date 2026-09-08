package boohee_test

import (
	"fmt"
	"net/url"

	boohee "github.com/BOOHEEAI/sdk/go"
)

// ===== 定义请求类 =====

// FoodSearchReq 搜索食物（GET 请求示例）
type FoodSearchReq struct {
	Keyword string
	Page    int
}

func (r *FoodSearchReq) Method() boohee.HttpMethod { return boohee.MethodGet }
func (r *FoodSearchReq) URL() string               { return "/open-apis/v1/food/search" }
func (r *FoodSearchReq) QueryParams() url.Values {
	return url.Values{
		"keyword": {r.Keyword},
		"page":    {fmt.Sprintf("%d", r.Page)},
	}
}
func (r *FoodSearchReq) Body() any { return nil }

// ===== 使用示例 =====

func Example_apiKeyMode() {
	client, err := boohee.NewClient(boohee.ClientConfig{
		AuthMode: boohee.AuthModeAPIKey,
		APIKey:   "your_api_key_here",
	})
	if err != nil {
		panic(err)
	}

	// GET 请求
	resp, err := client.Execute(&FoodSearchReq{Keyword: "apple", Page: 1})
	if err != nil {
		panic(err)
	}
	if !resp.IsSuccess() {
		panic(resp.Err())
	}

	// 解析 data
	var data map[string]any
	_ = resp.UnwrapData(&data)
	fmt.Println("foods:", data)
}

func Example_accessTokenMode() {
	privateKey := `-----BEGIN RSA PRIVATE KEY-----
...your private key...
-----END RSA PRIVATE KEY-----`

	client, err := boohee.NewClient(boohee.ClientConfig{
		AppID:      "your_app_id",
		AppKey:     "your_app_key",
		PrivateKey: privateKey,
	})
	if err != nil {
		panic(err)
	}

	resp, err := client.Execute(&FoodSearchReq{Keyword: "banana"})
	if err != nil {
		panic(err)
	}
	_ = resp
}

func Example_selfManagedToken() {
	client, err := boohee.NewClient(boohee.ClientConfig{
		AppID:      "your_app_id",
		AppKey:     "your_app_key",
		PrivateKey: "...",
	})
	if err != nil {
		panic(err)
	}

	// 开发者自行获取和缓存 token
	tokenInfo, err := client.FetchAccessToken()
	if err != nil {
		panic(err)
	}
	// 自行缓存 tokenInfo.AccessToken, 过期时间 tokenInfo.ExpiresIn

	// 使用自行管理的 token 发起请求
	resp, err := client.Execute(
		&FoodSearchReq{Keyword: "apple"},
		boohee.WithAccessToken(tokenInfo.AccessToken),
	)
	if err != nil {
		panic(err)
	}
	_ = resp
}
