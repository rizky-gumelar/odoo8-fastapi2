import xmlrpc.client
from config.settings import settings
import ssl

context = ssl._create_unverified_context()

class OdooModel:
    def __init__(self, model: str, uid: int, username: str, password: str):
        self.uid = uid
        self.username = username
        self.password = password
        self.model = model
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        # self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        self.models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object", allow_none=True,
            context=context
        )

    def call(self, method_name, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            method_name,
            args,
            kwargs
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

    def call2(self, method, ids=None, *args):
        """
        Memanggil method pada model atau record Odoo.
        - ids: list of record IDs (untuk method instance)
        - args: positional args untuk method tersebut
        """
        if ids is None:
            ids = []

        # Jangan bungkus sebagai list kalau memang hanya satu
        call_ids = ids
        if isinstance(ids, list) and len(ids) == 1:
            call_ids = ids[0]  # Kirim sebagai scalar

        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            self.model,
            method,
            [call_ids] + list(args)
        )