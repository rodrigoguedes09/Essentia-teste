from sqlalchemy.orm import sessionmaker
from src.database.connection import engine
from src.models.patient import Patient
from src.models.appointment import Doctor, Appointment, Schedule
from datetime import date, time, datetime

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_database():
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Patient).first():
            print("Database already has data. Skipping seed.")
            return
        
        # Seed Doctors
        doctors = [
            Doctor(name="Dr. Maria Silva", specialty="Cardiologia", email="maria.silva@clinic.com", phone="(11) 99999-0001"),
            Doctor(name="Dr. João Santos", specialty="Dermatologia", email="joao.santos@clinic.com", phone="(11) 99999-0002"),
            Doctor(name="Dr. Ana Costa", specialty="Pediatria", email="ana.costa@clinic.com", phone="(11) 99999-0003"),
            Doctor(name="Dr. Carlos Lima", specialty="Ortopedia", email="carlos.lima@clinic.com", phone="(11) 99999-0004"),
        ]
        
        for doctor in doctors:
            db.add(doctor)
        
        # Seed Patients
        patients = [
            Patient(name="Pedro Oliveira", email="pedro@email.com", phone="(11) 98888-0001", cpf="123.456.789-01", birth_date=date(1985, 3, 15)),
            Patient(name="Lucia Fernandes", email="lucia@email.com", phone="(11) 98888-0002", cpf="123.456.789-02", birth_date=date(1990, 7, 22)),
            Patient(name="Roberto Alves", email="roberto@email.com", phone="(11) 98888-0003", cpf="123.456.789-03", birth_date=date(1978, 11, 8)),
            Patient(name="Fernanda Costa", email="fernanda@email.com", phone="(11) 98888-0004", cpf="123.456.789-04", birth_date=date(1995, 1, 30)),
        ]
        
        for patient in patients:
            db.add(patient)
        
        db.commit()
        
        # Seed Schedules (available slots)
        schedules = [
            Schedule(doctor_id=1, date=date(2024, 1, 15), start_time=time(9, 0), end_time=time(10, 0), is_available='true'),
            Schedule(doctor_id=1, date=date(2024, 1, 15), start_time=time(10, 0), end_time=time(11, 0), is_available='true'),
            Schedule(doctor_id=1, date=date(2024, 1, 15), start_time=time(14, 0), end_time=time(15, 0), is_available='true'),
            Schedule(doctor_id=2, date=date(2024, 1, 15), start_time=time(9, 0), end_time=time(10, 0), is_available='true'),
            Schedule(doctor_id=2, date=date(2024, 1, 16), start_time=time(11, 0), end_time=time(12, 0), is_available='true'),
            Schedule(doctor_id=3, date=date(2024, 1, 16), start_time=time(8, 0), end_time=time(9, 0), is_available='true'),
            Schedule(doctor_id=4, date=date(2024, 1, 17), start_time=time(15, 0), end_time=time(16, 0), is_available='true'),
        ]
        
        for schedule in schedules:
            db.add(schedule)
        
        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    seed_database()
