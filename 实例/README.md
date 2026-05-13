# AI 视频去水印工具

基于 ProPainter 的 AI 视频去水印工具，支持静态水印、半透明水印及缓慢移动的水印。

## 系统要求

- Python 3.9+
- FFmpeg（需要在系统 PATH 中）
- CUDA（推荐，用于 GPU 加速）

## 安装步骤

### 方式一：使用 pip

```bash
# 克隆项目
git clone https://github.com/sczhou/ProPainter.git
cd video_watermark_remover

# 安装依赖
pip install -r requirements.txt
```

### 方式二：使用 conda

```bash
# 创建虚拟环境
conda create -n video_inpaint python=3.9
conda activate video_inpaint

# 安装 PyTorch（根据你的 CUDA 版本选择）
# CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# CPU only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 安装其他依赖
pip install -r requirements.txt
```

## 启动界面

```bash
python app.py
```

启动后，浏览器会自动打开界面。如果没有自动打开，请访问控制台显示的地址（通常是 http://localhost:7860）。

## 使用说明

### 1. 上传视频
- 点击"上传视频"按钮，选择需要去水印的视频文件
- 支持 MP4、AVI、MOV 等常见格式

### 2. 加载视频
- 点击"加载视频"按钮
- 系统会显示视频首帧和视频信息（分辨率、帧率、时长等）

### 3. 设置水印区域
- 在首帧中观察水印位置
- 输入左上角坐标（X1, Y1）和右下角坐标（X2, Y2）
- 坐标单位为像素

### 4. 开始处理
- 点击"开始去水印"按钮
- 等待处理完成（进度条会显示当前进度）
- 处理完成后可以预览和下载结果

### 5. 重置
- 点击"一键重置"按钮可以清空所有设置

## 常见问题

### Q: 处理速度很慢怎么办？
A: 
- 确保已安装 CUDA 版本的 PyTorch
- 减小"分段帧数"参数（如设为 100）
- 缩短视频长度或分辨率

### Q: 显存不足怎么办？
A:
- 减小"分段帧数"参数
- 降低视频分辨率
- 使用 CPU 模式（会更慢但不会报错）

### Q: 水印去除不干净怎么办？
A:
- 确保坐标准确覆盖整个水印区域
- 可以适当扩大坐标范围（多包含一些水印边缘）
- 对于动态水印，可能需要分段处理

### Q: 音频丢失怎么办？
A:
- 确保系统已安装 FFmpeg
- 检查原视频是否包含音频轨道

### Q: 下载模型失败怎么办？
A:
- 手动下载以下文件到 weights 目录：
  - ProPainter.pth: https://github.com/sczhou/ProPainter/releases/download/v1.0.0/ProPainter.pth
  - raft-things.pth: https://github.com/sczhou/ProPainter/releases/download/v1.0.0/raft-things.pth
  - recurrent_flow.pth: https://github.com/sczhou/ProPainter/releases/download/v1.0.0/recurrent_flow.pth

## 许可证

本项目基于 MIT 许可证开源。ProPainter 模型同样基于 MIT 许可证。
