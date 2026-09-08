from boohee_sdk.auth import AuthMode


def test_auth_mode_values():
    """测试认证模式枚举值"""
    assert AuthMode.ACCESS_TOKEN.value == 'access_token'
    assert AuthMode.API_KEY.value == 'api_key'


def test_auth_mode_enum():
    """测试枚举类型"""
    mode = AuthMode.ACCESS_TOKEN
    assert isinstance(mode, AuthMode)
    assert mode.name == 'ACCESS_TOKEN'


def test_auth_mode_string_interop():
    """测试字符串互操作"""
    assert AuthMode.ACCESS_TOKEN == 'access_token'
    assert f"{AuthMode.API_KEY}" == 'api_key'


def test_auth_mode_lookup():
    """测试值查找"""
    assert AuthMode('access_token') == AuthMode.ACCESS_TOKEN
    assert AuthMode('api_key') == AuthMode.API_KEY


def test_auth_mode_invalid_value():
    """测试无效值"""
    import pytest
    with pytest.raises(ValueError):
        AuthMode('invalid')


def test_auth_mode_immutable():
    """测试不可变性"""
    import pytest
    with pytest.raises(AttributeError):
        AuthMode.ACCESS_TOKEN = 'changed'


def test_auth_mode_iteration():
    """测试迭代"""
    modes = list(AuthMode)
    assert len(modes) == 2
    assert AuthMode.ACCESS_TOKEN in modes
    assert AuthMode.API_KEY in modes


def test_auth_mode_identity():
    """测试身份唯一性"""
    assert AuthMode.ACCESS_TOKEN is AuthMode.ACCESS_TOKEN
    assert AuthMode.API_KEY is AuthMode.API_KEY


def test_rsa_sign_with_generated_key():
    """测试 RSA-PSS 签名(使用生成的测试私钥)"""
    from Crypto.PublicKey import RSA
    import base64
    from boohee_sdk.auth import rsa_sign

    # 生成 2048 位测试私钥
    key = RSA.generate(2048)
    private_key_pem = key.export_key().decode()

    message = "test_message"
    signature = rsa_sign(message, private_key_pem)

    # 验证签名是 Base64 编码的字符串
    assert isinstance(signature, str)
    # 验证可以 Base64 解码
    decoded = base64.b64decode(signature)
    assert len(decoded) > 0
    # RSA 2048 签名长度应为 256 字节
    assert len(decoded) == 256


def test_rsa_sign_verification_roundtrip():
    """测试签名可被正确验证"""
    from Crypto.PublicKey import RSA
    from Crypto.Signature import pss
    from Crypto.Hash import SHA256
    import base64
    from boohee_sdk.auth import rsa_sign

    key = RSA.generate(2048)
    private_pem = key.export_key().decode()
    public_pem = key.publickey().export_key().decode()

    message = "test_message"
    signature = rsa_sign(message, private_pem)

    # 验证签名
    pub_key = RSA.import_key(public_pem)
    h = SHA256.new(message.encode("utf-8"))
    # 不应抛出异常
    pss.new(pub_key).verify(h, base64.b64decode(signature))


def test_rsa_sign_invalid_pem():
    """测试无效私钥抛出异常"""
    import pytest
    from boohee_sdk.auth import rsa_sign

    with pytest.raises((ValueError, TypeError)):
        rsa_sign("test", "not-a-valid-pem")


def test_rsa_sign_public_key_not_private():
    """测试传入公钥应抛出异常"""
    import pytest
    from Crypto.PublicKey import RSA
    from boohee_sdk.auth import rsa_sign

    key = RSA.generate(2048)
    public_pem = key.publickey().export_key().decode()

    with pytest.raises((TypeError, ValueError)):
        rsa_sign("test", public_pem)


def test_rsa_sign_empty_string():
    """测试空字符串签名"""
    import base64
    from Crypto.PublicKey import RSA
    from boohee_sdk.auth import rsa_sign

    key = RSA.generate(2048)
    private_pem = key.export_key().decode()

    signature = rsa_sign("", private_pem)
    assert isinstance(signature, str)
    assert len(base64.b64decode(signature)) == 256


def test_rsa_sign_unicode_message():
    """测试 Unicode 消息签名"""
    from Crypto.PublicKey import RSA
    from boohee_sdk.auth import rsa_sign

    key = RSA.generate(2048)
    private_pem = key.export_key().decode()

    signature = rsa_sign("测试中文消息 🎉", private_pem)
    assert isinstance(signature, str)


def test_rsa_sign_different_messages():
    """测试相同密钥对不同消息产生不同签名"""
    from Crypto.PublicKey import RSA
    from boohee_sdk.auth import rsa_sign

    key = RSA.generate(2048)
    private_pem = key.export_key().decode()

    sig1 = rsa_sign("message1", private_pem)
    sig2 = rsa_sign("message2", private_pem)
    assert sig1 != sig2


def test_build_signature_string():
    """测试签名串构造"""
    from boohee_sdk.auth import build_signature_string

    app_id = "my_app_123"
    app_key = "my_secret_key_456"
    timestamp = 1234567890

    result = build_signature_string(app_id, app_key, timestamp)
    expected = "my_secret_key_456app_idmy_app_123timestamp1234567890my_secret_key_456"

    assert result == expected


def test_build_signature_string_with_real_data():
    """测试真实数据格式"""
    from boohee_sdk.auth import build_signature_string

    app_id = "test_app"
    app_key = "test_key"
    timestamp = 1694073600

    result = build_signature_string(app_id, app_key, timestamp)
    assert result.startswith("test_key")
    assert result.endswith("test_key")
    assert "app_idtest_app" in result
    assert "timestamp1694073600" in result


def test_build_signature_string_combined_with_sign():
    """测试签名串构造 + 签名组合"""
    import base64
    from Crypto.PublicKey import RSA
    from boohee_sdk.auth import build_signature_string, rsa_sign

    app_id = "test_app"
    app_key = "test_key"
    timestamp = 1694073600

    # 构造签名串
    sig_str = build_signature_string(app_id, app_key, timestamp)

    # 生成密钥并签名
    key = RSA.generate(2048)
    private_pem = key.export_key().decode()
    signature = rsa_sign(sig_str, private_pem)

    # 验证签名有效
    assert isinstance(signature, str)
    assert len(base64.b64decode(signature)) == 256
