pipeline {
    agent any
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }
    parameters {
        booleanParam(name: 'SUBMIT_TO_IQ', defaultValue: false,
            description: 'Enable only after confirming the installed Lifecycle API accepts raw CycloneDX JSON.')
        string(name: 'IQ_SBOM_IMPORT_URL', defaultValue: '',
            description: 'Documented full POST URL, including application/stage where required. Not the UI URL.')
        choice(name: 'IQ_CONTENT_TYPE',
            choices: ['application/json', 'application/vnd.cyclonedx+json', 'application/octet-stream'],
            description: 'Use the content type required by the verified import API.')
    }
    environment {
        SYFT_IMAGE = 'anchore/syft:v1.20.0'
    }
    stages {
        stage('Checkout and prerequisites') {
            steps {
                deleteDir()
                checkout scmGit(
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        credentialsId: 'git-acess',
                        url: 'https://github.com/JithuPaul24/nexus-firewall-poc-tcr607.git'
                    ]]
                )
                script {
                    if (params.SUBMIT_TO_IQ && !params.IQ_SBOM_IMPORT_URL?.trim()) {
                        error('Provide the verified Lifecycle raw-SBOM POST URL before enabling submission.')
                    }
                    env.APP_IMAGE = 'nexus-lifecycle-sbom-poc:' + env.BUILD_TAG.toLowerCase().replaceAll('[^a-z0-9_.-]', '-').take(100)
                }
                sh '''
                    set -eu
                    mkdir -p evidence
                    docker version > evidence/docker-version.txt
                    python3 --version
                    git rev-parse HEAD > evidence/commit.txt
                    date -u > evidence/start.txt
                '''
            }
        }
        stage('Build and test application') {
            steps {
                sh 'docker build --target build --tag "$APP_IMAGE-build" .'
            }
        }
        stage('Build runtime image') {
            steps {
                sh '''
                    set -eu
                    docker build --target runtime --tag "$APP_IMAGE" .
                    docker image inspect "$APP_IMAGE" > evidence/image-inspect.json
                    docker run --rm --network none --entrypoint cat "$APP_IMAGE" /app/package-lock.json > evidence/package-lock.json
                '''
            }
        }
        stage('Generate image SBOM') {
            steps {
                sh '''
                    set -eu
                    docker run --rm --network none \
                        --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock,readonly \
                        "$SYFT_IMAGE" "docker:$APP_IMAGE" -o cyclonedx-json > evidence/sbom.cdx.json
                    docker image inspect "$SYFT_IMAGE" > evidence/generator-image-inspect.json
                    python3 scripts/validate_sbom.py > evidence/sbom-summary.json
                    cat evidence/sbom-summary.json
                    date -u > evidence/sbom-created.txt
                '''
            }
        }
        stage('Submit SBOM to Lifecycle') {
            when { expression { params.SUBMIT_TO_IQ } }
            steps {
                withEnv([
                    "IQ_SBOM_IMPORT_URL=${params.IQ_SBOM_IMPORT_URL.trim()}",
                    "IQ_CONTENT_TYPE=${params.IQ_CONTENT_TYPE}"
                ]) {
                    withCredentials([usernamePassword(credentialsId: 'iq-cred',
                        usernameVariable: 'IQ_USER', passwordVariable: 'IQ_PASS')]) {
                        sh 'set +x; python3 scripts/submit_sbom.py'
                    }
                }
                unstable('HTTP submission accepted. Confirm completed Lifecycle evaluation and inventory before declaring TC07 PASS.')
            }
        }
        stage('Generation-only result') {
            when { expression { !params.SUBMIT_TO_IQ } }
            steps {
                echo 'SBOM generated and archived. Lifecycle submission was disabled; TC07 import is NOT tested.'
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'evidence/**', allowEmptyArchive: true, fingerprint: true
        }
        cleanup {
            sh returnStatus: true, script: '''
                if [ -n "${APP_IMAGE:-}" ]; then
                    docker image rm "$APP_IMAGE" "$APP_IMAGE-build"
                fi
            '''
            deleteDir()
        }
    }
}