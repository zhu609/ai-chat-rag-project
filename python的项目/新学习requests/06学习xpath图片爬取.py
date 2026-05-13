import requests
from lxml import etree
# //*[@id="main"]/div[3]/ul/li[1]/a/img
# //*[@id="main"]/div[3]/ul/li[2]/a/img
url = 'https://pic.netbian.com/4k/index_61.html'
headers = {
    'user-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0'
}
response = requests.get(url=url,headers=headers)
response.encoding = 'gbk'
re = response.text
tree = etree.HTML(re)
list = tree.xpath('//*[@id="main"]/div[3]/ul/li')
for i in list:
    page = 'https://pic.netbian.com' + i.xpath('./a/img/@src')[0]
    name = i.xpath('./a/img/@alt')[0]
    path = requests.get(url=page,headers=headers).content
    img_path = (f'page/{name}.jpg')
    with open(img_path,'wb')as fp:
        fp.write(path)
        print(name,'下载成功！！！')
    print(name,page)