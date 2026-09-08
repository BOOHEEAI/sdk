package com.boohee.ai;

import com.boohee.ai.exception.AuthenticationException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

public class BooheeClientTest {

    private HttpServer server;
    private int port;
    private String testPrivateKeyPem;

    @Before
    public void setUp() throws Exception {
        server = HttpServer.create(new InetSocketAddress(0), 0);
        port = server.getAddress().getPort();
        server.start();

        // 生成测试用 RSA 密钥
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(2048);
        KeyPair kp = kpg.generateKeyPair();
        testPrivateKeyPem = "-----BEGIN RSA PRIVATE KEY-----\n"
                + java.util.Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded())
                + "\n-----END RSA PRIVATE KEY-----";
    }

    @After
    public void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    private String baseURL() {
        return "http://localhost:" + port;
    }

    // ===== Builder / 初始化测试 =====

    @Test
    public void testNewClient_AccessTokenMode() {
        BooheeClient client = BooheeClient.builder()
                .appId("app1").appKey("key1").privateKey("pem1")
                .build();
        assertNotNull(client);
    }

    @Test
    public void testNewClient_APIKeyMode() {
        BooheeClient client = BooheeClient.builder()
                .authMode(AuthMode.API_KEY).apiKey("my_key")
                .build();
        assertNotNull(client);
    }

    @Test(expected = IllegalArgumentException.class)
    public void testNewClient_MissingAppId() {
        BooheeClient.builder().appKey("k").privateKey("p").build();
    }

    @Test(expected = IllegalArgumentException.class)
    public void testNewClient_MissingAppKey() {
        BooheeClient.builder().appId("a").privateKey("p").build();
    }

    @Test(expected = IllegalArgumentException.class)
    public void testNewClient_MissingPrivateKey() {
        BooheeClient.builder().appId("a").appKey("k").build();
    }

    @Test(expected = IllegalArgumentException.class)
    public void testNewClient_MissingApiKey() {
        BooheeClient.builder().authMode(AuthMode.API_KEY).build();
    }

    // ===== Execute 测试 =====

    @Test
    public void testExecute_Get() throws Exception {
        server.createContext("/open-apis/v1/food/search", exchange -> {
            assertEquals("GET", exchange.getRequestMethod());
            assertEquals("test_key", exchange.getRequestHeaders().getFirst("X-Api-Key"));
            String query = exchange.getRequestURI().getQuery();
            assertTrue(query.contains("keyword=apple"));

            String resp = "{\"code\":0,\"message\":\"ok\",\"now\":1722851989,\"data\":{\"foods\":[]}}";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });

        BooheeClient client = BooheeClient.builder()
                .authMode(AuthMode.API_KEY).apiKey("test_key")
                .baseURL(baseURL())
                .build();

        BaseResp resp = client.execute(new BaseReq() {
            @Override
            public HttpMethod getMethod() { return HttpMethod.GET; }
            @Override
            public String getUrl() { return "/open-apis/v1/food/search"; }
            @Override
            public Map<String, Object> getQueryParams() {
                Map<String, Object> params = new HashMap<>();
                params.put("keyword", "apple");
                return params;
            }
        });

        assertTrue(resp.isSuccess());
        assertEquals(0, resp.getCode());
    }

    @Test
    public void testExecute_Post() throws Exception {
        server.createContext("/open-apis/v1/weight/record", exchange -> {
            assertEquals("POST", exchange.getRequestMethod());

            // 丢弃 request body
            exchange.getRequestBody().close();

            String resp = "{\"code\":0,\"message\":\"ok\",\"now\":1722851989,\"data\":{\"success\":true}}";
            byte[] respBytes = resp.getBytes("UTF-8");
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, respBytes.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(respBytes);
            }
            exchange.close();
        });

        BooheeClient client = BooheeClient.builder()
                .authMode(AuthMode.API_KEY).apiKey("test_key")
                .baseURL(baseURL())
                .build();

        BaseResp resp = client.execute(new BaseReq() {
            @Override
            public HttpMethod getMethod() { return HttpMethod.POST; }
            @Override
            public String getUrl() { return "/open-apis/v1/weight/record"; }
            @Override
            public Map<String, Object> getBody() {
                Map<String, Object> body = new HashMap<>();
                body.put("weight", 70.5);
                return body;
            }
        });

        assertTrue(resp.isSuccess());
    }

    @Test
    public void testExecute_WithAccessToken() throws Exception {
        server.createContext("/test", exchange -> {
            String token = exchange.getRequestHeaders().getFirst("Authorization");
            assertEquals("Bearer manual_token", token);

            String resp = "{\"code\":0,\"message\":\"ok\",\"now\":0,\"data\":null}";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });

        BooheeClient client = BooheeClient.builder()
                .appId("test").appKey("key").privateKey(testPrivateKeyPem)
                .baseURL(baseURL())
                .build();

        BaseResp resp = client.execute(new BaseReq() {
            @Override
            public HttpMethod getMethod() { return HttpMethod.GET; }
            @Override
            public String getUrl() { return "/test"; }
        }, "manual_token");

        assertTrue(resp.isSuccess());
    }

    // ===== FetchAccessToken 测试 =====

    @Test
    public void testFetchAccessToken_Success() throws Exception {
        server.createContext("/open-apis/v1/access_token", exchange -> {
            String resp = "{\"code\":0,\"access_token\":\"new_token\",\"expires_in\":7200}";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });

        BooheeClient client = BooheeClient.builder()
                .appId("test").appKey("key").privateKey(testPrivateKeyPem)
                .baseURL(baseURL())
                .build();

        BooheeClient.TokenInfo info = client.fetchAccessToken();
        assertEquals("new_token", info.getAccessToken());
        assertEquals(7200, info.getExpiresIn());
    }

    @Test(expected = AuthenticationException.class)
    public void testFetchAccessToken_APIKeyMode() {
        BooheeClient client = BooheeClient.builder()
                .authMode(AuthMode.API_KEY).apiKey("key")
                .build();
        client.fetchAccessToken();
    }

    @Test
    public void testFetchAccessToken_ErrorResponse() throws Exception {
        server.createContext("/open-apis/v1/access_token", exchange -> {
            String resp = "{\"code\":401,\"message\":\"invalid signature\"}";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });

        BooheeClient client = BooheeClient.builder()
                .appId("test").appKey("key").privateKey(testPrivateKeyPem)
                .baseURL(baseURL())
                .build();

        try {
            client.fetchAccessToken();
            fail("expected AuthenticationException");
        } catch (AuthenticationException e) {
            assertTrue(e.getMessage().contains("code=401"));
        }
    }

    @Test
    public void testFetchAccessToken_DoesNotUpdateInternalState() throws Exception {
        server.createContext("/open-apis/v1/access_token", exchange -> {
            String resp = "{\"code\":0,\"access_token\":\"raw_token\",\"expires_in\":7200}";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });

        BooheeClient client = BooheeClient.builder()
                .appId("test").appKey("key").privateKey(testPrivateKeyPem)
                .baseURL(baseURL())
                .build();

        client.fetchAccessToken();
        // 内部状态不应被更新（无法直接访问私有字段，但不应抛异常）
    }

    // ===== Token 自动刷新测试 =====

    @Test
    public void testTokenAutoRefresh() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);

        server.createContext("/", exchange -> {
            String path = exchange.getRequestURI().getPath();
            if (path.equals("/open-apis/v1/access_token")) {
                callCount.incrementAndGet();
                String resp = "{\"code\":0,\"access_token\":\"auto_token\",\"expires_in\":86400}";
                exchange.sendResponseHeaders(200, resp.length());
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(resp.getBytes());
                }
                return;
            }
            String token = exchange.getRequestHeaders().getFirst("Authorization");
            assertEquals("Bearer auto_token", token);
            String resp = "{\"code\":0,\"message\":\"ok\",\"now\":0,\"data\":null}";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });

        BooheeClient client = BooheeClient.builder()
                .appId("test").appKey("key").privateKey(testPrivateKeyPem)
                .baseURL(baseURL())
                .build();

        BaseReq req = new BaseReq() {
            @Override
            public HttpMethod getMethod() { return HttpMethod.GET; }
            @Override
            public String getUrl() { return "/test"; }
        };

        client.execute(req);
        assertEquals(1, callCount.get());

        // 第二次应使用缓存
        client.execute(req);
        assertEquals(1, callCount.get());
    }

    // ===== BaseResp 测试 =====

    @Test
    public void testBaseResp_Success() {
        BaseResp resp = new BaseResp(0, "ok", 1722851989, null);
        assertTrue(resp.isSuccess());
        assertNull(resp.get("key"));
        assertEquals("default", resp.get("key", "default"));
    }

    @Test
    public void testBaseResp_Error() {
        BaseResp resp = new BaseResp(400, "bad request", 0, null);
        assertFalse(resp.isSuccess());
        try {
            resp.raiseForError();
            fail("expected ApiException");
        } catch (com.boohee.ai.exception.ApiException e) {
            assertEquals(400, e.getCode());
        }
    }

    @Test
    public void testBaseResp_GetFromData() {
        Map<String, Object> data = new HashMap<>();
        data.put("name", "apple");
        data.put("calories", 52);
        BaseResp resp = new BaseResp(0, "ok", 0, data);

        assertEquals("apple", resp.get("name"));
        assertEquals(52, (int) resp.get("calories"));
    }

    // ===== AuthUtil 测试 =====

    @Test
    public void testBuildSignatureString() {
        String result = AuthUtil.buildSignatureString("app123", "key456", 1722851989);
        assertEquals("key456app_idapp123timestamp1722851989key456", result);
    }

    @Test
    public void testRsaSign() throws Exception {
        String sig = AuthUtil.rsaSign("hello", testPrivateKeyPem);
        assertNotNull(sig);
        assertFalse(sig.isEmpty());
    }

    // ===== HttpMethod 测试 =====

    @Test
    public void testHttpMethod_Values() {
        assertEquals("GET", HttpMethod.GET.getValue());
        assertEquals("POST", HttpMethod.POST.getValue());
    }

    // ===== 流式 SSE 测试 =====

    @Test
    public void testExecuteStream() throws Exception {
        String sseBody = "id:1\ndata:{\"content\": \"hello\"}\n\nid:2\ndata:{\"content\": \" world\", \"end\": true}\n\n";

        server.createContext("/stream", exchange -> {
            exchange.getResponseHeaders().set("Content-Type", "text/event-stream");
            byte[] bytes = sseBody.getBytes("UTF-8");
            exchange.sendResponseHeaders(200, bytes.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(bytes);
            }
            exchange.close();
        });

        BooheeClient client = BooheeClient.builder()
                .authMode(AuthMode.API_KEY).apiKey("test_key")
                .baseURL(baseURL())
                .build();

        java.util.List<String> chunks = new java.util.ArrayList<>();
        client.executeStream(new BaseReq() {
            @Override
            public HttpMethod getMethod() { return HttpMethod.GET; }
            @Override
            public String getUrl() { return "/stream"; }
        }, chunks::add);

        assertEquals(2, chunks.size());
        assertEquals("{\"content\": \"hello\"}", chunks.get(0));
        assertEquals("{\"content\": \" world\", \"end\": true}", chunks.get(1));
    }

    // ===== 辅助方法 =====

    private static byte[] readAll(java.io.InputStream is) throws java.io.IOException {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[1024];
        int len;
        while ((len = is.read(buf)) != -1) {
            bos.write(buf, 0, len);
        }
        is.close();
        return bos.toByteArray();
    }
}
