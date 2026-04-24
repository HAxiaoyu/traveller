## 11. 开发组件依赖与版本规范

为保证 MVP 快速落地且后续可维护，必须锁定核心依赖版本，并遵循现行主流实践。

### 11.1 后端依赖（Python）

**运行环境**：Python ≥ 3.11  
**包管理器**：推荐使用 `pip-tools` 或 `pipenv` 生成 lock 文件，以下依赖写入 `requirements.in` 或 `pyproject.toml`。

#### 核心框架与 API
| 库                  | 版本            | 说明                                         |
| ------------------- | --------------- | -------------------------------------------- |
| `fastapi`           | **≥0.115.0**    | 支持最新 Pydantic V2 集成                    |
| `uvicorn[standard]` | ≥0.30.0         | ASGI 服务器                                  |
| `pydantic`          | **≥2.5.0,<3.0** | V2 版本，使用 `model_validate`、`model_dump` |
| `pydantic-settings` | ≥2.0            | 环境变量管理（可选）                         |

#### Agent 与 LLM
| 库                    | 版本       | 说明                  |
| --------------------- | ---------- | --------------------- |
| `langgraph`           | **≥0.2.0** | 状态图 Agent 框架     |
| `langchain`           | **≥0.3.0** | LLM 抽象与工具调用    |
| `langchain-openai`    | ≥0.2.0     | OpenAI 兼容集成       |
| `langchain-anthropic` | ≥0.2.0     | Anthropic Claude 集成 |
| `langchain-community` | ≥0.3.0     | 可能用到的工具辅助    |

#### 数据持久化
| 库           | 版本        | 说明                                    |
| ------------ | ----------- | --------------------------------------- |
| `sqlalchemy` | **≥2.0.20** | 异步 ORM，使用 2.0 风格                 |
| `aiosqlite`  | ≥0.19.0     | SQLite 异步驱动                         |
| `alembic`    | ≥1.13.0     | 数据库迁移（可选，MVP 用 `create_all`） |

#### 异步 HTTP 与外部 API 调用
| 库         | 版本    | 说明                                 |
| ---------- | ------- | ------------------------------------ |
| `httpx`    | ≥0.27.0 | 异步 HTTP 客户端，调用地图、天气 API |
| `tenacity` | ≥8.0    | 外部 API 重试机制                    |

#### 开发工具
| 库               | 版本    | 说明         |
| ---------------- | ------- | ------------ |
| `pytest`         | ≥8.0    | 测试框架     |
| `pytest-asyncio` | ≥0.24.0 | 异步测试支持 |

> **重要版本要求说明**：
> - **Pydantic V2**：所有模型定义使用 `from pydantic import BaseModel`，字段定义使用新风格（`name: str = Field(...)`），避免 V1 的 `class Config`。  
> - **SQLAlchemy 2.0+**：模型声明使用 `mapped_column()`，而非旧式 `Column()`。会话创建使用 `async_sessionmaker`。  
> - **FastAPI**：依赖注入直接使用 `async def`，利用 Pydantic V2 的 `model_validator` 做请求体验证。

#### 后端 `requirements.in` 示例
```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.5.0,<3.0
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
langchain-community>=0.3.0
sqlalchemy>=2.0.20
aiosqlite>=0.19.0
httpx>=0.27.0
tenacity>=8.0
```

### 11.2 前端依赖（Node.js）

**运行环境**：Node.js ≥ 20 LTS  
**包管理器**：`pnpm`（推荐）或 `npm`，以 `package.json` 锁定版本。

#### 核心框架与构建
| 库           | 版本        | 说明                 |
| ------------ | ----------- | -------------------- |
| `react`      | **^18.3.0** | 使用函数组件 + Hooks |
| `react-dom`  | ^18.3.0     |                      |
| `vite`       | ^5.4.0      | 构建工具             |
| `typescript` | ^5.5.0      | 类型安全             |

