import requests
url = 'https://www.mcdonalds.com.cn/ajaxs/search_by_keywords'
data = {
    'keywords':'平顶山',
    'city':'平顶山市',
    'location[info]':'OK',
    'location[position][lng]':'113.290085',
    'location[position][lat]':'33.709073'
}
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
}
res = requests.post(url=url,data=data,headers=headers)
re = res.json()
print(re)