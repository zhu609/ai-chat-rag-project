from openai import OpenAI

client = OpenAI(
    api_key="sk-148aac430ead4e7bb1b627a252855430",
    base_url="https://api.deepseek.com/v1"
)

def get_encouragement(mood: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个温暖贴心的朋友，擅长用真诚友善的语言鼓励他人。当用户向你描述他们的心情时，你要生成一段贴合他们情绪的鼓励话语。要求：1）语言自然流畅，符合中文表达习惯；2）情感真挚，让人感到被理解；3）积极正面，给人希望和力量；4）长度适中，控制在50字以内。"},
                {"role": "user", "content": f"我的心情是：{mood}"}
            ],
            max_tokens=200,
            temperature=0.8
        )
        encouragement = response.choices[0].message.content.strip()
        return {"success": True, "encouragement": encouragement}
    except Exception as e:
        error_msg = str(e)
        if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
            return {"success": False, "error": "API余额不足，请前往DeepSeek平台充值"}
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return {"success": False, "error": "网络连接失败，请检查网络后重试"}
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            return {"success": False, "error": "API密钥无效，请检查配置"}
        else:
            return {"success": False, "error": f"发生错误：{error_msg}"}

if __name__ == "__main__":
    mood = input("请描述一下你此刻的心情：")
    result = get_encouragement(mood)
    if result["success"]:
        print("\n💚 鼓励话语：")
        print(result["encouragement"])
    else:
        print(f"\n❌ {result['error']}")
