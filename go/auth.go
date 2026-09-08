package boohee

import (
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"fmt"
)

// AuthMode 认证模式
type AuthMode string

const (
	AuthModeAccessToken AuthMode = "access_token"
	AuthModeAPIKey      AuthMode = "api_key"
)

// BuildSignatureString 构造签名串
//
// 格式: appKey + "app_id" + appId + "timestamp" + timestamp + appKey
func BuildSignatureString(appID, appKey string, timestamp int64) string {
	return fmt.Sprintf("%sapp_id%stimestamp%d%s", appKey, appID, timestamp, appKey)
}

// RSASign 使用 RSA-PSS + SHA256 签名
//
// privateKeyPEM: RSA 私钥 PEM 格式字符串
// 返回 Base64 编码的签名字符串
func RSASign(plaintext string, privateKeyPEM string) (string, error) {
	block, _ := pem.Decode([]byte(privateKeyPEM))
	if block == nil {
		return "", fmt.Errorf("failed to decode PEM block")
	}

	key, err := x509.ParsePKCS1PrivateKey(block.Bytes)
	if err != nil {
		// 尝试 PKCS8 格式
		pkcs8Key, err2 := x509.ParsePKCS8PrivateKey(block.Bytes)
		if err2 != nil {
			return "", fmt.Errorf("failed to parse private key: %w", err)
		}
		var ok bool
		key, ok = pkcs8Key.(*rsa.PrivateKey)
		if !ok {
			return "", fmt.Errorf("private key is not RSA")
		}
	}

	hashed := sha256.Sum256([]byte(plaintext))
	signature, err := rsa.SignPSS(rand.Reader, key, crypto.SHA256, hashed[:], nil)
	if err != nil {
		return "", fmt.Errorf("failed to sign: %w", err)
	}

	return base64.StdEncoding.EncodeToString(signature), nil
}
