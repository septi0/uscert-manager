from .certbot import CertbotProvider
from .openssl import OpenSslProvider

list = {
    'certbot': CertbotProvider,
    'openssl': OpenSslProvider,
}