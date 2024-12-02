from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.prompt_template import PromptTemplate
import json
import os
from pathlib import Path

router = APIRouter()

# Store prompts in a JSON file
PROMPTS_FILE = Path("data/prompts.json")
PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_prompts() -> List[Dict[str, Any]]:
    if not PROMPTS_FILE.exists():
        return []
    try:
        with open(PROMPTS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_prompts(prompts: List[Dict[str, Any]]):
    with open(PROMPTS_FILE, 'w') as f:
        json.dump(prompts, f, indent=2)

@router.get("")
async def get_prompts():
    """Get all prompt templates"""
    return load_prompts()

@router.post("")
async def create_prompt(prompt: dict):
    """Create a new prompt template"""
    prompts = load_prompts()
    prompts.append(prompt)
    save_prompts(prompts)
    return prompt

@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, prompt: dict):
    """Update an existing prompt template"""
    prompts = load_prompts()
    for i, p in enumerate(prompts):
        if p.get('id') == prompt_id:
            prompts[i] = prompt
            save_prompts(prompts)
            return prompt
    raise HTTPException(status_code=404, detail="Prompt template not found")

@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt template"""
    prompts = load_prompts()
    prompts = [p for p in prompts if p.get('id') != prompt_id]
    save_prompts(prompts)
    return {"status": "success"}
