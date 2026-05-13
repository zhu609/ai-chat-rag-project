import urllib.parse
url = 'https://movie.douban.com/j/chart/top_list?type=5&interval_id=100%3A90&action=&'
for page in range(1,10):
    data = {
        'start':(page-1)*20,
        'limit':'20'
    }
    data = urllib.parse.urlencode(data)
    url1 = url + data
    print(url1)