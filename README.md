# TC-R6-07: Application, container and CycloneDX SBOM

This isolated PoC builds a Node.js API, tests it, builds a non-root runtime image,
generates an image SBOM with Syft, and optionally POSTs the SBOM to a verified
Sonatype Lifecycle import API. It does not push the container image to a registry.

## Important Lifecycle prerequisite

The installed Lifecycle version and its SBOM import interface have not been supplied.
No version-specific URL or import capability is assumed here. Submission defaults
to off so the application/image/SBOM workflow can be tested independently.

Before enabling submission, ask the Sonatype PoC engineer to confirm:

- The installed version accepts CycloneDX JSON produced by the pinned Syft release.
- The full application-specific POST URL and stage configuration.
- The endpoint accepts a raw SBOM request body with HTTP Basic authentication.
- The required content type and how to retrieve the resulting evaluation/report.

If the documented API requires multipart form data, an archive, a different
authentication scheme, or a CLI import command, the uploader must be adapted first.
Do not point it at the Lifecycle UI or a Repository Manager hosted repository.
Storing a JSON file in Repository Manager does not evaluate it in Lifecycle.

## Jenkins setup

1. Use a trusted Linux worker with Git, Python 3, the Docker CLI and engine access.
2. Allow the Docker engine to reach the Node image registry, npm and the Syft image
   registry. This sample uses public upstream dependencies, not Nexus package proxies.
3. Create a username/password credential named `git-acess` for repository checkout.
4. Create a separate username/password credential named `iq-cred` with permission
   to submit an evaluation for the chosen Lifecycle application.
5. Create a Pipeline job using **Pipeline script from SCM**, Git URL
   `https://github.com/JithuPaul24/nexus-firewall-poc-tcr607.git`, credential
   `git-acess`, branch `*/main`, and script path `Jenkinsfile`.
6. Run with `SUBMIT_TO_IQ=false` to test image building and SBOM generation first.
7. Once the API prerequisite is confirmed, enable `SUBMIT_TO_IQ` and enter the
   documented `IQ_SBOM_IMPORT_URL` and `IQ_CONTENT_TYPE`.

No Sonatype Jenkins plugin is required for this raw HTTP upload implementation.
Python uses normal TLS certificate verification; configure system trust for
internal CAs instead of disabling verification.

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
- Optionally submits the unchanged JSON file using the verified API configuration.
- Archives evidence, removes per-run application image tags and cleans the workspace.

Application dependencies are pinned at the manifest level. No lockfile has been
fabricated or downloaded locally; npm creates one during the Docker build and it
is archived. Pin the base/scanner images by digest and review/commit an approved
lockfile if strict reproducibility is required. These sample versions are not a
claim that the components have no vulnerabilities.

## Evidence and verdict

Build artifacts include the SBOM, its SHA-256 and component count, source commit,
runtime/scanner image details, resolved package lock and timestamps. When submission
is enabled, the HTTP response and acceptance summary are also retained. Restrict
artifact access because evaluation responses may contain internal application data.

Structural validation is not full CycloneDX JSON-schema validation. Validate the
file using the matching official schema or an approved CycloneDX validator for
the formal TC07 evidence bundle.

A successful generation-only run does not test Lifecycle import. Accepted HTTP
submission deliberately marks the run UNSTABLE because HTTP acceptance is not
proof of completed evaluation. Confirm the application report, component inventory,
dependency relationships, policy findings and any unrecognized components in
Lifecycle before declaring PASS. Compare the SBOM's UUID component with the
imported inventory and retain the evaluation/report identifier.

This demonstrates an independently generated image SBOM submitted to Lifecycle.
It does not demonstrate Lifecycle-native SBOM export or regulatory compliance by
itself; record those as separate checks for the complete TC07 test.

## Run the API manually

On an approved build host:

```bash
docker build --target runtime -t nexus-lifecycle-sbom-poc:local .
docker run --rm -p 127.0.0.1:8081:8080 nexus-lifecycle-sbom-poc:local
```

The API serves JSON at `/`, health at `/health`, and HTTP 404 for unknown paths.
No packages or images were downloaded locally while authoring this repository.