"""
抖音精选页面热门内容爬取脚本
该脚本通过requests库获取抖音精选页面内容，使用lxml解析HTML并提取包含"热门"或"精选"文本的元素
"""

import requests
from lxml import etree

# 设置目标URL和请求头
url = 'https://www.douyin.com/jingxuan'
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0'
}

# 发送HTTP GET请求获取页面内容
res = requests.get(url=url, headers=headers).text

# 使用lxml解析HTML文档
tree = etree.HTML(res)

# 使用XPath定位包含"热门"或"精选"文本的div元素
li_list = tree.xpath('//div[contains(text(), "热门") or contains(text(), "精选")]')

# 遍历匹配的元素并打印其文本内容
for li in li_list:
    print(li.text)
