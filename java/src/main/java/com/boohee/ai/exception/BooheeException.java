package com.boohee.ai.exception;

/**
 * SDK 基础异常
 */
public class BooheeException extends RuntimeException {
    public BooheeException(String message) {
        super(message);
    }

    public BooheeException(String message, Throwable cause) {
        super(message, cause);
    }
}
