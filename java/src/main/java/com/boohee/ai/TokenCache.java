package com.boohee.ai;

/**
 * Token 缓存接口
 *
 * 开发者可以实现此接口自定义 token 存储方式
 */
public interface TokenCache {

    /**
     * 获取缓存的 token
     *
     * @param appId 应用 ID
     * @return 缓存的 token，不存在返回 null
     */
    String get(String appId);

    /**
     * 缓存 token
     *
     * @param appId     应用 ID
     * @param token     access_token
     * @param expiresIn 过期时间（秒）
     */
    void set(String appId, String token, long expiresIn);

    /**
     * 删除缓存的 token
     *
     * @param appId 应用 ID
     */
    void delete(String appId);
}
