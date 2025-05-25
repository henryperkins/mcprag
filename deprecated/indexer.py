# indexer.py
import os
import hashlib
import json
from pathlib import Path
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-search",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY")),
)


def index_repository(repo_path: str, repo_name: str):
    """Index code files from repository."""
    documents = []
    extensions = {".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"}

    for file_path in Path(repo_path).rglob("*"):
        if file_path.is_file() and file_path.suffix in extensions:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) > 1_000_000:  # Skip huge files
                    continue

                doc_id = hashlib.md5(f"{repo_name}:{file_path}".encode()).hexdigest()

                # Simple function extraction
                functions = []
                if file_path.suffix == ".py":
                    functions = [
                        line.split()[1].split("(")[0]
                        for line in content.splitlines()
                        if line.strip().startswith("def ")
                    ]

                documents.append(
                    {
                        "id": doc_id,
                        "repo_name": repo_name,
                        "file_path": str(file_path),
                        "language": file_path.suffix[1:],
                        "code_content": content[:50000],  # Limit content size
                        "function_name": functions[0] if functions else "",
                        "last_modified": file_path.stat().st_mtime,
                    }
                )

                # Upload in batches
                if len(documents) >= 100:
                    client.upload_documents(documents)
                    print(f"Indexed {len(documents)} files...")
                    documents = []

            except Exception as e:
                print(f"Error with {file_path}: {e}")

    # Upload remaining
    if documents:
        client.upload_documents(documents)

    print(f"✅ Indexed {repo_name}")


if __name__ == "__main__":
    # Index the example repository
    index_repository("./example-repo", "example-project")

    # Add your own repositories here:
    # index_repository("./path/to/your/repo", "your-project-name")
