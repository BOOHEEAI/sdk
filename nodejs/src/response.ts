import { ApiError } from './errors';

/**
 * API 响应
 *
 * 包装统一的响应结构: {code, message, now, data}
 */
export class Response {
  readonly code: number;
  readonly message: string;
  readonly now: number;
  readonly data: Record<string, any> | null;

  constructor(raw: { code?: number; message?: string; now?: number; data?: Record<string, any> | null }) {
    this.code = raw.code ?? -1;
    this.message = raw.message ?? '';
    this.now = raw.now ?? 0;
    this.data = raw.data ?? null;
  }

  /** 判断请求是否成功（code == 0） */
  isSuccess(): boolean {
    return this.code === 0;
  }

  /** 如果请求失败则抛出 ApiError */
  raiseForError(): void {
    if (!this.isSuccess()) {
      throw new ApiError(this.code, this.message);
    }
  }

  /** 从 data 中获取字段 */
  get<T = any>(key: string, defaultValue?: T): T | undefined {
    if (this.data == null) return defaultValue;
    return (this.data[key] as T) ?? defaultValue;
  }

  toString(): string {
    return `Response(code=${this.code}, message=${this.message})`;
  }
}
