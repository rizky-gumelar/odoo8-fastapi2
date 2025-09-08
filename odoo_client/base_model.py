import xmlrpc.client
from config.settings import settings
import socket

class TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout=5.0):
        super().__init__()
        self.timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self.timeout
        return conn

class OdooModel:
    def __init__(self, model: str, uid: int, username: str, password: str):
        self.uid = uid
        self.username = username
        self.password = password
        self.model = model
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        # self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        # self.models = xmlrpc.client.ServerProxy(
        #     f"{self.url}/xmlrpc/2/object", allow_none=True
        # )

        # TimeoutTransport
        self.models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object",
            allow_none=True,
            transport=TimeoutTransport(timeout=5.0)
        )

    def search_read(self, domain=None, fields=None, limit=10):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            'search_read',
            [domain or []],
            {'fields': fields or ['name'], 'limit': limit}
        )

    def create(self, values: dict):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            'create',
            [values]
        )

    def read(self, ids: list, fields=None):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            'read',
            [ids],
            {'fields': fields or ['name']}
        )

    def write(self, ids: list, values: dict):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            'write',
            [ids, values]
        )

    def unlink(self, ids: list):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            'unlink',
            [ids]
        )

    def search(self, domain=None, limit=10, offset=0, order=None):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            'search',
            [domain or []],
            {
                'limit': limit,
                'offset': offset,
                'order': order,
            }
        )
