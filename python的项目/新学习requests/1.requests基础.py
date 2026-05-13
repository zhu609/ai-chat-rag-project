import requests
url = input('请复制你想要爬取的源码')
response = requests.get(url=url)
page = response.text
print(page)