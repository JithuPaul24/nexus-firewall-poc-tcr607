# TC-R6-07: Application, container and CycloneDX SBOM

This isolated PoC builds a Node.js API, tests it, builds a non-root runtime image,
generates an image SBOM with Syft, and optionally evaluates the same container
with the Sonatype Platform Plugin for Jenkins. It can push the image to Nexus
and optionally attach the SBOM as an OCI artifact. It does not import the
generated SBOM into Lifecycle.

## Nexus image and SBOM publication

The supplied Docker hosted destination is
`bankofcanada.repo.sonatype.app/jithu-test-images/`. Each build publishes a unique
tag under `bankofcanada.repo.sonatype.app/jithu-test-images/nexus-lifecycle-sbom-poc`.
Docker login uses only the registry host, `bankofcanada.repo.sonatype.app`, not
the repository path.

Create a Jenkins username/password credential named `nexus-cred` with permission
to upload images and OCI artifacts to this repository. An account previously
used only for proxy downloads may not have the required write permissions.

- `PUSH_IMAGE_TO_NEXUS=true` enables image publication and is the default.
- `ATTACH_OCI_SBOM=false` is the default until registry compatibility is confirmed.
- To enable attachment, install a compatible ORAS CLI on the Jenkins worker and
   confirm your Nexus version supports the OCI artifacts/referrer mechanism used
   by that ORAS release. The pipeline does not install ORAS automatically.
- With attachment enabled, `oras attach` publishes the CycloneDX file associated
   with the pushed image's manifest digest, and `oras discover` records referrers.
   A registry rejection fails the stage; the workflow does not silently fall back
   to storing the SBOM elsewhere.

The pipeline uses temporary Docker authentication directories and removes them
after each publication stage. It does not archive credentials or registry login
configuration. Configure registry CA trust on the Docker host/worker as needed;
the pipeline does not enable insecure registries or disable TLS verification.

Publishing an OCI SBOM does not cause Lifecycle to analyze it automatically.
The existing IQ stage still scans the built container, not the attached JSON.
The version-specific external-SBOM import command/API remains required before
that part of the requested workflow can be implemented.

Image publication occurs before IQ evaluation as requested for this PoC. This
is not a production release gate: a later policy failure does not remove an
already published image or artifact. Use a staging repository and separate
promotion controls for production workflows.

## Documented Lifecycle integration

