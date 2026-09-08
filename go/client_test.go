package boohee

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"
)

// ===== 测试辅助 =====

func generateTestKey(t *testing.T) string {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("failed to generate key: %v", err)
	}
	return string(pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(key),
	}))
}

func newTestClient(t *testing.T, serverURL string) *Client {
	t.Helper()
	c, err := NewClient(ClientConfig{
		AppID:      "test_app",
		AppKey:     "test_key",
		PrivateKey: generateTestKey(t),
		BaseURL:    serverURL,
	})
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}
	return c
}

type testGetReq struct {
	keyword string
	page    int
}

func (r *testGetReq) Method() HttpMethod      { return MethodGet }
func (r *testGetReq) URL() string              { return "/open-apis/v1/food/search" }
func (r *testGetReq) QueryParams() url.Values   { return url.Values{"keyword": {r.keyword}, "page": {string(rune('0' + r.page))}} }
func (r *testGetReq) Body() any                 { return nil }

type testPostReq struct {
	weight float64
}

func (r *testPostReq) Method() HttpMethod     { return MethodPost }
func (r *testPostReq) URL() string             { return "/open-apis/v1/weight/record" }
func (r *testPostReq) QueryParams() url.Values  { return nil }
func (r *testPostReq) Body() any                { return map[string]any{"weight": r.weight} }

// ===== NewClient 测试 =====

func TestNewClient_AccessTokenMode(t *testing.T) {
	c, err := NewClient(ClientConfig{
		AppID:      "app1",
		AppKey:     "key1",
		PrivateKey: "pem1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.authMode != AuthModeAccessToken {
		t.Errorf("expected ACCESS_TOKEN mode, got %s", c.authMode)
	}
}

func TestNewClient_APIKeyMode(t *testing.T) {
	c, err := NewClient(ClientConfig{
		AuthMode: AuthModeAPIKey,
		APIKey:   "my_api_key",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.apiKey != "my_api_key" {
		t.Errorf("expected my_api_key, got %s", c.apiKey)
	}
}

func TestNewClient_MissingParams(t *testing.T) {
	_, err := NewClient(ClientConfig{AppKey: "k", PrivateKey: "p"})
	if err == nil {
		t.Error("expected error for missing app_id")
	}

	_, err = NewClient(ClientConfig{AppID: "a", PrivateKey: "p"})
	if err == nil {
		t.Error("expected error for missing app_key")
	}

	_, err = NewClient(ClientConfig{AppID: "a", AppKey: "k"})
	if err == nil {
		t.Error("expected error for missing private_key")
	}

	_, err = NewClient(ClientConfig{AuthMode: AuthModeAPIKey})
	if err == nil {
		t.Error("expected error for missing api_key")
	}
}

func TestNewClient_InvalidAuthMode(t *testing.T) {
	_, err := NewClient(ClientConfig{AuthMode: "invalid"})
	if err == nil {
		t.Error("expected error for invalid auth_mode")
	}
}

func TestNewClient_Defaults(t *testing.T) {
	c, err := NewClient(ClientConfig{
		AuthMode: AuthModeAPIKey,
		APIKey:   "key",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.baseURL != defaultBaseURL {
		t.Errorf("expected %s, got %s", defaultBaseURL, c.baseURL)
	}
	if c.timeout != defaultTimeout {
		t.Errorf("expected %v, got %v", defaultTimeout, c.timeout)
	}
}

func TestNewClient_CustomBaseURL(t *testing.T) {
	c, err := NewClient(ClientConfig{
		AuthMode: AuthModeAPIKey,
		APIKey:   "key",
		BaseURL:  "https://custom.api.com/",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.baseURL != "https://custom.api.com" {
		t.Errorf("expected trimmed URL, got %s", c.baseURL)
	}
}

// ===== Execute 测试 =====

func TestExecute_Get(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("expected GET, got %s", r.Method)
		}
		if r.URL.Path != "/open-apis/v1/food/search" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		if r.URL.Query().Get("keyword") != "apple" {
			t.Errorf("expected keyword=apple, got %s", r.URL.Query().Get("keyword"))
		}
		if r.Header.Get("X-Api-Key") != "test_key" {
			t.Errorf("expected X-Api-Key=test_key, got %s", r.Header.Get("X-Api-Key"))
		}
		json.NewEncoder(w).Encode(map[string]any{
			"code": 0,
			"data": map[string]any{"foods": []any{}},
		})
	}))
	defer server.Close()

	c, _ := NewClient(ClientConfig{AuthMode: AuthModeAPIKey, APIKey: "test_key", BaseURL: server.URL})

	resp, err := c.Execute(&testGetReq{keyword: "apple", page: 1})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.IsSuccess() {
		t.Errorf("expected success, got code=%d message=%s", resp.Code, resp.Message)
	}
}

func TestExecute_Post(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("expected POST, got %s", r.Method)
		}
		var body map[string]any
		json.NewDecoder(r.Body).Decode(&body)
		if body["weight"] != 70.5 {
			t.Errorf("expected weight=70.5, got %v", body["weight"])
		}
		json.NewEncoder(w).Encode(map[string]any{
			"code": 0,
			"data": map[string]any{"success": true},
		})
	}))
	defer server.Close()

	c, _ := NewClient(ClientConfig{AuthMode: AuthModeAPIKey, APIKey: "test_key", BaseURL: server.URL})

	resp, err := c.Execute(&testPostReq{weight: 70.5})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.IsSuccess() {
		t.Errorf("expected success")
	}
}

