from langgraph.graph import END, StateGraph

from app.agent.state import TravelPlannerState


async def intent_analysis(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append("intent_analysis: 正在分析您的偏好...")
    return {"intermediate_steps": steps}


async def plan_generation(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append("plan_generation: 正在生成行程方案...")
    return {"intermediate_steps": steps}


async def enrichment(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append("enrichment: 正在补充坐标和天气信息...")
    return {"intermediate_steps": steps}


async def format_response(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append("format_response: 正在整理回复...")
    return {"intermediate_steps": steps}


def build_agent_graph() -> StateGraph:
    workflow = StateGraph(TravelPlannerState)

    workflow.add_node("intent_analysis", intent_analysis)
    workflow.add_node("plan_generation", plan_generation)
    workflow.add_node("enrichment", enrichment)
    workflow.add_node("format_response", format_response)

    workflow.set_entry_point("intent_analysis")
    workflow.add_edge("intent_analysis", "plan_generation")
    workflow.add_edge("plan_generation", "enrichment")
    workflow.add_edge("enrichment", "format_response")
    workflow.add_edge("format_response", END)

    return workflow.compile()
