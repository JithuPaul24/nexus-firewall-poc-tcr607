import base64
import json
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def submit_sbom():
    endpoint = os.environ["IQ_SBOM_IMPORT_URL"].strip()
    url = urlsplit(endpoint)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError("Use a documented HTTPS import URL without embedded credentials or fragment")
    content_type = os.environ.get("IQ_CONTENT_TYPE", "application/json").strip()
    if content_type not in ("application/json", "application/vnd.cyclonedx+json", "application/octet-stream"):
        raise ValueError("Unsupported upload content type")
    payload = Path("evidence/sbom.cdx.json").read_bytes()
    document = json.loads(payload)
    if document.get("bomFormat") != "CycloneDX":
        raise ValueError("Refusing to submit a non-CycloneDX payload")
    credentials = os.environ["IQ_USER"] + ":" + os.environ["IQ_PASS"]
    authorization = base64.b64encode(credentials.encode()).decode("ascii")
    request = Request(endpoint, data=payload, method="POST", headers={
        "Authorization": "Basic " + authorization,
        "Content-Type": content_type,
        "Accept": "application/json",
    })
    opener = build_opener(RejectRedirects(), HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=120) as response:
            status = response.status
            body = response.read()
    except HTTPError as error:
        Path("evidence/iq-response.txt").write_bytes(error.read())
        raise RuntimeError(f"IQ submission rejected: HTTP {error.code}; inspect archived iq-response.txt") from None
    except URLError as error:
        raise RuntimeError(f"IQ submission connection failed: {error.reason}") from None
    Path("evidence/iq-response.txt").write_bytes(body)
    if not 200 <= status < 300:
        raise RuntimeError(f"Unexpected submission response: HTTP {status}")
    if body.strip():
        try:
            json.loads(body)
        except ValueError:
            raise RuntimeError("Endpoint returned a non-JSON response; verify it is an import API, not a login page") from None
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "httpStatus": status,
        "state": "HTTP_ACCEPTED_EVALUATION_UNVERIFIED",
        "nextAction": "Verify the Lifecycle evaluation, component inventory and policy results",
    }
    Path("evidence/iq-submission.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    submit_sbom()