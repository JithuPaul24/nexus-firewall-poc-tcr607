import hashlib
import json
from pathlib import Path


def validate_sbom(path):
    content = Path(path).read_bytes()
    document = json.loads(content)
    if document.get("bomFormat") != "CycloneDX" or not document.get("specVersion"):
        raise ValueError("Expected a CycloneDX document with a declared specification version")
    components = document.get("components", [])
    if not any(
        component.get("purl", "").startswith("pkg:npm/uuid@11.1.0")
        for component in components
    ):
        raise ValueError("SBOM does not contain the application's pinned uuid dependency")
    return {
        "bomFormat": document["bomFormat"],
        "specVersion": document["specVersion"],
        "components": len(components),
        "sha256": hashlib.sha256(content).hexdigest(),
        "validation": "Structural and fixture checks only; not full CycloneDX schema validation",
    }


if __name__ == "__main__":
    print(json.dumps(validate_sbom("evidence/sbom.cdx.json"), indent=2))