pipeline {
  agent any

  environment {
    IMAGE = "2025tm93164/aceest-fitness"
    TAG   = "${env.BUILD_NUMBER}"
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
          pytest --verbose --cov=app --cov-report=xml
        '''
      }
    }

    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv('SonarQube') {
          sh 'sonar-scanner'
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

    stage('Docker Build & Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
          sh '''
            echo "$PASS" | docker login -u "$USER" --password-stdin
            docker build -t $IMAGE:v2.0 -t $IMAGE:$TAG -t $IMAGE:latest .
            docker push $IMAGE:v2.0
            docker push $IMAGE:$TAG
            docker push $IMAGE:latest
          '''
        }
      }
    }

    stage('Deploy to Minikube') {
      steps {
        sh 'kubectl apply -f k8s/namespace.yaml'
        sh 'kubectl apply -f k8s/rolling/'
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: '**/pytest*.xml'
      archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
    }
  }
}
