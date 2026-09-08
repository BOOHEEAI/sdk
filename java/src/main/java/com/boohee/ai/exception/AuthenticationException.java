package com.boohee.ai.exception;

/**
 * 认证异常（签名错误、token 无效等）
 */
public class AuthenticationException extends BooheeException {
    public AuthenticationException(String message) {
        super(message);
    }

    public AuthenticationException(String message, Throwable cause) {
        super(message, cause);
    }
}
