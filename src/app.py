from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
import re
import json

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DEBUG, SECRET_KEY, API_VERSION
from src.database.connection import init_db, get_db
from src.database.seed_data import seed_database
from src.models.patient import Patient
from src.models.appointment import Doctor, Appointment, Schedule
from src.services.cache_service import cache_service
from datetime import datetime, date

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG
CORS(app)

# Initialize database
init_db()

# User session management
user_sessions = {}

def get_user_session(user_id):
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'state': 'idle',
            'data': {},
            'step': 0
        }
    return user_sessions[user_id]

def reset_user_session(user_id):
    """Reset user session to idle state"""
    if user_id in user_sessions:
        user_sessions[user_id] = {
            'state': 'idle',
            'data': {},
            'step': 0
        }
seed_database()

@app.route(f'/api/{API_VERSION}/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "Medical API is running", 
        "version": API_VERSION,
        "debug": DEBUG
    })

@app.route(f'/api/{API_VERSION}/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics"""
    stats = cache_service.get_cache_stats()
    return jsonify(stats)

@app.route(f'/api/{API_VERSION}/cache/health', methods=['GET'])
def get_cache_health():
    """Get cache health status"""
    health = cache_service.health_check()
    return jsonify(health)

@app.route(f'/api/{API_VERSION}/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cache (admin only)"""
    try:
        success = cache_service.clear_all_cache()
        if success:
            return jsonify({"message": "Cache cleared successfully"})
        else:
            return jsonify({"error": "Failed to clear cache"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route(f'/api/{API_VERSION}/patients', methods=['GET'])
def get_patients():
    """Get all patients"""
    db = next(get_db())
    patients = db.query(Patient).all()
    return jsonify([patient.to_dict() for patient in patients])

@app.route(f'/api/{API_VERSION}/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get specific patient"""
    db = next(get_db())
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient:
        return jsonify(patient.to_dict())
    return jsonify({"error": "Patient not found"}), 404

@app.route(f'/api/{API_VERSION}/doctors', methods=['GET'])
def get_doctors():
    """Get all doctors"""
    db = next(get_db())
    doctors = db.query(Doctor).all()
    return jsonify([doctor.to_dict() for doctor in doctors])

@app.route(f'/api/{API_VERSION}/schedules/available', methods=['GET'])
def get_available_schedules():
    """Get available schedules with cache support"""
    date_param = request.args.get('date')
    doctor_id_param = request.args.get('doctor_id')
    
    # Convert doctor_id to int for cache key consistency
    doctor_id = int(doctor_id_param) if doctor_id_param else None
    
    # Try to get from cache first
    cached_schedules = cache_service.get_available_schedules(
        date=date_param, 
        doctor_id=doctor_id
    )
    
    if cached_schedules and isinstance(cached_schedules, dict):
        # Return the actual schedules from cached data
        return jsonify(cached_schedules.get('schedules', []))
    
    # Cache miss - get from database
    db = next(get_db())
    query = db.query(Schedule, Doctor).join(Doctor).filter(Schedule.is_available == 'true')
    
    if date_param:
        try:
            filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            query = query.filter(Schedule.date == filter_date)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if doctor_id:
        query = query.filter(Schedule.doctor_id == doctor_id)
    
    results = query.all()
    
    schedules = []
    for schedule, doctor in results:
        schedule_dict = schedule.to_dict()
        schedule_dict['doctor_name'] = doctor.name
        schedule_dict['doctor_specialty'] = doctor.specialty
        schedules.append(schedule_dict)
    
    # Cache the results (5 minutes TTL)
    cache_service.set_available_schedules(
        schedules=schedules,
        date=date_param,
        doctor_id=doctor_id,
        ttl=300
    )
    
    return jsonify(schedules)

@app.route(f'/api/{API_VERSION}/appointments', methods=['GET'])
def get_appointments():
    """Get all appointments"""
    db = next(get_db())
    appointments = db.query(Appointment, Patient, Doctor).join(Patient).join(Doctor).all()
    
    result = []
    for appointment, patient, doctor in appointments:
        app_dict = appointment.to_dict()
        app_dict['patient_name'] = patient.name
        app_dict['doctor_name'] = doctor.name
        app_dict['doctor_specialty'] = doctor.specialty
        result.append(app_dict)
    
    return jsonify(result)

@app.route(f'/api/{API_VERSION}/appointments', methods=['POST'])
def create_appointment():
    """Create new appointment"""
    db = next(get_db())
    data = request.json
    
    try:
        # Validate required fields
        required_fields = ['patient_id', 'doctor_id', 'appointment_date', 'appointment_time']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse date and time
        appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
        appointment_time = datetime.strptime(data['appointment_time'], '%H:%M').time()
        
        # Check if slot is available
        schedule = db.query(Schedule).filter(
            Schedule.doctor_id == data['doctor_id'],
            Schedule.date == appointment_date,
            Schedule.start_time == appointment_time,
            Schedule.is_available == 'true'
        ).first()
        
        if not schedule:
            return jsonify({"error": "Time slot not available"}), 400
        
        # Create appointment
        appointment = Appointment(
            patient_id=data['patient_id'],
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='scheduled',
            notes=data.get('notes', '')
        )
        
        db.add(appointment)
        
        # Mark schedule as unavailable
        schedule.is_available = 'false'
        
        db.commit()
        
        # Invalidate cache for this doctor and date
        cache_service.invalidate_schedule_cache(
            doctor_id=data['doctor_id'], 
            date=appointment_date.strftime('%Y-%m-%d')
        )
        
        return jsonify({
            "message": "Appointment created successfully",
            "appointment": appointment.to_dict()
        }), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route(f'/api/{API_VERSION}/appointments/<int:appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    """Cancel appointment"""
    db = next(get_db())
    
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404
        
        # Update appointment status
        appointment.status = 'cancelled'
        
        # Make schedule available again
        schedule = db.query(Schedule).filter(
            Schedule.doctor_id == appointment.doctor_id,
            Schedule.date == appointment.appointment_date,
            Schedule.start_time == appointment.appointment_time
        ).first()
        
        if schedule:
            schedule.is_available = 'true'
        
        db.commit()
        
        # Invalidate cache for this doctor and date
        cache_service.invalidate_schedule_cache(
            doctor_id=appointment.doctor_id,
            date=appointment.appointment_date.strftime('%Y-%m-%d')
        )
        
        return jsonify({"message": "Appointment cancelled successfully"})
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route(f'/api/{API_VERSION}/payment-info', methods=['GET'])
def get_payment_info():
    """Get payment information"""
    return jsonify({
        "consultation_fees": {
            "private": "R$ 200,00",
            "insurance": "According to plan coverage"
        },
        "payment_methods": [
            "Cash",
            "Credit Card",
            "Debit Card", 
            "PIX",
            "Bank Transfer"
        ],
        "insurance_accepted": [
            "Unimed",
            "Bradesco Saúde",
            "Amil",
            "SulAmérica"
        ]
    })

@app.route(f'/api/{API_VERSION}/test', methods=['POST'])
def test_endpoint():
    """Simple test endpoint for N8N debugging"""
    try:
        print("🧪 Test endpoint called!")
        print(f"📥 Request headers: {dict(request.headers)}")
        data = request.json
        print(f"📥 Request body: {data}")
        
        return jsonify({
            "status": "success",
            "message": "N8N connection working!",
            "received_data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Test endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route(f'/api/{API_VERSION}/agent', methods=['POST'])
def ai_agent_endpoint():
    """
    State-based AI Agent endpoint with structured conversation flows
    """
    user_id = 'anonymous'  # Initialize user_id with default value
    try:
        print("🔄 AI Agent endpoint called!")
        print(f"📥 Request headers: {dict(request.headers)}")
        
        data = request.json
        print(f"📥 Request body: {data}")
        
        # Validate required fields
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        user_message = data.get('message')
        user_id = data.get('user_id')
        
        # Validate message is provided
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        # Validate user_id is provided
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
        
        # Normalize user_id to handle variations
        normalized_user_id = str(user_id).strip()
        if not normalized_user_id or normalized_user_id in ['anonymous', '', 'null', 'undefined']:
            normalized_user_id = 'default_user'
        
        print(f"💬 User message: '{user_message}' from user: {normalized_user_id}")
        
        # Get user session
        session = get_user_session(normalized_user_id)
        print(f"📋 User session state: {session['state']}, step: {session['step']}")
        
        # Initialize response structure
        response = {
            "success": True,
            "action_taken": "",
            "data": None,
            "message": "",
            "suggested_actions": []
        }
        
        # Handle conversation based on current state
        if session['state'] == 'idle':
            intent = analyze_intent(user_message)
            print(f"🧠 Detected intent: '{intent}'")
            
            if intent == "greeting":
                response = handle_greeting()
                
            elif intent == "payment_info":
                response = handle_payment_info()
                
            elif intent == "schedule_request":
                # User is asking for available schedules
                response = {
                    "action_taken": "show_available_schedules",
                    "message": f"Horários Disponíveis:\n\n{get_available_schedules_summary()}\n\nPara agendar uma consulta, você pode:\n• Escolher um médico específico: \"Quero consulta com Dr. Silva\"\n• Escolher uma data: \"Preciso de horário para amanhã\"\n• Ou simplesmente dizer: \"Quero agendar uma consulta\"",
                    "suggested_actions": ["book_appointment"]
                }
                
            elif intent == "book_appointment":
                # Check if user specified doctor or date in their message
                doctor_name = extract_doctor_name_from_message(user_message)
                preferred_date = extract_date_from_message(user_message)
                
                if doctor_name or preferred_date:
                    # User specified preferences, find matching schedules
                    db = next(get_db())
                    query = db.query(Schedule, Doctor).join(Doctor).filter(Schedule.is_available == 'true')
                    
                    if doctor_name:
                        query = query.filter(Doctor.name.ilike(f'%{doctor_name}%'))
                    
                    if preferred_date:
                        query = query.filter(Schedule.date == preferred_date)
                    
                    schedules = query.all()
                    
                    if schedules:
                        # Found matching schedules, start registration immediately
                        selected_schedule = schedules[0]  # Take first available
                        schedule_info = {
                            "id": selected_schedule[0].id,
                            "date": str(selected_schedule[0].date),
                            "start_time": str(selected_schedule[0].start_time),
                            "end_time": str(selected_schedule[0].end_time),
                            "doctor_name": selected_schedule[1].name,
                            "doctor_specialty": selected_schedule[1].specialty,
                            "doctor_id": selected_schedule[1].id
                        }
                        
                        session['data']['selected_schedule'] = schedule_info
                        session['state'] = 'registering_patient'
                        session['step'] = 1
                        
                        response = {
                            "action_taken": "schedule_selected",
                            "message": f"Perfeito! Encontrei um horário disponível para você:\n\nMédico: Dr. {schedule_info['doctor_name']}\nEspecialidade: {schedule_info['doctor_specialty']}\nData: {format_date_display(schedule_info['date'])}\nHorário: {format_time_display(schedule_info['start_time'])}\n\nPara confirmar o agendamento, preciso de algumas informações suas.\n\nPor favor, digite seu nome completo:",
                            "suggested_actions": ["provide_name"]
                        }
                    else:
                        # No matching schedules found
                        response = {
                            "action_taken": "no_schedules_found",
                            "message": f"Desculpe, não encontrei horários disponíveis {f'com Dr. {doctor_name}' if doctor_name else ''} {f'para o dia {format_date_display(preferred_date)}' if preferred_date else ''}.\n\nHorários Disponíveis:\n{get_available_schedules_summary()}",
                            "suggested_actions": ["book_appointment"]
                        }
                else:
                    # Show general availability
                    response = {
                        "action_taken": "show_availability",
                        "message": f"Horários Disponíveis:\n\n{get_available_schedules_summary()}\n\nVocê pode escolher um horário dizendo algo como:\n• \"Quero consulta com Dr. Silva\"\n• \"Preciso de horário para amanhã\"\n• \"Consulta na segunda-feira\"",
                        "suggested_actions": ["book_appointment"]
                    }
                
            elif intent == "cancel_appointment":
                # Start cancellation flow
                session['state'] = 'cancelling_appointment'
                session['step'] = 1
                
                response = {
                    "action_taken": "cancel_flow_started",
                    "message": "Cancelamento de Consulta\n\nPara localizar sua consulta e proceder com o cancelamento, por favor digite seu nome completo:",
                    "suggested_actions": ["provide_name"]
                }
            
            elif intent == "number_selection":
                # User sent a number but we're not in a selection context
                response = {
                    "action_taken": "number_without_context",
                    "message": "Vejo que você digitou um número, mas não consegui entender o contexto.\n\nComo posso ajudá-lo hoje?\n\n• Agendar uma consulta\n• Cancelar uma consulta\n• Informações sobre valores",
                    "suggested_actions": ["book_appointment", "cancel_appointment", "payment_info"]
                }
            
            else:
                response = handle_greeting()
        
        elif session['state'] == 'selecting_schedule':
            intent = analyze_intent(user_message)
            print(f"🧠 In selecting_schedule state, detected intent: '{intent}'")
            
            if intent == 'number_selection':
                selected_number = extract_number_from_message(user_message)
                print(f"🎯 Extracted number: {selected_number}")
                schedules = session['data'].get('schedules', [])
                print(f"📋 Available schedules count: {len(schedules)}")
                
                if selected_number and 1 <= selected_number <= len(schedules):
                    selected_schedule = schedules[selected_number - 1]
                    session['data']['selected_schedule'] = selected_schedule
                    session['state'] = 'registering_patient'
                    session['step'] = 1
                    print(f"✅ Schedule selected: {selected_schedule}")
                    
                    response = {
                        "action_taken": "schedule_selected",
                        "message": "Ótima escolha! Agora preciso registrar seus dados para confirmar o agendamento.\n\nPor favor, digite seu nome completo:",
                        "suggested_actions": ["provide_name"]
                    }
                else:
                    print(f"❌ Invalid selection: number={selected_number}, schedules_count={len(schedules)}")
                    response = {
                        "action_taken": "invalid_selection",
                        "message": "Por favor, digite um número válido da lista de opções.",
                        "suggested_actions": ["number_selection"]
                    }
            else:
                response = {
                    "action_taken": "awaiting_selection",
                    "message": "Por favor, escolha uma das opções digitando o número correspondente.",
                    "suggested_actions": ["number_selection"]
                }
        
        elif session['state'] == 'registering_patient':
            intent = analyze_intent(user_message)
            
            if intent == 'user_data':
                user_data = extract_user_data(user_message)
                
                # Store extracted data
                for key, value in user_data.items():
                    session['data'][key] = value
                
                # Progress through registration steps
                if session['step'] == 1 and 'name' in user_data:
                    session['step'] = 2
                    response = {
                        "action_taken": "name_collected",
                        "message": f"Obrigado, {user_data['name']}!\n\nAgora preciso do seu CPF. Por favor digite (apenas números ou com pontos e traço):",
                        "suggested_actions": ["provide_cpf"]
                    }
                elif session['step'] == 2 and 'cpf' in user_data:
                    session['step'] = 3
                    response = {
                        "action_taken": "cpf_collected",
                        "message": "CPF registrado com sucesso!\n\nAgora preciso do seu email:",
                        "suggested_actions": ["provide_email"]
                    }
                elif session['step'] == 3 and 'email' in user_data:
                    session['step'] = 4
                    response = {
                        "action_taken": "email_collected",
                        "message": "Email registrado!\n\nPor favor, digite seu telefone (com DDD):",
                        "suggested_actions": ["provide_phone"]
                    }
                elif session['step'] == 4 and 'phone' in user_data:
                    session['step'] = 5
                    response = {
                        "action_taken": "phone_collected",
                        "message": "Telefone registrado!\n\nPor último, preciso da sua data de nascimento no formato DD/MM/AAAA:",
                        "suggested_actions": ["provide_birth_date"]
                    }
                elif session['step'] == 5 and 'birth_date' in user_data:
                    # All data collected, create patient and appointment
                    response = complete_appointment_booking(session, user_id)
                else:
                    # Ask for missing information based on current step
                    response = get_step_message(session['step'])
            else:
                response = get_step_message(session['step'])
        
        elif session['state'] == 'cancelling_appointment':
            intent = analyze_intent(user_message)
            
            if intent == 'user_data' and session['step'] == 1:
                user_data = extract_user_data(user_message)
                
                if 'name' in user_data:
                    # Search for appointments with this name
                    db = next(get_db())
                    patient = db.query(Patient).filter(Patient.name.ilike(f"%{user_data['name']}%")).first()
                    
                    if patient:
                        appointments = db.query(Appointment).filter(
                            Appointment.patient_id == patient.id,
                            Appointment.status == 'scheduled'
                        ).all()
                        
                        if appointments:
                            # Show appointments for cancellation
                            session['data']['patient'] = patient
                            session['data']['appointments'] = [
                                {
                                    'id': apt.id,
                                    'date': apt.schedule.date.isoformat(),
                                    'time': apt.schedule.start_time.isoformat(),
                                    'doctor': apt.schedule.doctor.name
                                } for apt in appointments
                            ]
                            session['step'] = 2
                            
                            message = f"Encontrei as seguintes consultas agendadas para {patient.name}:\n\n"
                            for i, apt in enumerate(session['data']['appointments'], 1):
                                date_str = datetime.fromisoformat(apt['date']).strftime('%d/%m/%Y')
                                # Handle time parsing properly
                                time_str = apt['time']
                                if isinstance(time_str, str) and ':' in time_str:
                                    time_str = time_str[:5]  # Extract HH:MM
                                message += f"{i}. Data: {date_str} às {time_str}\n"
                                message += f"   Médico: Dr. {apt['doctor']}\n\n"
                            
                            message += "Digite o número da consulta que deseja cancelar:"
                            
                            response = {
                                "action_taken": "appointments_found",
                                "message": message,
                                "suggested_actions": ["number_selection"]
                            }
                        else:
                            reset_user_session(user_id)
                            response = {
                                "action_taken": "no_appointments",
                                "message": f"Não encontrei consultas agendadas em nome de {user_data['name']}.\n\nGostaria de agendar uma nova consulta?",
                                "suggested_actions": ["book_appointment"]
                            }
                    else:
                        reset_user_session(user_id)
                        response = {
                            "action_taken": "patient_not_found",
                            "message": f"Não encontrei um paciente registrado com o nome {user_data['name']}.\n\nGostaria de agendar uma nova consulta?",
                            "suggested_actions": ["book_appointment"]
                        }
                else:
                    response = {
                        "action_taken": "awaiting_name",
                        "message": "Por favor, digite seu nome completo para localizar suas consultas.",
                        "suggested_actions": ["provide_name"]
                    }
            
            elif intent == 'number_selection' and session['step'] == 2:
                selected_number = extract_number_from_message(user_message)
                appointments = session['data'].get('appointments', [])
                
                if selected_number and 1 <= selected_number <= len(appointments):
                    selected_appointment = appointments[selected_number - 1]
                    
                    # Cancel the appointment
                    db = next(get_db())
                    appointment = db.query(Appointment).filter(Appointment.id == selected_appointment['id']).first()
                    
                    if appointment:
                        appointment.status = 'cancelled'
                        
                        # Make schedule available again
                        schedule = appointment.schedule
                        schedule.is_available = 'true'
                        
                        db.commit()
                        
                        date_str = datetime.fromisoformat(selected_appointment['date']).strftime('%d/%m/%Y')
                        # Handle time parsing properly
                        time_str = selected_appointment['time']
                        if isinstance(time_str, str) and ':' in time_str:
                            time_str = time_str[:5]  # Extract HH:MM
                        
                        reset_user_session(user_id)
                        response = {
                            "action_taken": "appointment_cancelled",
                            "message": f"Consulta cancelada com sucesso!\n\nDetalhes da consulta cancelada:\nData: {date_str} às {time_str}\nMédico: Dr. {selected_appointment['doctor']}\n\nSe precisar reagendar ou marcar uma nova consulta, estarei aqui para ajudá-lo!",
                            "suggested_actions": ["book_appointment"]
                        }
                    else:
                        reset_user_session(user_id)
                        response = {
                            "action_taken": "cancellation_error",
                            "message": "Ocorreu um erro ao cancelar a consulta. Tente novamente.",
                            "suggested_actions": ["cancel_appointment"]
                        }
                else:
                    response = {
                        "action_taken": "invalid_selection",
                        "message": "Por favor, digite um número válido da lista de consultas.",
                        "suggested_actions": ["number_selection"]
                    }
            else:
                response = {
                    "action_taken": "awaiting_input",
                    "message": "Por favor, siga as instruções para cancelar sua consulta.",
                    "suggested_actions": ["provide_name"]
                }
        
        else:
            # Unknown state, reset
            reset_user_session(user_id)
            response = handle_greeting()
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in AI agent: {str(e)}")
        reset_user_session(user_id)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Desculpe, ocorreu um erro interno. Vamos começar novamente. Como posso ajudá-lo?",
            "action_taken": "error_occurred"
        }), 500

def analyze_intent(message):
    """Simple intent detection"""
    message_lower = message.lower().strip()
    
    # Greeting patterns
    greeting_patterns = [
        r'\b(oi|olá|ola|hey|hi|hello|bom dia|boa tarde|boa noite)\b',
        r'\btchau\b|\btchauzinho\b|\bfui\b|\bvaleu\b|\bobrigad[oa]\b',
        r'\b(como vai|tudo bem|tudo bom)\b'
    ]
    
    # Payment info patterns - mais específicos primeiro
    payment_patterns = [
        r'\b(pagamento|pagar|valor|preço|preços|custo|quanto custa|valores)\b',
        r'\b(payment|pay|cost|price|pricing)\b'
    ]
    
    # Cancel appointment patterns
    cancel_patterns = [
        r'\b(cancelar|desmarcar|remover.*consulta)\b',
        r'\b(cancel|remove.*appointment)\b'
    ]
    
    # Schedule request patterns - para consultar horários disponíveis
    schedule_request_patterns = [
        r'\b(horários?.*disponíveis?|disponíveis?.*horários?)\b',
        r'\b(que.*horários?.*tem|quais.*horários?|que.*horários?)\b',
        r'\b(ver.*horários?|mostrar.*horários?|listar.*horários?)\b',
        r'\b(available.*schedule|show.*schedule|list.*schedule)\b',
        r'\b(quando.*tem.*vaga|tem.*vaga)\b'
    ]
    
    # Book appointment patterns
    book_patterns = [
        r'\b(agendar|marcar|quero.*consulta|preciso.*consulta)\b',
        r'\b(appointment|schedule|booking)\b'
    ]
    
    # Number patterns (for selecting options)
    number_patterns = [
        r'^\s*(\d+)\s*$',
        r'\b(um|dois|três|quatro|cinco|seis|sete|oito|nove|dez)\b',
        r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b'
    ]
    
    for pattern in greeting_patterns:
        if re.search(pattern, message_lower):
            return 'greeting'
    
    # Verifica payment primeiro para evitar conflito com "consulta"
    for pattern in payment_patterns:
        if re.search(pattern, message_lower):
            return 'payment_info'
    
    # Verifica schedule_request antes de book_appointment para priorizar consulta de horários
    for pattern in schedule_request_patterns:
        if re.search(pattern, message_lower):
            return 'schedule_request'
    
    for pattern in cancel_patterns:
        if re.search(pattern, message_lower):
            return 'cancel_appointment'
    
    for pattern in book_patterns:
        if re.search(pattern, message_lower):
            return 'book_appointment'
    
    for pattern in number_patterns:
        if re.search(pattern, message_lower):
            return 'number_selection'
    
    # Check if it's user data (name, CPF, email, phone, birth date)
    if is_user_data(message):
        return 'user_data'
    
    return 'unknown'

def is_user_data(message):
    """Check if message contains user data"""
    message_lower = message.lower().strip()
    
    # CPF pattern
    cpf_pattern = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
    if re.search(cpf_pattern, message):
        return True
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if re.search(email_pattern, message):
        return True
    
    # Phone pattern
    phone_pattern = r'(\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4})'
    if re.search(phone_pattern, message):
        return True
    
    # Birth date pattern
    date_pattern = r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}'
    if re.search(date_pattern, message):
        return True
    
    # Name pattern (2 or more capitalized words)
    name_pattern = r'^[A-ZÁÊÇÃÕ][a-záêçãõ]+(\s+[A-ZÁÊÇÃÕ][a-záêçãõ]+)+\s*$'
    if re.search(name_pattern, message.strip()):
        return True
    
    return False

def extract_number_from_message(message):
    """Extract number from message"""
    # Direct number
    number_match = re.search(r'^\s*(\d+)\s*$', message.strip())
    if number_match:
        return int(number_match.group(1))
    
    # Word numbers (Portuguese)
    word_numbers = {
        'um': 1, 'dois': 2, 'três': 3, 'quatro': 4, 'cinco': 5,
        'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10,
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    }
    
    message_lower = message.lower().strip()
    for word, number in word_numbers.items():
        if word in message_lower:
            return number
    
    return None

def extract_user_data(message):
    """Extract user data from message"""
    data = {}
    
    # Extract name (if it looks like a name)
    name_pattern = r'^([A-ZÁÊÇÃÕ][a-záêçãõ]+(?:\s+[A-ZÁÊÇÃÕ][a-záêçãõ]+)+)\s*$'
    name_match = re.search(name_pattern, message.strip())
    if name_match:
        data['name'] = name_match.group(1).strip()
    
    # Extract CPF
    cpf_pattern = r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})'
    cpf_match = re.search(cpf_pattern, message)
    if cpf_match:
        data['cpf'] = cpf_match.group(1)
    
    # Extract email
    email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
    email_match = re.search(email_pattern, message)
    if email_match:
        data['email'] = email_match.group(1)
    
    # Extract phone
    phone_pattern = r'(\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4})'
    phone_match = re.search(phone_pattern, message)
    if phone_match:
        data['phone'] = phone_match.group(1)
    
    # Extract birth date
    date_pattern = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
    date_match = re.search(date_pattern, message)
    if date_match:
        try:
            day, month, year = date_match.groups()
            birth_date = date(int(year), int(month), int(day))
            data['birth_date'] = birth_date.isoformat()
        except ValueError:
            pass
    
    return data

def format_schedules_for_selection(schedules):
    """Format schedules as numbered options for user selection"""
    if not schedules:
        return "Desculpe, não há horários disponíveis no momento. Por favor, entre em contato conosco para mais opções."
    
    message = "Horários Disponíveis:\n\n"
    
    for i, schedule in enumerate(schedules, 1):
        # Handle date parsing - convert from YYYY-MM-DD to DD/MM/YYYY
        date_str = schedule['date']
        if isinstance(date_str, str) and '-' in date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_str = date_obj.strftime('%d/%m/%Y')
            except ValueError:
                pass  # Keep original format if parsing fails
        
        # Handle time parsing - extract just HH:MM from HH:MM:SS
        start_time = schedule['start_time']
        if isinstance(start_time, str) and ':' in start_time:
            start_time = start_time[:5]  # Extract HH:MM
        
        message += f"{i}. Dr. {schedule['doctor_name']}\n"
        message += f"   Especialidade: {schedule['doctor_specialty']}\n"
        message += f"   Data: {date_str}\n"
        message += f"   Horário: {start_time}\n\n"
    
    message += "Por favor, digite o número da consulta que deseja agendar:"
    return message

def handle_greeting():
    """Handle greeting intent"""
    return {
        "action_taken": "greeting",
        "message": "Olá! Sou seu assistente médico virtual e estou aqui para ajudá-lo.\n\nComo posso ajudá-lo hoje?\n\n• Agendar uma consulta\n• Cancelar uma consulta\n• Informações sobre valores e formas de pagamento\n\nFique à vontade para me dizer o que precisa.",
        "suggested_actions": ["book_appointment", "cancel_appointment", "payment_info"]
    }

def handle_payment_info():
    """Handle payment info request"""
    return {
        "action_taken": "payment_info",
        "message": "Informações sobre Valores e Formas de Pagamento\n\nConsulta Particular:\n• Clínica Geral: R$ 150,00\n• Especialistas: R$ 200,00\n\nConvênios Aceitos:\n• Unimed\n• Bradesco Saúde\n• SulAmérica\n• Amil\n\nFormas de Pagamento:\n• Dinheiro\n• Cartão de débito ou crédito\n• PIX\n• Transferência bancária\n\nPara mais informações ou dúvidas, ficarei feliz em ajudá-lo.",
        "suggested_actions": ["book_appointment"]
    }

def format_date_display(date_str):
    """Format date for display (YYYY-MM-DD to DD/MM/YYYY)"""
    try:
        if isinstance(date_str, str) and '-' in date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        return str(date_str)
    except:
        return str(date_str)

def format_time_display(time_str):
    """Format time for display (HH:MM:SS to HH:MM)"""
    try:
        if isinstance(time_str, str) and ':' in time_str:
            return time_str[:5]  # Extract HH:MM
        return str(time_str)
    except:
        return str(time_str)

def get_available_schedules_summary():
    """Get a summary of available schedules with cache support"""
    try:
        # Try to get from cache first (using a general cache key)
        cached_schedules = cache_service.get_available_schedules()
        
        if cached_schedules and isinstance(cached_schedules, dict):
            schedules_data = cached_schedules.get('schedules', [])
        else:
            # Cache miss - get from database
            db = next(get_db())
            schedule_results = db.query(Schedule, Doctor).join(Doctor).filter(Schedule.is_available == 'true').all()
            
            schedules_data = []
            for schedule, doctor in schedule_results:
                schedule_dict = schedule.to_dict()
                schedule_dict['doctor_name'] = doctor.name
                schedule_dict['doctor_specialty'] = doctor.specialty
                schedules_data.append(schedule_dict)
            
            # Cache the results
            cache_service.set_available_schedules(
                schedules=schedules_data,
                ttl=300  # 5 minutes
            )
        
        if not schedules_data:
            return "Nenhum horário disponível no momento. Por favor, entre em contato para verificar outras opções."
        
        summary = ""
        current_date = ""
        
        # Organizar por data
        schedules_by_date = {}
        for schedule_data in schedules_data:
            date_key = str(schedule_data.get('date', ''))
            if date_key not in schedules_by_date:
                schedules_by_date[date_key] = []
            schedules_by_date[date_key].append(schedule_data)
        
        # Ordenar as datas
        sorted_dates = sorted(schedules_by_date.keys())
        
        for date_key in sorted_dates:
            date_display = format_date_display(date_key)
            summary += f"📅 {date_display}\n"
            
            # Ordenar horários do dia
            day_schedules = sorted(schedules_by_date[date_key], 
                                 key=lambda x: x.get('start_time', ''))
            
            for schedule_data in day_schedules:
                time_display = format_time_display(str(schedule_data.get('start_time', '')))
                doctor_name = schedule_data.get('doctor_name', 'N/A')
                doctor_specialty = schedule_data.get('doctor_specialty', 'N/A')
                
                # Clean doctor name to avoid "Dr. Dr." duplication
                if doctor_name.startswith('Dr. '):
                    clean_doctor_name = doctor_name
                else:
                    clean_doctor_name = f"Dr. {doctor_name}"
                
                summary += f"   • {time_display} - {clean_doctor_name} ({doctor_specialty})\n"
            
            summary += "\n"
        
        return summary.strip()
    except Exception as e:
        print(f"Error getting schedules summary: {e}")
        return "Ocorreu um erro ao buscar os horários disponíveis. Por favor, tente novamente."

def handle_payment_info():
    """Handle payment info request"""
    payment_info = {
        "consultation_fees": {
            "private": "R$ 200,00",
            "insurance": "Conforme tabela do convênio"
        },
        "payment_methods": [
            "Dinheiro", "Cartão de crédito", "Cartão de débito", 
            "PIX", "Transferência bancária"
        ],
        "insurance_accepted": [
            "Unimed", "Bradesco Saúde", "Amil", "SulAmérica"
        ]
    }
    
    message = "Informações sobre Valores e Formas de Pagamento:\n\n"
    message += f"Consulta Particular: {payment_info['consultation_fees']['private']}\n"
    message += f"Convênio: {payment_info['consultation_fees']['insurance']}\n\n"
    message += "Formas de Pagamento:\n"
    for method in payment_info['payment_methods']:
        message += f"• {method}\n"
    message += "\nConvênios Aceitos:\n"
    for insurance in payment_info['insurance_accepted']:
        message += f"• {insurance}\n"
    message += "\nFicarei feliz em ajudá-lo com mais informações."
    
    return {
        "action_taken": "payment_info_provided",
        "data": payment_info,
        "message": message,
        "suggested_actions": ["book_appointment", "cancel_appointment"]
    }

def get_step_message(step):
    """Get message for current registration step"""
    step_messages = {
        1: {
            "action_taken": "awaiting_name",
            "message": "Por favor, digite seu nome completo:",
            "suggested_actions": ["provide_name"]
        },
        2: {
            "action_taken": "awaiting_cpf",
            "message": "Agora preciso do seu CPF (apenas números ou com pontos e traço):",
            "suggested_actions": ["provide_cpf"]
        },
        3: {
            "action_taken": "awaiting_email",
            "message": "Por favor, digite seu email:",
            "suggested_actions": ["provide_email"]
        },
        4: {
            "action_taken": "awaiting_phone",
            "message": "Digite seu telefone com DDD:",
            "suggested_actions": ["provide_phone"]
        },
        5: {
            "action_taken": "awaiting_birth_date",
            "message": "Por último, digite sua data de nascimento no formato DD/MM/AAAA:",
            "suggested_actions": ["provide_birth_date"]
        }
    }
    
    return step_messages.get(step, step_messages[1])

def complete_appointment_booking(session, user_id):
    """Complete the appointment booking process"""
    try:
        db = next(get_db())
        
        # Create or update patient
        # Prepare patient data
        patient_data = {
            'name': session['data']['name'],
            'cpf': session['data']['cpf'],
            'email': session['data']['email'],
            'phone': session['data']['phone'],
            'birth_date': datetime.strptime(session['data']['birth_date'], '%Y-%m-%d').date()
        }
        
        # Check if patient already exists
        existing_patient = db.query(Patient).filter(Patient.cpf == patient_data['cpf']).first()
        
        if existing_patient:
            # Update existing patient
            for key, value in patient_data.items():
                setattr(existing_patient, key, value)
            patient = existing_patient
        else:
            # Create new patient
            patient = Patient(**patient_data)
            db.add(patient)
            db.flush()  # To get the patient ID
        
        # Get the selected schedule
        selected_schedule = session['data']['selected_schedule']
        schedule_id = selected_schedule['id']
        
        # Create appointment
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=selected_schedule['doctor_id'],
            appointment_date=datetime.strptime(selected_schedule['date'], '%Y-%m-%d').date(),
            appointment_time=datetime.strptime(selected_schedule['start_time'], '%H:%M:%S').time(),
            status='scheduled'
        )
        db.add(appointment)
        
        # Mark schedule as unavailable
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        schedule.is_available = 'false'
        
        db.commit()
        
        # Invalidate cache for this doctor and date
        cache_service.invalidate_schedule_cache(
            doctor_id=selected_schedule['doctor_id'],
            date=selected_schedule['date']
        )
        
        # Format success message
        date_str = datetime.fromisoformat(selected_schedule['date']).strftime('%d/%m/%Y')
        # Handle time parsing properly
        time_str = selected_schedule['start_time']
        if isinstance(time_str, str) and ':' in time_str:
            time_str = time_str[:5]  # Extract HH:MM
        
        message = f"Consulta agendada com sucesso!\n\n"
        message += f"Paciente: {patient.name}\n"
        message += f"Data: {date_str}\n"
        message += f"Horário: {time_str}\n"
        message += f"Médico: Dr. {selected_schedule['doctor_name']}\n"
        message += f"Especialidade: {selected_schedule['doctor_specialty']}\n\n"
        message += "Você receberá uma confirmação em breve. Agradecemos a confiança!"
        
        # Reset user session
        reset_user_session(user_id)
        
        return {
            "action_taken": "appointment_booked",
            "data": {
                "appointment_id": appointment.id,
                "patient": patient_data,
                "schedule": selected_schedule
            },
            "message": message,
            "suggested_actions": ["payment_info"]
        }
        
    except Exception as e:
        print(f"❌ Error booking appointment: {str(e)}")
        reset_user_session(user_id)
        return {
            "action_taken": "booking_error",
            "message": "Ocorreu um erro ao agendar a consulta. Tente novamente.",
            "suggested_actions": ["book_appointment"]
        }

def extract_date_from_message(message):
    """Extract date from user message"""
    import re
    date_patterns = [
        r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',  # DD/MM/YYYY
        r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})',  # YYYY/MM/DD
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, message)
        if match:
            try:
                if len(match.group(1)) == 4:  # YYYY/MM/DD
                    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                else:  # DD/MM/YYYY
                    return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue
    return None