func TestExecute_WithAccessToken(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer manual_token" {
			t.Errorf("expected Authorization=Bearer manual_token, got %s", r.Header.Get("Authorization"))
		}
		json.NewEncoder(w).Encode(map[string]any{"code": 0, "data": nil})
	}))
	defer server.Close()

	c := newTestClient(t, server.URL)

	_, err := c.Execute(&testGetReq{}, WithAccessToken("manual_token"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// ===== FetchAccessToken 测试 =====

func TestFetchAccessToken_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != accessTokenEndpoint {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{
			"code": 0, "data": map[string]any{"access_token": "new_token", "expires_in": 7200},
		})
	}))
	defer server.Close()

	c := newTestClient(t, server.URL)

	info, err := c.FetchAccessToken()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if info.AccessToken != "new_token" {
		t.Errorf("expected new_token, got %s", info.AccessToken)
	}
	if info.ExpiresIn != 7200 {
		t.Errorf("expected 7200, got %d", info.ExpiresIn)
	}
}

func TestFetchAccessToken_APIKeyMode(t *testing.T) {
	c, _ := NewClient(ClientConfig{AuthMode: AuthModeAPIKey, APIKey: "key"})

	_, err := c.FetchAccessToken()
	if err == nil {
		t.Error("expected error in API_KEY mode")
	}
	if _, ok := err.(*AuthenticationError); !ok {
		t.Errorf("expected AuthenticationError, got %T", err)
	}
}

func TestFetchAccessToken_ErrorResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{
			"code": 401, "message": "invalid signature",
		})
	}))
	defer server.Close()

	c := newTestClient(t, server.URL)

	_, err := c.FetchAccessToken()
	if err == nil {
		t.Error("expected error")
	}
	authErr, ok := err.(*AuthenticationError)
	if !ok {
		t.Fatalf("expected AuthenticationError, got %T", err)
	}
	if authErr.Message == "" {
		t.Error("expected non-empty error message")
	}
}

func TestFetchAccessToken_DoesNotUpdateInternalState(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{
			"code": 0, "data": map[string]any{"access_token": "raw_token", "expires_in": 7200},
		})
	}))
	defer server.Close()

	c := newTestClient(t, server.URL)

	_, err := c.FetchAccessToken()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.accessToken != "" {
		t.Error("internal state should not be updated")
	}
}

// ===== Token 自动刷新测试 =====

