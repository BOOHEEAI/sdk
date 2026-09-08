package boohee

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

const (
	defaultBaseURL        = "https://api.boohee.com"
	defaultTimeout        = 30 * time.Second
	tokenRefreshBuffer    = 300 * time.Second
	accessTokenEndpoint   = "/open-apis/v1/access_token"
)

// ClientConfig 客户端配置
type ClientConfig struct {
	// Access Token 模式
	AppID      string
	AppKey     string
	PrivateKey string

	// API Key 模式
	APIKey string

	// 通用配置
	AuthMode AuthMode
	BaseURL  string
	Cache    TokenCache
	Timeout  time.Duration
}

// TokenInfo access_token 原始数据
type TokenInfo struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int64  `json:"expires_in"`
}

// Client 薄荷开放平台客户端
type Client struct {
	authMode   AuthMode
	baseURL    string
	cache      TokenCache
	timeout    time.Duration
	httpClient *http.Client

	// Access Token 模式
	appID      string
	appKey     string
	privateKey string

	// API Key 模式
	apiKey string

	// Token 管理
	accessToken    string
	tokenExpiresAt time.Time
	tokenMu        sync.Mutex
}

// NewClient 创建客户端
func NewClient(cfg ClientConfig) (*Client, error) {
	if cfg.AuthMode == "" {
		cfg.AuthMode = AuthModeAccessToken
	}
	if cfg.BaseURL == "" {
		cfg.BaseURL = defaultBaseURL
	}
	if cfg.Timeout == 0 {
		cfg.Timeout = defaultTimeout
	}

	c := &Client{
		authMode:   cfg.AuthMode,
		baseURL:    strings.TrimRight(cfg.BaseURL, "/"),
		cache:      cfg.Cache,
		timeout:    cfg.Timeout,
		httpClient: &http.Client{Timeout: cfg.Timeout},
	}

	switch cfg.AuthMode {
	case AuthModeAccessToken:
		if cfg.AppID == "" {
			return nil, fmt.Errorf("app_id is required for ACCESS_TOKEN mode")
		}
		if cfg.AppKey == "" {
			return nil, fmt.Errorf("app_key is required for ACCESS_TOKEN mode")
		}
		if cfg.PrivateKey == "" {
			return nil, fmt.Errorf("private_key is required for ACCESS_TOKEN mode")
		}
		c.appID = cfg.AppID
		c.appKey = cfg.AppKey
		c.privateKey = cfg.PrivateKey

	case AuthModeAPIKey:
		if cfg.APIKey == "" {
			return nil, fmt.Errorf("api_key is required for API_KEY mode")
		}
		c.apiKey = cfg.APIKey

	default:
		return nil, fmt.Errorf("invalid auth_mode: %s", cfg.AuthMode)
	}

	return c, nil
}

// ExecuteOption Execute 的可选参数
type ExecuteOption func(*executeOptions)

type executeOptions struct {
	accessToken string
}

// WithAccessToken 开发者自行获取的 token，传入后直接使用
func WithAccessToken(token string) ExecuteOption {
	return func(o *executeOptions) {
		o.accessToken = token
	}
}

// Execute 执行请求
//
// 开发者实现 Request 接口后，通过本方法统一发起调用。
// 可通过 WithAccessToken("xxx") 传入自行管理的 token，不传则走内部自动缓存和刷新逻辑。
func (c *Client) Execute(req Request, opts ...ExecuteOption) (*Response, error) {
	var options executeOptions
	for _, opt := range opts {
		opt(&options)
	}

	rawResp, err := c.doRequest(req.Method(), req.URL(), req.QueryParams(), req.Body(), options.accessToken)
	if err != nil {
		return nil, err
	}
	return rawResp, nil
}

