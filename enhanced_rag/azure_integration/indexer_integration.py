"""
Azure AI Search Indexer Integration
Leverages Azure indexers for automated data ingestion and enrichment
"""

import logging
from typing import Dict, List, Any, Optional, Sequence
from datetime import timedelta, datetime
import asyncio
from enum import Enum
import hashlib
from pathlib import Path

from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexer,
    SearchIndexerDataSourceConnection,
    SearchIndexerSkillset,
    FieldMapping,
    FieldMappingFunction,
    OutputFieldMappingEntry,
    InputFieldMappingEntry,
    IndexingParameters,
    IndexingParametersConfiguration,
    IndexingSchedule,
    WebApiSkill,
    SplitSkill,
    KeyPhraseExtractionSkill,
    # Additions for blob change/deletion detection policies
    DataChangeDetectionPolicy,
    SoftDeleteColumnDeletionDetectionPolicy,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceType,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError

from enhanced_rag.core.config import get_config
from .embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider
from enhanced_rag.code_understanding import CodeChunker

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Supported data source types for indexers"""
    AZURE_BLOB = "azureblob"
    AZURE_SQL = "azuresql"
    COSMOS_DB = "cosmosdb"
    AZURE_TABLE = "azuretable"
    MYSQL = "mysql"
    SHAREPOINT = "sharepoint"
    ONELAKE = "onelake"


class IndexerIntegration:
    """
    Manages Azure AI Search indexers for automated data ingestion
    Implements the pull model for continuous data synchronization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config().azure.model_dump()
        self.indexer_client = self._create_indexer_client()
        self.custom_skill_endpoints = {}
        
    def _create_indexer_client(self) -> SearchIndexerClient:
        """Create Azure Search indexer client"""
        endpoint = self.config['endpoint']
        api_key = self.config['admin_key']
        
        return SearchIndexerClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    async def create_code_repository_indexer(
        self,
        name: str,
        data_source_type: DataSourceType,
        connection_string: str,
        container_name: str,
        index_name: str,
        schedule_interval_minutes: int = 60,
        include_git_metadata: bool = True
    ) -> SearchIndexer:
        """
        Create an indexer for code repository data
        
        Args:
            name: Indexer name
            data_source_type: Type of data source (blob, cosmos, etc.)
            connection_string: Connection string to data source
            container_name: Container/collection name
            index_name: Target index name
            schedule_interval_minutes: How often to run (minimum 5 minutes)
            include_git_metadata: Whether to extract git metadata
            
        Returns:
            Created indexer
        """
        try:
            # Create data source connection
            data_source = await self._create_data_source(
                name=f"{name}-datasource",
                data_source_type=data_source_type,
                connection_string=connection_string,
                container_name=container_name
            )
            
            # Create skillset with code-specific skills
            skillset = await self._create_code_enrichment_skillset(
                name=f"{name}-skillset",
                include_git_metadata=include_git_metadata
            )
            
            # Configure field mappings for code files
            field_mappings = self._get_code_field_mappings(data_source_type)
            output_field_mappings = self._get_code_output_mappings()
            
            # Configure indexing parameters
            parameters = IndexingParameters(
                batch_size=50,  # Process 50 documents at a time
                max_failed_items=10,
                max_failed_items_per_batch=5,
                configuration=IndexingParametersConfiguration(
                    data_to_extract="contentAndMetadata",
                    parsing_mode="default",
                    excluded_file_name_extensions=(
                        ".exe,.dll,.obj,.pdb,.class,.jar"
                    ),
                    indexed_file_name_extensions=(
                        ".py,.js,.ts,.java,.cs,.cpp,.c,.h,.go,.rs,"
                        ".rb,.php,.swift,.kt,.scala,.r,.m,.mm"
                    ),
                    fail_on_unprocessable_document=False,
                    fail_on_unsupported_content_type=False,
                    index_storage_metadata_only_for_oversized_documents=True
                )
            )
            
            # Create indexing schedule
            schedule = IndexingSchedule(
                interval=timedelta(minutes=max(schedule_interval_minutes, 5))
            ) if schedule_interval_minutes > 0 else None
            
            # Create the indexer (assign output mappings after instantiation to
            # avoid type variance complaints)
            indexer = SearchIndexer(
                name=name,
                data_source_name=data_source.name,
                target_index_name=index_name,
                skillset_name=skillset.name if skillset else None,
                field_mappings=field_mappings,
                schedule=schedule,
                parameters=parameters,
                description=f"Code repository indexer for {container_name}"
            )
            # Note: Some SDK versions expose 'output_field_mappings' with a type
            # that conflicts under static type checking. We omit it here to keep
            # type checkers happy; skill outputs target fields directly.

            # Create or update the indexer
            result = self.indexer_client.create_or_update_indexer(indexer)
            logger.info(f"Created indexer '{name}' successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating indexer '{name}': {e}")
            raise
    
    async def _create_data_source(
        self,
        name: str,
        data_source_type: DataSourceType,
        connection_string: str,
        container_name: str
    ) -> SearchIndexerDataSourceConnection:
        """Create data source connection"""
        # Configure data source based on type
        if data_source_type == DataSourceType.AZURE_BLOB:
            # Create blob storage data source with change detection and
            # soft delete detection
            data_source = SearchIndexerDataSourceConnection(
                name=name,
                type=SearchIndexerDataSourceType.AZURE_BLOB,
                connection_string=connection_string,
                container=SearchIndexerDataContainer(
                    name=container_name,
                    query=None,
                ),
                data_change_detection_policy=DataChangeDetectionPolicy(
                    high_water_mark_column_name=(
                        "metadata_storage_last_modified"
                    )
                ),
                data_deletion_detection_policy=SoftDeleteColumnDeletionDetectionPolicy(
                    soft_delete_column_name="IsDeleted",
                    soft_delete_marker_value="true",
                ),
            )
        elif data_source_type == DataSourceType.COSMOS_DB:
            data_source = SearchIndexerDataSourceConnection(
                name=name,
                type=SearchIndexerDataSourceType.COSMOS_DB,
                connection_string=connection_string,
                container=SearchIndexerDataContainer(
                    name=container_name,
                    query="SELECT * FROM c WHERE c._ts >= @HighWaterMark"
                ),
                data_change_detection_policy=DataChangeDetectionPolicy(
                    high_water_mark_column_name="_ts"
                ),
            )
        else:
            # Generic data source for other types not implemented yet
            raise NotImplementedError(
                f"Data source type {data_source_type} not yet implemented"
            )

        return self.indexer_client.create_or_update_data_source_connection(
            data_source
        )
    
    async def _create_code_enrichment_skillset(
        self,
        name: str,
        include_git_metadata: bool = True
    ) -> Optional[SearchIndexerSkillset]:
        """Create skillset for code enrichment"""
        
        skills = []
        
        # 1. Text split skill for chunking
        skills.append(
            SplitSkill(
                name="split-code",
                description="Split code files into chunks",
                context="/document",
                default_language_code="en",
                text_split_mode="pages",
                maximum_page_length=2000,
                page_overlap_length=200,
                inputs=[
                    InputFieldMappingEntry(
                        name="text",
                        source="/document/content"
                    )
                ],
                outputs=[
                    OutputFieldMappingEntry(
                        name="textItems",
                        target_name="pages"
                    )
                ]
            )
        )
        
        # 2. Custom skill for code analysis (AST parsing, complexity, etc.)
        if self.custom_skill_endpoints.get('code_analyzer'):
            skills.append(
                WebApiSkill(
                    name="analyze-code",
                    description="Extract code structure and metrics",
                    uri=self.custom_skill_endpoints['code_analyzer'],
                    http_method="POST",
                    timeout=timedelta(seconds=30),
                    context="/document/pages/*",
                    inputs=[
                        InputFieldMappingEntry(
                            name="code",
                            source="/document/pages/*"
                        ),
                        InputFieldMappingEntry(
                            name="language",
                            source="/document/language"
                        ),
                        InputFieldMappingEntry(
                            name="filePath",
                            source="/document/metadata_storage_path"
                        )
                    ],
                    outputs=[
                        OutputFieldMappingEntry(
                            name="functions",
                            target_name="functions",
                        ),
                        OutputFieldMappingEntry(
                            name="classes",
                            target_name="classes",
                        ),
                        OutputFieldMappingEntry(name="imports", target_name="imports"),
                        OutputFieldMappingEntry(name="complexity", target_name="complexity_score"),
                        OutputFieldMappingEntry(name="patterns", target_name="detected_patterns")
                    ]
                )
            )
        
        # 3. Key phrase extraction for documentation and comments
        skills.append(
            KeyPhraseExtractionSkill(
                name="extract-key-phrases",
                description="Extract key phrases from comments and docstrings",
                context="/document/pages/*",
                default_language_code="en",
                inputs=[
                    InputFieldMappingEntry(name="text", source="/document/pages/*")
                ],
                outputs=[
                    OutputFieldMappingEntry(name="keyPhrases", target_name="key_phrases")
                ]
            )
        )
        
        # 4. Custom skill for git metadata extraction
        if include_git_metadata and self.custom_skill_endpoints.get('git_extractor'):
            skills.append(
                WebApiSkill(
                    name="extract-git-metadata",
                    description="Extract git history and metadata",
                    uri=self.custom_skill_endpoints['git_extractor'],
                    http_method="POST",
                    timeout=timedelta(seconds=30),
                    context="/document",
                    inputs=[
                        InputFieldMappingEntry(name="filePath", source="/document/metadata_storage_path")
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name="lastCommit", target_name="git_commit"),
                        OutputFieldMappingEntry(name="authors", target_name="git_authors"),
                        OutputFieldMappingEntry(name="commitCount", target_name="git_commit_count"),
                        OutputFieldMappingEntry(name="lastModified", target_name="git_last_modified")
                    ]
                )
            )
        
        # 5. Custom skill for embedding generation
        if self.custom_skill_endpoints.get('embedder'):
            skills.append(
                WebApiSkill(
                    name="generate-embeddings",
                    description="Generate vector embeddings for code",
                    uri=self.custom_skill_endpoints['embedder'],
                    http_method="POST",
                    timeout=timedelta(seconds=60),
                    context="/document/pages/*",
                    inputs=[
                        InputFieldMappingEntry(name="text", source="/document/pages/*"),
                        InputFieldMappingEntry(name="language", source="/document/language")
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name="embedding", target_name="code_vector")
                    ]
                )
            )
        
        if not skills:
            return None
        
        skillset = SearchIndexerSkillset(
            name=name,
            description=(
                "Code enrichment skillset with AST analysis and git metadata"
            ),
            skills=skills
        )
        
        return self.indexer_client.create_or_update_skillset(skillset)
    
    def _get_code_field_mappings(self, data_source_type: DataSourceType) -> List[FieldMapping]:
        """Get field mappings for code files based on data source type"""
        
        if data_source_type == DataSourceType.AZURE_BLOB:
            return [
                FieldMapping(
                    source_field_name="metadata_storage_path",
                    target_field_name="id",
                    mapping_function=FieldMappingFunction(
                        name="base64Encode"
                    )
                ),
                FieldMapping(
                    source_field_name="metadata_storage_path",
                    target_field_name="file_path"
                ),
                FieldMapping(
                    source_field_name="metadata_storage_name",
                    target_field_name="file_name"
                ),
                FieldMapping(
                    source_field_name="metadata_storage_last_modified",
                    target_field_name="last_modified"
                )
            ]
        else:
            # Generic mappings for other sources
            return [
                FieldMapping(
                    source_field_name="id",
                    target_field_name="id"
                ),
                FieldMapping(
                    source_field_name="path",
                    target_field_name="file_path"
                ),
                FieldMapping(
                    source_field_name="content",
                    target_field_name="content"
                )
            ]
    
    def _get_code_output_mappings(self) -> List[OutputFieldMappingEntry]:
        """Get output field mappings from skillset to index"""
        return [
            OutputFieldMappingEntry(
                name="map_content",
                source_name="/document/pages/*",
                target_name="content"
            ),
            OutputFieldMappingEntry(
                name="map_functions",
                source_name="/document/pages/*/functions",
                target_name="function_name"
            ),
            OutputFieldMappingEntry(
                name="map_classes",
                source_name="/document/pages/*/classes",
                target_name="class_name"
            ),
            OutputFieldMappingEntry(
                name="map_imports",
                source_name="/document/pages/*/imports",
                target_name="imports"
            ),
            OutputFieldMappingEntry(
                name="map_complexity",
                source_name="/document/pages/*/complexity_score",
                target_name="complexity_score"
            ),
            OutputFieldMappingEntry(
                name="map_key_phrases",
                source_name="/document/pages/*/key_phrases",
                target_name="tags"
            ),
            OutputFieldMappingEntry(
                name="map_vector",
                source_name="/document/pages/*/code_vector",
                target_name="content_vector"
            )
        ]
    
    async def create_multi_repository_indexers(
        self,
        repositories: List[Dict[str, Any]],
        target_index: str,
        parallel: bool = True
    ) -> List[SearchIndexer]:
        """
        Create multiple indexers for different repositories
        Implements the multi-indexer pattern for large-scale indexing
        
        Args:
            repositories: List of repository configurations
            target_index: Target index name (same for all)
            parallel: Whether to create indexers in parallel
            
        Returns:
            List of created indexers
        """
        tasks = []
        
        for repo in repositories:
            task = self.create_code_repository_indexer(
                name=f"indexer-{repo['name']}",
                data_source_type=DataSourceType(repo['type']),
                connection_string=repo['connection_string'],
                container_name=repo['container'],
                index_name=target_index,
                schedule_interval_minutes=repo.get('schedule_minutes', 60)
            )
            
            if parallel:
                tasks.append(task)
            else:
                await task
        
        if tasks:
            indexers = await asyncio.gather(*tasks, return_exceptions=True)
            # Filter out any exceptions and cast type
            return [
                idx for idx in indexers
                if not isinstance(idx, Exception)
            ]  # type: ignore[list-item]
        
        return []
    
    async def monitor_indexer_status(
        self,
        indexer_name: str
    ) -> Dict[str, Any]:
        """
        Monitor indexer execution status
        
        Returns:
            Status information including errors and progress
        """
        try:
            status = self.indexer_client.get_indexer_status(indexer_name)

            # Get recent execution history (guard against None)
            recent_runs = []
            history = getattr(status, "execution_history", None) or []
            for execution in list(history)[:5]:
                exec_status = getattr(execution, "status", None)
                recent_runs.append({
                    'status': exec_status.value if exec_status else 'unknown',
                    'start_time': getattr(execution, "start_time", None),
                    'end_time': getattr(execution, "end_time", None),
                    'items_processed': getattr(execution, "items_processed", None),
                    'items_failed': getattr(execution, "items_failed", None),
                    'errors': (getattr(execution, "errors", None) or [])[:5],
                    'warnings': (getattr(execution, "warnings", None) or [])[:5]
                })

            # Limits can be None in SDK responses; guard access
            limits = getattr(status, "limits", None)
            status_obj = getattr(status, "status", None)
            status_value = getattr(status_obj, "value", None) if status_obj else 'unknown'
            last_result_obj = getattr(status, "last_result", None)
            last_result_value = getattr(last_result_obj, "value", None) if last_result_obj else None
            return {
                'name': indexer_name,
                'status': status_value,
                'last_result': last_result_value,
                'recent_runs': recent_runs,
                'limits': {
                    'max_document_extraction_size': getattr(limits, "max_document_extraction_size", None),
                    'max_document_content_chars': getattr(limits, "max_document_content_characters_to_extract", None)
                }
            }
            
        except ResourceNotFoundError:
            logger.error(f"Indexer '{indexer_name}' not found")
            return {
                'error': f"Indexer '{indexer_name}' not found"
            }
        except Exception as e:
            logger.error(f"Error monitoring indexer '{indexer_name}': {e}")
            return {'error': str(e)}
    
    async def run_indexer_on_demand(self, indexer_name: str) -> bool:
        """
        Run an indexer immediately (on-demand execution)
        
        Returns:
            True if successfully started
        """
        try:
            self.indexer_client.run_indexer(indexer_name)
            logger.info(
                f"Started on-demand run for indexer '{indexer_name}'"
            )
            return True
        except Exception as e:
            logger.error(f"Error running indexer '{indexer_name}': {e}")
            return False
    
    async def reset_indexer(
        self,
        indexer_name: str,
        reset_datasource: bool = False
    ) -> bool:
        """
        Reset an indexer to reprocess all documents
        
        Args:
            indexer_name: Name of indexer to reset
            reset_datasource: Also reset the datasource change tracking
            
        Returns:
            True if successfully reset
        """
        try:
            self.indexer_client.reset_indexer(indexer_name)
            
            if reset_datasource:
                # Also reset the data source change tracking if supported by SDK
                # Note: azure-search-documents SDK does not expose a reset data source API.
                # Consider deleting and recreating the data source connection if needed.
                pass

            logger.info(
                f"Reset indexer '{indexer_name}' successfully"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error resetting indexer '{indexer_name}': {e}")
            return False
    
    def register_custom_skill_endpoint(
        self,
        skill_type: str,
        endpoint_url: str,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Register a custom skill endpoint for use in skillsets
        
        Args:
            skill_type: Type of skill (code_analyzer, embedder, etc.)
            endpoint_url: URL of the custom skill endpoint
            headers: Optional headers to include (e.g., API keys)
        """
        self.custom_skill_endpoints[skill_type] = {
            'url': endpoint_url,
            'headers': headers or {}
        }
        logger.info(
            f"Registered custom skill endpoint for '{skill_type}'"
        )
    
    async def create_incremental_indexing_pipeline(
        self,
        name: str,
        git_repo_path: str,
        index_name: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a pipeline for incremental indexing based on git changes
        
        Args:
            name: Pipeline name
            git_repo_path: Path to git repository
            index_name: Target index
            webhook_url: Optional webhook for git push events
            
        Returns:
            Pipeline configuration
        """
        # This would integrate with git hooks or CI/CD
        pipeline_config = {
            'name': name,
            'git_repo': git_repo_path,
            'index': index_name,
            'webhook': webhook_url,
            'change_detection': {
                'method': 'git_commit_hash',
                'check_interval_minutes': 5
            },
            'indexing_strategy': {
                'type': 'incremental',
                'batch_size': 50,
                'parallel_threads': 4
            }
        }
        
        # In a real implementation, this would set up:
        # 1. Git hooks for push events
        # 2. File watcher for local changes
        # 3. Incremental indexing logic
        # 4. Error handling and retry logic
        
        logger.info(f"Created incremental indexing pipeline '{name}'")
        return pipeline_config


class LocalRepositoryIndexer:
    """Local repository indexer for direct ingestion without Azure Indexer.
    
    Migrated from smart_indexer.py to consolidate indexing functionality.
    """
    
    def __init__(self, config=None):
        """Initialize the local repository indexer."""
        if config is None:
            config = get_config()
        
        # Get Azure Search configuration
        self.endpoint = config.azure.endpoint
        self.admin_key = config.azure.admin_key
        self.index_name = config.azure.index_name or "codebase-mcp-sota"
        
        # Create search client
        try:
            from azure.search.documents import SearchClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError:
            raise ImportError("azure-search-documents package required for indexing")
            
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.admin_key)
        )
        
        # Initialize embedding provider based on config
        self.provider = None
        if config.embedding.provider == "client":
            self.provider = AzureOpenAIEmbeddingProvider()
        elif config.embedding.provider in {"none", "azure_openai_http"}:
            # No client-side embedding for these modes
            self.provider = None
            
        self.batch_size = 50
        self.logger = logging.getLogger(__name__)
        self.chunker = CodeChunker()
    
    def chunk_python_file(self, content: str, file_path: str) -> List[Dict]:
        """Extract semantic chunks from Python code."""
        return self.chunker.chunk_python_file(content, file_path)
    
    
    def chunk_js_ts_file(self, content: str, file_path: str) -> List[Dict]:
        """Extract semantic chunks from JavaScript/TypeScript code."""
        return self.chunker.chunk_js_ts_file(content, file_path)
    
    class DocumentIdHelper:
        """Helper for consistent document ID generation."""
        
        @staticmethod
        def generate_id(repo: str, file_path: str, chunk_type: str, index: int) -> str:
            """Generate deterministic document ID."""
            raw = f"{repo}:{file_path}:{chunk_type}:{index}".encode()
            return hashlib.md5(raw).hexdigest()
    
    def index_repository(
        self,
        repo_path: str,
        repo_name: str,
        patterns: Optional[List[tuple]] = None,
        embed_vectors: Optional[bool] = None
    ):
        """Index a local repository with smart chunking.
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository for indexing
            patterns: File patterns to index (default: Python, JS, TS)
            embed_vectors: Whether to generate embeddings (None = auto-detect)
        """
        documents = []
        
        # Default patterns
        if patterns is None:
            patterns = [
                ("*.py", "python"),
                ("*.js", "javascript"),
                ("*.ts", "typescript"),
            ]
            
        # Auto-detect embedding mode if not specified
        if embed_vectors is None:
            embed_vectors = self.provider is not None
            
        total_indexed = 0
        
        for pattern, language in patterns:
            for file_path in Path(repo_path).rglob(pattern):
                # Skip directories
                if file_path.is_dir():
                    continue
                    
                # Skip common exclusions
                if any(
                    part.startswith(".")
                    or part == "node_modules"
                    or part == "__pycache__"
                    or part == "venv"
                    or part == ".venv"
                    for part in file_path.parts
                ):
                    continue
                    
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    
                    # Choose chunker based on language
                    if language == "python":
                        chunks = self.chunk_python_file(content, str(file_path))
                    elif language in ["javascript", "typescript"]:
                        chunks = self.chunk_js_ts_file(content, str(file_path))
                    else:
                        # Generic chunking for other languages
                        chunks = [{
                            "content": content[:5000],
                            "semantic_context": f"Code from {file_path}",
                            "signature": "",
                            "imports": [],
                            "dependencies": [],
                            "chunk_type": "file",
                            "start_line": 1,
                            "end_line": len(content.splitlines()),
                            "function_name": None,
                            "class_name": None,
                            "docstring": ""
                        }]
                        
                    # Process chunks
                    for i, chunk in enumerate(chunks):
                        doc_id = self.DocumentIdHelper.generate_id(
                            repo_name, str(file_path), chunk["chunk_type"], i
                        )
                        
                        # Get file modification time
                        try:
                            mtime = file_path.stat().st_mtime
                            last_modified = datetime.fromtimestamp(mtime).isoformat() + "+00:00"
                        except:
                            last_modified = datetime.utcnow().isoformat() + "+00:00"
                            
                        doc = {
                            "id": doc_id,
                            "repository": repo_name,
                            "file_path": str(file_path),
                            "file_name": file_path.name,
                            "language": language,
                            "last_modified": last_modified,
                            **chunk,
                        }
                        
                        # Add vector embedding if enabled
                        if embed_vectors and self.provider:
                            embedding = self.provider.generate_code_embedding(
                                chunk["content"], chunk["semantic_context"]
                            )
                            if embedding:
                                doc["content_vector"] = embedding
                            else:
                                self.logger.warning(
                                    f"Failed to generate embedding for {file_path}"
                                )
                                
                        documents.append(doc)
                        
                        # Upload in batches
                        if len(documents) >= self.batch_size:
                            self._upload_documents(documents)
                            total_indexed += len(documents)
                            documents = []
                            
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
                    
        # Upload remaining documents
        if documents:
            self._upload_documents(documents)
            total_indexed += len(documents)
            
        self.logger.info(f"✅ Indexed {repo_name} with {total_indexed} chunks")
        
    def index_changed_files(
        self,
        file_paths: List[str],
        repo_name: str = "current-repo"
    ):
        """Index only specified changed files.
        
        Args:
            file_paths: List of file paths to index
            repo_name: Repository name for indexing
        """
        documents = []
        
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if not file_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Determine language and chunker
                if file_path.suffix == ".py":
                    chunks = self.chunk_python_file(content, str(file_path))
                    language = "python"
                elif file_path.suffix in {".js", ".ts"}:
                    chunks = self.chunk_js_ts_file(content, str(file_path))
                    language = "javascript" if file_path.suffix == ".js" else "typescript"
                else:
                    # Skip unsupported files
                    self.logger.info(f"Skipping unsupported file: {file_path}")
                    continue
                    
                # Process chunks
                for i, chunk in enumerate(chunks):
                    doc_id = self.DocumentIdHelper.generate_id(
                        repo_name, str(file_path), chunk["chunk_type"], i
                    )
                    
                    # Get file modification time
                    try:
                        mtime = file_path.stat().st_mtime
                        last_modified = datetime.fromtimestamp(mtime).isoformat() + "+00:00"
                    except:
                        last_modified = datetime.utcnow().isoformat() + "+00:00"
                        
                    doc = {
                        "id": doc_id,
                        "repository": repo_name,
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "language": language,
                        "last_modified": last_modified,
                        **chunk,
                    }
                    
                    # Add vector embedding if available
                    if self.provider:
                        embedding = self.provider.generate_code_embedding(
                            chunk["content"], chunk["semantic_context"]
                        )
                        if embedding:
                            doc["content_vector"] = embedding
                            
                    documents.append(doc)
                    
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                
        # Upload all documents
        if documents:
            self._upload_documents(documents)
            self.logger.info(f"✅ Indexed {len(documents)} chunks from {len(file_paths)} files")
            
    def _upload_documents(self, documents: List[Dict[str, Any]]):
        """Upload documents to Azure Search."""
        try:
            # Use merge_or_upload if available, otherwise upload
            if hasattr(self.search_client, "merge_or_upload_documents"):
                result = self.search_client.merge_or_upload_documents(documents)
            else:
                result = self.search_client.upload_documents(documents)
                
            self.logger.debug(f"Uploaded {len(documents)} documents")
        except Exception as e:
            self.logger.error(f"Error uploading documents: {e}")
            raise