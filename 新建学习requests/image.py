import requests
from PIL import Image
from io import BytesIO
r = requests.get("https://img.iplaysoft.com/wp-content/uploads/2019/free-images/free_stock_photo_2x.jpg!0x0.webp")
i = Image.open(BytesIO(r.content))
fp = open("1.jpg","wb")
i.save(fp)
fp.close()