package com.boohee.ai;

/**
 * 认证模式
 */
public enum AuthMode {
    ACCESS_TOKEN("access_token"),
    API_KEY("api_key");

    private final String value;

    AuthMode(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
