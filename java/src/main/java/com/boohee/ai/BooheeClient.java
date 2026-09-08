package com.boohee.ai;

import com.boohee.ai.exception.AuthenticationException;
import com.boohee.ai.exception.NetworkException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.locks.ReentrantLock;

/**
 * 薄荷开放平台客户端
 */
public class BooheeClient {

    private static final String DEFAULT_BASE_URL = "https://api.boohee.com";
    private static final int DEFAULT_TIMEOUT_MS = 30_000;
    private static final long TOKEN_REFRESH_BUFFER_MS = 300_000;
    private static final String ACCESS_TOKEN_ENDPOINT = "/open-apis/v1/access_token";

    private final AuthMode authMode;
    private final String baseURL;
    private final TokenCache cache;
    private final int timeoutMs;
    private final ObjectMapper objectMapper;

    // Access Token 模式
    private final String appId;
    private final String appKey;
    private final String privateKey;

    // API Key 模式
    private final String apiKey;

    // Token 管理
    private String accessToken;
    private long tokenExpiresAt;
    private final ReentrantLock tokenLock = new ReentrantLock();

    private BooheeClient(Builder builder) {
        this.authMode = builder.authMode;
        this.baseURL = builder.baseURL.replaceAll("/+$", "");
        this.cache = builder.cache;
        this.timeoutMs = builder.timeoutMs;
        this.objectMapper = new ObjectMapper();

        if (authMode == AuthMode.ACCESS_TOKEN) {
            if (builder.appId == null || builder.appId.isEmpty()) {
                throw new IllegalArgumentException("app_id is required for ACCESS_TOKEN mode");
            }
            if (builder.appKey == null || builder.appKey.isEmpty()) {
                throw new IllegalArgumentException("app_key is required for ACCESS_TOKEN mode");
            }
            if (builder.privateKey == null || builder.privateKey.isEmpty()) {
                throw new IllegalArgumentException("private_key is required for ACCESS_TOKEN mode");
            }
            this.appId = builder.appId;
            this.appKey = builder.appKey;
            this.privateKey = builder.privateKey;
            this.apiKey = null;
        } else if (authMode == AuthMode.API_KEY) {
            if (builder.apiKey == null || builder.apiKey.isEmpty()) {
                throw new IllegalArgumentException("api_key is required for API_KEY mode");
            }
            this.apiKey = builder.apiKey;
            this.appId = null;
            this.appKey = null;
            this.privateKey = null;
        } else {
            throw new IllegalArgumentException("Invalid auth_mode: " + authMode);
        }
    }

    /**
     * 创建 Builder
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * 执行请求（走内部 token 缓存逻辑）
     */
    public BaseResp execute(BaseReq req) {
        return execute(req, null);
    }

    /**
     * 执行请求
     *
     * @param req         请求对象
     * @param accessToken 可选，开发者自行获取的 token，传入后直接使用
     */
    public BaseResp execute(BaseReq req, String accessToken) {
        Map<String, Object> rawResponse = doRequest(
                req.getMethod(), req.getUrl(), req.getQueryParams(), req.getBody(), accessToken);
        return parseResponse(rawResponse);
    }

    /**
     * 执行 SSE 流式请求
     *
     * 逐行读取 SSE 响应，对每个 data 行调用 onEvent 回调。
     * onEvent 收到的 data 是去掉 "data:" 前缀后的原始内容。
     * 连接关闭时自动结束。
     *
     * @param req         请求对象
     * @param onEvent     每收到一个 SSE data 事件时的回调
     */
    public void executeStream(BaseReq req, java.util.function.Consumer<String> onEvent) {
        executeStream(req, onEvent, null);
    }

    /**
     * 执行 SSE 流式请求
     *
     * @param req         请求对象
     * @param onEvent     每收到一个 SSE data 事件时的回调
     * @param accessToken 可选，开发者自行获取的 token
     */
    public void executeStream(BaseReq req, java.util.function.Consumer<String> onEvent, String accessToken) {
        String url = baseURL + req.getUrl();
        Map<String, String> headers = getHeaders(accessToken);
        headers.put("Accept", "text/event-stream");

        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestMethod(req.getMethod() == HttpMethod.GET ? "GET" : "POST");
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);

            for (Map.Entry<String, String> h : headers.entrySet()) {
                conn.setRequestProperty(h.getKey(), h.getValue());
            }

