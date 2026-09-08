package boohee

import "fmt"

// AuthenticationError 认证错误（签名错误、token 无效等）
type AuthenticationError struct {
	Message string
}

func (e *AuthenticationError) Error() string {
	return fmt.Sprintf("authentication error: %s", e.Message)
}

// APIError API 返回业务错误
type APIError struct {
	Code    int
	Message string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("api error %d: %s", e.Code, e.Message)
}

// NetworkError 网络错误（超时、连接失败等）
type NetworkError struct {
	Message string
}

func (e *NetworkError) Error() string {
	return fmt.Sprintf("network error: %s", e.Message)
}
