import requests
a = input('请输入你想翻译的英文单词')
url = 'https://fanyi.baidu.com/sug'
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
}
data = {
'kw': a
}
requests = requests.post(url=url, data=data, headers=headers)
json = requests.json()
# print(json)
for key, value in json.items():
    if key == 'data':
        print(value)