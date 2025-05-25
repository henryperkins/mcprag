#!/usr/bin/env python3
"""
GitHub Webhook Handler for Real-time Azure Indexing
Handles push events, pull requests, and other GitHub events to trigger indexing.
"""

import os
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GitHub Webhook → Azure Search")

class WebhookPayload(BaseModel):
    action: Optional[str] = None
    repository: Dict
    commits: Optional[List[Dict]] = None
    pull_request: Optional[Dict] = None
    before: Optional[str] = None
    after: Optional[str] = None

def verify_github_signature(payload_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode()
    if not webhook_secret:
        return True  # Skip verification if no secret set
    
    expected_signature = hmac.new(
        webhook_secret, payload_body, hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

async def process_push_event(payload: Dict, background_tasks: BackgroundTasks):
    """Process GitHub push event."""
    repository = payload["repository"]
    owner = repository["owner"]["login"]
    repo_name = repository["name"]
    
    # Get changed files from commits
    changed_files = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
    
    # Filter for code files
    code_files = [f for f in changed_files if any(f.endswith(ext) for ext in ['.py', '.js', '.ts'])]
    
    if code_files:
        print(f"🔄 Push event: {len(code_files)} code files changed in {owner}/{repo_name}")
        
        # Schedule background indexing
        background_tasks.add_task(
            index_changed_files_background,
            owner, repo_name, list(code_files)
        )
    
    return {"status": "processing", "files": len(code_files)}

async def process_pull_request_event(payload: Dict, background_tasks: BackgroundTasks):
    """Process GitHub pull request event."""
    action = payload.get("action")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "action": action}
    
    repository = payload["repository"]
    owner = repository["owner"]["login"]
    repo_name = repository["name"]
    pr_number = payload["pull_request"]["number"]
    
    print(f"🔄 PR event: {action} for PR #{pr_number} in {owner}/{repo_name}")
    
    # Schedule background indexing of PR files
    background_tasks.add_task(
        index_pull_request_background,
        owner, repo_name, pr_number
    )
    
    return {"status": "processing", "pr": pr_number, "action": action}

async def index_changed_files_background(owner: str, repo: str, files: List[str]):
    """Background task to index changed files."""
    try:
        from github_azure_integration import GitHubAzureIntegrator
        
        integrator = GitHubAzureIntegrator()
        integrator.index_changed_files_remote(owner, repo, files)
        
        print(f"✅ Successfully indexed {len(files)} files from {owner}/{repo}")
        
    except Exception as e:
        print(f"❌ Error indexing files from {owner}/{repo}: {e}")

async def index_pull_request_background(owner: str, repo: str, pr_number: int):
    """Background task to index pull request files."""
    try:
        from github_azure_integration import GitHubAzureIntegrator
        
        integrator = GitHubAzureIntegrator()
        files = integrator.get_pull_request_files(owner, repo, pr_number)
        integrator.index_changed_files_remote(owner, repo, files)
        
        print(f"✅ Successfully indexed PR #{pr_number} files from {owner}/{repo}")
        
    except Exception as e:
        print(f"❌ Error indexing PR #{pr_number} from {owner}/{repo}: {e}")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "github-webhook-handler"}

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events."""
    
    # Get request body and headers
    payload_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    
    # Verify signature
    if not verify_github_signature(payload_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse payload
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    print(f"📨 Received GitHub {event_type} event")
    
    # Route based on event type
    if event_type == "push":
        return await process_push_event(payload, background_tasks)
    elif event_type == "pull_request":
        return await process_pull_request_event(payload, background_tasks)
    else:
        return {"status": "ignored", "event_type": event_type}

@app.post("/manual/index-repo")
async def manual_index_repository(
    owner: str, 
    repo: str, 
    branch: str = "main",
    background_tasks: BackgroundTasks = None
):
    """Manually trigger repository indexing."""
    print(f"🔄 Manual indexing requested for {owner}/{repo}")
    
    background_tasks.add_task(
        index_repository_background,
        owner, repo, branch
    )
    
    return {"status": "processing", "repository": f"{owner}/{repo}", "branch": branch}

async def index_repository_background(owner: str, repo: str, branch: str):
    """Background task to index entire repository."""
    try:
        from github_azure_integration import GitHubAzureIntegrator
        
        integrator = GitHubAzureIntegrator()
        integrator.index_remote_repository(owner, repo, branch)
        
        print(f"✅ Successfully indexed entire repository {owner}/{repo}")
        
    except Exception as e:
        print(f"❌ Error indexing repository {owner}/{repo}: {e}")

@app.get("/status/repositories")
async def get_indexed_repositories():
    """Get list of indexed repositories from Azure Search."""
    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        
        client = SearchClient(
            endpoint=os.getenv("ACS_ENDPOINT"),
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
        )
        
        # Get unique repository names
        results = client.search(
            search_text="*",
            select=["repo_name"],
            top=1000
        )
        
        repositories = set()
        for result in results:
            repositories.add(result["repo_name"])
        
        return {"repositories": sorted(list(repositories))}
        
    except Exception as e:
        return {"error": str(e), "repositories": []}

if __name__ == "__main__":
    print("🚀 Starting GitHub Webhook Handler")
    print("📋 Supported events: push, pull_request")
    print("🔗 Webhook URL: http://your-domain/webhook/github")
    print("🔧 Manual indexing: POST /manual/index-repo")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("WEBHOOK_PORT", 8080)),
        log_level="info"
    )
