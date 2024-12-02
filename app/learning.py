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
        self.language_patterns: Dict[str, LanguagePatterns] = {}
        self.context_memory: Dict[str, Dict[str, Any]] = {}
        self.code_block_regex = re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL)
        self.vector_store = vector_store or VectorStore()
        
    def analyze_interaction(
        self,
        prompt: str,
        response: str,
        model: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze an interaction to extract patterns and learning points.
        """
        # Extract code blocks from prompt and response
        prompt_code_blocks = self._extract_code_blocks(prompt)
        response_code_blocks = self._extract_code_blocks(response)
        
        # Identify programming languages involved
        languages = set(block.language for block in prompt_code_blocks + response_code_blocks)
        
        learning_results = {
            "languages": list(languages),
            "patterns_found": [],
            "improvements": []
        }
        
        for language in languages:
            # Initialize language patterns if not exists
            if language not in self.language_patterns:
                self.language_patterns[language] = LanguagePatterns(language=language)
            
            # Analyze and update patterns
            patterns = self._analyze_language_patterns(
                language,
                prompt_code_blocks,
                response_code_blocks
            )
            learning_results["patterns_found"].extend(patterns)
            
            # Store code blocks in vector store
            for block in response_code_blocks:
                if block.language == language:
                    self.vector_store.store_code_snippet(
                        code=block.code,
                        language=language,
                        metadata={
                            "context": block.context,
                            "success_rate": block.success_rate,
                            "usage_count": block.usage_count,
                            "model": model,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
            
            # Store learned patterns
            patterns = self.language_patterns[language]
            self.vector_store.store_pattern(
                pattern={
                    "common_imports": dict(patterns.common_imports),
                    "function_patterns": dict(patterns.function_patterns),
                    "error_patterns": patterns.error_patterns,
                    "best_practices": dict(patterns.best_practices)
                },
                pattern_type="language_patterns",
                language=language
            )
        
        # Store the conversation for context learning
        self.vector_store.store_conversation(
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ],
            metadata={
                "model": model,
                "languages": list(languages),
                "context": context
            }
        )
        
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
        # Remove specific file paths, line numbers, and variable names
        simplified = re.sub(r'File ".*?"', 'File "..."', error_message)
        simplified = re.sub(r'line \d+', 'line X', simplified)
        simplified = re.sub(r'"\w+"', '"..."', simplified)
        return simplified
