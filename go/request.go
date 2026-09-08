package boohee

import (
	"net/http"
	"net/url"
)

// HttpMethod HTTP 方法
type HttpMethod string

const (
	MethodGet  HttpMethod = http.MethodGet
	MethodPost HttpMethod = http.MethodPost
)

// Request 请求接口
//
// 开发者实现此接口定义 API 请求，通过 Client.Execute(req) 统一执行。
type Request interface {
	// Method 返回 HTTP 方法
	Method() HttpMethod

	// URL 返回 API 路径，如 "/open-apis/v1/food/search"
	URL() string

	// QueryParams 返回查询参数（GET 请求使用），可为 nil
	QueryParams() url.Values

	// Body 返回请求体（POST 请求使用），可为 nil
	Body() any
}
