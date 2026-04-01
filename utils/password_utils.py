import bcrypt

# bcrypt 密码最大长度为 72 字节
BCRYPT_MAX_PASSWORD_LENGTH = 72


def _truncate_password(password: str) -> bytes:
    """截断密码到72字节，确保在UTF-8字符边界"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) <= BCRYPT_MAX_PASSWORD_LENGTH:
        return password_bytes
    
    # 截断到72字节
    truncated_bytes = password_bytes[:BCRYPT_MAX_PASSWORD_LENGTH]
    # 找到最后一个完整的UTF-8字符边界
    # UTF-8字符的第一个字节：0xxxxxxx (ASCII) 或 11xxxxxx (多字节起始)
    # UTF-8字符的后续字节：10xxxxxx
    while truncated_bytes and (truncated_bytes[-1] & 0xC0) == 0x80:
        truncated_bytes = truncated_bytes[:-1]
    
    return truncated_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        # 截断密码（与hash时保持一致）
        password_bytes = _truncate_password(plain_password)
        # 验证密码
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"密码验证错误: {e}")
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # bcrypt 限制：密码不能超过 72 字节
    # 截断密码到72字节
    password_bytes = _truncate_password(password)
    
    # 生成盐并哈希密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 返回字符串格式的哈希值
    return hashed.decode('utf-8')

