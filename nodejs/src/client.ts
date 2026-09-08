import { AuthMode, buildSignatureString, rsaSign } from './auth';
import { TokenCache } from './cache';
import { AuthenticationError, NetworkError } from './errors';
import { HttpMethod, Request } from './request';
import { Response } from './response';

const DEFAULT_BASE_URL = 'https://api.boohee.com';
const DEFAULT_TIMEOUT_MS = 30_000;
const TOKEN_REFRESH_BUFFER_MS = 300_000;
const ACCESS_TOKEN_ENDPOINT = '/open-apis/v1/access_token';

/**
 * access_token 原始数据
 */
export interface TokenInfo {
  accessToken: string;
  expiresIn: number;
}

/**
 * 客户端配置
 */
export interface ClientConfig {
  /** Access Token 模式 */
  appId?: string;
  appKey?: string;
  privateKey?: string;

  /** API Key 模式 */
  apiKey?: string;

  /** 通用配置 */
  authMode?: AuthMode;
  baseUrl?: string;
  cache?: TokenCache;
  timeoutMs?: number;
}

/**
 * execute 可选参数
 */
export interface ExecuteOptions {
  accessToken?: string;
}

/**
 * 薄荷开放平台客户端
 */
export class BooheeClient {
  private readonly authMode: AuthMode;
  private readonly baseUrl: string;
  private readonly cache?: TokenCache;
  private readonly timeoutMs: number;

  // Access Token 模式
  private readonly appId?: string;
  private readonly appKey?: string;
  private readonly privateKey?: string;

  // API Key 模式
  private readonly apiKey?: string;

  // Token 管理
  private accessToken?: string;
  private tokenExpiresAt = 0;
  private tokenPromise?: Promise<string>;

  constructor(config: ClientConfig) {
    this.authMode = config.authMode ?? AuthMode.ACCESS_TOKEN;
    this.baseUrl = (config.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
    this.cache = config.cache;
    this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;

    if (this.authMode === AuthMode.ACCESS_TOKEN) {
      if (!config.appId) throw new Error('app_id is required for ACCESS_TOKEN mode');
      if (!config.appKey) throw new Error('app_key is required for ACCESS_TOKEN mode');
      if (!config.privateKey) throw new Error('private_key is required for ACCESS_TOKEN mode');
      this.appId = config.appId;
      this.appKey = config.appKey;
      this.privateKey = config.privateKey;
    } else if (this.authMode === AuthMode.API_KEY) {
      if (!config.apiKey) throw new Error('api_key is required for API_KEY mode');
      this.apiKey = config.apiKey;
    } else {
      throw new Error(`Invalid auth_mode: ${this.authMode}`);
    }
  }

  /**
   * 执行请求
   *
   * @param req 请求对象
   * @param options 可选参数，可传入 accessToken 自行管理 token
   */
  async execute(req: Request, options?: ExecuteOptions): Promise<Response> {
    const token = options?.accessToken ?? (this.authMode === AuthMode.ACCESS_TOKEN
      ? await this.ensureAccessToken()
      : undefined);
    const raw = await this.doRequest(
      req.getMethod(),
      req.getUrl(),
      req.getQueryParams?.(),
      req.getBody?.(),
      token,
    );
    return new Response(raw);
  }

  /**
   * 执行 SSE 流式请求
   *
   * 返回一个异步生成器，逐块 yield SSE data 内容。
   * 连接关闭时自动结束。
   *
   * @param req 请求对象
   * @param options 可选参数
   */
  async *executeStream(req: Request, options?: ExecuteOptions): AsyncGenerator<string, void, unknown> {
    const token = options?.accessToken ?? (this.authMode === AuthMode.ACCESS_TOKEN
      ? await this.ensureAccessToken()
      : undefined);
    const url = this.baseUrl + req.getUrl();
    const headers = this.getHeaders(token);
    headers['Accept'] = 'text/event-stream';

    const fetchOptions: RequestInit = {
      method: req.getMethod(),
      headers,
      signal: AbortSignal.timeout(this.timeoutMs),
    };

    if (req.getMethod() === HttpMethod.GET && req.getQueryParams?.()) {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(req.getQueryParams()!)) {
        params.set(k, String(v));
      }
      const separator = url.includes('?') ? '&' : '?';
      const resp = await fetch(`${url}${separator}${params.toString()}`, fetchOptions);
      yield* this.parseSSEStream(resp);
    } else if (req.getMethod() === HttpMethod.POST) {
      fetchOptions.body = req.getBody?.() ? JSON.stringify(req.getBody()) : undefined;
      const resp = await fetch(url, fetchOptions);
      yield* this.parseSSEStream(resp);
    } else {
      const resp = await fetch(url, fetchOptions);
      yield* this.parseSSEStream(resp);
    }
  }

