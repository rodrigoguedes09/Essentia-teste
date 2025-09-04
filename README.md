# Medical Automation API

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache-red.svg)](https://redis.io/)
[![Tests](https://img.shields.io/badge/Tests-45%20Passing-brightgreen.svg)](#testes)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema de automação médica desenvolvido em Python com Flask, oferecendo uma API REST robusta para gerenciamento de pacientes, médicos, agendamentos e assistente virtual inteligente. A aplicação inclui sistema de cache Redis para otimização de performance e suíte completa de testes automatizados.

## Demonstração do Sistema

### Funcionalidades Principais

[![Demonstração do Sistema](https://img.youtube.com/vi/oVtqVpwjqBs/maxresdefault.jpg)](https://youtube.com/shorts/oVtqVpwjqBs)

**Gerenciamento de Pacientes:**
- Cadastro completo com validação de CPF, email e telefone
- Consulta, atualização e remoção de registros
- Armazenamento seguro de dados pessoais

**Sistema de Agendamentos:**
- Consulta de horários disponíveis por médico e data
- Agendamento automático de consultas
- Cancelamento e reagendamento de appointments
- Informações sobre valores e formas de pagamento

**Assistente Virtual Inteligente:**
- Processamento de linguagem natural
- Detecção automática de intenções do usuário
- Agendamento via conversação
- Respostas contextuais e personalizadas

**Sistema de Cache Redis:**
- Cache inteligente com TTL configurável
- Invalidação automática em operações CRUD
- Fallback graceful quando Redis não disponível
- Monitoramento de performance em tempo real

### Exemplo de Uso da API

```bash
# Verificar saúde do sistema
curl http://localhost:5000/health

# Consultar pacientes
curl http://localhost:5000/patients

# Verificar horários disponíveis
curl http://localhost:5000/available-schedules?date=2025-09-10

# Interagir com assistente virtual
curl -X POST http://localhost:5000/ai-agent \
  -H "Content-Type: application/json" \
  -d '{"message": "Quais horários estão disponíveis?", "user_id": "user123"}'
```

### Casos de Uso Demonstrados

1. **Fluxo de Agendamento Completo:** Desde a consulta de horários até confirmação
2. **Integração com Cache:** Performance otimizada para consultas frequentes
3. **Assistente Virtual:** Interação natural em português para agendamentos
4. **Validação de Dados:** Verificação rigorosa de entrada em todos os endpoints
5. **Tratamento de Erros:** Respostas adequadas para cenários de falha

## Integração com N8N

### Visão Geral

O sistema foi desenvolvido com integração nativa para N8N (Node Automation), permitindo automação completa de workflows médicos através de interfaces visuais.

### Características da Integração

**Webhook Endpoints:** Todos os endpoints da API são compatíveis com webhooks do N8N, permitindo triggers automáticos baseados em eventos.

**Processamento de Dados:** Respostas estruturadas em JSON facilitam o processamento por nodes do N8N.

**Assistente Virtual:** O endpoint `/ai-agent` oferece processamento de linguagem natural para automação de conversas.

**Cache e Performance:** Sistema otimizado para múltiplas requisições simultâneas do N8N.

### Configuração N8N

<img width="2108" height="1478" alt="image" src="https://github.com/user-attachments/assets/d1bd3f2b-3cae-4921-95c8-a7bf96779144" />


## Início Rápido

### Pré-requisitos

- Python 3.11 ou superior
- Redis Server (opcional - sistema funciona com fallback)
- Git para controle de versão

### Instalação e Execução

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/medical-automation-api.git
   cd medical-automation-api
   ```

2. **Crie um ambiente virtual:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente (opcional):**
   ```bash
   copy .env.example .env
   # Edite o arquivo .env conforme necessário
   ```

5. **Execute a aplicação:**
   ```bash
   cd src
   python app.py
   ```

6. **Acesse a API:**
   ```
   http://localhost:5000
   ```

### Execução dos Testes

```bash
# Executar todos os testes
python run_tests.py

# Ou usar pytest diretamente
pytest tests/ -v

# Gerar relatório HTML
pytest tests/ --html=test_report.html --self-contained-html
```

## Estrutura do Projeto

```
medical-automation-api/
├── README.md                       # Documentação principal
├── requirements.txt                # Dependências Python
├── pytest.ini                     # Configuração de testes
├── run_tests.py                    # Script executor de testes
├── .gitignore                      # Controle de versão
├── config/                         # Configurações
│   ├── __init__.py
│   └── settings.py                 # Settings da aplicação
├── src/                            # Código fonte principal
│   ├── app.py                      # Aplicação Flask principal
│   ├── database/                   # Camada de dados
│   │   ├── connection.py           # Conexão SQLAlchemy
│   │   ├── seed_data.py            # Dados iniciais
│   │   └── seed_data_new.py        # Dados expandidos
│   ├── models/                     # Modelos de dados
│   │   ├── patient.py              # Modelo de Paciente
│   │   └── appointment.py          # Modelos de Consulta/Médico
│   ├── routes/                     # Rotas da API
│   │   ├── patients.py             # Endpoints de pacientes
│   │   └── appointments.py         # Endpoints de consultas
│   ├── services/                   # Lógica de negócio
│   │   ├── patient_service.py      # Serviços de paciente
│   │   ├── appointment_service.py  # Serviços de consulta
│   │   └── cache_service.py        # Sistema de cache Redis
│   └── utils/                      # Utilitários
│       └── validators.py           # Validadores de entrada
├── tests/                          # Suíte de testes
│   ├── test_unit_core.py           # 17 testes unitários
│   ├── test_api_integration.py     # 28 testes de integração
│   └── TEST_DOCUMENTATION.md      # Documentação dos testes
└── docs/                           # Documentação adicional
    ├── cache-documentation.md      # Documentação do cache
    ├── advanced-features-guide.md  # Guia de recursos avançados
    └── n8n-workflow-guide.md       # Integração com N8N
```

## Tecnologias Utilizadas

### Framework Backend
- **Flask 2.3.3** - Framework web minimalista e flexível para Python
- **SQLAlchemy 2.0+** - ORM (Object-Relational Mapping) para Python
- **SQLite** - Banco de dados embarcado para desenvolvimento e testes

### Sistema de Cache
- **Redis** - Sistema de cache em memória de alta performance
- **Fallback Mode** - Sistema funciona normalmente sem Redis disponível
- **TTL Configurável** - Cache com expiração automática configurável (padrão: 5 minutos)

### Testes e Qualidade de Código
- **pytest 7.1.2+** - Framework de testes moderno para Python
- **pytest-html** - Geração de relatórios HTML detalhados
- **pytest-cov** - Análise de cobertura de código
- **45 Testes Automatizados** - Taxa de sucesso de 100%

### Ferramentas de Desenvolvimento
- **Requests** - Cliente HTTP para testes de integração
- **Flask-Testing** - Utilitários específicos para testes Flask
- **Type Hints** - Código com tipagem estática para melhor manutenibilidade

## Arquitetura da Aplicação

### Padrão de Design

A aplicação segue uma arquitetura em camadas (Layered Architecture) com separação clara de responsabilidades:

```
┌─────────────────────────────────────┐
│          API Routes Layer           │  ← Endpoints HTTP
├─────────────────────────────────────┤
│         Services Layer              │  ← Lógica de negócio
├─────────────────────────────────────┤
│          Cache Layer                │  ← Sistema de cache Redis
├─────────────────────────────────────┤
│         Models Layer                │  ← Modelos de dados
├─────────────────────────────────────┤
│        Database Layer               │  ← Persistência SQLite
└─────────────────────────────────────┘
```

### Sistema de Cache Redis

**Características Principais:**
- **Cache Inteligente:** TTL de 5 minutos para dados dinâmicos
- **Invalidação Automática:** Cache automaticamente limpo em operações CRUD
- **Fallback Graceful:** Sistema funciona normalmente sem Redis disponível
- **Health Monitoring:** Monitoramento contínuo da saúde do cache
- **Estatísticas de Performance:** Métricas de uso em tempo real

**Implementação Técnica:**
```python
# Exemplo de uso do sistema de cache
cache_service.set_available_schedules(data, ttl=300)
cached_data = cache_service.get_available_schedules()
cache_service.invalidate_schedule_cache()
```

### Assistente Virtual Integrado

**Funcionalidades Principais:**
- **Processamento de Linguagem Natural:** Detecção automática de intenções
- **Agendamento Inteligente:** Marcação de consultas através de conversação
- **Consulta de Informações:** Horários, valores e médicos disponíveis
- **Validação Rigorosa:** Verificação de parâmetros obrigatórios
- **Respostas Contextuais:** Interações naturais e intuitivas em português

## Referência da API

### Endpoints de Saúde e Cache

```http
GET /health
# Verifica o status de saúde da aplicação

GET /cache/stats  
# Retorna estatísticas do sistema de cache

GET /cache/health
# Verifica o status de saúde do Redis
```

### Endpoints de Pacientes

```http
GET /patients
# Lista todos os pacientes cadastrados
# Resposta: Array de objetos Patient

GET /patients/{id}
# Busca paciente específico por ID
# Resposta: Objeto Patient ou código 404

POST /patients
# Cria novo paciente
# Body: { "name": "string", "cpf": "string", "email": "string", "phone": "string", "birth_date": "YYYY-MM-DD" }
# Resposta: Patient criado com ID

PUT /patients/{id}
# Atualiza paciente existente
# Body: Campos a serem atualizados
# Resposta: Patient atualizado

DELETE /patients/{id}
# Remove paciente do sistema
# Resposta: 204 No Content
```

### Endpoints de Médicos e Agendamentos

```http
GET /doctors
# Lista todos os médicos cadastrados
# Resposta: Array de objetos Doctor

GET /available-schedules
# Lista horários disponíveis para agendamento
# Query params: ?date=YYYY-MM-DD&doctor_id=int
# Resposta: Array de objetos Schedule disponíveis

GET /available-schedules?date=2025-09-10
# Filtra horários por data específica

GET /available-schedules?doctor_id=1
# Filtra horários por médico específico
```

### Endpoints de Consultas

```http
GET /appointments
# Lista todas as consultas agendadas
# Resposta: Array de objetos Appointment

POST /appointments
# Agenda nova consulta
# Body: { "patient_id": int, "doctor_id": int, "date": "YYYY-MM-DD", "time": "HH:MM", "notes": "string" }
# Resposta: Appointment criado

DELETE /appointments/{id}
# Cancela consulta agendada
# Resposta: 204 No Content

GET /payment-info
# Informações sobre valores e formas de pagamento
# Resposta: Objeto com valores e métodos de pagamento
```

### Endpoint do Assistente Virtual

```http
POST /ai-agent
# Interage com o assistente virtual
# Body: { "message": "string", "user_id": "string" }
# Resposta: { "success": bool, "action_taken": "string", "message": "string", "data": object, "suggested_actions": array }

# Exemplos de mensagens suportadas:
# - "Olá" → Saudação e apresentação do menu de opções
# - "Quais horários disponíveis?" → Lista de horários disponíveis
# - "Qual o valor da consulta?" → Informações de pagamento
# - "Quero agendar uma consulta" → Inicia processo de agendamento
```

### Exemplos de Respostas

**Objeto Patient:**
```json
{
  "id": 1,
  "name": "João Silva",
  "cpf": "12345678901",
  "email": "joao@email.com",
  "phone": "11999999999",
  "birth_date": "1990-05-15",
  "created_at": "2025-09-03T10:00:00"
}
```

**Objeto Schedule:**
```json
{
  "id": 1,
  "doctor_id": 1,
  "doctor_name": "Dr. Ana Silva",
  "doctor_specialty": "Cardiologia",
  "date": "2025-09-10",
  "start_time": "09:00:00",
  "end_time": "10:00:00",
  "is_available": true
}
```

**Resposta do AI Agent:**
```json
{
  "success": true,
  "action_taken": "schedules_retrieved",
  "message": "Horários Disponíveis:\n\n1. 10/09/2025 às 09:00\n   Dr. Ana Silva - Cardiologia",
  "data": [...],
  "suggested_actions": ["book_appointment", "payment_info"]
}
```

## Testes

### Suíte de Testes Completa

A aplicação possui 45 testes automatizados com 100% de taxa de sucesso, cobrindo:

**Testes Unitários (17 testes)**
- Validação de formatos (CPF, email, telefone, datas)
- Lógica de negócio e regras de validação
- Funções utilitárias e formatação
- Gerenciamento de sessões
- AI Agent e detecção de intenções
- Estruturas de dados e modelos
- Tratamento de erros e exceções

**Testes de Integração (28 testes)**
- Todos os endpoints da API
- Sistema de cache Redis
- Validação de parâmetros HTTP
- Respostas de erro adequadas
- Integração com banco de dados
- AI Agent com casos de uso reais
- Fallback do sistema de cache

### Executando os Testes

**Opção 1: Script Interativo (Recomendado)**
```bash
python run_tests.py
```
- Menu interativo com opções
- Instalação automática de dependências
- Verificação de servidor da API
- Relatórios detalhados

**Opção 2: Pytest Direto**
```bash
# Todos os testes
pytest tests/ -v

# Apenas testes unitários
pytest tests/test_unit_core.py -v

# Apenas testes de integração
pytest tests/test_api_integration.py -v

# Com cobertura de código
pytest tests/ --cov=src --cov-report=html

# Gerar relatório HTML
pytest tests/ --html=test_report.html --self-contained-html
```

**Opção 3: Categorias Específicas**
```bash
# Testes de cache
pytest tests/ -m cache -v

# Testes da API
pytest tests/ -m api -v

# Testes unitários
pytest tests/ -m unit -v
```

### Relatórios de Teste

**Relatório HTML:** Gerado automaticamente em `test_report.html`
- Resultados detalhados por teste
- Tempo de execução de cada teste
- Logs de falhas (se houver)
- Estatísticas de performance

**Cobertura de Código:** Análise completa do código testado
- Percentual de cobertura por arquivo
- Linhas não cobertas identificadas
- Relatório visual em HTML

### Exemplo de Saída dos Testes

```
====================================================================== test session starts ======================================================================
platform win32 -- Python 3.11.9, pytest-7.1.2
collected 45 items

tests/test_unit_core.py::TestCoreBusinessLogic::test_date_format_validation PASSED                  [  2%]
tests/test_unit_core.py::TestCoreBusinessLogic::test_time_format_validation PASSED                  [  4%]
tests/test_unit_core.py::TestCoreBusinessLogic::test_cpf_format_validation PASSED                   [  6%]
tests/test_unit_core.py::TestCoreBusinessLogic::test_email_basic_validation PASSED                  [  8%]
tests/test_unit_core.py::TestCoreBusinessLogic::test_phone_basic_validation PASSED                  [ 11%]
...
tests/test_api_integration.py::TestAPIEndpoints::test_ai_agent_greeting PASSED                      [ 82%]
tests/test_api_integration.py::TestAPIEndpoints::test_ai_agent_payment_info_request PASSED          [ 84%]
tests/test_api_integration.py::TestCacheService::test_cache_fallback_behavior PASSED               [100%]

====================================================================== 45 passed in 9.74s =======================================================================
```

## Configuração e Personalização

### Variáveis de Ambiente

Crie um arquivo `.env` baseado no `.env.example`:

```bash
# Configuração do banco de dados
DATABASE_URL=sqlite:///medical_automation.db

# Configuração do Redis (opcional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Configuração da aplicação
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# Configuração de cache
CACHE_DEFAULT_TTL=300
CACHE_ENABLED=True
```

### Suporte Docker

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "src/app.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**Executar com Docker:**
```bash
docker-compose up -d
```

### Monitoramento e Observabilidade

**Health Checks:**
```bash
# Verificar saúde da aplicação
curl http://localhost:5000/health

# Status do cache Redis
curl http://localhost:5000/cache/health

# Estatísticas de performance
curl http://localhost:5000/cache/stats
```

**Exemplo de Response - Health Check:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-03T20:30:00",
  "version": "1.0.0",
  "database": "connected",
  "cache": "enabled"
}
```

## Integrações

### Exemplos de Cliente API

**JavaScript/Node.js:**
```javascript
const response = await fetch('http://localhost:5000/ai-agent', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Quero agendar uma consulta',
    user_id: 'user123'
  })
});
const data = await response.json();
```

**Python:**
```python
import requests

response = requests.post('http://localhost:5000/ai-agent', json={
    'message': 'Quais horários disponíveis?',
    'user_id': 'user123'
})
data = response.json()
```

**cURL:**
```bash
curl -X POST http://localhost:5000/ai-agent \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá", "user_id": "user123"}'
```

## Deploy em Produção

### Opções de Deployment

**1. Heroku:**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

**2. AWS EC2:**
```bash
# Instalar dependências
sudo apt update
sudo apt install python3-pip redis-server

# Clonar e configurar
git clone <repo-url>
cd medical-automation-api
pip3 install -r requirements.txt

# Executar com Gunicorn
pip3 install gunicorn
gunicorn --bind 0.0.0.0:5000 src.app:app
```

**3. Railway/Render:**
- Conectar repositório GitHub
- Configurar variáveis de ambiente
- Deploy automático

### Configurações de Produção

**Segurança:**
```python
# Em produção, configurar:
- SECRET_KEY forte e único
- CORS configurado adequadamente
- Rate limiting implementado
- HTTPS obrigatório
- Validação de entrada rigorosa
```

**Performance:**
```python
# Otimizações:
- Redis em servidor dedicado
- Connection pooling do banco
- Cache headers HTTP
- Compressão gzip
- CDN para assets estáticos
```

**Monitoramento:**
```python
# Ferramentas recomendadas:
- Prometheus + Grafana (métricas)
- Sentry (error tracking)
- New Relic (APM)
- CloudWatch (AWS)
```

## Documentação Adicional

- **[Cache Documentation](cache-documentation.md)** - Detalhes do sistema de cache Redis
- **[Advanced Features Guide](advanced-features-guide.md)** - Recursos avançados da API
- **[N8N Integration Guide](n8n-workflow-guide.md)** - Guia de integração com N8N
- **[Test Documentation](tests/TEST_DOCUMENTATION.md)** - Documentação completa dos testes


## Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---


