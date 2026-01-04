# core/orchestrator/pipeline_registry.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Type

from .app_registry import AppRegistry, AppSpec


class BasePipeline:
    """
    可选：为 pipeline 约束一个最小接口
    """
    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator

    def run(self, *, identity, intent: str, user_query: str, intent_params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class PipelineEntry:
    app_id: str
    pipeline: Any
    pipeline_path: Optional[Path] = None


class PipelineRegistry:
    """
    Pipeline 注册表：
    - 负责把 plugins/<app_id>/pipeline.py 动态 import
    - 实例化 pipeline（注入 core orchestrator）
    """

    def __init__(self) -> None:
        self._pipelines: Dict[str, PipelineEntry] = {}

    def load_from_app_registry(self, app_registry: AppRegistry, orchestrator: Any) -> None:
        for app_id in app_registry.list_apps():
            spec = app_registry.get(app_id)
            self.register_pipeline(app_spec=spec, orchestrator=orchestrator)

    def register_pipeline(self, app_spec: AppSpec, orchestrator: Any) -> None:
        app_id = app_spec.app_id
        if app_id in self._pipelines:
            return

        pipeline_path = app_spec.plugin_dir / "pipeline.py"

        if pipeline_path.exists():
            pipeline_cls = self._load_pipeline_class(pipeline_path)
            pipeline_obj = pipeline_cls(orchestrator)
            self._pipelines[app_id] = PipelineEntry(app_id=app_id, pipeline=pipeline_obj, pipeline_path=pipeline_path)
        else:
            # fallback：没有 pipeline.py 时使用“默认直通 pipeline”
            pipeline_obj = _DefaultPassThroughPipeline(orchestrator)
            self._pipelines[app_id] = PipelineEntry(app_id=app_id, pipeline=pipeline_obj, pipeline_path=None)

    def get(self, app_id: str) -> Any:
        if app_id not in self._pipelines:
            raise KeyError(f"pipeline 未注册: {app_id}")
        return self._pipelines[app_id].pipeline

    def is_registered(self, app_id: str) -> bool:
        return app_id in self._pipelines

    # ------------------------------------------------------------
    # 动态 import：从 pipeline.py 获取 Pipeline 类
    # 约定：优先找 InterviewerPipeline / <AppId>Pipeline / Pipeline / default export 类
    # ------------------------------------------------------------
    @staticmethod
    def _load_pipeline_class(pipeline_path: Path) -> Type:
        module_name = f"plugin_pipeline_{pipeline_path.parent.name}"
        spec = importlib.util.spec_from_file_location(module_name, str(pipeline_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 pipeline 模块: {pipeline_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 优先级：InterviewerPipeline -> <AppId>Pipeline -> Pipeline
        candidates = [
            "InterviewerPipeline",
            f"{pipeline_path.parent.name.capitalize()}Pipeline",
            "Pipeline",
        ]
        for cls_name in candidates:
            if hasattr(module, cls_name):
                cls = getattr(module, cls_name)
                if isinstance(cls, type):
                    return cls

        # 最后兜底：找第一个 class 且有 run 方法
        for k, v in vars(module).items():
            if isinstance(v, type) and hasattr(v, "run"):
                return v

        raise ImportError(f"pipeline.py 中未找到可用 Pipeline 类: {pipeline_path}")


class _DefaultPassThroughPipeline(BasePipeline):
    """
    默认直通 pipeline：
    - 适用于“单次 orchestrator.run 即可完成”的简单业务
    - 业务不需要多步编排时可不提供 pipeline.py
    """
    def run(self, *, identity, intent: str, user_query: str, intent_params: Dict[str, Any]) -> Dict[str, Any]:
        return self.orchestrator.run(
            wallet_id=identity.wallet_id,
            app_id=identity.app_id,
            session_id=identity.session_id,
            intent=intent,
            user_query=user_query,
            intent_params=intent_params or {},
        )
