from typing import Optional

from pydantic import BaseModel, Field


class Transport(BaseModel):
    mode: str = Field(default="公共交通", description="交通方式")
    duration: str = Field(default="约30分钟", description="预估耗时")


class Activity(BaseModel):
    name: str = Field(..., description="景点或活动名称")
    type: str = Field(default="景点", description="类型：景点/美食/购物/户外/其他")
    lat: Optional[float] = Field(default=None, description="纬度，可留空后续补全")
    lng: Optional[float] = Field(default=None, description="经度，可留空后续补全")
    duration: str = Field(default="1h", description="建议游玩时长")
    time: str = Field(default="09:00", description="建议开始时间")
    notes: str = Field(default="", description="备注提示")


class DayPlan(BaseModel):
    day: int = Field(..., ge=1, description="第几天")
    city: str = Field(..., description="当天所在城市")
    theme: str = Field(default="", description="当天主题")
    activities: list[Activity] = Field(..., min_length=1, description="当天活动列表")
    transport: Transport = Field(default_factory=Transport, description="当天主要交通")
    hotel: str = Field(default="当地推荐酒店", description="住宿建议")


class TravelPlan(BaseModel):
    title: str = Field(..., description="行程标题")
    days: list[DayPlan] = Field(..., min_length=1, description="每日行程")
