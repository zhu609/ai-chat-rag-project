# /html/body/div[7]/div[5]/div/div[8]/div[2]/div[1]/ul/div/div/div[1]/a
# /html/body/div[7]/div[5]/div/div[8]/div[2]/div[1]/ul/div[6]/div/div[1]/a
import requests
from lxml import etree
url = 'https://tcok.cn/diannao/'
re = requests.get(url).text
tree = etree.HTML(re)
list = tree.xpath('/html/body/div[7]/div[5]/div/div[8]/div[2]/div[1]/ul/div/div')

with open('58.txt','w',encoding='utf-8') as fp:
    for i in list:
        li = i.xpath('./div[1]/a/text()')[0]
        print(li)
        fp.write(li+'\n')