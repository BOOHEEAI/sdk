/**
 * HTTP 方法
 */
export enum HttpMethod {
  GET = 'GET',
  POST = 'POST',
}

/**
 * 请求接口
 *
 * 开发者实现此接口定义 API 请求，通过 client.execute(req) 统一执行。
 */
export interface Request {
  /** 获取 HTTP 方法 */
  getMethod(): HttpMethod;

  /** 获取 API 路径，如 '/open-apis/v1/food/search' */
  getUrl(): string;

  /** 获取查询参数（GET 请求使用），可为 null */
  getQueryParams?(): Record<string, any> | null;

  /** 获取请求体（POST 请求使用），可为 null */
  getBody?(): Record<string, any> | null;
}
