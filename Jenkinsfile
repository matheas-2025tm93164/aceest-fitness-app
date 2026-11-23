pipeline {
  agent any

  environment {
    IMAGE = "2025tm93164/aceest-fitness"
    TAG   = "${env.BUILD_NUMBER}"
  }

  triggers {
    pollSCM('H/2 * * * *')
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Install & Unit Test') {
      steps {
        sh '''
          python3 -m venv .venv
          . .venv/bin/activate
          pip install -r requirements.txt pytest-cov
          pytest --verbose --cov=app --cov-report=xml --junitxml=pytest-results.xml
        '''
      }
    }

    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv('SonarQube') {
          sh '''
            sonar-scanner -Dsonar.login="$SONAR_AUTH_TOKEN"
          '''
        }
      }
    }

    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    stage('Docker Build, Test & Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
          sh '''
            echo "$PASS" | docker login -u "$USER" --password-stdin
            docker build -t $IMAGE:v2.0 -t $IMAGE:v1.0 -t $IMAGE:$TAG -t $IMAGE:latest \
              -t $IMAGE:blue -t $IMAGE:green -t $IMAGE:canary .
            docker run --rm $IMAGE:v2.0 pytest --verbose
            docker push $IMAGE:v1.0
            docker push $IMAGE:v2.0
            docker push $IMAGE:$TAG
            docker push $IMAGE:latest
            docker push $IMAGE:blue
            docker push $IMAGE:green
            docker push $IMAGE:canary
          '''
        }
      }
    }

    stage('Deploy to Minikube') {
      steps {
        sh '''
          kubectl apply -f k8s/namespace.yaml
          kubectl apply -f k8s/rolling/
          kubectl apply -f k8s/blue-green/
          kubectl apply -f k8s/canary/
          kubectl apply -f k8s/shadow/
          kubectl apply -f k8s/ab-testing/
        '''
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: '**/pytest*.xml'
      archiveArtifacts artifacts: 'coverage.xml,pytest-results.xml', allowEmptyArchive: true
    }
  }
}
