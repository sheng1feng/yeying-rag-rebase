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
import json
import re
from typing import Any, Dict, Optional, List

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


def _try_json_obj(s: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _extract_json_obj(s: str) -> Optional[Dict[str, Any]]:
    """
    1) 直接 json.loads
    2) 抽取首个 {...} 子串再 json.loads（应对模型输出前后夹杂说明文字）
    """
    s = (s or "").strip()
    if not s:
        return None

    obj = _try_json_obj(s)
    if obj is not None:
        return obj

    m = _JSON_BLOCK_RE.search(s)
    if not m:
        return None
    return _try_json_obj(m.group(0).strip())


def _fallback_split_questions(s: str) -> List[str]:
    """
    JSON 失败时兜底：
    - 按行拆分
    - 去掉 1. / 1) / - / * / • 等前缀
    - 过滤空行
    """
    text = (s or "").strip()
    if not text:
        return []

    lines = [ln.strip().strip("`") for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    out: List[str] = []
    for ln in lines:
        ln2 = re.sub(r"^\s*(\d+[\.\)、)]\s*|[-*•]\s*)", "", ln).strip()
        if len(ln2) >= 4:
            out.append(ln2)

    # 极端情况仍为空：把全文按句号/分号拆一下
    if not out:
        chunks = re.split(r"[。；;\n]+", text)
        for c in chunks:
            c = c.strip()
            if len(c) >= 6:
                out.append(c)

    return out


def parse_questions_from_orchestrator_result(res: Any) -> List[str]:
    """
    允许 orchestrator 返回：
    - {"answer": {"questions":[...]}}  （结构化）
    - {"answer": {"content":"..."}}    （包装文本）
    - {"answer": "..." }              （纯文本）
    - 或者其它：尽力转成字符串解析
    最终保证返回 questions 非空（至少 1 条）。
    """
    # 1) res dict
    if isinstance(res, dict):
        ans = res.get("answer")

        # answer 已结构化
        if isinstance(ans, dict):
            if "questions" in ans:
                qs = _normalize_questions(ans.get("questions"))
                if qs:
                    return qs

            # 如果只有 content
            content = ans.get("content")
            if isinstance(content, str) and content.strip():
                return parse_questions_from_orchestrator_result({"answer": content})

        # answer 是字符串
        if isinstance(ans, str):
            raw = ans.strip()

            obj = _extract_json_obj(raw)
            if isinstance(obj, dict) and "questions" in obj:
                qs = _normalize_questions(obj.get("questions"))
                if qs:
                    return qs

            qs2 = _fallback_split_questions(raw)
            if qs2:
                return qs2

            return [raw] if raw else ["（模型未返回有效题目，请重试）"]

    # 2) 其它类型兜底
    raw2 = str(res).strip()
    if not raw2:
        return ["（模型未返回有效题目，请重试）"]
    return [raw2]


class InterviewerPipeline:
    """
    面试官 pipeline（轻量方案）
    - 对外只支持 generate_questions
    - 内部串 basic/project/scenario
    - 解析完全放在 pipeline 中（不增加中台复杂度）
    """

    def __init__(self, orchestrator = None):
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

        # 1) basic
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
        basic_qs = parse_questions_from_orchestrator_result(res_basic)
        # 尊重 count（如果模型返回多了，裁剪）
        if basic_count > 0:
            basic_qs = basic_qs[:basic_count]
        questions.extend(basic_qs)

        # 2) project
        res_proj = self.orchestrator.run_with_identity(
            identity=identity,
            intent="project_questions",
            user_query=user_query,
            intent_params={
                "project_count": project_count,
                "previous_basic": basic_qs,
                "target_position": target_position,
                "company": company,
            },
        )
        proj_qs = parse_questions_from_orchestrator_result(res_proj)
        if project_count > 0:
            proj_qs = proj_qs[:project_count]
        questions.extend(proj_qs)

        # 3) scenario
        res_scn = self.orchestrator.run_with_identity(
            identity=identity,
            intent="scenario_questions",
            user_query=user_query,
            intent_params={
                "scenario_count": scenario_count,
                "previous_all": questions,
                "target_position": target_position,
                "company": company,
            },
        )
        scn_qs = parse_questions_from_orchestrator_result(res_scn)
        if scenario_count > 0:
            scn_qs = scn_qs[:scenario_count]
        questions.extend(scn_qs)

        # 最终保证非空
        if not questions:
            questions = ["（未生成有效题目，请重试）"]

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