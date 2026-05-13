import os
import cv2
import numpy as np
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, List, Optional
from tqdm import tqdm
import torch


def get_video_info(video_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")

    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
    }
    cap.release()
    return info


def read_video_frames(video_path: str) -> Tuple[List[np.ndarray], dict]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")

    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    }

    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    cap.release()
    return frames, info


def read_first_frame(video_path: str) -> Optional[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return None


def write_video_frames(frames: List[np.ndarray], output_path: str, fps: float) -> bool:
    if not frames:
        return False

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    out.release()
    return True


def generate_mask_video(frames: List[np.ndarray], x1: int, y1: int, x2: int, y2: int) -> List[np.ndarray]:
    masks = []
    for frame in frames:
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        x1_c = max(0, min(x1, w))
        y1_c = max(0, min(y1, h))
        x2_c = max(0, min(x2, w))
        y2_c = max(0, min(y2, h))
        mask[y1_c:y2_c, x1_c:x2_c] = 255
        masks.append(mask)
    return masks


def merge_audio(video_path: str, processed_video_path: str, output_path: str) -> bool:
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", processed_video_path,
            "-i", video_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-shortest",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            cmd_fallback = [
                "ffmpeg", "-y",
                "-i", processed_video_path,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                output_path
            ]
            subprocess.run(cmd_fallback, capture_output=True, text=True)
        return True
    except Exception as e:
        print(f"音频合并失败: {e}")
        return False


def split_frames(frames: List[np.ndarray], masks: List[np.ndarray], chunk_size: int = 200) -> List[Tuple[List[np.ndarray], List[np.ndarray]]]:
    chunks = []
    for i in range(0, len(frames), chunk_size):
        chunk_frames = frames[i:i + chunk_size]
        chunk_masks = masks[i:i + chunk_size]
        chunks.append((chunk_frames, chunk_masks))
    return chunks


def frames_to_tensor(frames: List[np.ndarray], device: torch.device) -> torch.Tensor:
    tensors = []
    for frame in frames:
        tensor = torch.from_numpy(frame).float() / 255.0
        tensor = tensor.permute(2, 0, 1)
        tensors.append(tensor)
    return torch.stack(tensors).to(device)


def masks_to_tensor(masks: List[np.ndarray], device: torch.device) -> torch.Tensor:
    tensors = []
    for mask in masks:
        tensor = torch.from_numpy(mask).float() / 255.0
        tensor = tensor.unsqueeze(0)
        tensors.append(tensor)
    return torch.stack(tensors).to(device)


def tensor_to_frames(tensor: torch.Tensor) -> List[np.ndarray]:
    frames = []
    for i in range(tensor.shape[0]):
        frame = tensor[i].cpu().clamp(0, 1).numpy()
        frame = (frame * 255).astype(np.uint8)
        frame = frame.transpose(1, 2, 0)
        frames.append(frame)
    return frames


def create_temp_dir() -> str:
    temp_dir = tempfile.mkdtemp(prefix="video_watermark_")
    return temp_dir


def cleanup_temp_dir(temp_dir: str):
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
