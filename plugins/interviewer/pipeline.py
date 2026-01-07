from __future__ import annotations

## 设置一个基类，Pipeline，P1

## 优先和永智对齐起来，部署到生产上去。 *P0.5*
## 知识库schema这些产品化提到P0，先至少可以查看数据，数据可视化。通过一个可视化可操作页面构建数据库，后续pipeline使用这些数据库。
## 用户给予数据schema，后续rag才能处理，界面

# 1.记忆能力。QA。
# 2.知识库管理。JD，用户上传的数据-用户上传JD，用户的简历。更好的查询和检索。知识库需要用户来输入（构建）。站在业务的层面想，如何构建好。
# 3.Chat，携带12的能力。


## 业务怎么和我进行数据交互
## 用户调我的push，我返回一个地址给业务，业务带着这个地址对我进行访问。
## file地址，应该是列表
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, List, Tuple

# 仅用于从模型输出中提取 JSON 对象（若模型偶尔仍输出额外文本）
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _as_int(v: Any, default: int) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _as_str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return str(v)


def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _normalize_questions(v: Any) -> List[str]:
    """
    只做非常轻量的规范化：保证 list[str]、strip、去空。
    不做复杂清洗，因为提示词要求“只输出严格 JSON”，
    解析层应当尽量简单，避免产生新的不确定性。
    """
    if not isinstance(v, list):
        return []
    out: List[str] = []
    for x in v:
        if x is None:
            continue
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _try_parse_questions_json(text: str) -> List[str]:
    """
    期望输入是严格 JSON：
      {"questions": ["...","..."]}
    但为防止偶发前后夹杂文本，这里支持：
      1) 直接 json.loads
      2) 抽取首个 {...} 再 json.loads
    """
    text = (text or "").strip()
    if not text:
        return []

    # 1) 直接 loads
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "questions" in obj:
            return _normalize_questions(obj.get("questions"))
    except Exception:
        pass

    # 2) 尝试提取 {...}
    m = _JSON_BLOCK_RE.search(text)
    if not m:
        return []

    try:
        obj2 = json.loads(m.group(0))
        if isinstance(obj2, dict) and "questions" in obj2:
            return _normalize_questions(obj2.get("questions"))
    except Exception:
        return []

    return []


def parse_questions_from_orchestrator_result(res: Any) -> List[str]:
    """
    Orchestrator 可能返回：
      - {"answer": {"questions": [...]}}                 # 结构化
      - {"answer": {"content": "...JSON..."}}            # 包装一层
      - {"answer": "...JSON..."}                         # 纯字符串
      - {"answer": "..."}                                # 极端：非 JSON（按你的提示词应当不会发生）
    解析策略：
      - 优先从结构化字段取 questions
      - 否则从字符串里解析 JSON（严格 JSON / 提取 JSON block）
      - 不再做“按行拆分兜底”，避免把噪声当作题目
    """
    if isinstance(res, dict):
        ans = res.get("answer")

        # 1) answer 是 dict：优先 questions，其次 content
        if isinstance(ans, dict):
            if "questions" in ans:
                qs = _normalize_questions(ans.get("questions"))
                return qs

            content = ans.get("content")
            if isinstance(content, str):
                return _try_parse_questions_json(content)

            return []

        # 2) answer 是 str：直接解析 JSON
        if isinstance(ans, str):
            return _try_parse_questions_json(ans)

        return []

    # 3) 其它类型：尽力转字符串再解析 JSON
    try:
        return _try_parse_questions_json(str(res))
    except Exception:
        return []


def _jsonify_for_prompt(v: Any) -> str:
    """
    模板里需要 previous_basic / previous_all：
    用 JSON 字符串传递，避免 Python list 的 repr 干扰模型。
    """
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return "[]"


class InterviewerPipeline:
    """
    面试官 pipeline（收敛版）
    - 对外只支持 generate_questions
    - 内部串 basic/project/scenario
    - 依赖提示词保证严格 JSON 输出，pipeline 仅做最小解析与计数裁剪
    """

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator  # 运行时注入

    def run(
        self,
        *,
        identity,
        intent: str,
        user_query: str,
        intent_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self.orchestrator is None:
            raise RuntimeError("Orchestrator not injected into pipeline")

        if intent != "generate_questions":
            raise ValueError(f"Unsupported intent: {intent}")

        p = _as_dict(intent_params)

        basic_count = _as_int(p.get("basic_count"), 3)
        project_count = _as_int(p.get("project_count"), 3)
        scenario_count = _as_int(p.get("scenario_count"), 3)

        target_position = _as_str(p.get("target_position"), "")
        company = _as_str(p.get("company"), "")

        if basic_count < 0 or project_count < 0 or scenario_count < 0:
            raise ValueError("basic_count/project_count/scenario_count must be >= 0")

        questions: List[str] = []

        # ---------- 1) basic ----------
        basic_qs: List[str] = []
        if basic_count > 0:
            res_basic = self.orchestrator.run_with_identity(
                identity=identity,
                intent="basic_questions",
                user_query=user_query,
                intent_params={
                    "basic_count": basic_count,
                    "target_position": target_position,
                    "company": company,
                },
            )
            basic_qs = parse_questions_from_orchestrator_result(res_basic)[:basic_count]
            questions.extend(basic_qs)

        # ---------- 2) project ----------
        proj_qs: List[str] = []
        if project_count > 0:
            res_proj = self.orchestrator.run_with_identity(
                identity=identity,
                intent="project_questions",
                user_query=user_query,
                intent_params={
                    "project_count": project_count,
                    # 模板里用于避免重复：强烈建议传 JSON 字符串
                    "previous_basic": _jsonify_for_prompt(basic_qs),
                    "target_position": target_position,
                    "company": company,
                },
            )
            proj_qs = parse_questions_from_orchestrator_result(res_proj)[:project_count]
            questions.extend(proj_qs)

        # ---------- 3) scenario ----------
        scn_qs: List[str] = []
        if scenario_count > 0:
            res_scn = self.orchestrator.run_with_identity(
                identity=identity,
                intent="scenario_questions",
                user_query=user_query,
                intent_params={
                    "scenario_count": scenario_count,
                    # 模板里用于避免重复：传“截至当前全部题”的 JSON 字符串
                    "previous_all": _jsonify_for_prompt(questions),
                    "target_position": target_position,
                    "company": company,
                },
            )
            scn_qs = parse_questions_from_orchestrator_result(res_scn)[:scenario_count]
            questions.extend(scn_qs)

        # ---------- 兜底 ----------
        if not questions:
            # 这里不再塞各种“解释性长文本”，只给一条明确可用的提示
            questions = ["（未生成有效题目：模型未按要求输出严格 JSON 或上下文为空）"]

        return {
            "questions": questions,
            "meta": {
                "basic_count": len(basic_qs),
                "project_count": len(proj_qs),
                "scenario_count": len(scn_qs),
                "target_position": target_position,
                "company": company,
            },
        }
