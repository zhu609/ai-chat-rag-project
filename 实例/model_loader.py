import os
import sys
import subprocess
import torch
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path
from tqdm import tqdm


WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights")
PROPINTER_REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ProPainter")

PROPINTER_WEIGHTS_URL = "https://github.com/sczhou/ProPainter/releases/download/v1.0.0/ProPainter.pth"
RAFT_WEIGHTS_URL = "https://github.com/sczhou/ProPainter/releases/download/v1.0.0/raft-things.pth"
RECURRENT_FLOW_WEIGHTS_URL = "https://github.com/sczhou/ProPainter/releases/download/v1.0.0/recurrent_flow.pth"


def check_gpu() -> Tuple[torch.device, bool]:
    if torch.cuda.is_available():
        device = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        print(f"检测到 GPU: {gpu_name}")
        return device, True
    else:
        print("未检测到 GPU，将使用 CPU 处理（速度较慢）")
        return torch.device("cpu"), False


def download_file(url: str, save_path: str) -> bool:
    try:
        import urllib.request
        print(f"正在下载: {url}")
        urllib.request.urlretrieve(url, save_path)
        print(f"下载完成: {save_path}")
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False


def setup_propainter() -> bool:
    os.makedirs(WEIGHTS_DIR, exist_ok=True)

    propainter_weight = os.path.join(WEIGHTS_DIR, "ProPainter.pth")
    raft_weight = os.path.join(WEIGHTS_DIR, "raft-things.pth")
    recurrent_flow_weight = os.path.join(WEIGHTS_DIR, "recurrent_flow.pth")

    weights_exist = all([
        os.path.exists(propainter_weight),
        os.path.exists(raft_weight),
        os.path.exists(recurrent_flow_weight)
    ])

    if weights_exist:
        print("所有模型权重已存在")
        return True

    print("开始下载模型权重...")
    success = True
    if not os.path.exists(propainter_weight):
        success &= download_file(PROPINTER_WEIGHTS_URL, propainter_weight)
    if not os.path.exists(raft_weight):
        success &= download_file(RAFT_WEIGHTS_URL, raft_weight)
    if not os.path.exists(recurrent_flow_weight):
        success &= download_file(RECURRENT_FLOW_WEIGHTS_URL, recurrent_flow_weight)

    if not success:
        print("部分权重下载失败，请手动下载以下文件到 weights 目录:")
        print(f"  1. ProPainter.pth: {PROPINTER_WEIGHTS_URL}")
        print(f"  2. raft-things.pth: {RAFT_WEIGHTS_URL}")
        print(f"  3. recurrent_flow.pth: {RECURRENT_FLOW_WEIGHTS_URL}")
        return False

    return True


def clone_propainter_repo() -> bool:
    if os.path.exists(PROPINTER_REPO_DIR):
        print("ProPainter 仓库已存在")
        return True

    try:
        print("正在克隆 ProPainter 仓库...")
        subprocess.run(
            ["git", "clone", "https://github.com/sczhou/ProPainter.git", PROPINTER_REPO_DIR],
            check=True,
            capture_output=True
        )
        print("克隆完成")
        return True
    except Exception as e:
        print(f"克隆仓库失败: {e}")
        print("请手动克隆: git clone https://github.com/sczhou/ProPainter.git")
        return False


