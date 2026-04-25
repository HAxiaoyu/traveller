from app.agent.state import TravelPlannerState

REQUIRED_SLOTS = ("destination", "days", "interests", "travel_dates")


async def check_slots(state: TravelPlannerState) -> dict:
    slots: dict = state.get("slots", {})
    steps: list[str] = list(state.get("intermediate_steps", []))

    missing: list[str] = [s for s in REQUIRED_SLOTS if s not in slots or not slots[s]]
    all_filled: bool = len(missing) == 0

    if all_filled:
        if "energy_level" not in slots:
            slots = {**slots, "energy_level": "适中"}
        steps.append("intent_analysis: 所有必填槽位已填充，进入行程规划")
        return {"slots": slots, "slots_filled": True, "intermediate_steps": steps}

    steps.append(
        f"intent_analysis: 槽位不完整，缺失 {', '.join(missing)}，生成追问"
    )
    return {"slots_filled": False, "intermediate_steps": steps, "missing_slots": missing}