def format_schedules_message(schedules):
    """Format schedules into a user-friendly message"""
    if not schedules:
        return "Não há horários disponíveis no momento. Por favor, entre em contato conosco para verificar outras opções."
    
    message = "Horários Disponíveis:\n\n"
    for i, schedule in enumerate(schedules, 1):
        message += f"{i}. {schedule['date']} às {schedule['start_time'][:5]}\n"
        message += f"   Médico: {schedule['doctor_name']} ({schedule['doctor_specialty']})\n\n"
    
    message += "Para agendar, você pode escolher um horário dizendo: 'Agendar [data] às [hora] com [médico]'"
    return message

def format_payment_info_message(payment_info):
    """Format payment information"""
    message = "Informações sobre Valores e Formas de Pagamento:\n\n"
    message += f"Consulta Particular: {payment_info['consultation_fees']['private']}\n"
    message += f"Convênio: {payment_info['consultation_fees']['insurance']}\n\n"
    
    message += "Formas de Pagamento:\n"
    for method in payment_info['payment_methods']:
        message += f"• {method}\n"
    
    message += "\nConvênios Aceitos:\n"
    for insurance in payment_info['insurance_accepted']:
        message += f"• {insurance}\n"
    
    return message

def extract_doctor_name_from_message(message):
    """Extract doctor name from user message"""
    import re
    
    # Patterns to find doctor names (enhanced with more variations)
    patterns = [
        r'dr\.?\s+([a-záêçãõ\s]+)',  # Dr. Name or Dr Name
        r'doctor\s+([a-záêçãõ\s]+)',  # Doctor Name
        r'doutor\s+([a-záêçãõ\s]+)',  # Doutor Name
        r'doutora\s+([a-záêçãõ\s]+)',  # Doutora Name
        r'com\s+(?:o\s+)?dr\.?\s+([a-záêçãõ\s]+)',  # com (o) Dr. Name
        r'com\s+(?:o\s+)?doutor\s+([a-záêçãõ\s]+)',  # com (o) doutor Name
        r'com\s+(?:a\s+)?doutora\s+([a-záêçãõ\s]+)',  # com (a) doutora Name
        r'with\s+(?:dr\.?\s+)?([a-záêçãõ\s]+)',  # with Dr. Name
    ]
    
    message_lower = message.lower()
    print(f"🔍 Searching for doctor name in: '{message_lower}'")
    
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, message_lower)
        if match:
            doctor_name = match.group(1).strip()
            print(f"🎯 Pattern {i+1} matched: '{pattern}' -> '{doctor_name}'")
            
            # Clean up the name (remove extra words and common stopwords)
            doctor_name = re.sub(r'\s+', ' ', doctor_name)  # Remove extra spaces
            
            # Remove common stopwords that might be captured
            stopwords = ['lima', 'silva', 'costa', 'santos', 'oliveira', 'souza', 'pereira']
            name_parts = doctor_name.split()
            
            # Take first 1-2 meaningful name parts
            clean_name_parts = []
            for part in name_parts[:3]:  # Take up to 3 parts
                if part.lower() not in ['o', 'a', 'da', 'de', 'do', 'e']:
                    clean_name_parts.append(part.title())
                if len(clean_name_parts) >= 2:  # Limit to 2 main name parts
                    break
            
            if clean_name_parts:
                result = ' '.join(clean_name_parts)
                print(f"✅ Extracted doctor name: '{result}'")
                return result
    
    print("❌ No doctor name found")
    return None

