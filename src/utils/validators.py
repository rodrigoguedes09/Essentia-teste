def is_valid_email(email):
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def is_valid_appointment_time(appointment_time):
    from datetime import datetime
    try:
        datetime.strptime(appointment_time, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False

def is_valid_patient_data(patient_data):
    required_fields = ['name', 'age', 'contact']
    return all(field in patient_data for field in required_fields) and isinstance(patient_data['age'], int) and patient_data['age'] > 0

def is_valid_appointment_data(appointment_data):
    required_fields = ['patient_id', 'date', 'time']
    return all(field in appointment_data for field in required_fields) and is_valid_appointment_time(f"{appointment_data['date']} {appointment_data['time']}")