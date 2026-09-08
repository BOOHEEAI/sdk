package boohee

import "encoding/json"

// Response API 响应
//
// 包装统一的响应结构: {code, message, now, data}
type Response struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Now     int64           `json:"now"`
	Data    json.RawMessage `json:"data"`
}

// IsSuccess 判断请求是否成功（code == 0）
func (r *Response) IsSuccess() bool {
	return r.Code == 0
}

// Err 如果不成功则返回 APIError
func (r *Response) Err() error {
	if r.IsSuccess() {
		return nil
	}
	return &APIError{Code: r.Code, Message: r.Message}
}

// UnwrapData 将 data 反序列化到目标对象
func (r *Response) UnwrapData(v any) error {
	if r.Data == nil {
		return nil
	}
	return json.Unmarshal(r.Data, v)
}
