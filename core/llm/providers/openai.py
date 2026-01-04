# core/llm/providers/openai.py
# -*- coding: utf-8 -*-

import openai
import os
from typing import List, Dict, Any


class OpenAILLMProvider:
    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.2,
    ):
        self.model = model
        self.temperature = temperature
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        resp = openai.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )

        choice = resp.choices[0]
        return {
            "content": choice.message.content,
            "raw": resp,
        }
