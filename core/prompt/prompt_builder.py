# core/prompt/prompt_builder.py
# -*- coding: utf-8 -*-

from typing import List, Dict, Any, Optional, Tuple

from .prompt_loader import PromptLoader
from .prompt_render import render_template
from .prompt_assembler import assemble_messages


def _group_contexts(context_blocks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    primary = []
    memory = []
    kb = []
    for c in (context_blocks or []):
        ctype = (c.get("type") or "").strip()
        if ctype == "primary":
            primary.append(c)
        elif ctype == "memory":
            memory.append(c)
        elif ctype == "kb":
            kb.append(c)
    return primary, memory, kb


def _format_primary_turns(primary_blocks: List[Dict[str, Any]]) -> str:
    if not primary_blocks:
        return ""
    lines: List[str] = ["【最近对话（未摘要时间线）】"]
    for b in primary_blocks:
        meta = b.get("metadata") or {}
        role = (meta.get("role") or "user").strip()
        text = (b.get("text") or "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines).strip()


def _format_aux_memory(memory_blocks: List[Dict[str, Any]]) -> str:
    if not memory_blocks:
        return ""
    lines: List[str] = ["【相关历史片段（语义命中）】"]
    for b in memory_blocks:
        text = (b.get("text") or "").strip()
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines).strip()


def _format_kb_context(kb_blocks: List[Dict[str, Any]]) -> str:
    if not kb_blocks:
        return ""
    lines: List[str] = []
    for idx, b in enumerate(kb_blocks, 1):
        src = (b.get("source") or "").strip()
        text = (b.get("text") or "").strip()
        if not text:
            continue
        header = f"[KB {idx} | {src}]" if src else f"[KB {idx}]"
        lines.append(f"{header}\n{text}")
    return "\n\n".join(lines).strip()


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
        summary: Optional[str] = None,
        context_blocks: List[Dict[str, Any]] = None,
        intent_params: Optional[Dict[str, Any]] = None,
    ):
        global_sys = self.loader.load_global_system()
        app_sys = self.loader.load_app_system(app_id)
        intent_tpl = self.loader.load_intent(app_id, intent)

        primary_ctx, aux_ctx, kb_ctx = _group_contexts(context_blocks or [])

        # memory 文本拼装：summary 永远最上面
        memory_parts: List[str] = []
        if summary:
            memory_parts.append("【对话摘要】")
            memory_parts.append(summary.strip())
            memory_parts.append("")

        primary_text = _format_primary_turns(primary_ctx)
        if primary_text:
            memory_parts.append(primary_text)
            memory_parts.append("")

        aux_text = _format_aux_memory(aux_ctx)
        if aux_text:
            memory_parts.append(aux_text)

        memory_text = "\n".join([p for p in memory_parts if p is not None]).strip()
        kb_text = _format_kb_context(kb_ctx)

        render_params: Dict[str, Any] = {
            "query": user_query,
            "memory": memory_text,
            "context": kb_text,
            "wallet_id": getattr(identity, "wallet_id", ""),
            "app_id": getattr(identity, "app_id", app_id),
            "session_id": getattr(identity, "session_id", ""),
        }

        if intent_params:
            render_params.update(intent_params)

        user_prompt = render_template(intent_tpl, render_params)

        return assemble_messages(
            global_system=global_sys,
            app_system=app_sys,
            user_prompt=user_prompt,
        )