#### UI 与样式
| 库                         | 版本     | 说明                                 |
| -------------------------- | -------- | ------------------------------------ |
| `tailwindcss`              | ^3.4.0   | 原子化 CSS                           |
| `postcss`                  | ^8.4.0   |                                      |
| `autoprefixer`             | ^10.4.0  |                                      |
| `@shadcn/ui`               | latest   | 基于 Radix UI + Tailwind，按组件添加 |
| `lucide-react`             | ^0.400.0 | 图标库（shadcn 默认）                |
| `class-variance-authority` | ^0.7.0   | 组件变体管理                         |
| `clsx`                     | ^2.1.0   | 类名合并                             |
| `tailwind-merge`           | ^2.5.0   | 类名去重                             |

#### 地图与交互
| 库                         | 版本    | 说明                   |
| -------------------------- | ------- | ---------------------- |
| `@react-google-maps/api`   | ^2.19.0 | React 封装 Google Maps |
| `react-markdown`           | ^9.0.0  | 渲染 Markdown 消息     |
| `react-syntax-highlighter` | ^15.5.0 | 代码高亮（可选）       |

#### 网络与状态
| 库                      | 版本    | 说明               |
| ----------------------- | ------- | ------------------ |
| `event-source-polyfill` | ^1.0.31 | SSE 兼容性（可选） |
| `uuid`                  | ^10.0.0 | 生成客户端会话 ID  |

> **前端约束**：
> - 地图 API Key 由用户配置，存储在 `localStorage`，前端通过环境变量 `.env` 提供默认空值或占位。
> - 严格避免在客户端调用 LLM 端点；所有 LLM 请求必须经过后端代理。
> - 使用 `@react-google-maps/api` 的 `useJsApiLoader` 异步加载 Google Maps，避免阻塞。

#### 前端 `package.json` 示例（关键依赖）
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@react-google-maps/api": "^2.19.0",
    "react-markdown": "^9.0.0",
    "uuid": "^10.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

### 11.3 代码规范细节

#### SQLAlchemy 模型定义示范
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages: Mapped[dict] = mapped_column(JSON, default=list)
    slots: Mapped[dict] = mapped_column(JSON, default=dict)
    travel_plan: Mapped[dict] = mapped_column(JSON, nullable=True)
```

#### Pydantic V2 模型示例
```python
from pydantic import BaseModel, Field
from typing import Optional

class UserPreferences(BaseModel):
    destination: str = Field(..., description="主要目的地")
    days: int = Field(ge=1, le=30)
    interests: list[str] = Field(default_factory=list, description="兴趣标签列表")
    energy_level: Optional[str] = Field(default="medium", pattern="^(low|medium|high)$")
```

#### LangGraph 状态定义
```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class TravelPlannerState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    slots: dict
    travel_plan: dict
    intermediate_steps: list
```

### 11.4 外部 API 版本与配额

| API                            | 使用库/端点                                                  | 版本/注意事项                                                |
| ------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **Google Maps JavaScript API** | 前端 `@react-google-maps/api` 加载                           | 需启用 Maps JavaScript API、Geocoding API；设置 HTTP 引用限制 |
| **Google Geocoding API**       | 后端通过 `httpx` 调用 `https://maps.googleapis.com/maps/api/geocode/json` | 与上同一 Key，日配额有限，MVP 仅补全坐标                     |
| **OpenWeatherMap**             | 后端通过 `httpx` 调用 `https://api.openweathermap.org/data/3.0/onecall/day_summary` | 使用 One Call API 3.0（免费订阅下最多7天预报），需单独注册 Key |

> **安全约定**：所有后端用到的外部 API Key 由前端传递或配置在服务器环境变量，**绝不硬编码**在源码中。

---

**文档补充说明**：  
以上依赖清单和版本要求已确保各组件兼容性（例如 FastAPI 0.115+ 完全适配 Pydantic V2，SQLAlchemy 2.0+ 支持 `mapped_column`），可直接用于项目初始化。若在实际开发中遇到版本冲突，可优先参考本规范进行调整。