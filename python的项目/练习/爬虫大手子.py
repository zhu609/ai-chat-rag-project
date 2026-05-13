import urllib.request
url = 'https://www.baidu.com/'
#模拟浏览器向服务器发送请求
re = urllib.request.urlopen(url)
#读取服务器返回的数据
c = re.read().decode('utf-8')
#打印被赋值的变量
print(c)
