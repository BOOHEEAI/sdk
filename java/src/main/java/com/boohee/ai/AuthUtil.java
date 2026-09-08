package com.boohee.ai;

import org.bouncycastle.jce.provider.BouncyCastleProvider;

import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.Security;
import java.security.spec.RSAPrivateCrtKeySpec;
import java.util.Base64;

/**
 * 签名工具
 */
public class AuthUtil {

    static {
        if (Security.getProvider(BouncyCastleProvider.PROVIDER_NAME) == null) {
            Security.addProvider(new BouncyCastleProvider());
        }
    }

    /**
     * 构造签名串
     *
     * 格式: appKey + "app_id" + appId + "timestamp" + timestamp + appKey
     */
    public static String buildSignatureString(String appId, String appKey, long timestamp) {
        return appKey + "app_id" + appId + "timestamp" + timestamp + appKey;
    }

    /**
     * RSA-PSS + SHA256 签名
     *
     * @param plaintext    待签名的字符串
     * @param privateKeyPem RSA 私钥 PEM 格式字符串
     * @return Base64 编码的签名字符串
     */
    public static String rsaSign(String plaintext, String privateKeyPem) throws Exception {
        String pem = privateKeyPem
                .replace("-----BEGIN RSA PRIVATE KEY-----", "")
                .replace("-----END RSA PRIVATE KEY-----", "")
                .replace("-----BEGIN PRIVATE KEY-----", "")
                .replace("-----END PRIVATE KEY-----", "")
                .replaceAll("\\s+", "");

        byte[] keyBytes = Base64.getDecoder().decode(pem);
        KeyFactory keyFactory = KeyFactory.getInstance("RSA", "BC");
        PrivateKey privateKey;
        try {
            // PKCS#1
            org.bouncycastle.asn1.pkcs.RSAPrivateKey rsaKey =
                    org.bouncycastle.asn1.pkcs.RSAPrivateKey.getInstance(keyBytes);
            privateKey = keyFactory.generatePrivate(
                    new RSAPrivateCrtKeySpec(
                            rsaKey.getModulus(),
                            rsaKey.getPublicExponent(),
                            rsaKey.getPrivateExponent(),
                            rsaKey.getPrime1(),
                            rsaKey.getPrime2(),
                            rsaKey.getExponent1(),
                            rsaKey.getExponent2(),
                            rsaKey.getCoefficient()));
        } catch (Exception e) {
            // PKCS#8
            privateKey = keyFactory.generatePrivate(
                    new java.security.spec.PKCS8EncodedKeySpec(keyBytes));
        }

        Signature sig = Signature.getInstance("SHA256withRSA/PSS", "BC");
        sig.setParameter(new java.security.spec.PSSParameterSpec(
                "SHA-256", "MGF1",
                java.security.spec.MGF1ParameterSpec.SHA256,
                32, 1));
        sig.initSign(privateKey);
        sig.update(plaintext.getBytes("UTF-8"));
        return Base64.getEncoder().encodeToString(sig.sign());
    }
}
