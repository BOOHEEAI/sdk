/**
 * SDK 基础异常
 */
export class BooheeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BooheeError';
  }
}

/**
 * 认证异常（签名错误、token 无效等）
 */
export class AuthenticationError extends BooheeError {
  constructor(message: string) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

/**
 * API 返回业务错误
 */
export class ApiError extends BooheeError {
  readonly code: number;

  constructor(code: number, message: string) {
    super(`api error ${code}: ${message}`);
    this.name = 'ApiError';
    this.code = code;
  }
}

/**
 * 网络异常（超时、连接失败等）
 */
export class NetworkError extends BooheeError {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}
