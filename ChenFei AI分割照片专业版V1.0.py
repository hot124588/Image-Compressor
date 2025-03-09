import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import platform
import winsound
import logging
import sys
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
import datetime
import requests
import zipfile
import shutil
import subprocess
import tempfile

# 获取程序所在盘符
def get_program_drive():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.splitdrive(base_dir)[0] + os.sep

# 配置常量
PROGRAM_DRIVE = get_program_drive()
LOG_DIR = os.path.join(PROGRAM_DRIVE, "ChenFeiApp", "logs")
OUTPUT_DIR_ROOT = os.path.join(PROGRAM_DRIVE, "ChenFeiApp", "output")
MAX_FILES = 5
OUTPUT_DIR_NAME = "ChenFei_OK"
THUMBNAIL_SIZE = (100, 100)
STYLE_CONFIG = {
    "header_bg": "#34495e",
    "success_fg": "#27ae60",
    "error_fg": "#c0392b",
    "button_bg": "#f1c40f",
    "bg_color": "#f5f6fa"
}

# 日志配置
os.makedirs(LOG_DIR, exist_ok=True)
log_file_path = os.path.join(LOG_DIR, 'app.log')
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

# 更新配置
UPDATE_URL = "https://example.com/your-update-url"  # 替换为你的更新文件URL
CURRENT_VERSION = "1.0"

