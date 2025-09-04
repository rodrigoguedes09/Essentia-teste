from datetime import datetime
from src.database.connection import db
from src.models.appointment import Appointment
from src.models.patient import Patient

class AppointmentService:
    @staticmethod
    def schedule_appointment(patient_id, date, time):
        appointment = Appointment(patient_id=patient_id, date=date, time=time, status='scheduled')
        db.session.add(appointment)
        db.session.commit()
        return appointment

    @staticmethod
    def cancel_appointment(appointment_id):
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            appointment.status = 'canceled'
            db.session.commit()
            return appointment
        return None

    @staticmethod
    def get_appointments_by_patient(patient_id):
        return Appointment.query.filter_by(patient_id=patient_id).all()

    @staticmethod
    def get_available_slots(date):
        # This is a placeholder for actual logic to determine available slots
        # In a real application, you would check existing appointments for the date
        return [
            {'time': '09:00', 'available': True},
            {'time': '10:00', 'available': True},
            {'time': '11:00', 'available': False},
            {'time': '14:00', 'available': True},
            {'time': '15:00', 'available': True},
        ]