def extract_time_from_message(message):
    """Extract time from user message"""
    import re
    from datetime import time
    
    # Patterns to find time
    patterns = [
        r'às\s+(\d{1,2}):(\d{2})',  # às HH:MM
        r'at\s+(\d{1,2}):(\d{2})',  # at HH:MM
        r'(\d{1,2}):(\d{2})',  # HH:MM
        r'às\s+(\d{1,2})h',  # às HHh
        r'(\d{1,2})h(\d{2})',  # HHhMM
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2)) if len(match.groups()) > 1 else 0
                
                # Validate time
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return time(hour, minute)
            except (ValueError, IndexError):
                continue
    
    return None

def extract_appointment_id_from_message(message):
    """Extract appointment ID from user message"""
    import re
    
    # Patterns to find appointment ID
    patterns = [
        r'id\s+(\d+)',  # ID 123
        r'consulta\s+(\d+)',  # consulta 123
        r'appointment\s+(\d+)',  # appointment 123
        r'cancelar\s+(\d+)',  # cancelar 123
        r'cancel\s+(\d+)',  # cancel 123
        r'(?:a\s+)?terceira',  # a terceira (assuming appointment ID 3)
        r'(?:a\s+)?primeira',  # a primeira (assuming appointment ID 1)
        r'(?:a\s+)?segunda',  # a segunda (assuming appointment ID 2)
    ]
    
    message_lower = message.lower()
    
    for pattern in patterns:
        match = re.search(pattern, message_lower)
        if match:
            if pattern in [r'(?:a\s+)?terceira', r'(?:a\s+)?primeira', r'(?:a\s+)?segunda']:
                # Convert ordinal to number
                if 'primeira' in match.group(0):
                    return 1
                elif 'segunda' in match.group(0):
                    return 2
                elif 'terceira' in match.group(0):
                    return 3
            else:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
    
    return None