The integration follows the [Sonatype Platform Plugin for Jenkins documentation](https://help.sonatype.com/en/sonatype-platform-plugin-for-jenkins.html)
provided for this PoC. It uses `nexusPolicyEvaluation` with the documented
`container:` scan target. Evaluation defaults to off so the application, image
and SBOM generation can be checked before configuring the IQ connection.

The plugin documentation provided does not establish support for importing an
external CycloneDX file. Pointing `iqScanPatterns` at a JSON file is not evidence
that its SBOM contents were imported. The previous speculative HTTP uploader has
been removed rather than retained as an unverified submission path.

For TC07's external-SBOM exchange requirement, obtain the separately documented
import interface and supported CycloneDX version from Sonatype. Storing a JSON
file in Repository Manager does not evaluate it in Lifecycle.

## Jenkins setup

1. Use a trusted Linux worker with Git, Python 3, the Docker CLI and engine access.
2. Allow the Docker engine to reach the Node image registry, npm and the Syft image
   registry. This sample uses public upstream dependencies, not Nexus package proxies.
3. Create a username/password credential named `git-acess` for repository checkout.
4. Install a compatible Sonatype Platform Plugin for Jenkins that exposes the
   `nexusPolicyEvaluation` step and the documented scanning-error option.
5. Configure the IQ server connection in the plugin's global configuration. Record
   its instance ID; `IQ_INSTANCE_ID` is that configured ID, not the server URL.
6. Create a separate username/password credential named `iq-cred` with permission
   to evaluate the chosen Lifecycle application. The pipeline supplies it using
   the documented `jobCredentialsId` override. Use the credential type supported
   by your installed plugin and server configuration.
7. Create the application in Lifecycle, record its application ID and configure
   policy actions for the intended stage. The pipeline does not request automatic
   application creation or specify an organization.
8. Create a Pipeline job using **Pipeline script from SCM**, Git URL
   `https://github.com/JithuPaul24/nexus-firewall-poc-tcr607.git`, credential
   `git-acess`, branch `*/main`, and script path `Jenkinsfile`.
9. Configure `nexus-cred` as described above. For a generation-only run, set both
   `PUSH_IMAGE_TO_NEXUS=false` and `RUN_IQ_EVALUATION=false`. For publishing, leave
   `PUSH_IMAGE_TO_NEXUS=true`; enable `ATTACH_OCI_SBOM` only after its prerequisites.
10. Enable `RUN_IQ_EVALUATION`, enter `IQ_INSTANCE_ID` and `IQ_APPLICATION_ID`,
    then select a licensed `IQ_STAGE` with the intended policy actions.

Use Jenkins **Pipeline Syntax** to confirm the generated `nexusPolicyEvaluation`
arguments match the installed plugin. The documented example accepts a string
application ID; some generated snippets may use `selectedApplication(...)`.
If the installed version generates a different application representation,
substitute the generated form. Only select stages available under your licence.

The plugin uses Jenkins HTTP proxy settings in preference to JVM proxy settings.
Configure the non-proxy hosts list for IQ where required. Trust internal CAs in
the relevant Jenkins/scanner JVM rather than disabling certificate verification.
Jenkins must be able to reach IQ as well as the local Docker engine.

Docker socket access gives the job effectively root-level host privileges. Use
only an isolated PoC worker with trusted source code. The Syft container accesses
the host image through the socket; it does not bind-mount the Jenkins workspace,
which may not exist at the same path on the Docker host. A read-only socket mount
does not make Docker API access read-only.

## What Jenkins does

- Builds the `build` Docker stage, where `npm test` and `npm run build` execute.
- Builds the `runtime` stage and records its image ID and resolved package lock.
- Uses `anchore/syft:v1.20.0` to generate `evidence/sbom.cdx.json` from that image.
- Checks CycloneDX identity and confirms `uuid@11.1.0` is present.
- Pushes the runtime image to the supplied Nexus path when publication is enabled.
- Optionally attaches the SBOM to the published manifest digest using ORAS.
- Optionally invokes `nexusPolicyEvaluation` against `container:<built-image-tag>`.
- Sets `failBuildOnNetworkError` and `failBuildOnScanningErrors` to `true`.
- Leaves final policy status to the plugin: Warn is UNSTABLE, Fail is FAILURE,
  and No Action does not change the build result. It does not swallow errors or
  force all completed evaluations to UNSTABLE.
- Archives evidence, removes per-run application image tags and cleans the workspace.

Application dependencies are pinned at the manifest level. No lockfile has been
fabricated or downloaded locally; npm creates one during the Docker build and it
is archived. Pin the base/scanner images by digest and review/commit an approved
lockfile if strict reproducibility is required. These sample versions are not a
claim that the components have no vulnerabilities.

## Evidence and verdict

Build artifacts include the SBOM, its SHA-256 and component count, source commit,
runtime/scanner image details, resolved package lock and timestamps. Image pushes
also retain the push log, published image inspection and manifest-digest reference.
OCI attachment retains the ORAS version, attachment log and discovered referrers.
For formal storage verification, retrieve the attached SBOM with ORAS using its
artifact digest and compare its SHA-256 with the archived original. Discovery
alone does not establish a byte-for-byte round trip.

When IQ
evaluation is enabled, the application, instance, stage and container target are
recorded in `evidence/iq-evaluation-target.json`, with evaluation start/end times.
The plugin publishes **IQ Build Report** and **View Application Report** links.
Restrict artifact/report access because evidence may contain internal data.

Structural validation is not full CycloneDX JSON-schema validation. Validate the
file using the matching official schema or an approved CycloneDX validator for
the formal TC07 evidence bundle.

A successful generation-only run does not test Lifecycle analysis. With evaluation
enabled, inspect **IQ Build Report** in the Jenkins build and follow **View
Application Report** to confirm the application, stage, components and policy
findings in IQ. A successful policy evaluation does not imply zero vulnerabilities:
findings configured with No Action do not fail the build.

Compare the independently generated SBOM with the component inventory from the
container evaluation and record scanner differences. This workflow demonstrates
SBOM generation plus Lifecycle container analysis, not external SBOM import or
Lifecycle-native SBOM export. Keep those exchange checks and any regulatory
evidence assessment separate for the complete TC07 test.

## Run the API manually

On an approved build host:

```bash
docker build --target runtime -t nexus-lifecycle-sbom-poc:local .
docker run --rm -p 127.0.0.1:8081:8080 nexus-lifecycle-sbom-poc:local
```

The API serves JSON at `/`, health at `/health`, and HTTP 404 for unknown paths.
No packages or images were downloaded locally while authoring this repository.