import requests

url = 'https://www.douyin.com/jingxuan'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}

# 尝试添加Cookie（需要先登录获取）
cookies = {
    'sid_guard': '你的cookie',
    # 添加其他必要的cookie
}

res = requests.get(url=url, headers=headers, cookies=cookies)
print(res.status_code)
print(res.text[:1000])  # 查看返回内容