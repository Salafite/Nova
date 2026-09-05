import pytest
import base64
from modules.accounting.services.tlv_qr_service import (
    encode_tlv_item,
    encode_tlv,
    encode_tlv_base64,
    decode_tlv,
    generate_zatca_qr_tlv,
)


def test_encode_tlv_item():
    item = encode_tlv_item(1, "Nova")
    assert item[0] == 1
    assert item[1] == 4
    assert item[2:] == b"Nova"


def test_encode_decode_roundtrip():
    tags = {
        1: "Nova Wholesale Store",
        2: "310123456700003",
        3: "2026-09-05T08:00:00Z",
        4: "115.00",
        5: "15.00",
    }
    b64 = encode_tlv_base64(tags)
    decoded = decode_tlv(b64)

    assert decoded[1].decode("utf-8") == "Nova Wholesale Store"
    assert decoded[2].decode("utf-8") == "310123456700003"
    assert decoded[3].decode("utf-8") == "2026-09-05T08:00:00Z"
    assert decoded[4].decode("utf-8") == "115.00"
    assert decoded[5].decode("utf-8") == "15.00"


def test_generate_zatca_qr_tlv():
    qr_b64 = generate_zatca_qr_tlv(
        seller_name="Al-Madina Hypermarket",
        vat_number="300000000000003",
        timestamp="2026-09-05T12:00:00Z",
        total_amount=230.00,
        vat_total=30.00,
        invoice_hash="47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=",
    )

    assert isinstance(qr_b64, str)
    decoded = decode_tlv(qr_b64)
    assert decoded[1].decode("utf-8") == "Al-Madina Hypermarket"
    assert decoded[2].decode("utf-8") == "300000000000003"
    assert decoded[4].decode("utf-8") == "230.00"
    assert decoded[5].decode("utf-8") == "30.00"
    assert decoded[6].decode("utf-8") == "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="