  /**
   * 从服务端获取 access_token，返回原始数据
   *
   * 底层接口，不做任何缓存。开发者可根据 expiresIn 自行实现缓存策略。
   * 仅在 ACCESS_TOKEN 模式下可用。
   */
  async fetchAccessToken(): Promise<TokenInfo> {
    if (this.authMode !== AuthMode.ACCESS_TOKEN) {
      throw new AuthenticationError('fetchAccessToken is only available in ACCESS_TOKEN mode');
    }

    const timestamp = Math.floor(Date.now() / 1000);
    const sigStr = buildSignatureString(this.appId!, this.appKey!, timestamp);
    const sign = rsaSign(sigStr, this.privateKey!);

    const resp = await fetch(`${this.baseUrl}${ACCESS_TOKEN_ENDPOINT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: this.appId, timestamp, sign }),
      signal: AbortSignal.timeout(this.timeoutMs),
    });

    const data = await resp.json() as Record<string, any>;
    const code = data.code ?? -1;
    if (code !== 0) {
      throw new AuthenticationError(
        `failed to get access_token: code=${code}, message=${data.message ?? 'Unknown error'}`,
      );
    }

    const tokenData = data.data;
    if (!tokenData) {
      throw new AuthenticationError('response missing data field');
    }

    return {
      accessToken: tokenData.access_token,
      expiresIn: tokenData.expires_in,
    };
  }

  // ===== 内部方法 =====

  private async *parseSSEStream(resp: globalThis.Response): AsyncGenerator<string, void, unknown> {
    if (!resp.ok) {
      throw new NetworkError(`stream request failed with status ${resp.status}`);
    }
    if (!resp.body) {
      throw new NetworkError('stream response has no body');
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // 保留最后一个可能不完整的行
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;
          let payload = trimmed.substring(5);
          if (payload.startsWith(' ')) payload = payload.substring(1);
          yield payload;
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  private async doRequest(
    method: HttpMethod,
    path: string,
    params?: Record<string, any> | null,
    body?: Record<string, any> | null,
    accessToken?: string,
  ): Promise<Record<string, any>> {
    let url = `${this.baseUrl}${path}`;
    const headers = this.getHeaders(accessToken);

    const fetchOptions: RequestInit = {
      method,
      headers,
      signal: AbortSignal.timeout(this.timeoutMs),
    };

    if (method === HttpMethod.GET && params) {
      const searchParams = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        searchParams.set(k, String(v));
      }
      const separator = url.includes('?') ? '&' : '?';
      url = `${url}${separator}${searchParams.toString()}`;
    } else if (method === HttpMethod.POST && body) {
      fetchOptions.body = JSON.stringify(body);
    }

    try {
      const resp = await fetch(url, fetchOptions);
      const text = await resp.text();
      try {
        return JSON.parse(text);
      } catch {
        return { code: -1, message: text, data: null };
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        throw new NetworkError('request timed out');
      }
      throw new NetworkError(`request failed: ${e.message}`);
    }
  }

  private getHeaders(accessToken?: string): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (this.authMode === AuthMode.ACCESS_TOKEN) {
      if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;
    } else if (this.authMode === AuthMode.API_KEY) {
      headers['X-Api-Key'] = this.apiKey!;
    }

    return headers;
  }

  /**
   * 获取 access_token（带异步缓存和刷新）
   */
  private async ensureAccessToken(): Promise<string> {
    const now = Date.now();
    if (this.accessToken && now < this.tokenExpiresAt - TOKEN_REFRESH_BUFFER_MS) {
      return this.accessToken;
    }
    if (this.cache) {
      const cached = this.cache.get(this.appId!);
      if (cached) {
        this.accessToken = cached;
        this.tokenExpiresAt = now + 600_000;
        return cached;
      }
    }

    // 使用 promise 去重，防止并发刷新
    if (!this.tokenPromise) {
      this.tokenPromise = this.refreshAccessToken().finally(() => {
        this.tokenPromise = undefined;
      });
    }
    return this.tokenPromise;
  }

  private async refreshAccessToken(): Promise<string> {
    const info = await this.fetchAccessToken();
    this.accessToken = info.accessToken;
    this.tokenExpiresAt = Date.now() + info.expiresIn * 1000;
    if (this.cache) {
      this.cache.set(this.appId!, this.accessToken, info.expiresIn);
    }
    return this.accessToken;
  }
}