def extract_patient_info_from_message(message):
    """Extract patient information from user message"""
    import re
    from datetime import datetime
    
    patient_data = {
        'name': None,
        'cpf': None,
        'email': None,
        'phone': None,
        'birth_date': None
    }
    
    # Extract name
    name_patterns = [
        r'(?:meu nome é|me chamo|sou|nome é|my name is)\s+([a-záêçãõ\s]+?)(?:\s*[,.]|$)',
        r'nome:?\s*([a-záêçãõ\s]+?)(?:\s*[,.]|$)',
        r'^([a-záêçãõ\s]+?),\s*cpf',  # Name before CPF
        r'^([A-ZÁÊÇÃÕ][a-záêçãõ]+\s+[A-ZÁÊÇÃÕ][a-záêçãõ]+.*?)(?:\s*[,.]|$)',  # Just a name like "Rodrigo Guedes"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message.lower() if 'nome' in pattern.lower() else message)
        if match:
            name = match.group(1).strip()
            # Clean and format name
            name = re.sub(r'\s+', ' ', name)
            # Remove common extra words
            name_words = name.split()
            clean_words = []
            for word in name_words:
                if word.lower() not in ['da', 'de', 'do', 'dos', 'das', 'e']:
                    clean_words.append(word.title())
                if len(clean_words) >= 3:  # Limit to 3 name parts
                    break
            if clean_words:
                patient_data['name'] = ' '.join(clean_words)
                break
    
    # Extract CPF
    cpf_patterns = [
        r'cpf[:\s]*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})',
        r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})',
    ]
    
    for pattern in cpf_patterns:
        match = re.search(pattern, message)
        if match:
            cpf = match.group(1)
            # Clean CPF (remove dots and dashes)
            cpf_clean = re.sub(r'[.\-]', '', cpf)
            if len(cpf_clean) == 11:
                patient_data['cpf'] = cpf
            break
    
    # Extract email
    email_pattern = r'email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    email_match = re.search(email_pattern, message.lower())
    if email_match:
        patient_data['email'] = email_match.group(1)
    else:
        # Try to find email without prefix
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
        if email_match:
            patient_data['email'] = email_match.group(1)
    
    # Extract phone
    phone_patterns = [
        r'telefone[:\s]*\(?(\d{2})\)?\s*\d{4,5}-?\d{4}',
        r'phone[:\s]*\(?(\d{2})\)?\s*\d{4,5}-?\d{4}',
        r'\(?(\d{2})\)?\s*\d{4,5}-?\d{4}',
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, message)
        if match:
            phone = match.group(0)
            # Clean and format phone
            phone_clean = re.sub(r'[^\d]', '', phone)
            if len(phone_clean) >= 10:
                patient_data['phone'] = phone
            break
    
    # Extract birth date
    birth_patterns = [
        r'nascido em[:\s]*(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
        r'nascimento[:\s]*(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
        r'born[:\s]*(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
        r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
    ]
    
    for pattern in birth_patterns:
        match = re.search(pattern, message)
        if match:
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                
                # Validate date
                birth_date = datetime(year, month, day).date()
                patient_data['birth_date'] = birth_date
                break
            except ValueError:
                continue
    
    return patient_data

# Legacy routes for backward compatibility (without version)
@app.route('/api/health', methods=['GET'])
def health_check_legacy():
    return health_check()

@app.route('/api/patients', methods=['GET'])
def get_patients_legacy():
    return get_patients()

@app.route('/api/doctors', methods=['GET'])
def get_doctors_legacy():
    return get_doctors()

@app.route('/api/schedules/available', methods=['GET'])
def get_available_schedules_legacy():
    return get_available_schedules()

if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)