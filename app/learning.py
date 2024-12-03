"""
Learning system for the OllamaTIC agent.
Analyzes interactions, identifies patterns, and improves responses over time.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from pydantic import BaseModel, Field
import re
from collections import defaultdict
import numpy as np
from dataclasses import dataclass, field
from .vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

@dataclass
class CodeBlock:
    """Represents a code block found in text"""
    language: str
    code: str
    context: str = ""  # Text before the code block
    success_rate: float = 0.0
    usage_count: int = 0


@dataclass
class LanguagePatterns:
    """Patterns learned for a specific programming language"""
    language: str
    common_imports: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    function_patterns: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    error_patterns: Dict[str, str] = field(default_factory=dict)
    best_practices: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    code_blocks: Dict[str, CodeBlock] = field(default_factory=dict)


class LearningSystem:
    """
    Core learning system that analyzes interactions and improves responses.
    """
    def __init__(self, vector_store: Optional[VectorStore] = None):
        logger.info("Initializing learning system")
        self.language_patterns: Dict[str, LanguagePatterns] = {}
        self.context_memory: Dict[str, Dict[str, Any]] = {}
        self.code_block_regex = re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL)
        self.vector_store = vector_store or VectorStore()
        self._load_patterns()
        
    def _load_patterns(self):
        """Load patterns from vector store on startup"""
        logger.info("Loading patterns from vector store")
        patterns = self.vector_store.search_patterns(
            query="",  # Empty query to get all patterns
            pattern_type="language_patterns",
            limit=100  # Get all patterns
        )
        
        for pattern_data in patterns:
            language = pattern_data.get("language")
            pattern = pattern_data.get("pattern", {})
            if language and pattern:
                if language not in self.language_patterns:
                    self.language_patterns[language] = LanguagePatterns(language=language)
                
                lang_patterns = self.language_patterns[language]
                # Update pattern dictionaries with stored values
                lang_patterns.common_imports.update(pattern.get("common_imports", {}))
                lang_patterns.function_patterns.update(pattern.get("function_patterns", {}))
                lang_patterns.error_patterns.update(pattern.get("error_patterns", {}))
                lang_patterns.best_practices.update(pattern.get("best_practices", {}))
                
    def analyze_interaction(
        self,
        interaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze an interaction to extract patterns and learning points.
        
        Args:
            interaction: Dictionary containing interaction details with keys:
                - prompt: The input prompt
                - response: The model's response
                - model: The model used
                - context: Additional context dictionary
                - language: The programming language
                - code: The code snippet
                - error: The error message
                - query: The query string
        """
        # Validate required fields
        if not isinstance(interaction, dict):
            logger.warning("Invalid interaction data: expected dictionary")
            return {"error": "Invalid interaction data format"}
            
        prompt = interaction.get('prompt')
        response = interaction.get('response')
        
        if not prompt or not response:
            logger.warning("Invalid interaction data: missing prompt or response")
            return {"error": "Missing required fields: prompt and response"}
            
        # Get optional fields with defaults
        model = interaction.get('model', 'unknown')
        context = interaction.get('context', {})
        language = interaction.get('language', '')
        code = interaction.get('code', '')
        error = interaction.get('error', '')
        query = interaction.get('query', '')
        
        logger.info(f"Analyzing interaction for model: {model}")
        
        # Extract code blocks from prompt and response
        prompt_code_blocks = self._extract_code_blocks(prompt)
        response_code_blocks = self._extract_code_blocks(response)
            
        logger.debug(f"Found {len(prompt_code_blocks)} code blocks in prompt")
        logger.debug(f"Found {len(response_code_blocks)} code blocks in response")
            
        # Identify programming languages involved
        languages = set(block.language for block in prompt_code_blocks + response_code_blocks if block.language != "unknown")
        logger.info(f"Detected languages: {languages}")
            
        learning_results = {
            "languages": list(languages),
            "patterns_found": []
        }

        # If we have code blocks, analyze them
        if prompt_code_blocks or response_code_blocks:
            # Analyze each language's patterns
            for lang in languages:
                if lang not in self.language_patterns:
                    self.language_patterns[lang] = LanguagePatterns(language=lang)
                
                # Analyze patterns for this language
                patterns_found = self._analyze_language_patterns(
                    lang,
                    prompt_code_blocks,
                    response_code_blocks
                )
                learning_results["patterns_found"].extend(patterns_found)
                
                # Store updated patterns in vector store
                pattern_data = {
                    "language": lang,
                    "common_imports": dict(self.language_patterns[lang].common_imports),
                    "function_patterns": dict(self.language_patterns[lang].function_patterns),
                    "error_patterns": dict(self.language_patterns[lang].error_patterns),
                    "best_practices": dict(self.language_patterns[lang].best_practices)
                }
                
                # Store pattern with metadata
                self.vector_store.store_pattern(
                    pattern=pattern_data,
                    pattern_type="language_patterns",
                    language=lang
                )
                
                logger.info(f"Stored patterns for language: {lang}")
                
            # Store code blocks in vector store
            for block in response_code_blocks:
                if block.language == "unknown":
                    continue
                    
                logger.debug(f"Storing code block for {block.language}")
                self.vector_store.store_code_snippet(
                    code=block.code,
                    language=block.language,
                    metadata={
                        "context": block.context,
                        "success_rate": block.success_rate,
                        "usage_count": block.usage_count,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            return learning_results
        
        # If we have explicit language and code but no code blocks
        if language and code:
            # Initialize pattern structure
            pattern = {
                "language": language,
                "common_imports": {},
                "function_patterns": {},
                "error_patterns": {},
                "best_practices": {}
            }
            
            # Extract imports
            imports = self._extract_imports(language, code)
            if imports:
                pattern["common_imports"].update(imports)
                
            # Extract function patterns
            functions = self._extract_function_patterns(language, code)
            if functions:
                pattern["function_patterns"].update(functions)
                
            # Record error patterns
            if error:
                error_key = self._simplify_error_message(error)
                if error_key:
                    pattern["error_patterns"][error_key] = {
                        "count": 1,
                        "last_seen": datetime.now().isoformat(),
                        "example": error
                    }
                    
            # Store the pattern
            self.vector_store.store_pattern(
                pattern=pattern,
                pattern_type="language_patterns",
                language=language
            )
            
            learning_results["languages"].append(language)
            return learning_results
            
        # No code blocks or explicit code found
        return learning_results

    def enhance_prompt(
        self,
        prompt: str,
        model: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enhance a prompt using learned patterns and similar examples.
        """
        logger.info(f"Enhancing prompt for model: {model}")
        
        # Extract code blocks to identify languages
        code_blocks = self._extract_code_blocks(prompt)
        languages = set(block.language for block in code_blocks)
        
        enhanced_prompt = prompt
        
        for language in languages:
            if language in self.language_patterns:
                patterns = self.language_patterns[language]
                
                # Add common imports if missing
                for import_stmt, confidence in patterns.common_imports.items():
                    if confidence > 0.8 and import_stmt not in prompt:  # High confidence threshold
                        enhanced_prompt = f"Please include {import_stmt}\n{enhanced_prompt}"
                
                # Add best practices if relevant
                for practice, confidence in patterns.best_practices.items():
                    if confidence > 0.9:  # Very high confidence threshold
                        enhanced_prompt += f"\nPlease follow this best practice: {practice}"
                
                # Search for similar code examples
                similar_code = self.vector_store.search_code_snippets(
                    query=prompt,
                    language=language,
                    limit=2
                )
                
                if similar_code:
                    enhanced_prompt += "\n\nHere are some relevant examples:\n"
                    for example in similar_code:
                        if example["score"] > 0.8:  # Only include highly relevant examples
                            enhanced_prompt += f"\n```{language}\n{example['code']}\n```\n"
                
                # Search for similar patterns
                similar_patterns = self.vector_store.search_patterns(
                    query=prompt,
                    pattern_type="language_patterns",
                    language=language,
                    limit=1
                )
                
                if similar_patterns:
                    pattern = similar_patterns[0]["pattern"]
                    if "error_patterns" in pattern:
                        for error, solution in pattern["error_patterns"].items():
                            if error in prompt:
                                enhanced_prompt += f"\nConsider this solution for the error: {solution}"
        
        # Search for similar conversations for context
        similar_convs = self.vector_store.search_conversations(
            query=prompt,
            limit=1
        )
        
        if similar_convs:
            conv = similar_convs[0]
            if conv["score"] > 0.9:  # Only use very similar conversations
                messages = conv["messages"]
                enhanced_prompt += "\n\nBased on similar conversation context:"
                for msg in messages:
                    if msg["role"] == "assistant" and len(msg["content"]) < 500:
                        enhanced_prompt += f"\n{msg['content']}"
        
        return enhanced_prompt

    def _extract_code_blocks(self, text: str) -> List[CodeBlock]:
        """
        Extract code blocks from text and analyze their context.
        """
        logger.debug("Extracting code blocks")
        blocks = []
        matches = self.code_block_regex.finditer(text)
        
        for match in matches:
            language = match.group(1) or "unknown"
            code = match.group(2)
            
            # Get context (text before the code block)
            start_pos = match.start()
            context_start = max(0, start_pos - 200)  # Get up to 200 chars before
            context = text[context_start:start_pos].strip()
            
            blocks.append(CodeBlock(
                language=language.lower(),
                code=code,
                context=context
            ))
        
        return blocks

    def _analyze_language_patterns(
        self,
        language: str,
        prompt_blocks: List[CodeBlock],
        response_blocks: List[CodeBlock]
    ) -> List[str]:
        """
        Analyze code blocks to identify and learn patterns for a specific language.
        """
        logger.info(f"Analyzing patterns for language: {language}")
        patterns_found = []
        patterns = self.language_patterns[language]
        
        # Analyze imports
        for block in response_blocks:
            if block.language == language:
                imports = self._extract_imports(language, block.code)
                for imp in imports:
                    patterns.common_imports[imp] += 1
                    patterns_found.append(f"Import pattern: {imp}")
        
        # Analyze function patterns
        for block in response_blocks:
            if block.language == language:
                funcs = self._extract_function_patterns(language, block.code)
                for func in funcs:
                    patterns.function_patterns[func] += 1
                    patterns_found.append(f"Function pattern: {func}")
        
        # Update code blocks repository
        for block in response_blocks:
            if block.language == language:
                # Use first 100 chars of code as key
                key = block.code[:100]
                if key not in patterns.code_blocks:
                    patterns.code_blocks[key] = block
                else:
                    # Update existing block
                    patterns.code_blocks[key].usage_count += 1
        
        return patterns_found

    def _extract_imports(self, language: str, code: str) -> List[str]:
        """
        Extract import statements based on language.
        """
        logger.debug(f"Extracting imports for language: {language}")
        imports = []
        if language == "python":
            # Match Python imports including from imports
            import_regex = re.compile(r'^(?:from\s+[\w.]+\s+)?import\s+(?:[\w.]+(?:\s*,\s*[\w.]+)*(?:\s+as\s+\w+)?|\*)', re.MULTILINE)
            imports = import_regex.findall(code)
        elif language == "javascript":
            # Match JS imports including require and ES6 imports
            import_regex = re.compile(r'(?:import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"][^\'"]+'
                                    r'|require\s*\([^)]+\)'
                                    r'|import\s+[\'"][^\'"]+'
                                    r'|export\s+(?:{[^}]+}|\*)\s+from\s+[\'"][^\'"]+'
                                    r')', re.MULTILINE)
            imports = import_regex.findall(code)
        elif language == "typescript":
            # Match TypeScript imports including type imports
            import_regex = re.compile(r'(?:import\s+(?:type\s+)?(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"][^\'"]+'
                                    r'|import\s+type\s+{[^}]+}\s+from\s+[\'"][^\'"]+'
                                    r'|export\s+(?:type\s+)?(?:{[^}]+}|\*)\s+from\s+[\'"][^\'"]+'
                                    r')', re.MULTILINE)
            imports = import_regex.findall(code)
        elif language == "java":
            # Match Java imports
            import_regex = re.compile(r'^import\s+(?:static\s+)?[\w.]+(?:\s*\.\s*\*)?;', re.MULTILINE)
            imports = import_regex.findall(code)
        elif language == "go":
            # Match Go imports including parenthesized import groups
            import_regex = re.compile(r'(?:import\s+(?:"[^"]+"|`[^`]+`)'
                                    r'|import\s+\([^)]*\))', re.MULTILINE)
            imports = import_regex.findall(code)
        elif language == "rust":
            # Match Rust imports including use statements and external crates
            import_regex = re.compile(r'(?:use\s+(?:(?::[a-zA-Z0-9_]+)+(?:::[*{][^;]*)?|[a-zA-Z0-9_]+(?:::[*{][^;]*)?)'
                                    r'|extern\s+crate\s+[a-zA-Z0-9_]+(?:\s+as\s+[a-zA-Z0-9_]+)?)', re.MULTILINE)
            imports = import_regex.findall(code)
        # Add more languages as needed
        
        return imports

    def _extract_function_patterns(self, language: str, code: str) -> List[str]:
        """
        Extract function patterns based on language.
        """
        logger.debug(f"Extracting function patterns for language: {language}")
        patterns = []
        if language == "python":
            # Match Python function definitions including async, decorators, and type hints
            func_regex = re.compile(r'(?:@[\w.]+(?:\(.*?\))?\s+)*(?:async\s+)?def\s+(\w+)\s*(?:\[.*?\])?\s*\([^)]*\)\s*(?:->\s*[^:]+)?\s*:', re.MULTILINE)
            patterns = func_regex.findall(code)
        elif language == "javascript":
            # Match JS function definitions including async, arrow functions, and class methods
            func_regex = re.compile(r'(?:async\s+)?(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?function|\(\s*[^)]*\)\s*=>'
                                  r'|(?:get|set|static|async)\s+(\w+)\s*\([^)]*\)'
                                  r'|(\w+)\s*\([^)]*\)\s*{)', re.MULTILINE)
            matches = func_regex.finditer(code)
            for match in matches:
                # Get the first non-None group which contains the function name
                name = next((g for g in match.groups() if g), '')
                if name:
                    patterns.append(name)
        elif language == "typescript":
            # Match TypeScript function definitions including type parameters and return types
            func_regex = re.compile(r'(?:async\s+)?(?:function\s+(\w+)(?:<[^>]+>)?\s*\([^)]*\)(?:\s*:\s*[^{]+)?'
                                  r'|(\w+)\s*=\s*(?:async\s+)?function(?:<[^>]+>)?\s*\([^)]*\)(?:\s*:\s*[^{]+)?'
                                  r'|(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)(?:\s*:\s*[^{]+)?'
                                  r'|(?:get|set|static|async)\s+(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?)', re.MULTILINE)
            matches = func_regex.finditer(code)
            for match in matches:
                name = next((g for g in match.groups() if g), '')
                if name:
                    patterns.append(name)
        elif language == "java":
            # Match Java method definitions including annotations and modifiers
            func_regex = re.compile(r'(?:@\w+(?:\([^)]*\))?\s+)*(?:public|private|protected|static|final|native|synchronized|abstract|transient)?\s+(?:<[^>]+>\s+)?(?:[\w\[\]]+\s+)?(\w+)\s*\([^)]*\)', re.MULTILINE)
            patterns = func_regex.findall(code)
        elif language == "go":
            # Match Go function definitions including methods and interfaces
            func_regex = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\([^)]*\)\s*(?:\([^)]*\)|[\w\[\]*]+)?', re.MULTILINE)
            patterns = func_regex.findall(code)
        elif language == "rust":
            # Match Rust function definitions including generics, lifetimes, and traits
            func_regex = re.compile(r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)(?:\s*->\s*[^{]+)?', re.MULTILINE)
            patterns = func_regex.findall(code)
        # Add more languages as needed
        
        return patterns

    def update_success_metrics(
        self,
        language: str,
        code_block: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        """
        Update success metrics for code blocks and patterns.
        """
        logger.info(f"Updating success metrics for language: {language}")
        if language in self.language_patterns:
            patterns = self.language_patterns[language]
            
            # Update code block success rate
            key = code_block[:100]  # Use first 100 chars as key
            if key in patterns.code_blocks:
                block = patterns.code_blocks[key]
                block.usage_count += 1
                # Running average of success rate
                block.success_rate = (
                    (block.success_rate * (block.usage_count - 1) + (1.0 if success else 0.0))
                    / block.usage_count
                )
                
                # Store updated metrics in vector store
                logger.debug(f"Storing updated metrics for code block: {key}")
                self.vector_store.store_code_snippet(
                    code=block.code,
                    language=language,
                    metadata={
                        "context": block.context,
                        "success_rate": block.success_rate,
                        "usage_count": block.usage_count,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # If there's an error, update error patterns
            if not success and error_message:
                # Create a simplified error pattern
                error_pattern = self._simplify_error_message(error_message)
                if error_pattern:
                    patterns.error_patterns[error_pattern] = code_block
                    
                    # Store error pattern
                    logger.debug(f"Storing error pattern: {error_pattern}")
                    self.vector_store.store_pattern(
                        pattern={
                            "error": error_pattern,
                            "solution": code_block
                        },
                        pattern_type="error_pattern",
                        language=language
                    )

    def _simplify_error_message(self, error_message: str) -> str:
        """
        Create a simplified pattern from an error message.
        """
        logger.debug("Simplifying error message")
        # Remove specific file paths, line numbers, and variable names
        simplified = re.sub(r'File ".*?"', 'File "..."', error_message)
        simplified = re.sub(r'line \d+', 'line X', simplified)
        simplified = re.sub(r'"\w+"', '"..."', simplified)
        return simplified

    def store_pattern(self, pattern_type: str, pattern: dict, metadata: Optional[dict] = None):
        """Store a pattern in the vector store"""
        try:
            if not pattern:
                logger.warning("Attempted to store empty pattern")
                return
                
            # Ensure pattern has required fields
            if "language" not in pattern:
                logger.warning("Pattern missing language field")
                return
                
            # Initialize metadata if not provided
            if metadata is None:
                metadata = {}
                
            # Add timestamp and language to metadata
            metadata.update({
                "timestamp": datetime.now().isoformat(),
                "language": pattern["language"],
                "pattern_type": pattern_type
            })
            
            # Store pattern with metadata
            self.vector_store.store_pattern(
                pattern=pattern,
                pattern_type=pattern_type,
                metadata=metadata
            )
            logger.debug(f"Stored {pattern_type} pattern for {pattern['language']}")
            
        except Exception as e:
            logger.error(f"Error storing pattern: {str(e)}")
