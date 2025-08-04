"""
GitHub API Client
Thin wrapper around GitHub REST API with retry logic and authentication
"""

import os
import time
import base64
import logging
from typing import List, Dict, Optional, Any
try:
    import requests
    from requests.structures import CaseInsensitiveDict
except ImportError:
    raise ImportError("requests package required for GitHub API access. "
                      "Install with: pip install requests")
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Default network timeout (seconds) for outbound HTTP requests
DEFAULT_HTTP_TIMEOUT = 10


class GitHubClient:
    """GitHub API client with retry logic and authentication support."""

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token (optional, uses GITHUB_TOKEN env var if not provided)
        """
        # Check for network disabled environment
        if os.getenv("CODEX_SANDBOX_NETWORK_DISABLED") == "1":
            logger.warning("Network is disabled (CODEX_SANDBOX_NETWORK_DISABLED=1). "
                          "GitHub API calls will be stubbed.")
            self.network_disabled = True
        else:
            self.network_disabled = False

        self.github_token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}

        # Only add Authorization header if token is present
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        else:
            logger.warning("GITHUB_TOKEN is not set; GitHub API rate limits will be very low.")

    def _get_with_retry(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        *,
        max_retries: int = 3,
        backoff: float = 1.0,
    ) -> requests.Response:
        """Simple exponential-backoff wrapper around requests.get.

        Respects GitHub's primary rate-limit headers. Retries 3× by default
        on 429/5xx responses.

        Args:
            url: URL to fetch
            params: Query parameters
            max_retries: Maximum number of retry attempts
            backoff: Initial backoff delay in seconds

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On final failure
        """
        # Return stub response if network is disabled
        if self.network_disabled:
            logger.info(f"Network disabled: stubbing GET request to {url}")
            # Create a minimal stub response
            stub_response = requests.Response()
            stub_response.status_code = 200
            stub_response._content = b'{"message": "Network disabled - returning stub data"}'
            stub_response.headers = CaseInsensitiveDict({"content-type": "application/json"})
            return stub_response

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=DEFAULT_HTTP_TIMEOUT,
                )
            except requests.exceptions.Timeout as e:
                last_error = e
                # Treat timeout similar to a retryable condition
                if attempt < max_retries:
                    wait = backoff * (2 ** (attempt - 1))
                    logger.warning(f"Request timeout, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                # Re-raise on final attempt to surface the error
                raise
            except requests.exceptions.RequestException as e:
                last_error = e
                # Connection errors and other request issues: retry with backoff when possible
                if attempt < max_retries:
                    wait = backoff * (2 ** (attempt - 1))
                    logger.warning(f"Request error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise

            if resp.status_code < 400:
                return resp

            # On 429 or 5xx we back-off and retry
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < max_retries:
                wait = backoff * (2 ** (attempt - 1))
                logger.warning(f"HTTP {resp.status_code}, retrying in {wait}s...")
                time.sleep(wait)
                continue

            # Give up – propagate error details
            resp.raise_for_status()

        # This should be unreachable, but ensure we always raise if we get here
        raise requests.exceptions.RequestException(
            f"Failed to get response after {max_retries} attempts. Last error: {last_error}"
        )

    def list_repository_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main"
    ) -> List[Dict[str, Any]]:
        """List contents of a repository directory.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository (empty for root)
            ref: Git ref (branch, tag, or commit SHA)

        Returns:
            List of content items
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}

        response = self._get_with_retry(url, params=params)
        return response.json()

    def get_file_content_base64(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file content as base64-encoded data.

        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to file
            ref: Git ref (branch, tag, or commit SHA)

        Returns:
            File metadata including base64-encoded content
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        params = {"ref": ref}

        response = self._get_with_retry(url, params=params)
        return response.json()

    def get_file_content(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: str = "main"
    ) -> str:
        """Get decoded file content.

        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to file
            ref: Git ref (branch, tag, or commit SHA)

        Returns:
            Decoded file content as string
        """
        file_data = self.get_file_content_base64(owner, repo, file_path, ref)
        # GitHub API returns content as base64
        content = base64.b64decode(file_data["content"]).decode("utf-8")
        return content

    def compare_commits(
        self,
        owner: str,
        repo: str,
        before_sha: str,
        after_sha: str
    ) -> List[str]:
        """Compare two commits and get list of changed files.

        Args:
            owner: Repository owner
            repo: Repository name
            before_sha: Base commit SHA
            after_sha: Head commit SHA

        Returns:
            List of changed file paths
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/compare/{before_sha}...{after_sha}"
        response = self._get_with_retry(url)

        compare_data = response.json()
        changed_files = []

        for file in compare_data.get("files", []):
            # Only include non-removed files
            if file["status"] != "removed":
                changed_files.append(file["filename"])

        return changed_files

    def list_pull_request_files(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[str]:
        """Get list of files changed in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of changed file paths
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = self._get_with_retry(url)

        files = []
        for file in response.json():
            # Only include non-removed files
            if file["status"] != "removed":
                files.append(file["filename"])

        return files

    def get_repository_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main",
        extensions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Recursively get all files from a GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Starting path (empty for root)
            ref: Git ref (branch, tag, or commit SHA)
            extensions: File extensions to include (e.g., [".py", ".js"])

        Returns:
            List of file metadata
        """
        if extensions is None:
            extensions = [".py", ".js", ".ts"]

        files = []
        items = self.list_repository_contents(owner, repo, path, ref)

        for item in items:
            if item["type"] == "file":
                # Check if it's a file we want to include
                if any(item["name"].endswith(ext) for ext in extensions):
                    files.append(item)
            elif item["type"] == "dir":
                # Recursively get files from subdirectories
                subfiles = self.get_repository_files(
                    owner, repo, item["path"], ref, extensions
                )
                files.extend(subfiles)

        return files