            if (req.getMethod() == HttpMethod.POST && req.getBody() != null) {
                conn.setDoOutput(true);
                byte[] jsonBytes = objectMapper.writeValueAsBytes(req.getBody());
                conn.setFixedLengthStreamingMode(jsonBytes.length);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBytes);
                }
            }

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), "UTF-8"))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (line.isEmpty() || !line.startsWith("data:")) {
                        continue;
                    }
                    String payload = line.substring(5);
                    if (payload.startsWith(" ")) {
                        payload = payload.substring(1);
                    }
                    onEvent.accept(payload);
                }
            }
            conn.disconnect();
        } catch (NetworkException e) {
            throw e;
        } catch (Exception e) {
            throw new NetworkException("stream request failed: " + e.getMessage());
        }
    }

    /**
     * 从服务端获取 access_token，返回原始数据
     *
     * 底层接口，不做任何缓存。开发者可根据 expiresIn 自行实现缓存策略。
     * 仅在 ACCESS_TOKEN 模式下可用。
     */
    public TokenInfo fetchAccessToken() {
        if (authMode != AuthMode.ACCESS_TOKEN) {
            throw new AuthenticationException("fetchAccessToken is only available in ACCESS_TOKEN mode");
        }

        long timestamp = System.currentTimeMillis() / 1000;
        String sigStr = AuthUtil.buildSignatureString(appId, appKey, timestamp);
        String sign;
        try {
            sign = AuthUtil.rsaSign(sigStr, privateKey);
        } catch (Exception e) {
            throw new AuthenticationException("failed to sign: " + e.getMessage(), e);
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("app_id", appId);
        payload.put("timestamp", timestamp);
        payload.put("sign", sign);

        Map<String, Object> result = httpPost(baseURL + ACCESS_TOKEN_ENDPOINT, payload, null);

        int code = toInt(result.get("code"), -1);
        if (code != 0) {
            String message = result.get("message") != null ? result.get("message").toString() : "Unknown error";
            throw new AuthenticationException("failed to get access_token: code=" + code + ", message=" + message);
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) result.get("data");
        if (data == null) {
            throw new AuthenticationException("response missing data field");
        }

        return new TokenInfo(
                data.get("access_token").toString(),
                toLong(data.get("expires_in"), 0)
        );
    }

    // ===== 内部方法 =====

    @SuppressWarnings("unchecked")
    private Map<String, Object> doRequest(HttpMethod method, String path,
                                          Map<String, Object> params, Map<String, Object> body,
                                          String accessToken) {
        String url = baseURL + path;
        Map<String, String> headers = getHeaders(accessToken);

        try {
            if (method == HttpMethod.GET && params != null && !params.isEmpty()) {
                StringBuilder sb = new StringBuilder(url);
                sb.append('?');
                boolean first = true;
                for (Map.Entry<String, Object> entry : params.entrySet()) {
                    if (!first) sb.append('&');
                    sb.append(URLEncoder.encode(entry.getKey(), "UTF-8"));
                    sb.append('=');
                    sb.append(URLEncoder.encode(String.valueOf(entry.getValue()), "UTF-8"));
                    first = false;
                }
                url = sb.toString();
            }

            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestMethod(method == HttpMethod.GET ? "GET" : "POST");
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);

            for (Map.Entry<String, String> h : headers.entrySet()) {
                conn.setRequestProperty(h.getKey(), h.getValue());
            }

            if (method == HttpMethod.POST && body != null) {
                conn.setDoOutput(true);
                byte[] jsonBytes = objectMapper.writeValueAsBytes(body);
                conn.setFixedLengthStreamingMode(jsonBytes.length);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBytes);
                }
            }

            int status = conn.getResponseCode();
            InputStream is = (status >= 200 && status < 300)
                    ? conn.getInputStream()
                    : conn.getErrorStream();

            String responseBody = readStream(is);
            conn.disconnect();

            try {
                return objectMapper.readValue(responseBody, Map.class);
            } catch (Exception e) {
                Map<String, Object> fallback = new HashMap<>();
                fallback.put("code", -1);
                fallback.put("message", responseBody);
                fallback.put("data", null);
                return fallback;
            }
        } catch (NetworkException e) {
            throw e;
        } catch (Exception e) {
            throw new NetworkException("request failed: " + e.getMessage());
        }
    }

    private Map<String, String> getHeaders(String accessToken) {
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", "application/json");
        headers.put("Accept", "application/json");

        if (authMode == AuthMode.ACCESS_TOKEN) {
            String token = (accessToken != null && !accessToken.isEmpty())
                    ? accessToken : getAccessToken();
            headers.put("Authorization", "Bearer " + token);
        } else if (authMode == AuthMode.API_KEY) {
            headers.put("X-Api-Key", apiKey);
        }
        return headers;
    }

    private String getAccessToken() {
        long now = System.currentTimeMillis();

        // 检查内存缓存
        if (accessToken != null && now < tokenExpiresAt - TOKEN_REFRESH_BUFFER_MS) {
            return accessToken;
        }

        // 尝试从外部缓存获取
        if (cache != null) {
            String cached = cache.get(appId);
            if (cached != null) {
                accessToken = cached;
                tokenExpiresAt = now + 600_000; // 保守假设 10 分钟
                return accessToken;
            }
        }

        // 加锁刷新
        tokenLock.lock();
        try {
            // 双重检查
            if (accessToken != null && System.currentTimeMillis() < tokenExpiresAt - TOKEN_REFRESH_BUFFER_MS) {
                return accessToken;
            }
            return refreshAccessToken();
        } finally {
            tokenLock.unlock();
        }
    }

    private String refreshAccessToken() {
        TokenInfo info = fetchAccessToken();
        accessToken = info.getAccessToken();
        tokenExpiresAt = System.currentTimeMillis() + info.getExpiresIn() * 1000;
        if (cache != null) {
            cache.set(appId, accessToken, info.getExpiresIn());
        }
        return accessToken;
    }

    private Map<String, Object> httpPost(String url, Map<String, Object> payload, Map<String, String> extraHeaders) {
        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Accept", "application/json");
            if (extraHeaders != null) {
                for (Map.Entry<String, String> h : extraHeaders.entrySet()) {
                    conn.setRequestProperty(h.getKey(), h.getValue());
                }
            }

            conn.setDoOutput(true);
            byte[] jsonBytes = objectMapper.writeValueAsBytes(payload);
            conn.setFixedLengthStreamingMode(jsonBytes.length);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(jsonBytes);
            }

            InputStream is = conn.getInputStream();
            String responseBody = readStream(is);
            conn.disconnect();

            return objectMapper.readValue(responseBody, Map.class);
        } catch (Exception e) {
            throw new AuthenticationException("token request failed: " + e.getMessage(), e);
        }
    }

    private BaseResp parseResponse(Map<String, Object> raw) {
        int code = toInt(raw.get("code"), -1);
        String message = raw.get("message") != null ? raw.get("message").toString() : "";
        long now = toLong(raw.get("now"), 0);

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) raw.get("data");

        return new BaseResp(code, message, now, data);
    }

    private static String readStream(InputStream is) throws IOException {
        if (is == null) return "";
        BufferedReader reader = new BufferedReader(new InputStreamReader(is, "UTF-8"));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }
        reader.close();
        return sb.toString();
    }

    private static int toInt(Object obj, int defaultValue) {
        if (obj == null) return defaultValue;
        if (obj instanceof Number) return ((Number) obj).intValue();
        try {
            return Integer.parseInt(obj.toString());
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    private static long toLong(Object obj, long defaultValue) {
        if (obj == null) return defaultValue;
        if (obj instanceof Number) return ((Number) obj).longValue();
        try {
            return Long.parseLong(obj.toString());
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    // ===== Token 信息 =====

    /**
     * access_token 原始数据
     */
    public static class TokenInfo {
        private final String accessToken;
        private final long expiresIn;

        public TokenInfo(String accessToken, long expiresIn) {
            this.accessToken = accessToken;
            this.expiresIn = expiresIn;
        }

        public String getAccessToken() {
            return accessToken;
        }

        public long getExpiresIn() {
            return expiresIn;
        }
    }

    // ===== Builder =====

    public static class Builder {
        private AuthMode authMode = AuthMode.ACCESS_TOKEN;
        private String baseURL = DEFAULT_BASE_URL;
        private TokenCache cache;
        private int timeoutMs = DEFAULT_TIMEOUT_MS;

        private String appId;
        private String appKey;
        private String privateKey;
        private String apiKey;

        public Builder authMode(AuthMode authMode) {
            this.authMode = authMode;
            return this;
        }

        public Builder baseURL(String baseURL) {
            this.baseURL = baseURL;
            return this;
        }

        public Builder cache(TokenCache cache) {
            this.cache = cache;
            return this;
        }

        public Builder timeoutMs(int timeoutMs) {
            this.timeoutMs = timeoutMs;
            return this;
        }

        public Builder appId(String appId) {
            this.appId = appId;
            return this;
        }

        public Builder appKey(String appKey) {
            this.appKey = appKey;
            return this;
        }

        public Builder privateKey(String privateKey) {
            this.privateKey = privateKey;
            return this;
        }

        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }

        public BooheeClient build() {
            return new BooheeClient(this);
        }
    }
}
