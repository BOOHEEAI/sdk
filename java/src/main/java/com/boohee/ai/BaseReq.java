package com.boohee.ai;

import java.util.Map;

/**
 * 请求接口
 *
 * 开发者实现此接口定义 API 请求，通过 {@link BooheeClient#execute(BaseReq)} 统一执行。
 */
public interface BaseReq {

    /**
     * 获取 HTTP 方法
     */
    HttpMethod getMethod();

    /**
     * 获取 API 路径，如 "/open-apis/v1/food/search"
     */
    String getUrl();

    /**
     * 获取查询参数（GET 请求使用），可为 null
     */
    default Map<String, Object> getQueryParams() {
        return null;
    }

    /**
     * 获取请求体（POST 请求使用），可为 null
     */
    default Map<String, Object> getBody() {
        return null;
    }
}
