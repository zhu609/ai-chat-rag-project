import requests



url = 'https://www.baidu.com/s'
kw = input('请输入关键字')
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
}
param ={
    'wd':kw
}
res = requests.get(url=url,params=param,headers=headers)
page = res.text
print(page)