from typing import List, Optional

class PromptTemplate:
    template: str
    variables: List[str]
    model_id: str
    language: Optional[str]
    task_type: Optional[str]
    priority: int

    def __init__(self, template: str, variables: List[str], model_id: str, language: Optional[str] = None, task_type: Optional[str] = None, priority: int = 1):
        self.template = template
        self.variables = variables
        self.model_id = model_id
        self.language = language
        self.task_type = task_type
        self.priority = priority

    def render(self, **kwargs) -> str:
        """Render the prompt template with provided keyword arguments."""
        return self.template.format(**kwargs)
