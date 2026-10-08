"""
Fetch and extract job descriptions from URLs.

No Django imports: the caller (the view) decides how errors are presented.

The security-relevant problem here is SSRF (Server-Side Request Forgery):
a user could submit a link pointing at our own private network — e.g.
http://localhost:8000/ or http://169.254.169.254/ (cloud metadata) — and
make the server issue requests it should never make. Every URL we request,
including every redirect hop, must pass `validate_public_url` first.
"""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
import trafilatura

from .text_utils import clean_text

REQUEST_TIMEOUT = 10  # seconds per request
MAX_REDIRECTS = 5
MAX_HTML_BYTES = 2 * 1024 * 1024  # 2 MB; no real job page comes close
MIN_DESCRIPTION_LENGTH = 200  # chars; below this, extraction likely failed

# Some sites reject requests without a browser-like User-Agent.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


class JobFetchError(Exception):
    """User-facing error raised when a job page cannot be fetched or read."""


def validate_public_url(url):
    """
    Reject URLs that don't point at a public internet address.

    Checks:
      1. Scheme must be http/https (no file://, ftp://, etc).
      2. A hostname must exist.
      3. Every IP the hostname resolves to must be globally routable —
         loopback, private LAN, link-local (cloud metadata), and reserved
         ranges are all rejected.

    Returns the trimmed URL when it is safe to request.
    """
    parsed = urlparse(url.strip())

    if parsed.scheme not in {"http", "https"}:
        raise JobFetchError("Only http:// and https:// links are supported.")

    if not parsed.hostname:
        raise JobFetchError("This doesn't look like a valid link.")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise JobFetchError(
            "Could not resolve this website's address. Please check the link."
        ) from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise JobFetchError(
                "This link points to a private or local network address, "
                "which is not allowed."
            )

    return url.strip()


def fetch_job_page(url):
    """
    Download a job page as HTML, following redirects safely.

    Redirects are followed manually (allow_redirects=False) so that every
    hop passes validate_public_url — otherwise a public URL could bounce us
    to http://localhost/. The response body is read with a hard size cap so
    a huge or malicious page cannot exhaust memory.
    """
    current_url = validate_public_url(url)
    response = None

    for _ in range(MAX_REDIRECTS + 1):
        try:
            response = requests.get(
                current_url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
        except requests.Timeout as exc:
            raise JobFetchError(
                "The website took too long to respond. Try again or paste "
                "the job description instead."
            ) from exc
        except requests.RequestException as exc:
            raise JobFetchError(
                "Could not reach this website. Check your internet "
                "connection or paste the job description instead."
            ) from exc

        if response.is_redirect and response.headers.get("Location"):
            location = urljoin(current_url, response.headers["Location"])
            response.close()
            current_url = validate_public_url(location)
            continue

        break
    else:
        raise JobFetchError("Too many redirects — the link may be broken.")

    status = response.status_code

    if status == 404:
        response.close()
        raise JobFetchError(
            "This job page was not found (HTTP 404). Please check the link."
        )

    # 999 is LinkedIn's "go away, bot" status; the rest are standard blocks.
    if status in (401, 403, 429) or status == 999:
        response.close()
        raise JobFetchError(
            f"This website blocked automated access (HTTP {status}). "
            "Open the link, copy the job description and paste it instead."
        )

    if status >= 400:
        response.close()
        raise JobFetchError(
            f"The website returned an error (HTTP {status}). "
            "Try again or paste the job description instead."
        )

    content_type = response.headers.get("Content-Type", "")
    if "text" not in content_type and "html" not in content_type:
        response.close()
        raise JobFetchError(
            "This link does not point to a readable web page. "
            "Please paste the job description instead."
        )

    encoding = response.encoding or "utf-8"
    chunks = []
    total = 0

    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > MAX_HTML_BYTES:
                raise JobFetchError(
                    "This page is too large to process. "
                    "Please paste the job description instead."
                )
            chunks.append(chunk)
    finally:
        response.close()

    return b"".join(chunks).decode(encoding, errors="replace")


def extract_job_description(html, url=None):
    """Pull the main readable content out of a job page's HTML."""
    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            output_format="txt",
        )

        if not text:
            # Some pages need a more eager extraction pass.
            text = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
                output_format="txt",
            )
    except Exception as exc:
        raise JobFetchError(
            "Couldn't read this page as a web page. "
            "Please paste the job description instead."
        ) from exc

    if not text:
        raise JobFetchError(
            "Couldn't find a readable job description on this page. "
            "Many job boards require JavaScript — open the link, copy the "
            "description and paste it instead."
        )

    cleaned = clean_text(text)

    if len(cleaned) < MIN_DESCRIPTION_LENGTH:
        raise JobFetchError(
            "The job description on this page is too short to analyze. "
            "Please paste the full description instead."
        )

    return cleaned


def fetch_job_description(url):
    """Fetch a URL and return the extracted, cleaned job description text."""
    html = fetch_job_page(url)
    return extract_job_description(html, url=url)
