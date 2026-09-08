import { describe, it, before, after } from 'node:test';
import * as assert from 'node:assert';
import * as http from 'node:http';
import * as crypto from 'node:crypto';

import {
  BooheeClient,
  AuthMode,
  HttpMethod,
  Response,
  AuthenticationError,
  ApiError,
  buildSignatureString,
  rsaSign,
} from '../src';
import type { Request, TokenCache } from '../src';

// ===== 辅助 =====

function generateTestKey(): string {
  const { privateKey } = crypto.generateKeyPairSync('rsa', {
    modulusLength: 2048,
    privateKeyEncoding: { type: 'pkcs1', format: 'pem' },
    publicKeyEncoding: { type: 'spki', format: 'pem' },
  });
  return privateKey;
}

function createServer(handler: http.RequestListener): Promise<{ server: http.Server; port: number }> {
  return new Promise((resolve) => {
    const server = http.createServer(handler);
    server.listen(0, () => {
      const addr = server.address() as { port: number };
      resolve({ server, port: addr.port });
    });
  });
}

function closeServer(server: http.Server): Promise<void> {
  return new Promise((resolve) => server.close(() => resolve()));
}

class TestGetReq implements Request {
  getMethod() { return HttpMethod.GET; }
  getUrl() { return '/test'; }
  getQueryParams() { return null; }
  getBody() { return null; }
}

class TestPostReq implements Request {
  getMethod() { return HttpMethod.POST; }
  getUrl() { return '/test'; }
  getQueryParams() { return null; }
  getBody() { return { weight: 70.5 }; }
}

// ===== 测试 =====

describe('BooheeClient', () => {
  it('should create client in ACCESS_TOKEN mode', () => {
    const client = new BooheeClient({
      appId: 'app1', appKey: 'key1', privateKey: 'pem1',
    });
    assert.ok(client);
  });

  it('should create client in API_KEY mode', () => {
    const client = new BooheeClient({
      authMode: AuthMode.API_KEY, apiKey: 'my_key',
    });
    assert.ok(client);
  });

  it('should throw on missing app_id', () => {
    assert.throws(
      () => new BooheeClient({ appKey: 'k', privateKey: 'p' }),
      /app_id is required/,
    );
  });

  it('should throw on missing api_key', () => {
    assert.throws(
      () => new BooheeClient({ authMode: AuthMode.API_KEY }),
      /api_key is required/,
    );
  });

  it('should throw on invalid auth_mode', () => {
    assert.throws(
      () => new BooheeClient({ authMode: 'invalid' as any }),
      /Invalid auth_mode/,
    );
  });
});

describe('execute', () => {
  let server: http.Server;
  let port: number;

  before(async () => {
    const s = await createServer((req, res) => {
      if (req.url?.startsWith('/test')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ code: 0, message: 'ok', now: 1722851989, data: { result: 'test' } }));
        return;
      }
      res.writeHead(404);
      res.end();
    });
    server = s.server;
    port = s.port;
  });

  after(async () => {
    await closeServer(server);
  });

  it('should execute GET request with API_KEY', async () => {
    const client = new BooheeClient({
      authMode: AuthMode.API_KEY,
      apiKey: 'test_key',
      baseUrl: `http://localhost:${port}`,
    });

    const resp = await client.execute(new TestGetReq());
    assert.ok(resp.isSuccess());
    assert.strictEqual(resp.code, 0);
    assert.deepStrictEqual(resp.data, { result: 'test' });
  });

  it('should execute POST request', async () => {
    const client = new BooheeClient({
      authMode: AuthMode.API_KEY,
      apiKey: 'test_key',
      baseUrl: `http://localhost:${port}`,
    });

    const resp = await client.execute(new TestPostReq());
    assert.ok(resp.isSuccess());
  });

  it('should use manual access_token', async () => {
    let receivedToken = '';
    const s = await createServer((req, res) => {
      receivedToken = req.headers['authorization'] as string || '';
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ code: 0, data: null }));
    });

    const client = new BooheeClient({
      appId: 'test', appKey: 'key', privateKey: generateTestKey(),
      baseUrl: `http://localhost:${s.port}`,
    });

    await client.execute(new TestGetReq(), { accessToken: 'manual_token' });
    assert.strictEqual(receivedToken, 'Bearer manual_token');
    await closeServer(s.server);
  });
});

