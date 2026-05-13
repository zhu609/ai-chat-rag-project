# DeepSeek Chat API Server

基于 FastAPI 框架开发的 DeepSeek AI 对话接口服务。

## 功能特性

- `/chat` - 基础对话接口
- `/chat_rag` - 知识库增强对话接口
- `/chat_agent` - 智能助手接口（支持工具调用）

## 环境要求

- Python 3.10+
- FastAPI
- OpenAI Python SDK

## 安装依赖

```bash
pip install fastapi uvicorn openai python-dotenv
```

## 环境变量配置

在运行前必须设置 `DEEPSEEK_KEY` 环境变量：

### Linux / macOS

```bash
export DEEPSEEK_KEY="your-api-key-here"
```

### Windows PowerShell

```powershell
$env:DEEPSEEK_KEY="your-api-key-here"
```

### 或创建 .env 文件

```bash
echo DEEPSEEK_KEY=your-api-key-here > .env
```

## 启动服务

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动后访问 http://localhost:8000/docs 查看交互式 API 文档。

## 接口说明

### POST /chat
基础对话接口

**请求体**：
```json
{"msg": "你的问题"}
```

**响应**：
```json
{"response": "AI回复内容"}
```

### POST /chat_rag
基于知识库的对话接口

**请求体**：
```json
{"msg": "你的问题"}
```

**响应**：
```json
{"response": "基于知识库的回答或'我暂时不了解这个'"}
```

### POST /chat_agent
智能助手接口，支持工具调用

**请求体**：
```json
{"msg": "你的问题"}
```

**响应**：
```json
{"response": "AI回复内容", "tool_calls": []}
```

## 错误处理

- **401** - API密钥无效或未设置
- **402** - API余额不足
- **404** - 知识库文件不存在
- **500** - 服务器内部错误
- **503** - 网络连接失败
