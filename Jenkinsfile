pipeline {
    agent { label 'testslave' }
    environment {
        ENV=".env"
        VENV_BIN = "${WORKSPACE}/${ENV}/bin"
        PATH = "/usr/bin:/usr/local/bin"
    }
    stages {
        stage('Setup Environment') {
            steps {
                sh """echo ${VENV_BIN}
                      echo ${PATH}
                      virtualenv ${ENV}
                      source ${VENV_BIN}/activate
                      pip install -r requirements.txt
                      pip freeze
                   """
            }
        }
        stage('Lint the YAML') {
            steps {
                sh """source ${VENV_BIN}/activate
                      git ls-files *.yml | grep -v -E '(test(-|_)?)' | xargs yamllint
                   """
            }
        }
        stage('Lint the Ansible Playbooks') {
            steps {
                sh """source ${VENV_BIN}/activate
                      git ls-files *.yml | grep -v -E '(requirements|test(-|_)?)' | xargs ansible-lint
                   """
            }
        }
    }
}
