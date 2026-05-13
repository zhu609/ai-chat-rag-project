import requests
a = 0
url = 'https://movie.douban.com/j/chart/top_list?type=5&interval_id=100%3A90&action=&start=0&limit='
a = int(input('请输入你要看的页数'))
b = a * 20
url1 = url + str(b)
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
}
moives = requests.get(url=url1,headers=headers).json()
movie_names = [movie['title']for movie in moives]
for name in movie_names:
    print(name)
    a +=1

