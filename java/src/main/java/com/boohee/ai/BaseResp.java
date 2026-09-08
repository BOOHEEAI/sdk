package com.boohee.ai;

import com.boohee.ai.exception.ApiException;

import java.util.Map;

/**
 * API 响应
 *
 * 包装统一的响应结构: {code, message, now, data}
 */
public class BaseResp {

    private final int code;
    private final String message;
    private final long now;
    private final Map<String, Object> data;

    public BaseResp(int code, String message, long now, Map<String, Object> data) {
        this.code = code;
        this.message = message;
        this.now = now;
        this.data = data;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    public long getNow() {
        return now;
    }

    public Map<String, Object> getData() {
        return data;
    }

    /**
     * 判断请求是否成功（code == 0）
     */
    public boolean isSuccess() {
        return code == 0;
    }

    /**
     * 如果请求失败则抛出 ApiException
     */
    public void raiseForError() {
        if (!isSuccess()) {
            throw new ApiException(code, message);
        }
    }

    /**
     * 从 data 中获取字段
     */
    @SuppressWarnings("unchecked")
    public <T> T get(String key) {
        if (data == null) {
            return null;
        }
        return (T) data.get(key);
    }

    /**
     * 从 data 中获取字段，带默认值
     */
    @SuppressWarnings("unchecked")
    public <T> T get(String key, T defaultValue) {
        if (data == null) {
            return defaultValue;
        }
        Object value = data.get(key);
        return value != null ? (T) value : defaultValue;
    }

    @Override
    public String toString() {
        return "BaseResp(code=" + code + ", message=" + message + ")";
    }
}
