from datetime import datetime, timezone

class PayrollModel:
    def __init__(self, db):
        self.collection = db.payroll_runs
        self.people = db.personnel

    def _num(self, v):
        try:
            return float(str(v).replace(',', '').strip())
        except Exception:
            return 0.0

    def build_entry(self, personnel_doc):
        """Convert a personnel document into a payroll entry (supports legacy and canonical keys)."""
        d = personnel_doc or {}
        # Canonical fallbacks
        basic = self._num(d.get("basicSalary", d.get("BasicSalary", d.get("Basic_Pay", 0))))
        allowance = self._num(d.get("allowance", d.get("Allowance", 0)))
        deductions = self._num(d.get("deductions", d.get("Deductions", 0)))
        net = basic + allowance - deductions

        armynumber = d.get("armyNumber", d.get("Army_Number", d.get("armynumber", "")))
        name = d.get("fullName", d.get("Name", d.get("name", "")))
        rank = d.get("rank", d.get("Rank", ""))
        corps = d.get("corps", d.get("Corps", ""))
        fmnunit = d.get("fmn_unit", d.get("Fmn/Unit", d.get("Fmn_Unit", "")))
        region = d.get("region", d.get("Region", ""))

        return {
          "armynumber": armynumber,
          "name": name,
          "rank": rank,
          "corps": corps,
          "fmnunit": fmnunit,
          "region": region,
          "basic": basic,
          "allowance": allowance,
          "deductions": deductions,
          "net": net,
          "status": "approved"
        }

    def compute_preview(self, personnel_list):
        """Compute payroll totals and entries"""
        entries = [self.build_entry(p) for p in personnel_list]
        totals = {
            "gross": sum(e["basic"] + e["allowance"] for e in entries),
            "allowances": sum(e["allowance"] for e in entries),
            "deductions": sum(e["deductions"] for e in entries)
        }
        return entries, totals

    def get_by_period(self, period):
        return self.collection.find_one({"period": period})

    def _recompute_totals(self, entries):
        return {
            "gross": sum((e.get("basic", 0) + e.get("allowance", 0)) for e in entries),
            "allowances": sum(e.get("allowance", 0) for e in entries),
            "deductions": sum(e.get("deductions", 0) for e in entries)
        }

    def create_run(self, period, entries, totals, approved_by):
        doc = {
            "period": period,
            "entries": entries,
            "totals": totals,
            "approved_by": approved_by,
            "approved_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        self.collection.insert_one(doc)
        return doc

    def overwrite_run(self, existing_id, new_doc):
        self.collection.replace_one({"_id": existing_id}, new_doc)

    def list_history(self, limit=20):
        """Return latest payroll runs"""
        runs = list(self.collection.find({}, {"entries": 0}).sort("approved_at", -1).limit(limit))
        for r in runs:
            r["_id"] = str(r["_id"])
        return runs

    def upsert_person_entry(self, period, person_doc, approved_by):
        """Add or update a single person's entry in a payroll run for the period."""
        entry = self.build_entry(person_doc)
        run = self.get_by_period(period)
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if not run:
            entries = [entry]
            totals = self._recompute_totals(entries)
            doc = {
                "period": period,
                "entries": entries,
                "totals": totals,
                "approved_by": approved_by,
                "approved_at": now,
            }
            self.collection.insert_one(doc)
            doc["_id"] = str(doc.get("_id", ""))
            return doc

        # Update or append
        entries = list(run.get("entries", []))
        key = entry.get("armynumber")
        found = False
        for i, e in enumerate(entries):
            if e.get("armynumber") == key:
                entries[i] = entry
                found = True
                break
        if not found:
            entries.append(entry)
        totals = self._recompute_totals(entries)
        self.collection.update_one({"_id": run["_id"]}, {"$set": {"entries": entries, "totals": totals, "updated_at": now}})
        # Return minimal run info
        run["entries"] = entries
        run["totals"] = totals
        return run
