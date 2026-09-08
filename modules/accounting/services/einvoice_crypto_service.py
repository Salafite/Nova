import base64
import hashlib
from typing import Optional, Tuple, Union
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding
from cryptography.hazmat.backends import default_backend


class EInvoiceCryptoService:
    """Cryptographic operations service for e-invoicing compliance (ZATCA / Tax XML hashing and signing)."""

    GENESIS_PIH = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjAzZTQ4MmUwNzMzYTJhNw=="

    @staticmethod
    def compute_sha256_hash(content: Union[str, bytes]) -> str:
        """Compute Base64-encoded SHA-256 hash of canonicalized content."""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        digest = hashlib.sha256(content_bytes).digest()
        return base64.b64encode(digest).decode("ascii")

    @staticmethod
    def compute_hex_sha256_hash(content: Union[str, bytes]) -> str:
        """Compute Hex-encoded SHA-256 hash."""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        return hashlib.sha256(content_bytes).hexdigest()

    @staticmethod
    def get_genesis_pih() -> str:
        """Return standard genesis Previous Invoice Hash (PIH) for the first invoice in a chain."""
        return EInvoiceCryptoService.GENESIS_PIH

    @staticmethod
    def generate_ecdsa_keypair() -> Tuple[str, str]:
        """Generate a secp256k1 ECDSA private and public key pair in PEM format."""
        private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")

        public_key = private_key.public_key()
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        return priv_pem, pub_pem

    @staticmethod
    def sign_invoice_hash(invoice_hash_base64: str, private_key_pem: str) -> str:
        """Sign a Base64 invoice hash using ECDSA or RSA private key and return Base64 signature."""
        priv_bytes = private_key_pem.strip().encode("utf-8")
        private_key = serialization.load_pem_private_key(priv_bytes, password=None, backend=default_backend())

        # Decode hash to raw bytes for signing
        data_to_sign = base64.b64decode(invoice_hash_base64)

        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            signature = private_key.sign(data_to_sign, ec.ECDSA(hashes.SHA256()))
        elif isinstance(private_key, rsa.RSAPrivateKey):
            signature = private_key.sign(
                data_to_sign,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        else:
            raise ValueError(f"Unsupported private key type: {type(private_key)}")

        return base64.b64encode(signature).decode("ascii")

    @staticmethod
    def verify_invoice_signature(invoice_hash_base64: str, signature_base64: str, public_key_pem: str) -> bool:
        """Verify an ECDSA or RSA digital signature against the invoice hash."""
        try:
            pub_bytes = public_key_pem.strip().encode("utf-8")
            public_key = serialization.load_pem_public_key(pub_bytes, backend=default_backend())
            data_to_verify = base64.b64decode(invoice_hash_base64)
            signature = base64.b64decode(signature_base64)

            if isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, data_to_verify, ec.ECDSA(hashes.SHA256()))
                return True
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    data_to_verify,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def embed_signature_in_ubl_xml(
        ubl_xml: str,
        signature_base64: str,
        certificate_pem: Optional[str] = None,
    ) -> str:
        """Embed digital signature into UBL Extension Content in UBL 2.1 XML document."""
        try:
            root = ET.fromstring(ubl_xml)
            namespaces = {
                "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
                "ds": "http://www.w3.org/2000/09/xmldsig#",
            }
            
            ext_content = root.find(".//ext:ExtensionContent", namespaces)
            if ext_content is not None:
                # Clear any existing child
                for child in list(ext_content):
                    ext_content.remove(child)

                # Construct ds:Signature block
                sig_elem = ET.SubElement(ext_content, "ds:Signature", {"xmlns:ds": "http://www.w3.org/2000/09/xmldsig#"})
                sig_val = ET.SubElement(sig_elem, "ds:SignatureValue")
                sig_val.text = signature_base64

                if certificate_pem:
                    key_info = ET.SubElement(sig_elem, "ds:KeyInfo")
                    x509_data = ET.SubElement(key_info, "ds:X509Data")
                    x509_cert = ET.SubElement(x509_data, "ds:X509Certificate")
                    # Strip headers/newlines from certificate PEM
                    cleaned_cert = "".join(
                        line.strip()
                        for line in certificate_pem.splitlines()
                        if not line.startswith("-----")
                    )
                    x509_cert.text = cleaned_cert

            return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        except Exception:
            # Fallback if XML parsing fails: return unchanged
            return ubl_xml
