"""
Language-specific pattern recognition and analysis.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class LanguageConfig:
    """Configuration for language-specific pattern recognition"""
    name: str
    file_extensions: List[str]
    import_patterns: List[str]
    function_patterns: List[str]
    class_patterns: List[str]
    common_patterns: Dict[str, str]
    best_practices: List[str]

# Language-specific configurations
LANGUAGE_CONFIGS = {
    "python": LanguageConfig(
        name="Python",
        file_extensions=[".py"],
        import_patterns=[
            r'^import\s+[\w.]+',
            r'^from\s+[\w.]+\s+import\s+[\w.]+(?:\s+as\s+\w+)?'
        ],
        function_patterns=[
            r'def\s+(\w+)\s*\([^)]*\)\s*:',
            r'async\s+def\s+(\w+)\s*\([^)]*\)\s*:',
            r'lambda\s+[^:]+:'
        ],
        class_patterns=[
            r'class\s+(\w+)\s*(?:\([^)]*\))?\s*:',
        ],
        common_patterns={
            "error_handling": r'try:.*?except.*?:',
            "context_manager": r'with\s+.*?:',
            "list_comprehension": r'\[.*?\s+for\s+.*?\s+in\s+.*?\]',
            "async_pattern": r'async\s+(?:def|with|for)',
        },
        best_practices=[
            "Use type hints for function arguments and return values",
            "Follow PEP 8 style guide",
            "Use context managers for resource handling",
            "Prefer list comprehensions over loops for simple transformations"
        ]
    ),
    "javascript": LanguageConfig(
        name="JavaScript",
        file_extensions=[".js", ".jsx", ".ts", ".tsx"],
        import_patterns=[
            r'^import\s+.*?\s+from\s+[\'"].*?[\'"]',
            r'^const\s+.*?\s*=\s*require\([\'"].*?[\'"]\)',
            r'^import\s*{[^}]+}\s*from\s+[\'"].*?[\'"]'
        ],
        function_patterns=[
            r'function\s+(\w+)\s*\([^)]*\)',
            r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            r'(\w+)\s*:\s*(?:async\s*)?\([^)]*\)\s*=>'
        ],
        class_patterns=[
            r'class\s+(\w+)\s*(?:extends\s+\w+)?\s*{',
            r'interface\s+(\w+)\s*(?:extends\s+\w+)?\s*{'
        ],
        common_patterns={
            "error_handling": r'try\s*{.*?}\s*catch\s*\(.*?\)\s*{',
            "promise_pattern": r'new\s+Promise\s*\(\s*(?:async\s*)?\([^)]*\)',
            "async_await": r'async.*?await',
            "destructuring": r'(?:const|let|var)\s*{[^}]+}\s*=',
        },
        best_practices=[
            "Use const for values that won't be reassigned",
            "Use async/await instead of raw promises",
            "Use destructuring for object properties",
            "Use template literals instead of string concatenation"
        ]
    ),
    "typescript": LanguageConfig(
        name="TypeScript",
        file_extensions=[".ts", ".tsx"],
        import_patterns=[
            r'^import\s+.*?\s+from\s+[\'"].*?[\'"]',
            r'^import\s*{[^}]+}\s*from\s+[\'"].*?[\'"]',
            r'^import\s+type\s+.*?\s+from\s+[\'"].*?[\'"]'
        ],
        function_patterns=[
            r'function\s+(\w+)\s*<[^>]*>?\s*\([^)]*\)\s*:',
            r'const\s+(\w+)\s*=\s*(?:<[^>]*>)?\s*\([^)]*\)\s*:.*?=>',
            r'(\w+)\s*:\s*(?:<[^>]*>)?\s*\([^)]*\)\s*=>'
        ],
        class_patterns=[
            r'class\s+(\w+)\s*(?:<[^>]*>)?\s*(?:extends\s+\w+)?\s*{',
            r'interface\s+(\w+)\s*(?:<[^>]*>)?\s*(?:extends\s+\w+)?\s*{',
            r'type\s+(\w+)\s*(?:<[^>]*>)?\s*='
        ],
        common_patterns={
            "type_definition": r'type\s+\w+\s*=',
            "interface": r'interface\s+\w+\s*{',
            "generic": r'<[^>]+>',
            "enum": r'enum\s+\w+\s*{',
        },
        best_practices=[
            "Use strict TypeScript configuration",
            "Define explicit return types for functions",
            "Use interfaces for object shapes",
            "Leverage TypeScript's type system"
        ]
    ),
    "rust": LanguageConfig(
        name="Rust",
        file_extensions=[".rs"],
        import_patterns=[
            r'^use\s+.*?;',
            r'^extern\s+crate\s+\w+;'
        ],
        function_patterns=[
            r'fn\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)',
            r'async\s+fn\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)'
        ],
        class_patterns=[
            r'struct\s+(\w+)\s*(?:<[^>]+>)?\s*{',
            r'trait\s+(\w+)\s*(?:<[^>]+>)?\s*{',
            r'impl\s+(?:<[^>]+>)?\s*(\w+)'
        ],
        common_patterns={
            "error_handling": r'Result<.*?,.*?>',
            "lifetime": r'\'[a-z]+\s+(?:&|ref)',
            "pattern_matching": r'match\s+.*?\s*{',
            "unsafe_block": r'unsafe\s*{',
        },
        best_practices=[
            "Use Result for fallible operations",
            "Prefer pattern matching over if-let when possible",
            "Use proper lifetime annotations",
            "Follow the official Rust style guide"
        ]
    ),
    "go": LanguageConfig(
        name="Go",
        file_extensions=[".go"],
        import_patterns=[
            r'^import\s+\([^)]+\)',
            r'^import\s+[\'"].*?[\'"]'
        ],
        function_patterns=[
            r'func\s+(\w+)\s*\([^)]*\)',
            r'func\s*\([^)]+\)\s*(\w+)\s*\([^)]*\)'
        ],
        class_patterns=[
            r'type\s+(\w+)\s+struct\s*{',
            r'type\s+(\w+)\s+interface\s*{'
        ],
        common_patterns={
            "error_handling": r'if\s+err\s*!=\s*nil\s*{',
            "defer_pattern": r'defer\s+.*?[({]',
            "goroutine": r'go\s+\w+\(',
            "channel_ops": r'(?:make\s*\(\s*chan\b)|(?:<-\s*chan\b)',
        },
        best_practices=[
            "Always handle errors explicitly",
            "Use defer for cleanup operations",
            "Use channels for communication between goroutines",
            "Follow the official Go style guide"
        ]
    ),
    "java": LanguageConfig(
        name="Java",
        file_extensions=[".java"],
        import_patterns=[
            r'^import\s+(?:static\s+)?[\w.]+(?:\.\*)?;'
        ],
        function_patterns=[
            r'(?:public|private|protected)?\s*(?:static\s+)?(?:<[^>]+>\s+)?(\w+)\s+(\w+)\s*\([^)]*\)',
            r'@Override\s+(?:public|private|protected)?\s+(?:<[^>]+>\s+)?(\w+)\s+(\w+)\s*\([^)]*\)'
        ],
        class_patterns=[
            r'class\s+(\w+)\s*(?:<[^>]+>)?\s*(?:extends\s+\w+)?\s*(?:implements\s+[^{]+)?\s*{',
            r'interface\s+(\w+)\s*(?:<[^>]+>)?\s*(?:extends\s+[^{]+)?\s*{',
            r'enum\s+(\w+)\s*{'
        ],
        common_patterns={
            "exception_handling": r'try\s*{.*?}\s*catch\s*\([^)]+\)\s*{',
            "stream_api": r'stream\(\).*?collect\(',
            "lambda": r'->\s*{.*?}',
            "annotation": r'@\w+(?:\([^)]*\))?',
        },
        best_practices=[
            "Follow Java naming conventions",
            "Use proper exception handling",
            "Leverage the Stream API for collections",
            "Use dependency injection"
        ]
    ),
    "kotlin": LanguageConfig(
        name="Kotlin",
        file_extensions=[".kt", ".kts"],
        import_patterns=[
            r'^import\s+[\w.]+(?:\.\*)?'
        ],
        function_patterns=[
            r'fun\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)',
            r'suspend\s+fun\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)'
        ],
        class_patterns=[
            r'class\s+(\w+)\s*(?:<[^>]+>)?\s*(?:\([^)]*\))?\s*(?::\s*[^{]+)?\s*{?',
            r'interface\s+(\w+)\s*(?:<[^>]+>)?\s*(?::\s*[^{]+)?\s*{?',
            r'object\s+(\w+)\s*(?::\s*[^{]+)?\s*{'
        ],
        common_patterns={
            "null_safety": r'\?\.',
            "coroutine": r'launch\s*{|async\s*{',
            "extension_function": r'fun\s+\w+\.\w+',
            "data_class": r'data\s+class',
        },
        best_practices=[
            "Use data classes for DTOs",
            "Leverage null safety features",
            "Use coroutines for async operations",
            "Prefer val over var"
        ]
    ),
    "react": LanguageConfig(
        name="React",
        file_extensions=[".jsx", ".tsx"],
        import_patterns=[
            r'^import\s+.*?\s+from\s+[\'"]react[\'"]',
            r'^import\s*{[^}]+}\s*from\s+[\'"]react[\'"]',
            r'^import\s+.*?\s+from\s+[\'"]react-.*?[\'"]'
        ],
        function_patterns=[
            r'function\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)',
            r'const\s+(\w+)\s*=\s*(?:React\.)?memo\(',
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{',
            r'use\w+(?:\s*<[^>]+>)?\s*\([^)]*\)'  # Hook pattern
        ],
        class_patterns=[
            r'class\s+(\w+)\s+extends\s+(?:React\.)?Component\s*{',
            r'class\s+(\w+)\s+extends\s+(?:React\.)?PureComponent\s*{'
        ],
        common_patterns={
            "hooks": r'use[A-Z]\w+',
            "jsx": r'<[A-Z]\w+[^>]*>',
            "props_destructure": r'const\s*{\s*[^}]+\s*}\s*=\s*props',
            "effect": r'useEffect\s*\(\s*\(\)\s*=>\s*{[^}]*}\s*,\s*\[[^\]]*\]\s*\)',
            "state": r'useState\s*\([^)]*\)',
            "ref": r'useRef\s*\([^)]*\)',
            "context": r'useContext\s*\([^)]*\)',
            "callback": r'useCallback\s*\(\s*\([^)]*\)\s*=>\s*{[^}]*}\s*,\s*\[[^\]]*\]\s*\)',
            "memo": r'useMemo\s*\(\s*\(\)\s*=>\s*[^,]+,\s*\[[^\]]*\]\s*\)',
            "reducer": r'useReducer\s*\([^,]+,\s*[^,]+(?:,\s*[^)]+)?\)',
            "prop_types": r'PropTypes\.',
        },
        best_practices=[
            "Use functional components over class components",
            "Follow the Rules of Hooks",
            "Memoize callbacks and expensive computations",
            "Use proper dependency arrays in hooks",
            "Keep components small and focused",
            "Use TypeScript for better type safety",
            "Implement proper error boundaries",
            "Use React.memo for performance optimization"
        ]
    ),
    "vue": LanguageConfig(
        name="Vue",
        file_extensions=[".vue"],
        import_patterns=[
            r'^import\s+.*?\s+from\s+[\'"]vue[\'"]',
            r'^import\s*{[^}]+}\s*from\s+[\'"]vue[\'"]',
            r'^import\s+.*?\s+from\s+[\'"]@vue/.*?[\'"]'
        ],
        function_patterns=[
            r'(?:export\s+)?default\s+defineComponent\s*\(',
            r'setup\s*\([^)]*\)\s*{',
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{',
            r'(?:ref|computed|watch|watchEffect)\s*\([^)]*\)'
        ],
        class_patterns=[
            r'@Component\s*\([^)]*\)\s*class\s+(\w+)',
            r'@Options\s*\([^)]*\)\s*class\s+(\w+)'
        ],
        common_patterns={
            "composition_api": {
                "ref": r'ref\s*\([^)]*\)',
                "reactive": r'reactive\s*\([^)]*\)',
                "computed": r'computed\s*\(\s*\(\)\s*=>\s*[^}]+\)',
                "watch": r'watch\s*\([^,]+,\s*\([^)]*\)\s*=>\s*{[^}]*}\s*\)',
                "watchEffect": r'watchEffect\s*\(\s*\(\)\s*=>\s*{[^}]*}\s*\)',
                "provide": r'provide\s*\([^)]+\)',
                "inject": r'inject\s*\([^)]+\)',
                "lifecycle_hooks": r'on[A-Z]\w+\s*\([^)]*\)',
            },
            "template": {
                "v-if": r'v-if=[\'""][^\'""\n]+[\'""]',
                "v-for": r'v-for=[\'""][^\'""\n]+[\'""]',
                "v-model": r'v-model(?:\.[\w.]+)?=[\'""][^\'""\n]+[\'""]',
                "v-on": r'@[\w]+(?:\.[\w.]+)?=[\'""][^\'""\n]+[\'""]',
                "v-bind": r':[\w]+(?:\.[\w.]+)?=[\'""][^\'""\n]+[\'""]',
            },
            "script_setup": r'<script\s+setup\s*(?:lang=[\'""].*?[\'""])?\s*>',
            "style_scoped": r'<style\s+scoped\s*(?:lang=[\'""].*?[\'""])?\s*>',
        },
        best_practices=[
            "Use Composition API for better type inference and reusability",
            "Implement proper prop validation",
            "Use script setup for simpler component code",
            "Keep component logic in composables",
            "Use TypeScript for better type safety",
            "Implement proper error handling",
            "Use computed properties over methods for caching",
            "Keep components small and focused",
            "Use proper naming conventions for events",
            "Implement proper component communication patterns"
        ]
    ),
}

class LanguagePatternAnalyzer:
    """Analyzes code patterns for specific programming languages."""
    
    def __init__(self):
        self.configs = LANGUAGE_CONFIGS

    def detect_language(self, code: str) -> Optional[str]:
        """
        Detect the programming language from code content.
        Returns the language name or None if unknown.
        """
        # Check for language-specific patterns
        for lang, config in self.configs.items():
            # Check imports
            for pattern in config.import_patterns:
                if re.search(pattern, code, re.MULTILINE):
                    return lang
            
            # Check function definitions
            for pattern in config.function_patterns:
                if re.search(pattern, code, re.MULTILINE):
                    return lang
            
            # Check class definitions
            for pattern in config.class_patterns:
                if re.search(pattern, code, re.MULTILINE):
                    return lang
        
        return None

    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Analyze code for patterns in a specific language.
        """
        if language not in self.configs:
            return {}

        config = self.configs[language]
        analysis = {
            "language": language,
            "imports": [],
            "functions": [],
            "classes": [],
            "patterns": {},
            "best_practices_violations": []
        }

        # Extract imports
        for pattern in config.import_patterns:
            imports = re.finditer(pattern, code, re.MULTILINE)
            analysis["imports"].extend(match.group(0) for match in imports)

        # Extract functions
        for pattern in config.function_patterns:
            functions = re.finditer(pattern, code, re.MULTILINE)
            analysis["functions"].extend(match.group(1) for match in functions if match.group(1))

        # Extract classes
        for pattern in config.class_patterns:
            classes = re.finditer(pattern, code, re.MULTILINE)
            analysis["classes"].extend(match.group(1) for match in classes if match.group(1))

        # Check common patterns
        for name, pattern in config.common_patterns.items():
            matches = re.finditer(pattern, code, re.MULTILINE | re.DOTALL)
            analysis["patterns"][name] = [match.group(0) for match in matches]

        # Check best practices
        for practice in config.best_practices:
            # This is a simplified check - in reality, you'd want more sophisticated analysis
            if practice.lower() not in code.lower():
                analysis["best_practices_violations"].append(practice)

        return analysis

    def get_language_best_practices(self, language: str) -> List[str]:
        """Get best practices for a specific language."""
        if language in self.configs:
            return self.configs[language].best_practices
        return []

    def get_common_patterns(self, language: str) -> Dict[str, str]:
        """Get common patterns for a specific language."""
        if language in self.configs:
            return self.configs[language].common_patterns
        return {}