describe('fetchAccessToken', () => {
  it('should fetch token successfully', async () => {
    const s = await createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ code: 0, access_token: 'new_token', expires_in: 7200 }));
    });

    const client = new BooheeClient({
      appId: 'test', appKey: 'key', privateKey: generateTestKey(),
      baseUrl: `http://localhost:${s.port}`,
    });

    const info = await client.fetchAccessToken();
    assert.strictEqual(info.accessToken, 'new_token');
    assert.strictEqual(info.expiresIn, 7200);
    await closeServer(s.server);
  });

  it('should throw in API_KEY mode', () => {
    const client = new BooheeClient({
      authMode: AuthMode.API_KEY, apiKey: 'key',
    });
    assert.rejects(() => client.fetchAccessToken(), AuthenticationError);
  });

  it('should throw on error response', async () => {
    const s = await createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ code: 401, message: 'invalid signature' }));
    });

    const client = new BooheeClient({
      appId: 'test', appKey: 'key', privateKey: generateTestKey(),
      baseUrl: `http://localhost:${s.port}`,
    });

    await assert.rejects(
      () => client.fetchAccessToken(),
      (err: any) => err instanceof AuthenticationError && err.message.includes('code=401'),
    );
    await closeServer(s.server);
  });
});

describe('executeStream', () => {
  it('should parse SSE stream', async () => {
    const sseBody = 'id:1\ndata:{"content": "hello"}\n\nid:2\ndata:{"content": " world", "end": true}\n\n';
    const s = await createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/event-stream' });
      res.end(sseBody);
    });

    const client = new BooheeClient({
      authMode: AuthMode.API_KEY, apiKey: 'test_key',
      baseUrl: `http://localhost:${s.port}`,
    });

    const chunks: string[] = [];
    for await (const chunk of client.executeStream(new TestGetReq())) {
      chunks.push(chunk);
    }

    assert.strictEqual(chunks.length, 2);
    assert.strictEqual(chunks[0], '{"content": "hello"}');
    assert.strictEqual(chunks[1], '{"content": " world", "end": true}');
    await closeServer(s.server);
  });
});

describe('Response', () => {
  it('should detect success', () => {
    const resp = new Response({ code: 0, message: 'ok' });
    assert.ok(resp.isSuccess());
    assert.strictEqual(resp.get('key'), undefined);
    assert.strictEqual(resp.get('key', 'default'), 'default');
  });

  it('should detect error', () => {
    const resp = new Response({ code: 400, message: 'bad request' });
    assert.ok(!resp.isSuccess());
    assert.throws(() => resp.raiseForError(), (err: any) => err instanceof ApiError && err.code === 400);
  });

  it('should get data fields', () => {
    const resp = new Response({ code: 0, data: { name: 'apple', calories: 52 } });
    assert.strictEqual(resp.get('name'), 'apple');
    assert.strictEqual(resp.get('calories'), 52);
  });
});

describe('Auth', () => {
  it('should build signature string', () => {
    const result = buildSignatureString('app123', 'key456', 1722851989);
    assert.strictEqual(result, 'key456app_idapp123timestamp1722851989key456');
  });

  it('should RSA sign', () => {
    const key = generateTestKey();
    const sig = rsaSign('hello', key);
    assert.ok(sig.length > 0);
  });
});

describe('HttpMethod', () => {
  it('should have correct values', () => {
    assert.strictEqual(HttpMethod.GET, 'GET');
    assert.strictEqual(HttpMethod.POST, 'POST');
  });
});
