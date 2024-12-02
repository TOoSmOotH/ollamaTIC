"""
API endpoints for viewing and analyzing learned patterns.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
from app.learning import LearningSystem
from app.storage import Storage
from app.language_patterns import LanguagePatternAnalyzer

router = APIRouter()
storage = Storage()
analyzer = LanguagePatternAnalyzer()

class LanguageStats(BaseModel):
    """Statistics for a programming language"""
    total_interactions: int
    success_rate: float
    common_patterns: Dict[str, int]
    best_practices: List[str]
    common_errors: Dict[str, str]

class PatternAnalysis(BaseModel):
    """Analysis of learned patterns"""
    language: str
    imports: List[str]
    functions: List[str]
    patterns: Dict[str, List[str]]
    success_rate: float

class CodeAnalysisRequest(BaseModel):
    """Request body for code analysis"""
    code: str

@router.get("/languages")
async def get_supported_languages() -> List[str]:
    """Get list of supported programming languages."""
    return list(analyzer.configs.keys())

@router.get("/language/{language}")
async def get_language_patterns(language: str) -> LanguageStats:
    """Get learned patterns and statistics for a specific language."""
    if language not in analyzer.configs:
        raise HTTPException(status_code=404, detail=f"Language {language} not supported")
    
    # Get metrics from storage
    metrics = storage.get_language_metrics(language)
    success_rate = storage.get_language_success_rate(language)
    
    # Get patterns from analyzer
    common_patterns = analyzer.get_common_patterns(language)
    best_practices = analyzer.get_language_best_practices(language)
    
    # Load language patterns
    patterns = storage.load_language_patterns()
    language_pattern = patterns.get(language, {})
    
    return LanguageStats(
        total_interactions=len(storage.get_recent_interactions()),
        success_rate=success_rate,
        common_patterns={
            name: metrics.get("patterns", {}).get(name, 0)
            for name in common_patterns.keys()
        },
        best_practices=best_practices,
        common_errors=language_pattern.get("error_patterns", {})
    )

@router.post("/analyze/{language}")
async def analyze_code(language: str, request: CodeAnalysisRequest) -> PatternAnalysis:
    """Analyze code patterns for a specific language."""
    if language not in analyzer.configs:
        raise HTTPException(status_code=404, detail=f"Language {language} not supported")
    
    # Analyze the code
    analysis = analyzer.analyze_code(request.code, language)
    
    # Get success rate
    success_rate = storage.get_language_success_rate(language)
    
    return PatternAnalysis(
        language=language,
        imports=analysis.get("imports", []),
        functions=analysis.get("functions", []),
        patterns=analysis.get("patterns", {}),
        success_rate=success_rate
    )

@router.get("/recent")
async def get_recent_patterns(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recently learned patterns across all languages."""
    interactions = storage.get_recent_interactions(limit)
    
    recent_patterns = []
    for interaction in interactions:
        language = interaction["context"].get("language", "unknown")
        if language in analyzer.configs:
            analysis = analyzer.analyze_code(
                interaction["response"],
                language
            )
            recent_patterns.append({
                "timestamp": interaction["timestamp"],
                "language": language,
                "analysis": analysis,
                "success": interaction["success_indicators"]["completion"]
            })
    
    return recent_patterns