// ExecuteStream 执行 SSE 流式请求
//
// 逐行读取 SSE 响应，对每个 data 行调用 onEvent 回调。
// onEvent 收到的 data 是去掉 "data:" 前缀后的原始内容。
// 连接关闭时自动结束。
func (c *Client) ExecuteStream(req Request, onEvent func(data string), opts ...ExecuteOption) error {
	var options executeOptions
	for _, opt := range opts {
		opt(&options)
	}

	u := c.baseURL + req.URL()
	headers := c.getHeaders(options.accessToken)
	headers["Accept"] = "text/event-stream"

	var bodyReader io.Reader
	if req.Body() != nil {
		b, err := json.Marshal(req.Body())
		if err != nil {
			return fmt.Errorf("failed to marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	httpReq, err := http.NewRequest(string(req.Method()), u, bodyReader)
	if err != nil {
		return &NetworkError{Message: fmt.Sprintf("failed to create request: %v", err)}
	}
	for k, v := range headers {
		httpReq.Header.Set(k, v)
	}
	if req.Method() == MethodGet && req.QueryParams() != nil {
		httpReq.URL.RawQuery = req.QueryParams().Encode()
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return &NetworkError{Message: fmt.Sprintf("stream request failed: %v", err)}
	}
	defer resp.Body.Close()

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" || !strings.HasPrefix(line, "data:") {
			continue
		}
		payload := line[5:]
		if strings.HasPrefix(payload, " ") {
			payload = payload[1:]
		}
		onEvent(payload)
	}
	if err := scanner.Err(); err != nil {
		return &NetworkError{Message: fmt.Sprintf("stream read error: %v", err)}
	}
	return nil
}

// FetchAccessToken 从服务端获取 access_token，返回原始数据
//
// 底层接口，不做任何缓存。开发者可根据 ExpiresIn 自行实现缓存策略。
// 仅在 AuthModeAccessToken 模式下可用。
func (c *Client) FetchAccessToken() (*TokenInfo, error) {
	if c.authMode != AuthModeAccessToken {
		return nil, &AuthenticationError{Message: "FetchAccessToken is only available in ACCESS_TOKEN mode"}
	}

	timestamp := time.Now().Unix()
	sigStr := BuildSignatureString(c.appID, c.appKey, timestamp)
	sign, err := RSASign(sigStr, c.privateKey)
	if err != nil {
		return nil, &AuthenticationError{Message: fmt.Sprintf("failed to sign: %v", err)}
	}

	payload := map[string]any{
		"app_id":    c.appID,
		"timestamp": timestamp,
		"sign":      sign,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, &AuthenticationError{Message: fmt.Sprintf("failed to marshal payload: %v", err)}
	}

	httpReq, err := http.NewRequest(http.MethodPost, c.baseURL+accessTokenEndpoint, bytes.NewReader(body))
	if err != nil {
		return nil, &AuthenticationError{Message: fmt.Sprintf("failed to create request: %v", err)}
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, &AuthenticationError{Message: fmt.Sprintf("token request failed: %v", err)}
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, &AuthenticationError{Message: fmt.Sprintf("failed to read response: %v", err)}
	}

	var result struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    struct {
			AccessToken string `json:"access_token"`
			ExpiresIn   int64  `json:"expires_in"`
		} `json:"data"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, &AuthenticationError{Message: fmt.Sprintf("invalid response format: %v", err)}
	}

	if result.Code != 0 {
		return nil, &AuthenticationError{Message: fmt.Sprintf("failed to get access_token: code=%d, message=%s", result.Code, result.Message)}
	}

	return &TokenInfo{
		AccessToken: result.Data.AccessToken,
		ExpiresIn:   result.Data.ExpiresIn,
	}, nil
}

// doRequest 发送 HTTP 请求
func (c *Client) doRequest(method HttpMethod, path string, params url.Values, body any, accessToken string) (*Response, error) {
	u := c.baseURL + path

	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	httpReq, err := http.NewRequest(string(method), u, bodyReader)
	if err != nil {
		return nil, &NetworkError{Message: fmt.Sprintf("failed to create request: %v", err)}
	}

	headers := c.getHeaders(accessToken)
	for k, v := range headers {
		httpReq.Header.Set(k, v)
	}

	if method == MethodGet && params != nil {
		httpReq.URL.RawQuery = params.Encode()
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, &NetworkError{Message: fmt.Sprintf("request failed: %v", err)}
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, &NetworkError{Message: fmt.Sprintf("failed to read response: %v", err)}
	}

	var result Response
	if err := json.Unmarshal(respBody, &result); err != nil {
		result = Response{
			Code:    -1,
			Message: string(respBody),
		}
	}

	return &result, nil
}

// getHeaders 构造请求头
func (c *Client) getHeaders(accessToken string) map[string]string {
	headers := map[string]string{
		"Content-Type": "application/json",
		"Accept":       "application/json",
	}

	switch c.authMode {
	case AuthModeAccessToken:
		token := accessToken
		if token == "" {
			token, _ = c.getAccessToken()
		}
		headers["Authorization"] = "Bearer " + token
	case AuthModeAPIKey:
		headers["X-Api-Key"] = c.apiKey
	}

	return headers
}

// getAccessToken 获取 access_token（自动缓存和刷新）
func (c *Client) getAccessToken() (string, error) {
	now := time.Now()

	// 检查内存缓存
	if c.accessToken != "" && now.Before(c.tokenExpiresAt.Add(-tokenRefreshBuffer)) {
		return c.accessToken, nil
	}

	// 尝试从外部缓存获取
	if c.cache != nil {
		if token, ok := c.cache.Get(c.appID); ok {
			c.accessToken = token
			c.tokenExpiresAt = now.Add(10 * time.Minute)
			return c.accessToken, nil
		}
	}

	// 加锁刷新
	c.tokenMu.Lock()
	defer c.tokenMu.Unlock()

	// 双重检查
	if c.accessToken != "" && time.Now().Before(c.tokenExpiresAt.Add(-tokenRefreshBuffer)) {
		return c.accessToken, nil
	}

	return c.refreshAccessToken()
}

// refreshAccessToken 调用 API 刷新 access_token
func (c *Client) refreshAccessToken() (string, error) {
	info, err := c.FetchAccessToken()
	if err != nil {
		return "", err
	}

	c.accessToken = info.AccessToken
	c.tokenExpiresAt = time.Now().Add(time.Duration(info.ExpiresIn) * time.Second)

	if c.cache != nil {
		c.cache.Set(c.appID, c.accessToken, info.ExpiresIn)
	}

	return c.accessToken, nil
}
