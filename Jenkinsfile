pipeline {
    agent any
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }
    parameters {
        booleanParam(name: 'RUN_IQ_EVALUATION', defaultValue: false,
            description: 'Evaluate the built container using the Sonatype Platform Plugin. This does not import the generated SBOM.')
        string(name: 'IQ_INSTANCE_ID', defaultValue: '',
            description: 'Instance ID from the Sonatype Platform Plugin configuration in Jenkins, not the IQ URL.')
        string(name: 'IQ_APPLICATION_ID', defaultValue: '',
            description: 'Existing Lifecycle application ID used for policy evaluation.')
        choice(name: 'IQ_STAGE', choices: ['build', 'develop', 'source', 'stage-release', 'release', 'operate'],
            description: 'Choose a stage available under your Lifecycle licence and configured policies.')
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
                    if (params.RUN_IQ_EVALUATION &&
                        (!params.IQ_INSTANCE_ID?.trim() || !params.IQ_APPLICATION_ID?.trim())) {
                        error('Provide IQ_INSTANCE_ID and IQ_APPLICATION_ID before enabling policy evaluation.')
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
        stage('Lifecycle container policy evaluation') {
            when { expression { params.RUN_IQ_EVALUATION } }
            steps {
                sh 'date -u > evidence/iq-evaluation-start.txt'
                script {
                    writeFile file: 'evidence/iq-evaluation-target.json', text: groovy.json.JsonOutput.prettyPrint(
                        groovy.json.JsonOutput.toJson([
                            instanceId: params.IQ_INSTANCE_ID.trim(),
                            applicationId: params.IQ_APPLICATION_ID.trim(),
                            stage: params.IQ_STAGE,
                            scanTarget: "container:${env.APP_IMAGE}",
                            mode: 'container-policy-evaluation-not-external-sbom-import'
                        ])
                    )
                }
                nexusPolicyEvaluation(
                    iqInstanceId: params.IQ_INSTANCE_ID.trim(),
                    iqApplication: params.IQ_APPLICATION_ID.trim(),
                    iqStage: params.IQ_STAGE,
                    iqScanPatterns: [[scanPattern: "container:${env.APP_IMAGE}"]],
                    jobCredentialsId: 'iq-cred',
                    failBuildOnNetworkError: true,
                    failBuildOnScanningErrors: true
                )
                echo 'Open IQ Build Report / View Application Report for components and policy findings. The external SBOM import remains a separate TC07 check.'
            }
            post {
                always {
                    sh 'date -u > evidence/iq-evaluation-end.txt'
                }
            }
        }
        stage('Generation-only result') {
            when { expression { !params.RUN_IQ_EVALUATION } }
            steps {
                echo 'SBOM generated and archived. Lifecycle container evaluation was disabled; external SBOM import is NOT tested.'
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