# 图像处理核心模块
class ImageProcessor:
    @staticmethod
    def process_image(input_path: str, output_dir: str) -> List[str]:
        """处理单张图像的主流程"""
        try:
            if not os.path.isfile(input_path):
                raise FileNotFoundError(f"输入文件不存在：{input_path}")

            with Image.open(input_path) as pil_image:
                if pil_image.mode == 'RGBA':
                    pil_image = pil_image.convert('RGB')
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            processed = ImageProcessor._preprocess_image(image)
            contours = ImageProcessor._find_contours(processed)
            return ImageProcessor._process_contours(image, contours, input_path, output_dir)

        except Exception as e:
            logging.error(f"处理失败：{str(e)}", exc_info=True)
            raise

    @staticmethod
    def _preprocess_image(image: np.ndarray) -> np.ndarray:
        """图像预处理管道"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    @staticmethod
    def _find_contours(image: np.ndarray) -> List[np.ndarray]:
        """寻找有效轮廓"""
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise RuntimeError("未检测到有效轮廓")
        return sorted(contours, key=cv2.contourArea, reverse=True)[:4]

    @staticmethod
    def _process_contours(original: np.ndarray, contours: List[np.ndarray],
                          input_path: str, output_dir: str) -> List[str]:
        """处理所有检测到的轮廓"""
        output_files = []
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

        for idx, cnt in enumerate(contours):
            try:
                warped = ImageProcessor._warp_perspective(original, cnt)
                bordered = cv2.copyMakeBorder(warped, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                output_path = os.path.join(output_dir, f"{base_name}_{timestamp}_{idx:02d}.jpg")

                if ImageProcessor._save_image(output_path, bordered):
                    output_files.append(output_path)
            except Exception as e:
                logging.error(f"轮廓{idx}处理失败：{str(e)}")
                continue

        if not output_files:
            raise RuntimeError("所有轮廓处理均失败")
        return output_files

    @staticmethod
    def _warp_perspective(image: np.ndarray, contour: np.ndarray) -> np.ndarray:
        """透视变换核心逻辑"""
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        width, height = ImageProcessor._calculate_size(rect)

        dst = np.array([[0, height - 1], [0, 0], [width - 1, 0], [width - 1, height - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(box, dst)
        warped = cv2.warpPerspective(image, M, (width, height))

        if warped.size == 0:
            raise ValueError("透视变换返回空图像")
        return warped

    @staticmethod
    def _calculate_size(rect: Tuple[Tuple[float, float], Tuple[float, float], float]) -> Tuple[int, int]:
        """计算实际尺寸"""
        _, (w, h), angle = rect
        return (int(h), int(w)) if angle < -45 else (int(w), int(h))

    @staticmethod
    def _save_image(output_path: str, image: np.ndarray) -> bool:
        """安全保存图像"""
        try:
            output_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 检查写入权限
            test_file = os.path.join(os.path.dirname(output_path), "test_permission.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)

            success = cv2.imwrite(output_path, image)
            if not success:
                raise RuntimeError("OpenCV写入失败")
            logging.info(f"成功保存文件到：{output_path}")
            return True
        except PermissionError as e:
            logging.error(f"权限拒绝：{output_path} - {str(e)}")
            return False
        except Exception as e:
            logging.error(f"文件保存失败：{output_path} - {str(e)}")
            return False


# GUI界面模块
class ImageProcessorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.file_entries: List[dict] = []
        self.thumbnails: List[ttk.Label] = []
        self._init_ui()
        self._setup_window()
        self._check_for_updates()

    def _init_ui(self):
        """初始化用户界面"""
        self._configure_styles()
        self._create_header()
        self._create_main_content()
        self._create_controls()

    def _setup_window(self):
        """窗口配置"""
        self.root.title("ChenFei AI分割照片专业版 v1.0")
        self.root.geometry("1000x680+200+100")
        self.root.minsize(1000, 680)

    def _configure_styles(self):
        """配置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        self.root.configure(background=STYLE_CONFIG["bg_color"])
        style.configure(".",
                        background=STYLE_CONFIG["bg_color"],
                        font=("Segoe UI", 10) if platform.system() == "Windows" else ("Helvetica", 11))
        style.configure("Header.TFrame", background=STYLE_CONFIG["header_bg"])
        style.configure("Header.TLabel",
                        font=("Microsoft YaHei", 14, "bold"),
                        foreground="#ecf0f1",
                        background=STYLE_CONFIG["header_bg"])
        style.configure("Process.TButton",
                        font=("Microsoft YaHei", 12, "bold"),
                        foreground="#2c3e50",
                        background=STYLE_CONFIG["button_bg"],
                        padding=10)
        style.map("Process.TButton",
                  background=[('active', '#f39c12'), ('disabled', '#bdc3c7')])
        style.configure("Entry.TEntry",
                        fieldbackground="#ffffff",
                        padding=5,
                        relief="flat")
        style.configure("Success.TEntry",
                        fieldbackground="#e8f6e3",
                        foreground=STYLE_CONFIG["success_fg"])
        style.configure("Error.TEntry",
                        fieldbackground="#fadbd8",
                        foreground=STYLE_CONFIG["error_fg"])

    def _create_header(self):
        """创建头部区域"""
        header = ttk.Frame(self.root, style="Header.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="ChenFei AI分割照片系统", style="Header.TLabel").pack(side=tk.LEFT, padx=20)

    def _create_main_content(self):
        """主内容区域"""
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self._create_file_section(main_container)
        self._create_info_panel(main_container)

    def _create_file_section(self, parent: ttk.Frame):
        """左侧文件选择区域"""
        container = ttk.Frame(parent)
        container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(container, bg=STYLE_CONFIG["bg_color"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._create_file_entries(scroll_frame)

    def _create_file_entries(self, parent: ttk.Frame):
        """创建文件输入行"""
        for i in range(MAX_FILES):
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=tk.X, pady=5, padx=5)
            self._create_single_entry(row_frame, i)

    def _create_single_entry(self, parent: ttk.Frame, index: int):
        """单个文件条目组件"""
        thumb_frame = ttk.Frame(parent,
                                width=THUMBNAIL_SIZE[0] + 10,
                                height=THUMBNAIL_SIZE[1] + 10)
        thumb_frame.pack_propagate(False)
        thumb_frame.pack(side=tk.LEFT, padx=(0, 5))

        thumbnail = ttk.Label(thumb_frame,
                              background="#ffffff",
                              relief="groove")
        thumbnail.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.thumbnails.append(thumbnail)

        control_frame = ttk.Frame(parent)
        control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn = ttk.Button(control_frame,
                         text=f"📁 选择照片 {index + 1}",
                         command=lambda: self._select_file(index))
        btn.pack(side=tk.LEFT, padx=(0, 5))

        entry_var = tk.StringVar()
        entry = ttk.Entry(control_frame,
                          textvariable=entry_var,
                          style="Entry.TEntry",
                          state="readonly")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        del_btn = ttk.Button(control_frame,
                             text="✕",
                             command=lambda: self._clear_entry(index),
                             width=3)
        del_btn.pack(side=tk.RIGHT)

        self.file_entries.append({
            "var": entry_var,
            "path": "",
            "entry": entry,
            "btn": del_btn
        })

    def _create_info_panel(self, parent: ttk.Frame):
        """右侧说明面板"""
        info_frame = ttk.Frame(parent, width=280)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

        info_text = """📢 软件说明

        本软件由尘飞开发
        专门用于扫描照片智能分割

        ⚙️ 主要功能：
        1. 一张上包含多张的扫描照片
        2. 智能分割成多张独立照片
        3. AI自动识别并摆正照片
        4. 多线同时处理最多5张照片

        🎮 使用提示：
        • 点击"选择照片"按钮添加图片
        • 点击"✕"按钮可清除已选文件
        • 处理完成后自动打开输出目录

        🎉 祝您使用愉快！"""

        info_label = ttk.Label(info_frame,
                               text=info_text,
                               background=STYLE_CONFIG["bg_color"],
                               wraplength=260,
                               padding=15,
                               justify=tk.LEFT,
                               font=("Microsoft YaHei", 10))
        info_label.pack(fill=tk.BOTH, expand=True)

        ttk.Label(info_frame,
                  text="版本：v1.0\n开发者：尘飞",
                  background=STYLE_CONFIG["bg_color"],
                  font=("Microsoft YaHei", 9),
                  foreground="#7f8c8d",
                  padding=(0, 20)).pack(side=tk.BOTTOM)

    def _create_controls(self):
        """底部控制区域"""
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=10)

        self.progress = ttk.Progressbar(control_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=5)

        process_btn = ttk.Button(control_frame,
                                 text="🚀 开始AI分割处理 🚀",
                                 style="Process.TButton",
                                 command=self._start_processing)
        process_btn.pack(fill=tk.X, pady=5)

    # 功能方法
    def _select_file(self, index: int):
        """处理文件选择"""
        path = filedialog.askopenfilename(
            filetypes=[("图像文件", "*.jpg *.jpeg *.png *.bmp")],
            title=f"选择第 {index + 1} 张照片"
        )
        if path:
            self._load_and_display_image(index, path)

    def _load_and_display_image(self, index: int, path: str):
        """加载并显示图像"""
        try:
            abs_path = os.path.abspath(path)
            if not os.path.isfile(abs_path):
                raise FileNotFoundError(f"文件不存在：{abs_path}")
            if not os.access(abs_path, os.R_OK):
                raise PermissionError(f"无读取权限：{abs_path}")

            img = Image.open(abs_path)
            img.thumbnail(THUMBNAIL_SIZE)
            photo = ImageTk.PhotoImage(img)

            self.thumbnails[index].configure(image=photo)
            self.thumbnails[index].image = photo
            self.file_entries[index]["var"].set(os.path.basename(abs_path))
            self.file_entries[index]["path"] = abs_path
            self.file_entries[index]["entry"].configure(style="Success.TEntry")

        except Exception as e:
            self.file_entries[index]["entry"].configure(style="Error.TEntry")
            messagebox.showerror("错误", f"文件加载失败:\n{str(e)}")
            logging.error(f"文件加载错误: {path}", exc_info=True)

    def _clear_entry(self, index: int):
        """清除文件条目"""
        self.file_entries[index]["var"].set("")
        self.file_entries[index]["path"] = ""
        self.thumbnails[index].configure(image='')
        self.thumbnails[index].image = None
        self.file_entries[index]["entry"].configure(style="Entry.TEntry")

    def _start_processing(self):
        """启动处理流程"""
        valid_files = [e["path"] for e in self.file_entries if e["path"].strip()]
        if not valid_files:
            messagebox.showwarning("提示", "请先选择至少一张图像文件！")
            return

        try:
            output_dir = self._prepare_output_dir()
            logging.info(f"输出目录路径：{output_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"无法创建输出目录：{str(e)}")
            return

        self._init_progress_bar(len(valid_files))

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for path in valid_files:
                    futures.append(executor.submit(
                        ImageProcessor.process_image,
                        path,
                        output_dir
                    ))

                results = []
                for future in futures:
                    try:
                        results.extend(future.result())
                        self.progress["value"] += 1
                        self.root.update()
                    except Exception as e:
                        logging.error(str(e))

            success = len(results)
            self._show_results(success, [], results, output_dir)
            self._open_output_dir(output_dir)
        except Exception as e:
            messagebox.showerror("严重错误", f"处理意外中断:\n{str(e)}")
            logging.critical("处理中断", exc_info=True)
        finally:
            self.progress["value"] = 0

    def _prepare_output_dir(self) -> str:
        """准备输出目录"""
        try:
            output_dir = os.path.join(OUTPUT_DIR_ROOT, OUTPUT_DIR_NAME)
            os.makedirs(output_dir, exist_ok=True)
            return output_dir
        except Exception as e:
            logging.error(f"无法创建输出目录：{str(e)}")
            raise

    def _init_progress_bar(self, total: int):
        """初始化进度条"""
        self.progress["maximum"] = total
        self.progress["value"] = 0

    def _show_results(self, success: int, errors: List[str], outputs: List[str], output_dir: str):
        """显示处理结果"""
        msg = []
        if success > 0:
            msg.append(f"成功处理 {success} 张图片")
            msg.append(f"生成文件数：{len(outputs)}")
            msg.append(f"输出目录：{output_dir}")
        if errors:
            msg.append("\n错误列表：\n• " + "\n• ".join(errors))

        title = "处理完成" if success > 0 else "处理失败"
        messagebox.showinfo(title, "\n".join(msg))
        self._play_sound(success > 0)

    def _play_sound(self, success: bool):
        """播放提示音"""
        if platform.system() == "Windows":
            frequency = 2000 if success else 500
            duration = 1000 if success else 2000
            winsound.Beep(frequency, duration)

    def _open_output_dir(self, path: str):
        """打开输出目录"""
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            os.system(f"open {path}")
        else:
            os.system(f"xdg-open {path}")

    def _check_for_updates(self):
        """检查更新"""
        try:
            response = requests.get(UPDATE_URL)
            if response.status_code == 200:
                latest_version = response.json().get("version", "")
                if latest_version and latest_version != CURRENT_VERSION:
                    if messagebox.askyesno("更新提示", f"发现新版本 {latest_version}，是否现在更新？"):
                        self._download_and_install_update(latest_version)
        except Exception as e:
            logging.error(f"检查更新失败：{str(e)}")

    def _download_and_install_update(self, latest_version: str):
        """下载并安装更新"""
        try:
            update_url = f"https://example.com/your-update-file.zip"  # 替换为你的更新文件URL
            response = requests.get(update_url, stream=True)
            if response.status_code == 200:
                temp_dir = tempfile.mkdtemp()
                update_zip_path = os.path.join(temp_dir, "update.zip")
                with open(update_zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                update_exe_path = os.path.join(temp_dir, "ChenFeiAI.exe")  # 替换为你的更新文件名
                if os.path.exists(update_exe_path):
                    subprocess.Popen([update_exe_path, "--update"])
                    self.root.quit()
                else:
                    messagebox.showerror("更新失败", "未能找到更新文件，请手动下载更新。")
            else:
                messagebox.showerror("更新失败", "下载更新文件失败，请稍后再试。")
        except Exception as e:
            logging.error(f"下载并安装更新失败：{str(e)}")
            messagebox.showerror("更新失败", "下载并安装更新失败，请稍后再试。")


if __name__ == "__main__":
    cv2.setUseOptimized(True)
    cv2.setNumThreads(4)
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()