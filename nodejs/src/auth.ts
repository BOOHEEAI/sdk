import * as crypto from 'crypto';

/**
 * 认证模式
 */
export enum AuthMode {
  ACCESS_TOKEN = 'access_token',
  API_KEY = 'api_key',
}

/**
 * 构造签名串
 *
 * 格式: appKey + "app_id" + appId + "timestamp" + timestamp + appKey
 */
export function buildSignatureString(appId: string, appKey: string, timestamp: number): string {
  return `${appKey}app_id${appId}timestamp${timestamp}${appKey}`;
}

/**
 * RSA-PSS + SHA256 签名
 *
 * @param plaintext 待签名的字符串
 * @param privateKeyPem RSA 私钥 PEM 格式字符串
 * @returns Base64 编码的签名字符串
 */
export function rsaSign(plaintext: string, privateKeyPem: string): string {
  const sign = crypto.createSign('RSA-SHA256');
  sign.update(plaintext);
  sign.end();

  // Node.js crypto.sign with RSA-PSS padding
  const signature = crypto.sign('RSA-SHA256', Buffer.from(plaintext), {
    key: privateKeyPem,
    padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
    saltLength: 32,
  });

  return signature.toString('base64');
}
