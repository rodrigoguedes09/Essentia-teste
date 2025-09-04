from flask import Blueprint, request, jsonify
from src.models.patient import Patient
from src.services.patient_service import PatientService

patients_bp = Blueprint('patients', __name__)
patient_service = PatientService()

@patients_bp.route('/patients', methods=['POST'])
def create_patient():
    data = request.json
    patient = patient_service.create_patient(data)
    return jsonify(patient), 201

@patients_bp.route('/patients', methods=['GET'])
def get_patients():
    patients = patient_service.get_all_patients()
    return jsonify(patients), 200

@patients_bp.route('/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    patient = patient_service.get_patient(patient_id)
    if patient:
        return jsonify(patient), 200
    return jsonify({'message': 'Patient not found'}), 404

@patients_bp.route('/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    data = request.json
    updated_patient = patient_service.update_patient(patient_id, data)
    if updated_patient:
        return jsonify(updated_patient), 200
    return jsonify({'message': 'Patient not found'}), 404

@patients_bp.route('/patients/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    success = patient_service.delete_patient(patient_id)
    if success:
        return jsonify({'message': 'Patient deleted'}), 204
    return jsonify({'message': 'Patient not found'}), 404