"""
网页摘要API服务
使用FastAPI框架提供网页内容摘要功能
"""

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from openai import OpenAI
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="网页摘要API",
    description="获取网页内容并使用AI生成摘要",
    version="1.0.0"
)

class SummaryResponse(BaseModel):
    """网页摘要响应模型"""
    summary: str

def validate_api_key() -> str:
    """
    验证并获取API密钥
    
    Returns:
        str: API密钥
        
    Raises:
        HTTPException: 密钥未设置时抛出
    """
    api_key = os.getenv("DEEPSEEK_KEY")
    if not api_key:
        raise HTTPException(status_code=401, detail="API密钥未设置，请设置DEEPSEEK_KEY环境变量")
    return api_key

def is_valid_url(url: str) -> bool:
    """
    验证URL格式是否合法
    
    Args:
        url: 待验证的URL字符串
        
    Returns:
        bool: True表示合法，False表示不合法
    """
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def fetch_webpage_content(url: str) -> tuple[str, str]:
    """
    获取网页内容并提取标题和正文
    
    Args:
        url: 网页URL
        
    Returns:
        tuple: (标题, 正文内容)
        
    Raises:
        Exception: 抓取失败时抛出
    """
    if not is_valid_url(url):
        raise ValueError("无效的URL格式")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    try:
        logger.info(f"开始请求网页: {url}")
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        logger.info("网页请求成功")
    except requests.exceptions.Timeout:
        logger.error("请求超时")
        raise TimeoutError("请求超时（30秒）")
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到服务器")
        raise ConnectionError("无法连接到目标服务器")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP错误: {str(e)}")
        raise RuntimeError(f"HTTP错误: {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求失败: {str(e)}")
        raise RuntimeError(f"网络请求失败: {str(e)}")
    
    try:
        logger.info("开始解析HTML")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题：使用h1标签
        title = ""
        h1_tags = soup.find_all('h1')
        if h1_tags:
            title = h1_tags[0].get_text(strip=True)
            logger.info(f"提取到标题: {title}")
        
        # 提取正文：优先 article p，其次 .article p，最后 p 标签
        paragraphs = []
        
        # 方式1: article p
        article_p = soup.select('article p')
        if article_p:
            logger.info("使用 article p 选择器")
            paragraphs = article_p
        else:
            # 方式2: .article p
            dot_article_p = soup.select('.article p')
            if dot_article_p:
                logger.info("使用 .article p 选择器")
                paragraphs = dot_article_p
            else:
                # 方式3: 所有 p 标签
                logger.info("使用所有 p 标签")
                paragraphs = soup.find_all('p')
        
        # 提取文本内容
        text_content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                text_content.append(text)
        
        combined_text = ' '.join(text_content)
        combined_text = re.sub(r'\s+', ' ', combined_text).strip()
        
        if not combined_text:
            logger.warning("未提取到正文内容")
            raise ValueError("网页中未找到有效文本内容")
        
        logger.info(f"成功提取内容 - 标题: {len(title)} 字符, 正文: {len(combined_text)} 字符")
        return title, combined_text
        
    except Exception as e:
        logger.error(f"HTML解析失败: {str(e)}")
        raise RuntimeError(f"HTML解析失败: {str(e)}")

@app.get("/summary", response_model=SummaryResponse)
def summarize_url(
    url: str = Query(..., description="要总结的网页URL", min_length=1)
) -> SummaryResponse:
    """
    网页内容摘要接口
    
    获取指定URL的网页内容，使用DeepSeek AI生成三句话摘要。
    
    Args:
        url: 网页URL（支持http和https）
        
    Returns:
        SummaryResponse: 包含摘要内容的JSON响应
    """
    logger.info(f"收到摘要请求: {url}")
    
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    
    try:
        title, webpage_text = fetch_webpage_content(url)
    except Exception as e:
        logger.error(f"网页抓取失败: {str(e)}")
        return SummaryResponse(summary="抓取失败，请检查网址或稍后重试")
    
    try:
        api_key = validate_api_key()
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1"
        )
        
        prompt_parts = []
        if title:
            prompt_parts.append(f"标题：{title}")
        if webpage_text:
            prompt_parts.append(f"正文：{webpage_text[:7500]}")
        
        full_content = "\n\n".join(prompt_parts)
        
        prompt = f"""请用三句话总结以下网页的核心内容。每句话不超过50字，要简洁准确。

{full_content}"""
        
        logger.info("开始调用AI生成摘要")
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"摘要生成成功: {summary[:100]}...")
        
        return SummaryResponse(summary=summary)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"API调用失败: {error_msg}")
        return SummaryResponse(summary="抓取失败，请检查网址或稍后重试")

@app.get("/")
def root():
    """根路径欢迎信息"""
    return {"message": "网页摘要API服务", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
