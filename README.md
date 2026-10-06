# ACEest Fitness & Gym - Automated CI/CD Pipeline

## Project Overview
This repository contains the web application and automated DevOps workflow for ACEest Fitness & Gym. The system transitions from Python microservices through containerization with Docker, secondary quality validation in Jenkins, and continuous delivery execution using GitHub Actions.

---

## Repository Structure
├── .github/
│   └── workflows/
│       └── main.yml        # GitHub Actions CI/CD Pipeline Configuration
├── app.py                  # Core Flask Web Application & API Service
├── test_app.py             # Pytest Unit Testing Suite
├── Dockerfile              # Docker Containerization Specification
├── .dockerignore           # Exclusions for Docker Build Context
├── requirements.txt        # Python Application Dependencies
└── README.md               # Operations & Infrastructure Documentation

---

## Local Setup & Execution Instructions

### Prerequisites
* Python 3.10+
* Docker Engine 24.0+

### Manual Run (Local Environment)
1. Clone the repository:
   
   ```bash
   git clone [https://github.com/matheas-2025tm93164/aceest-fitness-app.git](https://github.com/matheas-2025tm93164/aceest-fitness-app.git)
   cd aceest-fitness-app

3. Create and activate a virtual environment:
   
   ```bash
   python3 -m venv venv
   source venv/bin/activate

5. Install required packages:
   
   ```bash
   pip install -r requirements.txt

7. Start the application:
   
   ```bash
   python app.py

Access the web app at http://localhost:5000.

### Running Unit Tests Manually

Run the test suite using pytest:

Execute unit tests

```bash
pytest --verbose
```

Run test coverage report

```bash
pytest --verbose -s
```

### Docker Containerization

1. Build Docker Image:
docker build -t aceest-fitness:latest .

2. Run Container:
docker run -d -p 5000:5000 --name aceest_app aceest-fitness:latest

3. Verify Execution:
curl http://localhost:5000/health
