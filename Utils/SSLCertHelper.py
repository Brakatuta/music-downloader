import os
import ssl
import certifi
from urllib.request import HTTPSHandler, build_opener, install_opener

# Set the default SSL context globally
def set_default_ssl_context():
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    https_handler = HTTPSHandler(context=context)
    opener = build_opener(https_handler)
    install_opener(opener)
    
    os.environ['SSL_CERT_FILE'] = certifi.where()
    ssl.default_ca_certs = certifi.where()
    
    print("Default SSL context set.")
