"""
DeepSeek Chat API Server
使用FastAPI框架提供对话接口
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator, Field
from openai import OpenAI
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepSeek Chat API",
    description="调用DeepSeek API进行对话生成的接口服务",
    version="1.0.0"
)

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
if not DEEPSEEK_KEY:
    raise EnvironmentError("环境变量 DEEPSEEK_KEY 未设置，请在运行前设置该环境变量")

class ChatRequest(BaseModel):
    """聊天请求模型"""
    msg: str = Field(..., min_length=1, description="用户输入的消息")

    @field_validator("msg")
    @classmethod
    def validate_msg(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息内容不能为空")
        return v.strip()

class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str

class ToolCallResponse(BaseModel):
    """工具调用响应模型"""
    response: str
    tool_calls: list = Field(default_factory=list, description="工具调用记录")

def get_deepseek_client() -> OpenAI:
    """
    创建DeepSeek API客户端
    """
    return OpenAI(
        api_key=DEEPSEEK_KEY,
        base_url="https://api.siliconflow.cn/v1"
    )

def get_weather(city: str) -> str:
    """
    获取城市天气信息

    Args:
        city: 城市名称

    Returns:
        str: 天气信息字符串
    """
    logger.info(f"调用工具: get_weather, 参数: city={city}")

    weather_map = {
        "北京": "北京晴25度",
        "上海": "上海阴22度",
        "深圳": "深圳多云28度"
    }

    result = weather_map.get(city, f"{city}的天气数据暂不可用")
    logger.info(f"工具返回: {result}")
    return result

def get_time() -> str:
    """
    获取当前系统时间

    Returns:
        str: 格式化的时间字符串
    """
    logger.info("调用工具: get_time (无参数)")
    result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"工具返回: {result}")
    return result

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气，返回字符串",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前系统时间",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "get_time": get_time
}

def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    执行工具调用

    Args:
        tool_name: 工具名称
        tool_args: 工具参数字典

    Returns:
        str: 工具执行结果

    Raises:
        ValueError: 工具不存在或参数错误
    """
    logger.info(f"执行工具: {tool_name}, 参数: {tool_args}")

    if tool_name not in TOOL_FUNCTIONS:
        error_msg = f"未知工具: {tool_name}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        func = TOOL_FUNCTIONS[tool_name]
        if tool_name == "get_weather":
            return func(tool_args.get("city", ""))
        elif tool_name == "get_time":
            return func()
    except Exception as e:
        error_msg = f"工具执行失败: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def read_knowledge_file(filepath: str = "knowledge.txt") -> str:
    """
    读取知识库文件内容
    """
    if not os.path.exists(filepath):
        logger.error(f"知识库文件不存在: {filepath}")
        raise FileNotFoundError(f"知识库文件不存在: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"成功读取知识库文件，共 {len(content)} 个字符")
        return content
    except Exception as e:
        logger.error(f"读取知识库文件失败: {str(e)}")
        raise IOError(f"读取知识库文件失败: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    处理用户对话请求
    """
    try:
        logger.info(f"收到消息: {request.msg}")

        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "user", "content": request.msg}
            ]
        )

        ai_response = response.choices[0].message.content.strip()
        logger.info(f"AI回复: {ai_response}")

        return ChatResponse(response=ai_response)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"API调用失败: {error_msg}")

        if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
            raise HTTPException(status_code=402, detail="API余额不足，请前往平台充值")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail="网络连接失败，请检查网络后重试")
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            raise HTTPException(status_code=401, detail="API密钥无效")
        else:
            raise HTTPException(status_code=500, detail=f"发生错误: {error_msg}")

@app.post("/chat_rag", response_model=ChatResponse)
def chat_rag(request: ChatRequest) -> ChatResponse:
    """
    基于知识库的对话接口
    """
    try:
        logger.info(f"收到RAG请求: {request.msg}")

        knowledge = read_knowledge_file("knowledge.txt")
        logger.info(f"知识库内容长度: {len(knowledge)} 字符")

        client = get_deepseek_client()

        system_prompt = f"""你是一个知识库助手，请严格按照以下规则回答：

知识库内容：
{knowledge}

规则：
1. 仅根据知识库内容回答用户问题，禁止编造任何信息
2. 如果知识库中没有相关信息，**必须只回复：我暂时不了解这个**
3. 禁止添加任何额外解释、礼貌用语，只返回最终结果
"""

        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.msg}
            ]
        )

        ai_response = response.choices[0].message.content.strip()
        logger.info(f"RAG AI回复: {ai_response}")

        return ChatResponse(response=ai_response)

    except FileNotFoundError as e:
        logger.error(f"知识库文件不存在: {str(e)}")
        raise HTTPException(status_code=404, detail=f"知识库文件不存在，请创建knowledge.txt文件")
    except IOError as e:
        logger.error(f"读取知识库文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="读取知识库文件失败")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"RAG API调用失败: {error_msg}")

        if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
            raise HTTPException(status_code=402, detail="API余额不足，请前往平台充值")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail="网络连接失败，请检查网络后重试")
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            raise HTTPException(status_code=401, detail="API密钥无效")
        else:
            raise HTTPException(status_code=500, detail=f"发生错误: {error_msg}")

@app.post("/chat_agent", response_model=ToolCallResponse)
def chat_agent(request: ChatRequest) -> ToolCallResponse:
    """
    智能助手接口，支持工具调用

    支持以下工具：
    - get_weather(city): 查询指定城市的天气，返回字符串
    - get_time(): 获取当前系统时间

    当用户询问天气或时间时，AI会自动调用相应工具。
    """
    try:
        import json

        logger.info(f"收到Agent请求: {request.msg}")

        client = get_deepseek_client()

        system_prompt = """你是一个智能助手，擅长根据用户需求判断是否需要调用工具。

可用工具：
1. get_weather(city): 查询指定城市的天气，返回字符串
2. get_time(): 获取当前系统时间

规则：
1. 当用户询问天气时，调用 get_weather 工具
2. 当用户询问时间时，调用 get_time 工具
3. 如果不需要调用工具，直接回答用户问题
4. 收到工具返回结果后，将结果自然地融入回答中
5. 回答要简洁、友好、符合中文表达习惯
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.msg}
        ]

        tool_calls_log = []

        while True:
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            logger.info(f"AI响应类型: {'工具调用' if assistant_message.tool_calls else '直接回答'}")

            if assistant_message.tool_calls:
                logger.info(f"检测到工具调用，共 {len(assistant_message.tool_calls)} 个")

                tool_results = []

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                    except (json.JSONDecodeError, TypeError):
                        tool_args = {}
                    if tool_args is None:
                        tool_args = {}

                    logger.info(f"执行工具: {tool_name}, 参数: {tool_args}")
                    tool_calls_log.append({
                        "tool": tool_name,
                        "arguments": tool_args
                    })

                    try:
                        tool_result = execute_tool(tool_name, tool_args)
                        logger.info(f"工具执行成功: {tool_result}")
                        tool_calls_log[-1]["result"] = tool_result
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": tool_result
                        })
                    except Exception as e:
                        error_result = f"工具执行失败: {str(e)}"
                        logger.error(error_result)
                        tool_calls_log[-1]["result"] = error_result
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": error_result
                        })

                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [tc.model_dump() for tc in assistant_message.tool_calls]
                })

                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"]
                    })

            else:
                content = assistant_message.content.strip() if assistant_message.content else "无法生成回复"
                logger.info(f"无需工具调用，直接回复: {content}")
                return ToolCallResponse(
                    response=content,
                    tool_calls=tool_calls_log
                )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Agent API调用失败: {error_msg}")

        if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
            raise HTTPException(status_code=402, detail="API余额不足，请前往平台充值")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail="网络连接失败，请检查网络后重试")
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            raise HTTPException(status_code=401, detail="API密钥无效")
        else:
            raise HTTPException(status_code=500, detail=f"发生错误: {error_msg}")

@app.get("/")
def root():
    """根路径欢迎信息"""
    return {"message": "欢迎使用DeepSeek Chat API服务", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
