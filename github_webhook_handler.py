#!/usr/bin/env python3
"""
GitHub Webhook Handler for Real-time Code Indexing
Processes push and pull request events to update Azure Cognitive Search
"""
import os
import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from github_azure_integration import GitHubAzureIntegrator
from dotenv import load_dotenv
import logging
from starlette.requests import Request as StarletteRequest  # used by limiter error handler

load_dotenv()

# Set up logging
logging.basicConfig(
    level=os.getenv("WEBHOOK_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="GitHub Webhook Handler")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Unified rate limit error handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: StarletteRequest, exc: RateLimitExceeded):
    return HTTPException(status_code=429, detail="Rate limit exceeded, try again later")

# Security
security = HTTPBearer()

# Configuration
ADMIN_TOKEN = os.getenv("WEBHOOK_ADMIN_TOKEN")
MAX_WORKERS = int(os.getenv("WEBHOOK_MAX_WORKERS", "5"))

# Validate required environment settings early; fail-closed for critical vars
MISSING_ENV = []
if not os.getenv("GITHUB_WEBHOOK_SECRET"):
    MISSING_ENV.append("GITHUB_WEBHOOK_SECRET")
if not ADMIN_TOKEN:
    MISSING_ENV.append("WEBHOOK_ADMIN_TOKEN")
if MISSING_ENV:
    # Fail closed to avoid running an insecure webhook handler
    missing_str = ", ".join(MISSING_ENV)
    logger.critical(f"Missing required environment variables: {missing_str}")
    raise RuntimeError(f"Critical configuration missing: {missing_str}")

integrator = GitHubAzureIntegrator()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Store repository indexing status
indexing_status = {}


def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify admin token for manual API endpoints."""
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500, detail="Admin token not configured"
        )
    
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401, detail="Invalid authentication token"
        )
    
    return True


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature using constant-time comparison."""
    if not signature or not signature.startswith("sha256="):
        return False
    
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


async def process_push_event(data: Dict):
    """Process push event and index changed files."""
    try:
        repo_name = data["repository"]["full_name"]
        owner, repo = repo_name.split("/")
    except Exception as e:
        logger.exception("Malformed push payload: %s", e)
        return

    # Mark as indexing
    indexing_status[repo_name] = {
        "status": "indexing",
        "started_at": datetime.now().isoformat(),
        "event": "push",
    }
    logger.info("Starting push indexing for %s", repo_name)

    try:
        # Get changed files
        before = data.get("before")
        after = data.get("after")

        if not before or not after:
            raise ValueError("Missing 'before' or 'after' commit SHAs in push payload")

        if before == "0000000000000000000000000000000000000000":
            # Initial commit - index entire repository
            await asyncio.get_event_loop().run_in_executor(
                executor, integrator.index_remote_repository, owner, repo
            )
        else:
            # Get changed files
            changed_files = await asyncio.get_event_loop().run_in_executor(
                executor,
                integrator.get_changed_files_from_push,
                owner,
                repo,
                before,
                after,
            )

            if changed_files:
                logger.info("Indexing %d changed files for %s", len(changed_files), repo_name)
                # Index changed files
                await asyncio.get_event_loop().run_in_executor(
                    executor,
                    integrator.index_changed_files_remote,
                    owner,
                    repo,
                    changed_files,
                )
            else:
                # No-op for non-code changes; update status to completed with zero files
                logger.info("No indexable file changes detected for %s", repo_name)

        # Update status
        indexing_status[repo_name] = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "event": "push",
        }
        logger.info("Completed push indexing for %s", repo_name)

    except Exception as e:
        logger.exception("Push indexing failed for %s: %s", repo_name, e)
        indexing_status[repo_name] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
            "event": "push",
        }


async def process_pull_request_event(data: Dict):
    """Process pull request event and index changed files."""
    try:
        repo_name = data["repository"]["full_name"]
        owner, repo = repo_name.split("/")
        pr_number = data["pull_request"]["number"]
        action = data["action"]
    except Exception as e:
        logger.exception("Malformed pull_request payload: %s", e)
        return

    # Only process opened, synchronize, and reopened events
    if action not in ["opened", "synchronize", "reopened"]:
        logger.debug("Ignoring PR action '%s' for %s", action, repo_name)
        return

    # Mark as indexing
    indexing_status[repo_name] = {
        "status": "indexing",
        "started_at": datetime.now().isoformat(),
        "event": f"pull_request_{action}",
        "pr_number": pr_number,
    }
    logger.info("Starting PR indexing for %s PR #%s (action=%s)", repo_name, pr_number, action)

    try:
        # Get PR files
        pr_files = await asyncio.get_event_loop().run_in_executor(
            executor, integrator.get_pull_request_files, owner, repo, pr_number
        )

        if pr_files:
            logger.info("Indexing %d PR files for %s PR #%s", len(pr_files), repo_name, pr_number)
            # Index PR files
            await asyncio.get_event_loop().run_in_executor(
                executor, integrator.index_changed_files_remote, owner, repo, pr_files
            )
        else:
            # No-op for non-code diffs; still mark completed with zero files
            logger.info("No indexable PR file changes for %s PR #%s", repo_name, pr_number)

        # Update status
        indexing_status[repo_name] = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "event": f"pull_request_{action}",
            "pr_number": pr_number,
        }
        logger.info("Completed PR indexing for %s PR #%s", repo_name, pr_number)

    except Exception as e:
        logger.exception("PR indexing failed for %s PR #%s: %s", repo_name, pr_number, e)
        indexing_status[repo_name] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
            "event": f"pull_request_{action}",
            "pr_number": pr_number,
        }


