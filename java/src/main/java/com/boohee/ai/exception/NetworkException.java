package com.boohee.ai.exception;

/**
 * 网络异常（超时、连接失败等）
 */
public class NetworkException extends BooheeException {
    public NetworkException(String message) {
        super(message);
    }

    public NetworkException(String message, Throwable cause) {
        super(message, cause);
    }
}
