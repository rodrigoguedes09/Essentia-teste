from flask import Blueprint, request, jsonify
from ..services.appointment_service import AppointmentService

appointments_bp = Blueprint('appointments', __name__)
appointment_service = AppointmentService()

@appointments_bp.route('/appointments', methods=['GET'])
def get_appointments():
    appointments = appointment_service.get_all_appointments()
    return jsonify(appointments), 200

@appointments_bp.route('/appointments', methods=['POST'])
def schedule_appointment():
    data = request.json
    appointment = appointment_service.schedule_appointment(data)
    return jsonify(appointment), 201

@appointments_bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    success = appointment_service.cancel_appointment(appointment_id)
    if success:
        return jsonify({"message": "Appointment canceled successfully."}), 200
    return jsonify({"message": "Appointment not found."}), 404