from langgraph.graph import END, StateGraph

from app.agent.enrichment import enrich as enrichment
from app.agent.intent_analysis import build_intent_analysis_subgraph
from app.agent.plan_generation import generate_plan as plan_generation
from app.agent.state import TravelPlannerState


async def format_response(state: TravelPlannerState) -> dict:
    steps: list[str] = list(state.get("intermediate_steps", []))
    travel_plan: dict | None = state.get("travel_plan")

    if travel_plan is None or not travel_plan.get("days"):
        steps.append("format_response: 无行程数据，跳过格式化")
        return {"intermediate_steps": steps, "formatted_response": ""}

    steps.append("format_response: 正在整理回复...")
    try:
        formatted = _build_markdown(travel_plan)
    except Exception:
        title = travel_plan.get("title", "行程")
        day_count = len(travel_plan.get("days", []))
        formatted = f"## {title}\n\n已为您规划 {day_count} 天行程，请在详情中查看。"
    return {
        "intermediate_steps": steps,
        "formatted_response": formatted,
    }


def _build_markdown(plan: dict) -> str:
    title: str = plan.get("title", "旅行计划")
    lines: list[str] = [f"## {title}", ""]

    for day in plan.get("days", []):
        if not isinstance(day, dict):
            continue
        day_num: int = day.get("day", 0)
        city: str = day.get("city", "")
        theme: str = day.get("theme", "")
        lines.append(f"### Day {day_num} — {city} · {theme}")
        lines.append("")

        activities: list = day.get("activities", [])
        if activities:
            lines.append("| 时间 | 活动 | 类型 | 时长 | 备注 |")
            lines.append("|------|------|------|------|------|")
            for act in activities:
                if not isinstance(act, dict):
                    continue
                name: str = act.get("name", "")
                act_type: str = act.get("type", "")
                duration: str = act.get("duration", "")
                time: str = act.get("time", "")
                notes: str = act.get("notes", "")
                lines.append(f"| {time} | {name} | {act_type} | {duration} | {notes} |")
            lines.append("")

        transport: dict | None = day.get("transport")
        if transport:
            mode: str = transport.get("mode", "")
            dur: str = transport.get("duration", "")
            lines.append(f"交通：{mode} · {dur}")
            lines.append("")

        hotel: str = day.get("hotel", "")
        if hotel:
            lines.append(f"酒店：{hotel}")
            lines.append("")

        weather: dict | None = day.get("weather")
        if weather:
            desc: str = weather.get("description", "")
            temp: int = weather.get("temp", 0)
            temp_min: int = weather.get("temp_min", 0)
            temp_max: int = weather.get("temp_max", 0)
            humidity: int = weather.get("humidity", 0)
            lines.append(f"天气：{desc} {temp}°C ({temp_min}°C ~ {temp_max}°C) 湿度{humidity}%")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


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
