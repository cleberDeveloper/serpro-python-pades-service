import base64
import hashlib
from io import BytesIO

from asn1crypto import x509
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import fields
from pyhanko.sign.signers import Signer
from pyhanko.sign.signers.pdf_signer import PdfSigner, PdfSignatureMetadata
from pyhanko_certvalidator.registry import SimpleCertificateStore

from .logger import log
from .serpro_client import assinar_hash_serpro


def _pem_to_asn1_certs(pem_data: str):
    certs = []
    current = []
    inside = False

    for line in pem_data.splitlines():
        if "BEGIN CERTIFICATE" in line:
            inside = True
            current = []
        elif "END CERTIFICATE" in line:
            der = base64.b64decode("".join(current))
            certs.append(x509.Certificate.load(der))
            inside = False
        elif inside:
            current.append(line.strip())

    if not certs:
        certs.append(x509.Certificate.load(base64.b64decode(pem_data)))

    return certs


class SerproRemoteSigner(Signer):
    def __init__(
        self,
        *,
        access_token: str,
        protocolo: str,
        alias: str,
        certificate_pem: str,
    ):
        certs = _pem_to_asn1_certs(certificate_pem)

        self.access_token = access_token
        self.protocolo = protocolo
        self.alias = alias

        store = SimpleCertificateStore()

        for cert in certs[1:]:
            store.register(cert)

        super().__init__(
            signing_cert=certs[0],
            cert_registry=store,
            signature_mechanism=None,
        )

    async def async_sign_raw(self, data: bytes, digest_algorithm: str, dry_run=False) -> bytes:
        if dry_run:
            return bytes(256)

        digest_name = digest_algorithm.lower().replace("-", "")

        if digest_name not in ("sha256", "sha256rsa", "sha256_rsa"):
            raise RuntimeError(f"Algoritmo não suportado neste serviço: {digest_algorithm}")

        hash_base64 = base64.b64encode(hashlib.sha256(data).digest()).decode()

        log(
            self.protocolo,
            "SERPRO_SIGNATURE",
            "Enviando hash pyHanko para assinatura RAW",
            {
                "alias": self.alias,
                "hashBase64": hash_base64,
            },
        )

        raw_signature_b64 = await assinar_hash_serpro(
            self.access_token,
            self.protocolo,
            self.alias,
            hash_base64,
        )

        clean = raw_signature_b64.strip().replace("-", "+").replace("_", "/")
        clean += "=" * (-len(clean) % 4)

        return base64.b64decode(clean)


async def assinar_pdf_pades(
    *,
    pdf_base64: str,
    certificate_pem: str,
    access_token: str,
    protocolo: str,
    alias: str,
) -> str:
    input_pdf = base64.b64decode(pdf_base64)

    signer = SerproRemoteSigner(
        access_token=access_token,
        protocolo=protocolo,
        alias=alias,
        certificate_pem=certificate_pem,
    )

    metadata = PdfSignatureMetadata(
        field_name="Signature1",
        md_algorithm="sha256",
        subfilter=fields.SigSeedSubFilter.PADES,
    )

    pdf_signer = PdfSigner(metadata, signer=signer)

    output = BytesIO()

    with BytesIO(input_pdf) as input_stream:
        writer = IncrementalPdfFileWriter(input_stream)
        await pdf_signer.async_sign_pdf(writer, output=output)

    return base64.b64encode(output.getvalue()).decode()
