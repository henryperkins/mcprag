"""
Tests for unified pattern registry
"""

import pytest
from enhanced_rag.pattern_registry import get_pattern_registry, PatternType, PatternMatch


class TestPatternRegistry:
    
    def setup_method(self):
        self.registry = get_pattern_registry()
    
    def test_singleton_pattern_recognition(self):
        """Test singleton pattern recognition"""
        code = """
class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    def getInstance(self):
        return self._instance
"""
        
        matches = self.registry.recognize_patterns(code)
        
        # Should find singleton pattern
        singleton_matches = [m for m in matches if m.pattern_name == 'singleton']
        assert len(singleton_matches) > 0
        assert singleton_matches[0].confidence > 0.5
        assert 'singleton' in singleton_matches[0].matched_keywords or 'instance' in singleton_matches[0].matched_keywords
    
    def test_factory_pattern_recognition(self):
        """Test factory pattern recognition"""
        code = """
class AnimalFactory:
    @staticmethod
    def create_animal(animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
"""
        
        matches = self.registry.recognize_patterns(code)
        
        # Should find factory pattern
        factory_matches = [m for m in matches if m.pattern_name == 'factory']
        assert len(factory_matches) > 0
        assert factory_matches[0].confidence > 0.4
    
    def test_error_handling_patterns(self):
        """Test error handling pattern recognition"""
        code = """
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Validation failed: {e}")
    raise
finally:
    cleanup()
"""
        
        matches = self.registry.recognize_patterns(code)
        
        # Should find try_catch pattern
        error_matches = [m for m in matches if m.pattern_name == 'try_catch']
        assert len(error_matches) > 0
        assert error_matches[0].confidence > 0.6
    
    def test_vector_dimension_mismatch_pattern(self):
        """Test vector dimension mismatch pattern"""
        code = """
if len(query_vector) != len(doc_vector):
    raise ValueError(f"Dimension mismatch: query {len(query_vector)} != doc {len(doc_vector)}")
    
if embedding.shape[0] != expected_dim:
    raise IndexError(f"Expected embedding dimension {expected_dim}, got {embedding.shape[0]}")
"""
        
        matches = self.registry.recognize_patterns(code)
        
        # Should find vector dimension mismatch pattern
        vector_matches = [m for m in matches if m.pattern_name == 'vector_dimension_mismatch']
        assert len(vector_matches) > 0
        assert vector_matches[0].confidence > 0.5
    
    def test_api_endpoint_pattern(self):
        """Test API endpoint pattern recognition"""
        code = """
@app.get("/users/{user_id}")
async def get_user(user_id: int, request: Request):
    return await user_service.get_user(user_id)
    
@router.post("/auth/login")
def login(credentials: LoginRequest):
    return authenticate_user(credentials)
"""
        
        matches = self.registry.recognize_patterns(code)
        
        # Should find api_endpoint pattern
        api_matches = [m for m in matches if m.pattern_name == 'api_endpoint']
        assert len(api_matches) > 0
        assert api_matches[0].confidence >= 0.6
    
    def test_framework_detection(self):
        """Test framework-specific pattern detection"""
        code = """
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}
"""
        
        matches = self.registry.recognize_patterns(code)
        
        # Should find FastAPI patterns
        fastapi_matches = [m for m in matches if m.pattern_name == 'fastapi']
        assert len(fastapi_matches) > 0
        assert fastapi_matches[0].confidence >= 0.45
    
    def test_dominant_pattern(self):
        """Test getting dominant pattern"""
        code = """
class Singleton:
    _instance = None
    
    def getInstance():
        return Singleton._instance
"""
        
        dominant = self.registry.get_dominant_pattern(code)
        
        assert dominant is not None
        assert dominant.pattern_name == 'singleton'
        assert dominant.confidence > 0.5
    
    def test_pattern_suggestions(self):
        """Test pattern suggestions based on context"""
        context = {
            'imports': ['from fastapi import FastAPI', 'import asyncio'],
            'functions': ['create_user', 'get_user', 'login'],
            'classes': ['UserService', 'AuthController']
        }
        
        suggestions = self.registry.suggest_patterns(context)
        
        assert len(suggestions) > 0
        
        # Should suggest FastAPI patterns
        fastapi_suggestions = [s for s in suggestions if s.pattern_name == 'fastapi']
        assert len(fastapi_suggestions) > 0
        
        # Should suggest MVC patterns (controller detected)
        mvc_suggestions = [s for s in suggestions if s.pattern_name == 'mvc']
        assert len(mvc_suggestions) > 0
    
    def test_pattern_info_retrieval(self):
        """Test retrieving pattern information"""
        info = self.registry.get_pattern_info(PatternType.DESIGN_PATTERN, 'singleton')
        
        assert info is not None
        assert 'keywords' in info
        assert 'patterns' in info
        assert 'description' in info
        assert 'singleton' in info['keywords']
    
    def test_patterns_by_type(self):
        """Test getting patterns by type"""
        design_patterns = self.registry.get_patterns_by_type(PatternType.DESIGN_PATTERN)
        
        assert len(design_patterns) > 0
        assert 'singleton' in design_patterns
        assert 'factory' in design_patterns
        assert 'observer' in design_patterns
        
        error_patterns = self.registry.get_patterns_by_type(PatternType.ERROR_HANDLING)
        assert len(error_patterns) > 0
        assert 'try_catch' in error_patterns
        assert 'vector_dimension_mismatch' in error_patterns
    
    def test_confidence_calculation(self):
        """Test confidence calculation accuracy"""
        # High confidence case - multiple matches
        high_confidence_code = """
class SingletonLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def getInstance(cls):
        return cls._instance
"""
        
        matches = self.registry.recognize_patterns(high_confidence_code)
        singleton_match = [m for m in matches if m.pattern_name == 'singleton'][0]
        assert singleton_match.confidence > 0.7
        
        # Low confidence case - partial match
        low_confidence_code = """
def get_database_instance():
    return db_connection
"""
        
        matches = self.registry.recognize_patterns(low_confidence_code)
        singleton_matches = [m for m in matches if m.pattern_name == 'singleton']
        if singleton_matches:
            assert singleton_matches[0].confidence < 0.5
    
    def test_no_false_positives(self):
        """Test that unrelated code doesn't trigger false positives"""
        unrelated_code = """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""
        
        matches = self.registry.recognize_patterns(unrelated_code)
        
        # Should have very low confidence matches if any
        high_confidence_matches = [m for m in matches if m.confidence > 0.6]
        assert len(high_confidence_matches) == 0


if __name__ == "__main__":
    pytest.main([__file__])
