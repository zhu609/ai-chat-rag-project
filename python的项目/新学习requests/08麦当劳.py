import requests
url = 'https://www.mcdonalds.com.cn/ajaxs/search_by_keywords'
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0'
}
data = {
    'keywords':'ping',
    'city':'平顶山市',
    'location''[info]':'OK',
    'location[position][lng]':'113.290224',
    'location[position][lat]':'33.709002'
}
res = requests.post(url=url,headers=headers,data=data).json()
name = [movie['address'] for movie in res['data']]
id = [movie['id'] for movie in res['data']]
title = [movie['title'] for movie in res['data']]
for x,y,z in zip(name,id,title):
    print(x,y,z)
