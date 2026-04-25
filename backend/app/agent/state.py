from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TravelPlannerState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    slots: dict
    travel_plan: dict | None
    intermediate_steps: list[str]
    model_provider: str
    model_name: str
    api_key: str
    base_url: str
    google_maps_key: str
    weather_api_key: str
    slots_filled: bool
    missing_slots: list[str]
    follow_up_question: str
    formatted_response: str
