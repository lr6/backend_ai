"""
第三阶段 · 15 HTTPS / SSL/TLS — 检验练习

练习已完成，可运行: .venv/bin/python practice.py
全部通过 = 15 HTTPS / SSL/TLS 过关 ✅
"""


# ===== 练习 1：HTTPS 提供的保护 =====
def https_protections(is_https: bool) -> set[str]:
    """
    返回 HTTPS 相比 HTTP 提供的安全属性。

    HTTPS 提供：confidentiality（机密性）、integrity（完整性）、
    authentication（服务器身份认证）。HTTP 不提供这些 TLS 保护。

    例如:
        https_protections(True) -> {"confidentiality", "integrity", "authentication"}
        https_protections(False) -> set()
    """
    if is_https:
        return {"confidentiality", "integrity", "authentication"}
    return set()


# ===== 练习 2：服务器证书验证 =====
def validate_certificate(
    requested_host: str,
    certificate_host: str,
    trusted: bool,
    expired: bool,
) -> str:
    """
    根据主机名匹配、信任链和有效期，判断客户端是否接受服务器证书。

    返回 "accepted" 或具体错误："hostname_mismatch"、"untrusted"、"expired"。
    验证顺序：先比主机名，再检查信任链，最后检查有效期。

    例如:
        validate_certificate("api.example.com", "api.example.com", True, False)
        -> "accepted"
        validate_certificate("evil.example", "api.example.com", True, False)
        -> "hostname_mismatch"
    """
    if requested_host != certificate_host:
        return "hostname_mismatch"
    if not trusted:
        return "untrusted"
    if expired:
        return "expired"
    return "accepted"


# ===== 练习 3：TLS 握手步骤 =====
def tls_handshake_steps() -> list[str]:
    """
    返回简化 TLS 握手中客户端与服务器完成身份验证、协商密钥的步骤。

    按顺序返回：
    ["client_hello", "server_hello", "certificate",
     "certificate_validation", "key_agreement", "secure_application_data"]

    例如:
        tls_handshake_steps()[0] -> "client_hello"
    """
    return [
        "client_hello",
        "server_hello",
        "certificate",
        "certificate_validation",
        "key_agreement",
        "secure_application_data",
    ]


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    def check(label, actual, expected):
        if actual != expected:
            errors.append(f"{label}: 期望 {expected!r}，实际 {actual!r}")
        else:
            print(f"✅ {label}")

    protections = {"confidentiality", "integrity", "authentication"}
    check("练习1 HTTPS", https_protections(True), protections)
    check("练习1 HTTP", https_protections(False), set())

    check("练习2 正常证书", validate_certificate("api.example.com", "api.example.com", True, False), "accepted")
    check("练习2 主机名不匹配", validate_certificate("evil.example", "api.example.com", True, False), "hostname_mismatch")
    check("练习2 不受信任", validate_certificate("api.example.com", "api.example.com", False, False), "untrusted")
    check("练习2 已过期", validate_certificate("api.example.com", "api.example.com", True, True), "expired")
    check("练习2 多项错误按顺序判断", validate_certificate("evil.example", "api.example.com", False, True), "hostname_mismatch")

    expected_steps = [
        "client_hello",
        "server_hello",
        "certificate",
        "certificate_validation",
        "key_agreement",
        "secure_application_data",
    ]
    check("练习3 握手步骤", tls_handshake_steps(), expected_steps)

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for error in errors:
            print("  ❌ " + error)
    else:
        print("🎉 全部通过！15 HTTPS / SSL/TLS = ✅")
