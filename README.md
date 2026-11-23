# ACEest Fitness & Gym — CI/CD Pipeline

Flask gym portal with Jenkins CI/CD, SonarQube quality gates, Docker Hub images, and five Kubernetes deployment strategies on Minikube.

- GitHub: https://github.com/matheas-2025tm93164/aceest-fitness-app
- Docker Hub: https://hub.docker.com/r/2025tm93164/aceest-fitness

## Pipeline

GitHub → Jenkins (Poll SCM) → Pytest → SonarQube Quality Gate → Docker build
→ Pytest in container → Docker Hub (`v1.0`, `v2.0`, `latest`, `blue`, `green`, `canary`)
→ `kubectl apply` to Minikube namespace `aceest`.

## Repository layout

```
app.py                      Flask application
test_app.py                 Pytest suite
Dockerfile
Jenkinsfile
sonar-project.properties
k8s/namespace.yaml
k8s/rolling/                Rolling update
k8s/blue-green/             Blue-green + rollback
k8s/canary/                 Canary (~20%)
k8s/shadow/                 Shadow / traffic mirror
k8s/ab-testing/             A/B versions A and B
```

## Local run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest --verbose
python app.py
```

App: http://localhost:5000  
Default login: `admin` / `admin`

## Docker

```bash
docker build -t 2025tm93164/aceest-fitness:latest .
docker run -d -p 5000:5000 --name aceest_app 2025tm93164/aceest-fitness:latest
curl http://localhost:5000/health
curl http://localhost:5000/version
```

## Deploy all strategies

```bash
minikube start
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rolling/
kubectl apply -f k8s/blue-green/
kubectl apply -f k8s/canary/
kubectl apply -f k8s/shadow/
kubectl apply -f k8s/ab-testing/
```

| Strategy | Command for URL |
|---|---|
| Rolling | `minikube service aceest-rolling -n aceest --url` |
| Blue-Green | `minikube service aceest-bluegreen -n aceest --url` |
| Canary | `minikube service aceest-canary -n aceest --url` |
| Shadow | `minikube service aceest-shadow-proxy -n aceest --url` |
| A/B A | `minikube service aceest-version-a -n aceest --url` |
| A/B B | `minikube service aceest-version-b -n aceest --url` |

Verify: `curl <url>/health` and `curl <url>/version`

## Rollback

```bash
kubectl rollout undo deployment/aceest-rolling -n aceest

kubectl patch svc aceest-bluegreen -n aceest --type='json' \
  -p='[{"op":"replace","path":"/spec/selector/version","value":"blue"}]'

kubectl scale deployment aceest-stable --replicas=4 -n aceest
kubectl scale deployment aceest-canary --replicas=0 -n aceest
```

