from datetime import datetime, timezone
from bson import ObjectId

class PersonnelModel:
    def __init__(self, db):
        self.collection = db.personnel

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def _num(self, v, default=0.0):
        try:
            # handle strings with commas or spaces
            s = str(v).replace(',', '').strip()
            if s == '' or s.lower() == 'none':
                return float(default)
            return float(s)
        except Exception:
            return float(default)

    def _coerce_create(self, data: dict) -> dict:
        """Map inbound payload (possibly with legacy keys) to canonical fields."""
        d = data or {}
        # Accept both canonical and legacy keys
        full_name = d.get('fullName') or d.get('Name')
        rank = d.get('rank') or d.get('Rank')
        corps = d.get('corps') or d.get('Corps')
        fmn_unit = d.get('fmn_unit') or d.get('Fmn/Unit') or d.get('fmnUnit')
        basic_salary = d.get('basicSalary') if 'basicSalary' in d else d.get('BasicSalary')
        allowance = d.get('allowance') if 'allowance' in d else d.get('Allowance')
        deductions = d.get('deductions') if 'deductions' in d else d.get('Deductions')
        status = (d.get('status') or 'Active')

        doc = {
            'armyNumber': (d.get('armyNumber') or '').strip(),
            'fullName': (full_name or '').strip(),
            'rank': (rank or None) or None,
            'corps': (corps or None) or None,
            'fmn_unit': (fmn_unit or None) or None,
            'basicSalary': self._num(basic_salary, 0.0),
            'allowance': self._num(allowance, 0.0),
            'deductions': self._num(deductions, 0.0),
            'bankName': (d.get('bankName') or None) or None,
            'accountNumber': (str(d.get('accountNumber') or '').strip() or None),
            'status': status,
            'active': (str(status).strip().lower() == 'active'),
        }
        return doc

    def _coerce_update(self, data: dict) -> dict:
        """Return only provided fields mapped to canonical names, for $set update."""
        d = data or {}
        out = {}
        def set_if_present(keys, target, transform=lambda x: x):
            for k in keys:
                if k in d and d.get(k) is not None:
                    out[target] = transform(d.get(k))
                    return
        set_if_present(['armyNumber'], 'armyNumber', lambda v: str(v).strip())
        set_if_present(['fullName', 'Name'], 'fullName', lambda v: str(v).strip())
        set_if_present(['rank', 'Rank'], 'rank', lambda v: (str(v).strip() or None))
        set_if_present(['corps', 'Corps'], 'corps', lambda v: (str(v).strip() or None))
        set_if_present(['fmn_unit', 'Fmn/Unit', 'fmnUnit'], 'fmn_unit', lambda v: (str(v).strip() or None))
        set_if_present(['basicSalary', 'BasicSalary'], 'basicSalary', lambda v: self._num(v, 0.0))
        set_if_present(['allowance', 'Allowance'], 'allowance', lambda v: self._num(v, 0.0))
        set_if_present(['deductions', 'Deductions'], 'deductions', lambda v: self._num(v, 0.0))
        set_if_present(['bankName'], 'bankName', lambda v: (str(v).strip() or None))
        set_if_present(['accountNumber'], 'accountNumber', lambda v: (str(v).strip() or None))
        # If status provided, update both status and active flag
        if 'status' in d and d.get('status') is not None:
            status_val = str(d.get('status')).strip() or 'Active'
            out['status'] = status_val
            out['active'] = (status_val.lower() == 'active')
        # Allow explicit active boolean override
        if 'active' in d and isinstance(d.get('active'), (bool,)):
            out['active'] = bool(d.get('active'))
        if out:
            out['updated_at'] = self._now_iso()
        return out

    def to_dict(self, doc):
        """Convert MongoDB document to JSON-safe dict"""
        if not doc:
            return None
        doc = dict(doc)
        doc['_id'] = str(doc['_id'])
        return doc

    def list_all(self):
        print( "list_all called", self )
        """Return all personnel, newest first"""
        people = list(self.collection.find().sort('created_at', -1))
        print("people:", people)
        return [self.to_dict(p) for p in people]

    def get_by_id(self, pid):
        """Find a single personnel by ObjectId"""
        try:
            oid = ObjectId(pid)
        except Exception:
            return None
        doc = self.collection.find_one({'_id': oid})
        return self.to_dict(doc)

    def create(self, data):
        """Insert new personnel document. Deduplicates by armyNumber (case-insensitive)."""
        payload = self._coerce_create(data)
        if not payload.get('armyNumber') or not payload.get('fullName'):
            raise ValueError('armyNumber and fullName are required')
        # Duplicate check by armyNumber
        exists = self.collection.find_one({'armyNumber': {'$regex': f"^{payload['armyNumber']}$", '$options': 'i'}})
        if exists:
            # For idempotency, just return existing
            return self.to_dict(exists)
        now = self._now_iso()
        payload['created_at'] = now
        payload['updated_at'] = now
        result = self.collection.insert_one(payload)
        payload['_id'] = str(result.inserted_id)
        return payload

    def update(self, pid, data):
        """Update existing personnel with provided fields only (canonicalized)."""
        try:
            oid = ObjectId(pid)
        except Exception:
            return None
        update_fields = self._coerce_update(data)
        if not update_fields:
            # nothing to update, return current
            return self.get_by_id(pid)
        self.collection.update_one({'_id': oid}, {'$set': update_fields})
        return self.get_by_id(pid)

    def delete(self, pid):
        """Delete personnel by ID"""
        try:
            oid = ObjectId(pid)
        except Exception:
            return False
        result = self.collection.delete_one({'_id': oid})
        return result.deleted_count > 0
