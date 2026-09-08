import base64
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from modules.accounting.services.einvoice_crypto_service import EInvoiceCryptoService


def test_compute_sha256_hash():
    content_str = "<Invoice>Test Content</Invoice>"
    hash_b64 = EInvoiceCryptoService.compute_sha256_hash(content_str)
    assert isinstance(hash_b64, str)
    assert len(hash_b64) > 0

    # Byte input test
    content_bytes = content_str.encode("utf-8")
    hash_b64_bytes = EInvoiceCryptoService.compute_sha256_hash(content_bytes)
    assert hash_b64 == hash_b64_bytes

    # Hex test
    hex_hash = EInvoiceCryptoService.compute_hex_sha256_hash(content_str)
    assert len(hex_hash) == 64
    assert all(c in "0123456789abcdef" for c in hex_hash)


def test_get_genesis_pih():
    genesis_pih = EInvoiceCryptoService.get_genesis_pih()
    assert genesis_pih == EInvoiceCryptoService.GENESIS_PIH
    assert len(genesis_pih) > 0
    # Must be valid base64
    decoded = base64.b64decode(genesis_pih)
    assert len(decoded) > 0


def test_generate_ecdsa_keypair():
    priv_pem, pub_pem = EInvoiceCryptoService.generate_ecdsa_keypair()

    assert "-----BEGIN PRIVATE KEY-----" in priv_pem
    assert "-----END PRIVATE KEY-----" in priv_pem
    assert "-----BEGIN PUBLIC KEY-----" in pub_pem
    assert "-----END PUBLIC KEY-----" in pub_pem


def test_sign_and_verify_ecdsa_signature():
    priv_pem, pub_pem = EInvoiceCryptoService.generate_ecdsa_keypair()
    content = "<Invoice><ID>INV-001</ID></Invoice>"
    invoice_hash_b64 = EInvoiceCryptoService.compute_sha256_hash(content)

    # Sign
    signature_b64 = EInvoiceCryptoService.sign_invoice_hash(invoice_hash_b64, priv_pem)
    assert isinstance(signature_b64, str)
    assert len(signature_b64) > 0

    # Verify
    is_valid = EInvoiceCryptoService.verify_invoice_signature(
        invoice_hash_b64, signature_b64, pub_pem
    )
    assert is_valid is True

    # Tampered hash verification
    tampered_hash_b64 = EInvoiceCryptoService.compute_sha256_hash("<Invoice><ID>INV-TAMPERED</ID></Invoice>")
    is_valid_tampered = EInvoiceCryptoService.verify_invoice_signature(
        tampered_hash_b64, signature_b64, pub_pem
    )
    assert is_valid_tampered is False

    # Tampered signature verification
    invalid_sig_b64 = base64.b64encode(b"invalid_signature_bytes_1234567890").decode("ascii")
    assert EInvoiceCryptoService.verify_invoice_signature(invoice_hash_b64, invalid_sig_b64, pub_pem) is False


def test_sign_and_verify_rsa_signature():
    # Generate RSA Keypair
    rsa_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    priv_pem = rsa_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub_pem = rsa_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    content = "<Invoice><ID>INV-RSA-001</ID></Invoice>"
    invoice_hash_b64 = EInvoiceCryptoService.compute_sha256_hash(content)

    signature_b64 = EInvoiceCryptoService.sign_invoice_hash(invoice_hash_b64, priv_pem)
    assert isinstance(signature_b64, str)

    is_valid = EInvoiceCryptoService.verify_invoice_signature(
        invoice_hash_b64, signature_b64, pub_pem
    )
    assert is_valid is True


def test_embed_signature_in_ubl_xml():
    sample_ubl_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
        'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
        'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" '
        'xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">\n'
        '  <ext:UBLExtensions>\n'
        '    <ext:UBLExtension>\n'
        '      <ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:enveloped:xades</ext:ExtensionURI>\n'
        '      <ext:ExtensionContent/>\n'
        '    </ext:UBLExtension>\n'
        '  </ext:UBLExtensions>\n'
        '  <cbc:ID>INV-1001</cbc:ID>\n'
        '</Invoice>'
    )
    sig_b64 = "MEQCIAz9xyzEXAMPLE_SIG_123456=="
    cert_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIB+zCCAXWgAwIBAgIUEXAMPLECERTIFICATE1234567890==\n"
        "-----END CERTIFICATE-----\n"
    )

    signed_xml = EInvoiceCryptoService.embed_signature_in_ubl_xml(
        ubl_xml=sample_ubl_xml,
        signature_base64=sig_b64,
        certificate_pem=cert_pem,
    )

    assert "ds:Signature" in signed_xml
    assert f"<ds:SignatureValue>{sig_b64}</ds:SignatureValue>" in signed_xml
    assert "MIIB+zCCAXWgAwIBAgIUEXAMPLECERTIFICATE1234567890==" in signed_xml
    assert "<ds:X509Certificate>" in signed_xml


def test_embed_signature_invalid_xml_fallback():
    invalid_xml = "not an xml string <<>>"
    sig_b64 = "sig123"
    result = EInvoiceCryptoService.embed_signature_in_ubl_xml(invalid_xml, sig_b64)
    assert result == invalid_xml
