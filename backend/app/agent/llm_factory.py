from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI


def create_chat_model(provider: str, model_name: str, api_key: str) -> BaseChatModel:
    if provider == "anthropic":
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0.3)
    if provider == "openai":
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.3)

    raise ValueError(f"不支持的模型提供商: {provider}，当前支持 openai / anthropic")