class ProPainterInference:
    def __init__(self, device: torch.device):
        self.device = device
        self.model = None
        self.raft_model = None
        self.flow_model = None
        self._load_models()

    def _load_models(self):
        try:
            sys.path.insert(0, PROPINTER_REPO_DIR)
            from models.propainter import ProPainter
            from models.recurrent_flow_completion import RecurrentFlowCompleteNet
            from models.raft import RAFT

            propainter_weight = os.path.join(WEIGHTS_DIR, "ProPainter.pth")
            raft_weight = os.path.join(WEIGHTS_DIR, "raft-things.pth")
            recurrent_flow_weight = os.path.join(WEIGHTS_DIR, "recurrent_flow.pth")

            if not all(os.path.exists(w) for w in [propainter_weight, raft_weight, recurrent_flow_weight]):
                raise FileNotFoundError("模型权重文件不存在")

            self.raft_model = RAFT()
            raft_state = torch.load(raft_weight, map_location=self.device)
            self.raft_model.load_state_dict(raft_state)
            self.raft_model.to(self.device)
            self.raft_model.eval()

            self.flow_model = RecurrentFlowCompleteNet()
            flow_state = torch.load(recurrent_flow_weight, map_location=self.device)
            self.flow_model.load_state_dict(flow_state)
            self.flow_model.to(self.device)
            self.flow_model.eval()

            self.model = ProPainter()
            state = torch.load(propainter_weight, map_location=self.device)
            self.model.load_state_dict(state)
            self.model.to(self.device)
            self.model.eval()

            print("ProPainter 模型加载成功")
        except Exception as e:
            print(f"ProPainter 模型加载失败: {e}")
            self.model = None

    @torch.no_grad()
    def inpaint(self, frames: List[np.ndarray], masks: List[np.ndarray]) -> List[np.ndarray]:
        if self.model is None:
            raise RuntimeError("模型未正确加载")

        import torchvision.transforms.functional as TF

        h, w = frames[0].shape[:2]
        new_h = (h // 8) * 8
        new_w = (w // 8) * 8

        frames_tensor = []
        for frame in frames:
            frame_resized = frame[:new_h, :new_w]
            t = torch.from_numpy(frame_resized).float().permute(2, 0, 1) / 255.0
            frames_tensor.append(t)

        masks_tensor = []
        for mask in masks:
            mask_resized = mask[:new_h, :new_w]
            t = torch.from_numpy(mask_resized).float().unsqueeze(0) / 255.0
            masks_tensor.append(t)

        frames_batch = torch.stack(frames_tensor).unsqueeze(0).to(self.device)
        masks_batch = torch.stack(masks_tensor).unsqueeze(0).to(self.device)

        flows = self._compute_flows(frames_batch)
        completed_flows = self._complete_flows(flows, masks_batch)

        result = self.model(frames_batch, masks_batch, completed_flows)

        result_frames = []
        for i in range(result.shape[1]):
            frame = result[0, i].cpu().clamp(0, 1).numpy()
            frame = (frame * 255).astype(np.uint8)
            frame = frame.transpose(1, 2, 0)
            if frame.shape[:2] != (h, w):
                frame_resized = np.zeros((h, w, 3), dtype=np.uint8)
                frame_resized[:new_h, :new_w] = frame
                frame = frame_resized
            result_frames.append(frame)

        return result_frames

    def _compute_flows(self, frames: torch.Tensor) -> torch.Tensor:
        b, t, c, h, w = frames.shape
        flows = []
        for i in range(t - 1):
            img1 = frames[:, i]
            img2 = frames[:, i + 1]
            flow = self.raft_model(img1, img2)
            flows.append(flow)
        return torch.stack(flows, dim=1)

    def _complete_flows(self, flows: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        return self.flow_model(flows, masks[:, :-1])


class SimpleInpainter:
    def __init__(self, device: torch.device):
        self.device = device
        print("使用简单修复模式（基于 OpenCV）")

    def inpaint(self, frames: List[np.ndarray], masks: List[np.ndarray]) -> List[np.ndarray]:
        result_frames = []
        for frame, mask in tqdm(zip(frames, masks), total=len(frames), desc="修复进度"):
            mask_binary = (mask > 127).astype(np.uint8) * 255
            kernel = np.ones((5, 5), np.uint8)
            mask_dilated = cv2.dilate(mask_binary, kernel, iterations=2)
            result = cv2.inpaint(frame, mask_dilated, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
            result_frames.append(result)
        return result_frames


def load_inpainter(device: torch.device):
    try:
        if setup_propainter() and clone_propainter_repo():
            return ProPainterInference(device)
    except Exception as e:
        print(f"ProPainter 加载失败，回退到简单模式: {e}")

    return SimpleInpainter(device)


def process_video(
    frames: List[np.ndarray],
    masks: List[np.ndarray],
    device: torch.device,
    chunk_size: int = 200,
    progress_callback=None
) -> List[np.ndarray]:
    from utils import split_frames

    inpainter = load_inpainter(device)
    chunks = split_frames(frames, masks, chunk_size)
    result_frames = []

    for i, (chunk_frames, chunk_masks) in enumerate(chunks):
        if progress_callback:
            progress_callback(i, len(chunks), "处理中...")

        chunk_result = inpainter.inpaint(chunk_frames, chunk_masks)
        result_frames.extend(chunk_result)

    return result_frames
