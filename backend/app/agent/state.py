from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TravelPlannerState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    slots: dict
    travel_plan: dict | None
    intermediate_steps: list[str]
