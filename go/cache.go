package boohee

// TokenCache Token 缓存接口
//
// 开发者可以实现此接口自定义 token 存储方式
type TokenCache interface {
	Get(appID string) (string, bool)
	Set(appID, token string, expiresIn int64)
	Delete(appID string)
}
