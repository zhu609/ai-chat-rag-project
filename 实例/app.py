import os
import sys
import gradio as gr
import cv2
import numpy as np
import torch
from typing import Tuple, Optional
from pathlib import Path

from utils import (
    read_video_frames,
    read_first_frame,
    write_video_frames,
    generate_mask_video,
    merge_audio,
    create_temp_dir,
    cleanup_temp_dir,
    get_video_info
)
from model_loader import check_gpu, process_video, setup_propainter


class VideoWatermarkRemover:
    def __init__(self):
        self.device, self.has_gpu = check_gpu()
        self.temp_dir = create_temp_dir()
        self.current_video_path = None
        self.current_frames = None
        self.video_info = None

    def load_video(self, video_path: str) -> Tuple[Optional[np.ndarray], str]:
        if video_path is None:
            return None, "请上传视频文件"

        try:
            self.current_video_path = video_path
            self.current_frames, self.video_info = read_video_frames(video_path)

            if not self.current_frames:
                return None, "无法读取视频帧"

            first_frame = self.current_frames[0]
            info_text = (
                f"视频加载成功\n"
                f"分辨率: {self.video_info['width']}x{self.video_info['height']}\n"
                f"帧率: {self.video_info['fps']:.2f} fps\n"
                f"总帧数: {self.video_info['frame_count']}\n"
                f"时长: {self.video_info['duration']:.2f} 秒\n"
                f"设备: {'GPU (' + torch.cuda.get_device_name(0) + ')' if self.has_gpu else 'CPU'}"
            )
            return first_frame, info_text

        except Exception as e:
            return None, f"加载视频失败: {str(e)}"

    def process(
        self,
        video_path: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        chunk_size: int,
        progress: gr.Progress = gr.Progress()
    ) -> Tuple[Optional[str], str]:
        if video_path is None:
            return None, "请先上传视频"

        if self.current_frames is None:
            return None, "请先加载视频"

        if x1 >= x2 or y1 >= y2:
            return None, "坐标无效：x1 必须小于 x2，y1 必须小于 y2"

        try:
            progress(0, desc="正在生成掩膜...")
            masks = generate_mask_video(
                self.current_frames, x1, y1, x2, y2
            )

            progress(0.1, desc="正在处理视频...")

            def progress_callback(current, total, desc):
                progress(0.1 + 0.7 * (current / total), desc=desc)

            result_frames = process_video(
                self.current_frames,
                masks,
                self.device,
                chunk_size=chunk_size,
                progress_callback=progress_callback
            )

            progress(0.8, desc="正在合成视频...")
            temp_output = os.path.join(self.temp_dir, "output_no_audio.mp4")
            write_video_frames(result_frames, temp_output, self.video_info['fps'])

            progress(0.9, desc="正在合并音频...")
            final_output = os.path.join(self.temp_dir, "output_final.mp4")
            merge_audio(self.current_video_path, temp_output, final_output)

            progress(1.0, desc="处理完成!")
            return final_output, "视频处理完成！可以预览和下载"

        except Exception as e:
            return None, f"处理失败: {str(e)}"

    def reset(self):
        self.current_video_path = None
        self.current_frames = None
        self.video_info = None
        return None, None, "", 0, 0, 0, 0, 200


def create_interface():
    remover = VideoWatermarkRemover()

    with gr.Blocks(
        title="AI 视频去水印工具",
        theme=gr.themes.Soft()
    ) as demo:
        gr.Markdown(
            """
            # AI 视频去水印工具
            上传视频并指定水印区域，自动去除水印
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(label="上传视频")
                first_frame_display = gr.Image(label="视频首帧（用于确定水印位置）")
                video_info_text = gr.Textbox(label="视频信息", lines=6, interactive=False)

                load_btn = gr.Button("加载视频", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("### 水印区域坐标")
                gr.Markdown("请在上方首帧中观察水印位置，输入左上角和右下角坐标")

                with gr.Row():
                    x1_input = gr.Number(label="左上角 X", value=0, precision=0)
                    y1_input = gr.Number(label="左上角 Y", value=0, precision=0)

                with gr.Row():
                    x2_input = gr.Number(label="右下角 X", value=100, precision=0)
                    y2_input = gr.Number(label="右下角 Y", value=100, precision=0)

                chunk_size_input = gr.Slider(
                    label="分段帧数（显存不足时减小）",
                    minimum=50,
                    maximum=500,
                    value=200,
                    step=10
                )

                with gr.Row():
                    process_btn = gr.Button("开始去水印", variant="primary")
                    reset_btn = gr.Button("一键重置", variant="secondary")

                status_text = gr.Textbox(label="处理状态", interactive=False)

        with gr.Row():
            video_output = gr.Video(label="处理结果预览")

        def on_load_video(video_path):
            frame, info = remover.load_video(video_path)
            return frame, info

        def on_process(video_path, x1, y1, x2, y2, chunk_size, progress=gr.Progress()):
            return remover.process(video_path, int(x1), int(y1), int(x2), int(y2), int(chunk_size), progress)

        def on_reset():
            result = remover.reset()
            return result

        load_btn.click(
            fn=on_load_video,
            inputs=[video_input],
            outputs=[first_frame_display, video_info_text]
        )

        process_btn.click(
            fn=on_process,
            inputs=[
                video_input,
                x1_input,
                y1_input,
                x2_input,
                y2_input,
                chunk_size_input
            ],
            outputs=[video_output, status_text]
        )

        reset_btn.click(
            fn=on_reset,
            outputs=[
                video_input,
                first_frame_display,
                video_info_text,
                x1_input,
                y1_input,
                x2_input,
                y2_input,
                chunk_size_input
            ]
        )

    return demo


if __name__ == "__main__":
    print("=" * 50)
    print("AI 视频去水印工具")
    print("=" * 50)

    setup_propainter()

    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
