from langgraph.graph import END, StateGraph

from app.agent.intent_analysis.check_slots import check_slots
from app.agent.intent_analysis.extract_slots import extract_slots
from app.agent.intent_analysis.generate_question import generate_question
from app.agent.state import TravelPlannerState


def _route_after_check(state: TravelPlannerState) -> str:
    if state.get("slots_filled", False):
        return "end"
    return "generate_question"


def build_intent_analysis_subgraph() -> StateGraph:
    subgraph = StateGraph(TravelPlannerState)

    subgraph.add_node("extract_slots", extract_slots)
    subgraph.add_node("check_slots", check_slots)
    subgraph.add_node("generate_question", generate_question)

    subgraph.set_entry_point("extract_slots")
    subgraph.add_edge("extract_slots", "check_slots")
    subgraph.add_conditional_edges(
        "check_slots",
        _route_after_check,
        {"end": END, "generate_question": "generate_question"},
    )
    subgraph.add_edge("generate_question", END)

    return subgraph.compile()
