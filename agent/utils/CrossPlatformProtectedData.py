from ctypes import (
    windll,
    Structure,
    POINTER,
    byref,
    c_char,
    c_uint,
    create_string_buffer,
    cast,
    pointer,
)
from ctypes.wintypes import DWORD, LPVOID
import base64


# 定义结构体
class DATA_BLOB(Structure):
    _fields_ = [("cbData", DWORD), ("pbData", POINTER(c_char))]


crypt32 = windll.crypt32
kernel32 = windll.kernel32


def decrypt_data_protectedData(encrypted_data: str, entropy: bytes = None) -> bytes:
    """
    使用Windows DPAPI解密数据

    Args:
        encrypted_data: Base64编码的加密数据
        entropy: 可选的熵值（必须与加密时一致）

    Returns:
        解密后的字节数据
    """
    # 解码Base64数据
    encrypted_bytes = base64.b64decode(encrypted_data)

    # 创建输入数据结构
    input_blob = DATA_BLOB()
    input_blob.cbData = len(encrypted_bytes)
    input_blob.pbData = cast(create_string_buffer(encrypted_bytes), POINTER(c_char))

    # 创建熵数据结构（如果提供）
    entropy_blob = None
    if entropy:
        entropy_blob = DATA_BLOB()
        entropy_blob.cbData = len(entropy)
        entropy_blob.pbData = cast(create_string_buffer(entropy), POINTER(c_char))

    # 输出数据结构
    output_blob = DATA_BLOB()

    # 调用CryptUnprotectData
    result = crypt32.CryptUnprotectData(
        byref(input_blob),
        None,  # ppszDataDescr
        entropy_blob,
        None,  # pvReserved
        None,  # pDataStruct
        0,  # dwFlags
        byref(output_blob),
    )

    if not result:
        raise Exception("Failed to decrypt data")

    # 获取解密结果
    decrypted_data = output_blob.pbData[: output_blob.cbData]

    # 清理内存
    kernel32.LocalFree(output_blob.pbData)

    return decrypted_data


def encrypt_data_protectedData(data: bytes, entropy: bytes = None) -> str:
    """
    使用Windows DPAPI加密数据

    Args:
        data: 要加密的字节数据
        entropy: 可选的熵值，增加加密强度

    Returns:
        Base64编码的加密数据
    """
    # 创建输入数据结构
    input_blob = DATA_BLOB()
    input_blob.cbData = len(data)
    input_blob.pbData = cast(create_string_buffer(data), POINTER(c_char))

    # 创建熵数据结构（如果提供）
    entropy_blob = None
    if entropy:
        entropy_blob = DATA_BLOB()
        entropy_blob.cbData = len(entropy)
        entropy_blob.pbData = cast(create_string_buffer(entropy), POINTER(c_char))

    # 输出数据结构
    output_blob = DATA_BLOB()

    # 调用CryptProtectData
    result = crypt32.CryptProtectData(
        byref(input_blob),
        None,  # ppszDataDescr
        entropy_blob,
        None,  # pvReserved
        None,  # pDataStruct
        0,  # dwFlags
        byref(output_blob),
    )

    if not result:
        raise Exception("Failed to encrypt data")

    # 获取加密结果
    encrypted_data = output_blob.pbData[: output_blob.cbData]

    # 清理内存
    kernel32.LocalFree(output_blob.pbData)

    # 返回Base64编码的数据
    return base64.b64encode(encrypted_data).decode("utf-8")