func TestTokenAutoRefresh(t *testing.T) {
	callCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == accessTokenEndpoint {
			callCount++
			json.NewEncoder(w).Encode(map[string]any{
				"code": 0, "data": map[string]any{"access_token": "auto_token", "expires_in": 86400},
			})
			return
		}
		if r.Header.Get("Authorization") != "Bearer auto_token" {
			t.Errorf("expected Bearer auto_token, got %s", r.Header.Get("Authorization"))
		}
		json.NewEncoder(w).Encode(map[string]any{"code": 0, "data": nil})
	}))
	defer server.Close()

	c := newTestClient(t, server.URL)

	_, err := c.Execute(&testGetReq{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if callCount != 1 {
		t.Errorf("expected 1 token fetch, got %d", callCount)
	}

	// 第二次调用应使用缓存
	_, err = c.Execute(&testGetReq{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if callCount != 1 {
		t.Errorf("expected still 1 token fetch (cached), got %d", callCount)
	}
}

// ===== TokenCache 测试 =====

type memCache struct {
	store map[string]string
}

func newMemCache() *memCache { return &memCache{store: make(map[string]string)} }
func (c *memCache) Get(appID string) (string, bool) {
	v, ok := c.store[appID]
	return v, ok
}
func (c *memCache) Set(appID, token string, _ int64) { c.store[appID] = token }
func (c *memCache) Delete(appID string)               { delete(c.store, appID) }

func TestTokenCache_Integration(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == accessTokenEndpoint {
			json.NewEncoder(w).Encode(map[string]any{
				"code": 0, "data": map[string]any{"access_token": "cached_token", "expires_in": 86400},
			})
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"code": 0, "data": nil})
	}))
	defer server.Close()

	cache := newMemCache()
	c, _ := NewClient(ClientConfig{
		AppID:      "test_app",
		AppKey:     "test_key",
		PrivateKey: generateTestKey(t),
		BaseURL:    server.URL,
		Cache:      cache,
	})

	_, err := c.Execute(&testGetReq{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if token, ok := cache.Get("test_app"); !ok || token != "cached_token" {
		t.Errorf("expected cached_token in cache, got %s", token)
	}
}

// ===== Response 测试 =====

func TestResponse_IsSuccess(t *testing.T) {
	resp := &Response{Code: 0, Message: "ok"}
	if !resp.IsSuccess() {
		t.Error("expected success")
	}
	if resp.Err() != nil {
		t.Error("expected nil error")
	}
}

func TestResponse_Error(t *testing.T) {
	resp := &Response{Code: 400, Message: "bad request"}
	if resp.IsSuccess() {
		t.Error("expected failure")
	}
	err := resp.Err()
	if err == nil {
		t.Fatal("expected error")
	}
	apiErr, ok := err.(*APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if apiErr.Code != 400 {
		t.Errorf("expected code 400, got %d", apiErr.Code)
	}
}

func TestResponse_UnwrapData(t *testing.T) {
	data := map[string]any{"name": "apple", "calories": 52}
	raw, _ := json.Marshal(data)
	resp := &Response{Code: 0, Data: raw}

	var result map[string]any
	if err := resp.UnwrapData(&result); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result["name"] != "apple" {
		t.Errorf("expected apple, got %v", result["name"])
	}
}

func TestResponse_UnwrapData_NilData(t *testing.T) {
	resp := &Response{Code: 0}
	var result map[string]any
	if err := resp.UnwrapData(&result); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// ===== Auth 测试 =====

func TestBuildSignatureString(t *testing.T) {
	result := BuildSignatureString("app123", "key456", 1722851989)
	expected := "key456app_idapp123timestamp1722851989key456"
	if result != expected {
		t.Errorf("expected %s, got %s", expected, result)
	}
}

func TestRSASign(t *testing.T) {
	keyPEM := generateTestKey(t)
	sig, err := RSASign("hello", keyPEM)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if sig == "" {
		t.Error("expected non-empty signature")
	}
}

func TestRSASign_InvalidPEM(t *testing.T) {
	_, err := RSASign("hello", "not-a-pem")
	if err == nil {
		t.Error("expected error for invalid PEM")
	}
}

// ===== Error 测试 =====

func TestErrorTypes(t *testing.T) {
	tests := []struct {
		err  error
		want string
	}{
		{&AuthenticationError{Message: "bad token"}, "authentication error: bad token"},
		{&APIError{Code: 400, Message: "bad request"}, "api error 400: bad request"},
		{&NetworkError{Message: "timeout"}, "network error: timeout"},
	}
	for _, tt := range tests {
		if got := tt.err.Error(); got != tt.want {
			t.Errorf("expected %q, got %q", tt.want, got)
		}
	}
}

// ===== 并发安全测试 =====

func TestTokenRefresh_Concurrent(t *testing.T) {
	callCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == accessTokenEndpoint {
			callCount++
			time.Sleep(50 * time.Millisecond)
			json.NewEncoder(w).Encode(map[string]any{
				"code": 0, "data": map[string]any{"access_token": "concurrent_token", "expires_in": 86400},
			})
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"code": 0, "data": nil})
	}))
	defer server.Close()

	c := newTestClient(t, server.URL)

	done := make(chan error, 10)
	for i := 0; i < 10; i++ {
		go func() {
			_, err := c.Execute(&testGetReq{})
			done <- err
		}()
	}

	for i := 0; i < 10; i++ {
		if err := <-done; err != nil {
			t.Errorf("con Execute %d: %v", i, err)
		}
	}

	// 由于双重检查锁，token 刷新次数应远小于 10
	if callCount > 3 {
		t.Errorf("expected few token refreshes with double-check lock, got %d", callCount)
	}
}

// ===== 流式 SSE 测试 =====

func TestExecuteStream(t *testing.T) {
	sseBody := "id:1\ndata:{\"content\": \"hello\"}\n\nid:2\ndata:{\"content\": \" world\", \"end\": true}\n\n"

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(200)
		w.Write([]byte(sseBody))
	}))
	defer server.Close()

	c, _ := NewClient(ClientConfig{AuthMode: AuthModeAPIKey, APIKey: "test_key", BaseURL: server.URL})

	var chunks []string
	err := c.ExecuteStream(&testGetReq{}, func(data string) {
		chunks = append(chunks, data)
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(chunks) != 2 {
		t.Fatalf("expected 2 chunks, got %d", len(chunks))
	}
	if chunks[0] != `{"content": "hello"}` {
		t.Errorf("unexpected chunk[0]: %s", chunks[0])
	}
	if chunks[1] != `{"content": " world", "end": true}` {
		t.Errorf("unexpected chunk[1]: %s", chunks[1])
	}
}
