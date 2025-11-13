from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import mongo
from models.personnel import PersonnelModel

personnel_bp = Blueprint("personnel", __name__)
personnel_model = PersonnelModel(mongo.db)

# -------------------------------------------------------------
#  List all personnel
# -------------------------------------------------------------
@personnel_bp.route("/", methods=["GET"])
# @jwt_required()
def list_personnel():
    people = personnel_model.list_all()
    return jsonify({"personnel": people}), 200


# -------------------------------------------------------------
#  Get one personnel by ID
# -------------------------------------------------------------
@personnel_bp.route("/<pid>", methods=["GET"])
# @jwt_required()
def get_personnel(pid):
    doc = personnel_model.get_by_id(pid)
    if not doc:
        return jsonify({"error": "Personnel not found"}), 404
    return jsonify(doc), 200


# -------------------------------------------------------------
#  Add new personnel
# -------------------------------------------------------------
@personnel_bp.route("", methods=["POST"])
# @jwt_required()
def add_personnel():
    data = request.get_json() or {}
    # Validate required canonical fields
    if not data.get("armyNumber") or not data.get("fullName") and not data.get("Name"):
        return jsonify({"error": "Missing required fields: armyNumber and fullName"}), 400
    try:
        new_doc = personnel_model.create(data)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create personnel: {str(e)}"}), 500
    return jsonify({"message": "Personnel added successfully", "personnel": new_doc}), 201


# -------------------------------------------------------------
#  Update personnel
# -------------------------------------------------------------
@personnel_bp.route("/<pid>", methods=["PUT", "PATCH"])
# @jwt_required()
def update_personnel(pid):
    data = request.get_json() or {}
    updated = personnel_model.update(pid, data)
    if not updated:
        return jsonify({"error": "Personnel not found or invalid ID"}), 404
    return jsonify({"message": "Personnel updated successfully", "personnel": updated}), 200


# -------------------------------------------------------------
#  Delete personnel
# -------------------------------------------------------------
@personnel_bp.route("/<pid>", methods=["DELETE"])
# @jwt_required()
def delete_personnel(pid):
    success = personnel_model.delete(pid)
    if not success:
        return jsonify({"error": "Personnel not found or invalid ID"}), 404
    return jsonify({"message": "Personnel deleted successfully"}), 200


