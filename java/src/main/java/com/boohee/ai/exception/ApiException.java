package com.boohee.ai.exception;

/**
 * API 返回业务错误
 */
public class ApiException extends BooheeException {
    private final int code;

    public ApiException(int code, String message) {
        super("api error " + code + ": " + message);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}
