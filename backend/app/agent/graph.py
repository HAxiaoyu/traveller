from langgraph.graph import END, StateGraph

from app.agent.intent_analysis import build_intent_analysis_subgraph
from app.agent.plan_generation import generate_plan as plan_generation
from app.agent.state import TravelPlannerState


async def enrichment(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append("enrichment: 正在补充坐标和天气信息...")
    return {"intermediate_steps": steps}


async def format_response(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append("format_response: 正在整理回复...")
    return {"intermediate_steps": steps}


def _route_after_intent(state: TravelPlannerState) -> str:
    if state.get("slots_filled", False):
        return "plan_generation"
    return "end"


def build_agent_graph() -> StateGraph:
    workflow = StateGraph(TravelPlannerState)

    intent_subgraph = build_intent_analysis_subgraph()
    workflow.add_node("intent_analysis", intent_subgraph)
    workflow.add_node("plan_generation", plan_generation)
    workflow.add_node("enrichment", enrichment)
    workflow.add_node("format_response", format_response)

    workflow.set_entry_point("intent_analysis")
    workflow.add_conditional_edges(
        "intent_analysis",
        _route_after_intent,
        {
            "plan_generation": "plan_generation",
            "end": END,
        },
    )
    workflow.add_edge("plan_generation", "enrichment")
    workflow.add_edge("enrichment", "format_response")
    workflow.add_edge("format_response", END)

    return workflow.compile()
