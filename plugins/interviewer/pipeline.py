from typing import Dict, Any, List

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
class InterviewerPipeline:
    """
    面试官业务 pipeline
    orchestrator 由 query router 在运行时注入
    """

    def __init__(self):
        self.orchestrator = None  # 运行时注入

    def run(self, *, identity, intent, user_query, intent_params):
        if self.orchestrator is None:
            raise RuntimeError("Orchestrator not injected into pipeline")

        if intent != "generate_questions":
            raise ValueError(f"Unsupported intent: {intent}")

        # pipeline 内部策略（不是用户输入）
        basic_count = 3
        project_count = 3
        scenario_count = 3

        questions = []

        # 基础题
        res = self.orchestrator.run(
            identity=identity,
            intent="basic_questions",
            user_query=user_query,
            intent_params={
                "basic_count": basic_count,
            },
        )
        basic_questions = res.get("questions", [])
        questions.extend(basic_questions)

        # 项目题
        res = self.orchestrator.run(
            identity=identity,
            intent="project_questions",
            user_query=user_query,
            intent_params={
                "project_count": project_count,
                "previous_basic": basic_questions,
            },
        )
        project_questions = res.get("questions", [])
        questions.extend(project_questions)

        # 场景题
        res = self.orchestrator.run(
            identity=identity,
            intent="scenario_questions",
            user_query=user_query,
            intent_params={
                "scenario_count": scenario_count,
                "previous_all": questions,
            },
        )
        questions.extend(res.get("questions", []))

        return {
            "questions": questions,
            "meta": {
                "basic_count": len(basic_questions),
                "project_count": len(project_questions),
                "scenario_count": scenario_count,
            },
        }
