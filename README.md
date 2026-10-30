# 江西短途旅行规划助手

面向江西省内 1～5 天短途旅行的规划应用。用户输入出发地、江西目的地、日期、天数、预算和偏好后，系统会组合真实 POI、路线估算、本地攻略引用、预算与可行性校验，生成逐日行程。

本项目基于 MIT 许可的开源项目
[`moumouw89-cmyk/trip-planner-agent`](https://github.com/moumouw89-cmyk/trip-planner-agent)
进行二次开发，保留其原有 `LICENSE` 和版权声明。

## 范围

- 目的地和行程 POI 仅限江西省内。
- 出发地可以在江西省外。
- 当前内置南昌、九江、景德镇、上饶的本地演示数据和攻略。
- 其他江西地级市可在配置高德 Key 后按需获取真实 POI。
- 江西省外目的地会被拒绝。

## 已实现能力

- Streamlit 表单和自然语言输入。
- DeepSeek、Qwen、GLM 及 OpenAI-compatible 多模型切换。
- 高德 POI、酒店、餐厅、天气和驾车路线适配。
- 本地攻略检索与来源引用。
- 预算拆分、活动数量、通勤、重复地点、闭馆日等规则校验。
- 预算利用策略：在不超支的前提下，优先升级住宿、餐饮和体验，目标使用总预算的 90%～98%。
- 支持出行人数输入，餐饮、门票和房型数量会随人数调整。
- 自动修复超预算或活动过多的问题。
- 无 API Key 时的本地演示降级。
- SQLite 行程保存、历史版本、Markdown / ICS 导出。
- Pytest 自动测试。

## 本地运行

建议 Python 3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run app.py
```

没有配置任何模型 Key 时，系统仍可使用本地规则和演示数据跑通；没有高德 Key 时会显示 Mock/本地数据标记。

Windows 下也可以直接双击项目根目录的 `启动.bat`。不要使用
`python app.py` 启动，`app.py` 必须由 Streamlit 运行时启动。

## 模型配置

项目使用 OpenAI-compatible 配置：

```env
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

通义千问示例：

```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

智谱示例：

```env
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4-flash
```

高德地图需要 Web 服务 Key：

```env
AMAP_API_KEY=your-amap-web-service-key
```

不要把真实密钥写入代码或提交到 GitHub。

## Streamlit Community Cloud

1. 将项目推送到公开 GitHub 仓库。
2. 在 Streamlit Community Cloud 选择仓库和 `app.py`。
3. 在 Advanced settings 的 Secrets 中配置：

```toml
OPENAI_API_KEY = "..."
OPENAI_BASE_URL = "https://api.deepseek.com/v1"
OPENAI_MODEL = "deepseek-chat"
AMAP_API_KEY = "..."
PUBLIC_DEMO_MODE = "true"
```

4. 部署后获得 `*.streamlit.app` 公共地址。

`PUBLIC_DEMO_MODE=true` 会隐藏后台配置入口，避免访客修改服务端模型配置。Streamlit Community Cloud 的本地文件系统不是永久数据库。公开演示时应使用内置数据重建机制，并限制模型调用额度。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 当前阶段边界

当前版本复用上游的 SQLite FTS5 + BM25 本地攻略检索。后续阶段可增加小型 ChromaDB 并形成 BM25 + 向量混合检索，不影响现有行程生成和范围校验。
