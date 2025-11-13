from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from app import mongo
from models.payroll import PayrollModel

payroll_bp = Blueprint("payroll", __name__, url_prefix="/api/payroll")
payroll_model = PayrollModel(mongo.db)

# -------------------------------------------------------------
# 1️⃣ Payroll Preview
# -------------------------------------------------------------
@payroll_bp.route("/preview", methods=["GET"])
@jwt_required()
def preview_payroll():
    period = request.args.get("period")
    if not period:
        return jsonify({"error": "Missing period parameter"}), 400

    personnel = list(mongo.db.personnel.find({"active": True}))
    if not personnel:
        return jsonify({"entries": [], "totals": {}}), 200

    entries, totals = payroll_model.compute_preview(personnel)

    return jsonify({"entries": entries, "totals": totals}), 200


# -------------------------------------------------------------
# 2️⃣ Approve Payroll
# -------------------------------------------------------------
@payroll_bp.route("", methods=["POST"])
@jwt_required()
def approve_payroll():
    data = request.get_json() or {}
    period = data.get("period")
    overwrite = data.get("overwrite", False)

    if not period:
        return jsonify({"error": "Missing period"}), 400

    existing = payroll_model.get_by_period(period)
    if existing and not overwrite:
        return jsonify({"error": "Payroll already exists"}), 409

    personnel = list(mongo.db.personnel.find({"active": True}))
    if not personnel:
        return jsonify({"error": "No active personnel found"}), 400

    entries, totals = payroll_model.compute_preview(personnel)
    user = get_jwt_identity()

    if existing and overwrite:
        payroll_model.collection.delete_one({"_id": existing["_id"]})

    payroll_model.create_run(period, entries, totals, approved_by=user)

    return jsonify({"message": f"Payroll for {period} approved successfully."}), 200


# -------------------------------------------------------------
# 3️⃣ Approve Personnel
# -------------------------------------------------------------
@payroll_bp.route("/approve/<pid>", methods=["POST"])
@jwt_required()
def approve_person(pid):
    data = request.get_json() or {}
    period = data.get("period")
    if not period:
        return jsonify({"error": "Missing period"}), 400

    try:
        oid = ObjectId(pid)
    except Exception:
        return jsonify({"error": "Invalid personnel id"}), 400

    person = mongo.db.personnel.find_one({"_id": oid})
    if not person:
        return jsonify({"error": "Personnel not found"}), 404
    if not person.get("active", True):
        return jsonify({"error": "Personnel is inactive"}), 400

    user = get_jwt_identity()
    run = payroll_model.upsert_person_entry(period, person, user)
    entry = payroll_model.build_entry(person)
    return jsonify({
        "message": f"Approved {entry.get('name') or entry.get('armynumber')} for {period}",
        "period": period,
        "entry": entry,
        "totals": run.get("totals", {}),
    }), 200


# -------------------------------------------------------------
# 4️⃣ Get Payroll Run (with entries)
# -------------------------------------------------------------
@payroll_bp.route("/run", methods=["GET"])
@jwt_required()
def get_payroll_run():
    period = request.args.get("period")
    if not period:
        return jsonify({"error": "Missing period parameter"}), 400
    run = payroll_model.get_by_period(period)
    if not run:
        return jsonify({"period": period, "entries": [], "totals": {}}), 200
    # Convert _id to string for JSON
    run["_id"] = str(run.get("_id"))
    return jsonify({
        "period": run.get("period"),
        "entries": run.get("entries", []),
        "totals": run.get("totals", {}),
        "approved_at": run.get("approved_at"),
        "approved_by": run.get("approved_by"),
        "updated_at": run.get("updated_at"),
        "id": run.get("_id"),
    }), 200


# -------------------------------------------------------------
# 5️⃣ Payroll History
# -------------------------------------------------------------
@payroll_bp.route("/history", methods=["GET"])
@jwt_required()
def list_payroll_history():
    runs = payroll_model.list_history(limit=50)
    return jsonify({"runs": runs}), 200
