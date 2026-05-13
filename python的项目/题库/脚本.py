import pyautogui
import time

print("5秒后开始，请切换到目标窗口...")
time.sleep(5)

for i in range(20):
    pyautogui.click()   # 鼠标点击
    time.sleep(0.1)

print("执行完毕")