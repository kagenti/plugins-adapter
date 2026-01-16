import logging
import re
from nemoguardrails.actions import action

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

logger = logging.getLogger(__name__)


@action()
def debug_log(value, label: str = "DEBUG"):
    # Purposely high logger level for now to make sure this is visible
    logger.warning(f"{label}: {value}")
    return value


@action()
def detect_pii(tool_input):
    """
    Simple PII detector to start
    """
    text = str(tool_input)

    findings = []

    if EMAIL_RE.search(text):
        findings.append("email")

    if SSN_RE.search(text):
        findings.append("ssn")

    return {
        "found": len(findings) > 0,
        "types": findings,
    }
