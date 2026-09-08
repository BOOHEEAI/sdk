/**
 * Token 缓存接口
 *
 * 开发者可以实现此接口自定义 token 存储方式
 */
export interface TokenCache {
  get(appId: string): string | null;
  set(appId: string, token: string, expiresIn: number): void;
  delete(appId: string): void;
}
