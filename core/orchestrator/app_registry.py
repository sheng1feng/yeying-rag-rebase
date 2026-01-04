# core/orchestrator/app_register.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass(frozen=True)
class IntentSpec:
    name: str
    description: str = ""
    params: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AppSpec:
    app_id: str
    plugin_dir: Path
    config: Dict[str, Any]
    intents: Dict[str, IntentSpec]


class AppRegistry:
    """
    App 插件注册表：负责发现/校验/加载 plugins/<app_id> 目录中的声明文件。

    - 只做“插件元信息”管理：config.yaml、intents.yaml、prompts存在性、pipeline.py存在性
    - 不做：LLM/KB/Memory 逻辑
    - 不做：真正实例化 pipeline（那是 PipelineRegistry 的职责）
    """

    def __init__(self, project_root: str, plugins_dirname: str = "plugins") -> None:
        self.project_root = Path(project_root)
        self.plugins_root = self.project_root / plugins_dirname
        self._apps: Dict[str, AppSpec] = {}

    # ------------------------------------------------------------
    # 外部入口：注册一个 app
    # ------------------------------------------------------------
    def register_app(self, app_id: str) -> AppSpec:
        if not app_id:
            raise ValueError("app_id 不能为空")

        if app_id in self._apps:
            return self._apps[app_id]

        plugin_dir = self.plugins_root / app_id
        if not plugin_dir.exists():
            raise FileNotFoundError(f"插件目录不存在: {plugin_dir}")

        config = self._load_yaml(plugin_dir / "config.yaml")
        intents_raw = self._load_yaml(plugin_dir / "intents.yaml")

        self._validate_config(app_id, config)
        intents = self._parse_intents(intents_raw)

        # prompts 目录检查（至少 system.md 存在；intent 的 md 可以按需缺省，但建议严格校验）
        prompts_dir = plugin_dir / "prompts"
        if not prompts_dir.exists():
            raise FileNotFoundError(f"prompts 目录不存在: {prompts_dir}")

        system_md = prompts_dir / "system.md"
        if not system_md.exists():
            raise FileNotFoundError(f"缺少 prompts/system.md: {system_md}")

        # pipeline.py 可选（某些业务可用默认 pipeline），但面试官通常需要
        # 这里不强制；由 PipelineRegistry 决定无 pipeline.py 时的 fallback 策略
        app_spec = AppSpec(
            app_id=app_id,
            plugin_dir=plugin_dir,
            config=config,
            intents=intents,
        )
        self._apps[app_id] = app_spec
        return app_spec

    def get(self, app_id: str) -> AppSpec:
        if app_id not in self._apps:
            raise KeyError(f"app_id 尚未注册: {app_id}")
        return self._apps[app_id]

    def is_registered(self, app_id: str) -> bool:
        return app_id in self._apps

    def list_apps(self) -> List[str]:
        return sorted(self._apps.keys())

    # ------------------------------------------------------------
    # 内部：yaml / 校验 / intent 解析
    # ------------------------------------------------------------
    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"缺少文件: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML 必须为 dict: {path}")
        return data

    @staticmethod
    def _validate_config(app_id: str, config: Dict[str, Any]) -> None:
        # 最小校验：app_id 匹配，enabled 可选
        cfg_app_id = (config.get("app_id") or "").strip()
        if cfg_app_id and cfg_app_id != app_id:
            raise ValueError(f"config.yaml 中 app_id={cfg_app_id} 与目录 app_id={app_id} 不一致")

        enabled = config.get("enabled", True)
        if enabled not in (True, False):
            raise ValueError("config.yaml enabled 必须为 bool")

        # memory / knowledge_bases 可选，但若存在必须是 dict
        if "memory" in config and not isinstance(config["memory"], dict):
            raise ValueError("config.yaml memory 必须为 dict")
        if "knowledge_bases" in config and not isinstance(config["knowledge_bases"], dict):
            raise ValueError("config.yaml knowledge_bases 必须为 dict")

    @staticmethod
    def _parse_intents(intents_raw: Dict[str, Any]) -> Dict[str, IntentSpec]:
        # 支持格式：
        # intents:
        #   ask_question:
        #     description: ...
        #     params: [...]
        intents_block = intents_raw.get("intents") or {}
        if not isinstance(intents_block, dict):
            raise ValueError("intents.yaml 必须包含 intents: dict")

        intents: Dict[str, IntentSpec] = {}
        for name, meta in intents_block.items():
            if not isinstance(name, str) or not name.strip():
                continue
            meta = meta or {}
            if not isinstance(meta, dict):
                meta = {}

            desc = str(meta.get("description", "") or "")
            params = meta.get("params", []) or []
            if not isinstance(params, list):
                raise ValueError(f"intent={name} 的 params 必须为 list")

            params_norm = tuple(str(p) for p in params if str(p).strip())
            intents[name] = IntentSpec(name=name, description=desc, params=params_norm)

        if not intents:
            raise ValueError("intents.yaml 中 intents 不能为空")

        return intents
