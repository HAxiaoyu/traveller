from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI


def create_chat_model(
    provider: str, model_name: str, api_key: str, base_url: str = ""
) -> BaseChatModel:
    if not api_key:
        raise ValueError("API Key 未配置，请在设置中填入有效的 API Key。")

    if provider == "anthropic":
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0.3)
    if provider == "openai":
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.3)
    if provider == "zhipu":
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            temperature=0.3,
        )
    if provider == "custom":
        if not base_url:
            raise ValueError("自定义提供商需要填写 Base URL。")
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
        )

    raise ValueError(f"不支持的模型提供商: {provider}，当前支持 openai / anthropic / zhipu / custom")
