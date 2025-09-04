from models.patient import Patient
from database.connection import db_session

def create_patient(name, age, contact_info):
    new_patient = Patient(name=name, age=age, contact_info=contact_info)
    db_session.add(new_patient)
    db_session.commit()
    return new_patient

def get_patient(patient_id):
    return db_session.query(Patient).filter(Patient.id == patient_id).first()

def get_all_patients():
    return db_session.query(Patient).all()

def update_patient(patient_id, name=None, age=None, contact_info=None):
    patient = get_patient(patient_id)
    if patient:
        if name:
            patient.name = name
        if age:
            patient.age = age
        if contact_info:
            patient.contact_info = contact_info
        db_session.commit()
    return patient

def delete_patient(patient_id):
    patient = get_patient(patient_id)
    if patient:
        db_session.delete(patient)
        db_session.commit()
    return patient