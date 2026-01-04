# core/prompt/prompt_builder.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional

from .prompt_loader import PromptLoader
from .prompt_render import render_template
from .prompt_assembler import assemble_messages


def _group_contexts(context_blocks):
    memory = []
    kb = []
    for c in context_blocks:
        if c.type == "memory":
            memory.append(c)
        elif c.type == "kb":
            kb.append(c)
    return memory, kb


def _format_memory_context(memory_blocks) -> str:
    if not memory_blocks:
        return ""
    lines = []
    for b in memory_blocks:
        lines.append(f"- {b.text}")
    return "\n".join(lines)


def _format_kb_context(kb_blocks) -> str:
    if not kb_blocks:
        return ""
    lines = []
    for idx, b in enumerate(kb_blocks, 1):
        lines.append(f"[KB {idx} | {b.source}]\n{b.text}")
    return "\n\n".join(lines)


class PromptBuilder:
    def __init__(self, project_root: str):
        self.loader = PromptLoader(project_root)

    def build(
        self,
        *,
        identity,
        app_id: str,
        intent: str,
        user_query: str,
        context_blocks: List,
        intent_params: Optional[Dict[str, Any]] = None,
    ):
        # 1. load prompt templates
        global_sys = self.loader.load_global_system()
        app_sys = self.loader.load_app_system(app_id)
        intent_tpl = self.loader.load_intent(app_id, intent)

        # 2. group contexts
        memory_ctx, kb_ctx = _group_contexts(context_blocks)

        # 3. format contexts
        memory_text = _format_memory_context(memory_ctx)
        kb_text = _format_kb_context(kb_ctx)

        # 4. merge render params (core + intent params)
        render_params: Dict[str, Any] = {
            "query": user_query,
            "memory": memory_text,
            "context": kb_text,
        }
        if intent_params:
            # 后写覆盖前写：允许业务覆盖 query/context（通常不建议，但保持灵活）
            render_params.update(intent_params)

        # 5. render intent prompt
        user_prompt = render_template(intent_tpl, render_params)

        # 6. assemble messages
        return assemble_messages(
            global_system=global_sys,
            app_system=app_sys,
            user_prompt=user_prompt,
        )
