from datetime import date
from typing import Any, Dict

def preprocess_odoo_data(data: dict) -> dict:
    processed = {}

    for k, v in data.items():
        if isinstance(v, date):
            processed[k] = v.isoformat()
        elif isinstance(v, list) and all(isinstance(i, int) for i in v):
            # Anggap ini field many2many, ubah ke (6, 0, [...])
            processed[k] = [(6, 0, v)]
        else:
            processed[k] = v
    return processed

def normalize_relations(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ubah relasi many2one & many2many ke list atau int ID saja."""
    cleaned = {}
    for field, value in record.items():
        if isinstance(value, list):
            if len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], str):
                # Many2one: [id, name]
                cleaned[field] = value[0]
            elif value and isinstance(value[0], tuple):
                # Many2many: [(id, name), ...]
                cleaned[field] = [v[0] for v in value]
            else:
                cleaned[field] = value
        else:
            cleaned[field] = value
    return cleaned