import xmlrpc.client
from config.settings import settings

def odoo_login(username: str, password: str) -> int:
    common = xmlrpc.client.ServerProxy(f"{settings.ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(settings.ODOO_DB, username, password, {})
    if not uid:
        raise ValueError("Login gagal: username atau password salah")
    return uid