@app.post("/webhook")
@limiter.limit("10/minute")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events."""
    # Get webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        logger.warning("Webhook request missing X-Hub-Signature-256")
        raise HTTPException(status_code=401, detail="Missing signature")

    # Get payload
    payload = await request.body()

    # Verify signature - require webhook secret to be set
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("GITHUB_WEBHOOK_SECRET is not configured")
        raise HTTPException(
            status_code=500,
            detail="GITHUB_WEBHOOK_SECRET environment variable is required",
        )

    if not verify_webhook_signature(payload, signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event data
    event_type = request.headers.get("X-GitHub-Event")
    data = json.loads(payload)

    # Process events in background
    if event_type == "push":
        background_tasks.add_task(process_push_event, data)
        return {"status": "accepted", "event": "push"}

    elif event_type == "pull_request":
        background_tasks.add_task(process_pull_request_event, data)
        return {"status": "accepted", "event": "pull_request"}

    else:
        return {"status": "ignored", "event": event_type}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "github-webhook-handler",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/status/repositories")
async def get_repository_status():
    """Get indexing status for all repositories."""
    return {"repositories": indexing_status, "total": len(indexing_status)}


@app.get("/status/repository/{owner}/{repo}")
async def get_specific_repository_status(owner: str, repo: str):
    """Get indexing status for a specific repository."""
    repo_name = f"{owner}/{repo}"
    if repo_name in indexing_status:
        return indexing_status[repo_name]
    else:
        raise HTTPException(status_code=404, detail="Repository not found")


@app.post("/manual/index-repo")
@limiter.limit("5/hour")
async def manual_index_repository(
    owner: str, repo: str, background_tasks: BackgroundTasks, ref: str = "main",
    authorized: bool = Depends(verify_admin_token)
):
    """Manually trigger repository indexing."""
    repo_name = f"{owner}/{repo}"

    # Check if already indexing
    if (
        repo_name in indexing_status
        and indexing_status[repo_name]["status"] == "indexing"
    ):
        return {"status": "already_indexing", "repository": repo_name}

    # Mark as indexing
    indexing_status[repo_name] = {
        "status": "indexing",
        "started_at": datetime.now().isoformat(),
        "event": "manual",
        "ref": ref,
    }

    # Index in background
    async def index_task():
        try:
            await asyncio.get_event_loop().run_in_executor(
                executor, integrator.index_remote_repository, owner, repo, ref
            )
            indexing_status[repo_name] = {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "event": "manual",
                "ref": ref,
            }
        except Exception as e:
            indexing_status[repo_name] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat(),
                "event": "manual",
                "ref": ref,
            }

    background_tasks.add_task(index_task)

    return {"status": "accepted", "repository": repo_name, "ref": ref}


@app.post("/manual/index-pr")
@limiter.limit("5/hour")
async def manual_index_pull_request(
    owner: str, repo: str, pr_number: int, background_tasks: BackgroundTasks,
    authorized: bool = Depends(verify_admin_token)
):
    """Manually trigger pull request indexing."""
    repo_name = f"{owner}/{repo}"

    # Mark as indexing
    indexing_status[repo_name] = {
        "status": "indexing",
        "started_at": datetime.now().isoformat(),
        "event": "manual_pr",
        "pr_number": pr_number,
    }

    # Index in background
    async def index_task():
        try:
            pr_files = await asyncio.get_event_loop().run_in_executor(
                executor, integrator.get_pull_request_files, owner, repo, pr_number
            )

            if pr_files:
                await asyncio.get_event_loop().run_in_executor(
                    executor,
                    integrator.index_changed_files_remote,
                    owner,
                    repo,
                    pr_files,
                )

            indexing_status[repo_name] = {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "event": "manual_pr",
                "pr_number": pr_number,
                "files_indexed": len(pr_files),
            }
        except Exception as e:
            indexing_status[repo_name] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat(),
                "event": "manual_pr",
                "pr_number": pr_number,
            }

    background_tasks.add_task(index_task)

    return {"status": "accepted", "repository": repo_name, "pr_number": pr_number}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WEBHOOK_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
