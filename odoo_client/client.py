import xmlrpc.client
from config.settings import settings
import ssl

context = ssl._create_unverified_context()

def odoo_login(username: str, password: str) -> int:
    common = xmlrpc.client.ServerProxy(f"{settings.ODOO_URL}/xmlrpc/2/common", context=context)
    uid = common.authenticate(settings.ODOO_DB, username, password, {})
    if not uid:
        raise ValueError("Login gagal: username atau password salah")
    return uid
