import base64
from datetime import datetime
from typing import Dict, Union, Optional, Any


def encode_tlv_item(tag: int, value: Union[str, bytes, float, int]) -> bytes:
    """Encode a single Tag-Length-Value (TLV) element.
    
    Tag: 1 byte (integer 1-255)
    Length: 1 byte (length of UTF-8 or raw bytes)
    Value: UTF-8 encoded string or raw bytes
    """
    if isinstance(value, (int, float)):
        val_bytes = f"{value:.2f}".encode("utf-8")
    elif isinstance(value, str):
        val_bytes = value.encode("utf-8")
    elif isinstance(value, bytes):
        val_bytes = value
    else:
        val_bytes = str(value).encode("utf-8")

    tag_byte = bytes([tag])
    length = len(val_bytes)
    
    # Standard single-byte length for ZATCA TLV tags
    if length <= 255:
        length_bytes = bytes([length])
    else:
        # Multi-byte length encoding if value exceeds 255 bytes
        length_bytes = bytes([255])
        val_bytes = val_bytes[:255]

    return tag_byte + length_bytes + val_bytes


def encode_tlv(tags: Dict[int, Union[str, bytes, float, int]]) -> bytes:
    """Encode a dictionary of tag IDs to values into concatenated TLV binary data."""
    tlv_data = bytearray()
    for tag in sorted(tags.keys()):
        val = tags[tag]
        if val is not None and val != "":
            tlv_data.extend(encode_tlv_item(tag, val))
    return bytes(tlv_data)


def encode_tlv_base64(tags: Dict[int, Union[str, bytes, float, int]]) -> str:
    """Encode tags to TLV binary and return standard Base64 string."""
    tlv_bytes = encode_tlv(tags)
    return base64.b64encode(tlv_bytes).decode("ascii")


def decode_tlv(data: Union[str, bytes]) -> Dict[int, bytes]:
    """Decode a Base64 string or raw bytes into a dictionary of {tag: value_bytes}."""
    if isinstance(data, str):
        raw_bytes = base64.b64decode(data)
    else:
        raw_bytes = data

    result: Dict[int, bytes] = {}
    idx = 0
    total_len = len(raw_bytes)

    while idx < total_len:
        if idx + 2 > total_len:
            break
        tag = raw_bytes[idx]
        length = raw_bytes[idx + 1]
        idx += 2
        value = raw_bytes[idx:idx + length]
        idx += length
        result[tag] = value

    return result


def generate_zatca_qr_tlv(
    seller_name: str,
    vat_number: str,
    timestamp: Union[str, datetime],
    total_amount: Union[float, str, int],
    vat_total: Union[float, str, int],
    invoice_hash: Optional[Union[str, bytes]] = None,
    ecdsa_signature: Optional[Union[str, bytes]] = None,
    public_key: Optional[Union[str, bytes]] = None,
    certificate_stamp: Optional[Union[str, bytes]] = None,
) -> str:
    """Generate compliant ZATCA / Tax QR Code Base64 TLV payload."""
    if isinstance(timestamp, datetime):
        ts_str = timestamp.isoformat()
        if not ts_str.endswith("Z") and "+" not in ts_str:
            ts_str += "Z"
    else:
        ts_str = str(timestamp)

    if isinstance(total_amount, (int, float)):
        tot_str = f"{float(total_amount):.2f}"
    else:
        tot_str = str(total_amount)

    if isinstance(vat_total, (int, float)):
        vat_str = f"{float(vat_total):.2f}"
    else:
        vat_str = str(vat_total)

    tags: Dict[int, Union[str, bytes]] = {
        1: seller_name,
        2: vat_number,
        3: ts_str,
        4: tot_str,
        5: vat_str,
    }

    if invoice_hash:
        tags[6] = invoice_hash
    if ecdsa_signature:
        tags[7] = ecdsa_signature
    if public_key:
        tags[8] = public_key
    if certificate_stamp:
        tags[9] = certificate_stamp

    return encode_tlv_base64(tags)
