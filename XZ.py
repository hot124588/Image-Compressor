import os
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image
from datetime import datetime
import sys
import shutil
import glob
import configparser
import requests
import tempfile
import subprocess
import hashlib
from threading import Thread
import logging

# 设置日志
log_file = "image_optimizer.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=log_file,
                    filemode='a')


# ===================== 自动更新模块 =====================
class AutoUpdater:
    def __init__(self, current_version):
        self.current_version = current_version
        self.update_url = "http://127.0.0.1:8000/"
        self.config_file = "version.ini"
        self.temp_dir = tempfile.gettempdir()

    def check_update(self):
        try:
            remote_cfg = self._download_file(self.config_file)
            if not remote_cfg:
                return False

            config = configparser.ConfigParser()
            config.read(remote_cfg)
            new_version = config.get('update', 'version', fallback='')
            download_url = config.get('update', 'url', fallback='')
            file_md5 = config.get('update', 'md5', fallback='')

            if not all([new_version, download_url, file_md5]):
                return False

            if self._version_compare(new_version):
                return self._perform_update(download_url, file_md5)

        except Exception as e:
            logging.error(f"更新检查失败: {str(e)}")
        return False

    def _version_compare(self, new_version):
        current = [int(x) for x in self.current_version.split('.')]
        new_ver = [int(x) for x in new_version.split('.')]
        return new_ver > current

    def _download_file(self, filename):
        try:
            url = f"{self.update_url}{filename}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                temp_path = os.path.join(self.temp_dir, filename)
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                return temp_path
        except requests.exceptions.RequestException as e:
            logging.error(f"下载失败: {str(e)}")
        return None

    def _perform_update(self, url, expected_md5):
        try:
            update_file = self._download_file(url.split('/')[-1])
            if not update_file:
                return False

            if not self._verify_file(update_file, expected_md5):
                os.remove(update_file)
                return False

            self._create_update_script(update_file)
            if messagebox.askyesno("发现新版本", "检测到新版本，是否立即更新？"):
                self._launch_updater()
                return True
        except Exception as e:
            logging.error(f"更新失败: {str(e)}")
        return False

    def _verify_file(self, filepath, expected_md5):
        with open(filepath, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash == expected_md5

    def _create_update_script(self, update_file):
        script = f"""@echo off
timeout /t 3 /nobreak >nul
taskkill /F /PID {os.getpid()} >nul 2>&1
move /Y "{update_file}" "{sys.executable}" >nul 2>&1
start "" "{sys.executable}"
del %0
"""
        bat_path = os.path.join(self.temp_dir, "auto_update.bat")
        with open(bat_path, 'w') as f:
            f.write(script)
        return bat_path

    def _launch_updater(self):
        bat_path = os.path.join(self.temp_dir, "auto_update.bat")
        subprocess.Popen(['cmd', '/C', bat_path], shell=True)
        sys.exit()


# ===================== 主程序模块 =====================
class ImageOptimizer:
    def __init__(self, root):
        self.root = root
        self.root.title("尘飞图片压缩工具1.1")
        self.root.geometry("1000x700")

        # 初始化配置
        self.selected_files = []
        self.output_folder = "CFOK"
        self.report_folder = "TJSJ"
        self.total_saved_file = "total_saved.txt"
        self.usage_count_file = "usage_count.txt"
        self.start_time = None
        self.time_records = []
        self.processing = False

        # 自动更新组件
        self.current_version = "1.1"
        self.updater = AutoUpdater(self.current_version)

        # 创建界面元素
        self.create_widgets()

        # 加载历史数据
        self.total_saved_gb = self.load_total_saved()
        self.usage_count = self.load_usage_count()

        # 启动更新检查
        self.check_for_update()

        # 显示使用说明
        self.show_usage_instructions()

    # ===================== 数据持久化方法 =====================
    def get_root_dir(self):
        """获取程序根目录路径"""
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return base_dir

    def load_total_saved(self):
        """加载历史累计节省空间"""
        root_dir = self.get_root_dir()
        total_path = os.path.join(root_dir, self.total_saved_file)

        try:
            with open(total_path, "r") as f:
                return float(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0.0

    def save_total_saved(self, value):
        """保存累计节省空间"""
        root_dir = self.get_root_dir()
        total_path = os.path.join(root_dir, self.total_saved_file)

        with open(total_path, "w") as f:
            f.write(f"{value:.6f}")

    def load_usage_count(self):
        """加载使用次数"""
        root_dir = self.get_root_dir()
        usage_path = os.path.join(root_dir, self.usage_count_file)

        try:
            with open(usage_path, "r") as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            with open(usage_path, "w") as f:
                f.write("0")
            return 0

    def save_usage_count(self):
        """保存使用次数"""
        root_dir = self.get_root_dir()
        usage_path = os.path.join(root_dir, self.usage_count_file)

        with open(usage_path, "w") as f:
            f.write(str(self.usage_count))

    # ===================== 界面相关方法 =====================
    def check_for_update(self):
        try:
            Thread(target=self._async_check_update, daemon=True).start()
        except Exception as e:
            logging.error(f"更新线程启动失败: {str(e)}")

    def _async_check_update(self):
        if self.updater.check_update():
            self.root.after(100, lambda: messagebox.showinfo("提示", "更新已准备就绪，重启后生效"))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧操作面板
        left_panel = ttk.Frame(main_frame, width=700)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧说明面板
        self.create_info_panel(main_frame)

        # 左侧内容
        self.create_left_panel(left_panel)

    def create_info_panel(self, parent):
        info_panel = ttk.Frame(parent, width=300)
        info_panel.pack(side=tk.RIGHT, fill=tk.BOTH)

        container = ttk.Frame(info_panel)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(container, text="使用说明", font=('微软雅黑', 14, 'bold')).pack(anchor=tk.W)

        info_text = """【功能说明】
- 选择图片文件：选择要优化的图片文件。
- 清空列表：清空已选择的文件列表。
- 开始优化：开始优化已选择的图片文件。
- 替换原文件：将优化后的文件替换原文件，并删除CFOK目录。
- 替换目录所有：批量处理选定目录及其所有子目录中的图片文件。

【注意事项】
- 在执行替换原文件或批量处理操作前，请务必对重要数据进行备份。
- 非JPG格式的图片文件在优化过程中会被转换为JPG格式。
- 替换原文件和批量处理操作会永久删除原始图片文件，请谨慎操作。
- 自动更新功能需要网络连接，请确保有网络的情况下运行程序以检查更新。
- 统计文件在程序目录里查看 开发维护：ChenFei。"""

        text_widget = tk.Text(container, wrap=tk.WORD, font=('微软雅黑', 10),
                              height=15, padx=10, pady=10, bg="#f0f0f0")
        text_widget.insert(tk.END, info_text)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

    def create_left_panel(self, parent):
        # 文件选择区域
        file_frame = ttk.Frame(parent)
        file_frame.pack(pady=10, fill=tk.X)

        self.select_btn = ttk.Button(file_frame, text="选择图片文件", command=self.select_files)
        self.select_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(file_frame, text="清空列表", command=self.clear_files)
        self.clear_btn.pack(side=tk.LEFT)

        # 文件列表
        self.file_list = ttk.Treeview(parent,
                                      columns=("文件名", "原始大小", "优化后大小", "压缩率"),
                                      show="headings",
                                      selectmode="extended",
                                      height=15
                                      )
        columns = {
            "文件名": 300,
            "原始大小": 120,
            "优化后大小": 120,
            "压缩率": 100
        }
        for col, width in columns.items():
            self.file_list.heading(col, text=col)
            self.file_list.column(col, width=width, anchor='center')
        self.file_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 优化选项
        option_frame = ttk.LabelFrame(parent, text="优化选项")
        option_frame.pack(pady=10, fill=tk.X, padx=10)

        self.quality_label = ttk.Label(option_frame, text="压缩质量（1-100）:")
        self.quality_label.pack(side=tk.LEFT, padx=5)
        self.quality_var = tk.IntVar(value=60)
        self.quality_spin = ttk.Spinbox(
            option_frame,
            from_=1,
            to=100,
            textvariable=self.quality_var,
            width=5
        )
        self.quality_spin.pack(side=tk.LEFT, padx=5)

        # 操作按钮框架
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)

        self.optimize_btn = ttk.Button(btn_frame, text="开始优化", command=self.start_optimization)
        self.optimize_btn.pack(side=tk.LEFT, padx=5)

        self.replace_btn = ttk.Button(btn_frame, text="替换原文件", command=self.replace_original_files)
        self.replace_btn.pack(side=tk.LEFT, padx=5)

        self.replace_all_btn = ttk.Button(btn_frame, text="替换目录所有", command=self.replace_all_in_directory)
        self.replace_all_btn.pack(side=tk.LEFT)

    # ===================== 文件操作方法 =====================
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=(("图片文件", "*.jpg;*.jpeg;*.png;*.bmp"), ("所有文件", "*.*"))
        )
        if files:
            self.selected_files.extend(files)
            self.update_file_list()

    def clear_files(self):
        self.selected_files = []
        for item in self.file_list.get_children():
            self.file_list.delete(item)

    def update_file_list(self):
        self.file_list.delete(*self.file_list.get_children())
        for file in self.selected_files:
            file_size = os.path.getsize(file) / 1024
            self.file_list.insert("", "end", values=(
                os.path.basename(file),
                f"{file_size:.2f} KB",
                "待优化",
                "0%"
            ))

    # ===================== 批量处理功能 =====================
    def replace_all_in_directory(self):
        warning_msg = """警告：此操作将会替换选定目录及其所有子目录中的图片文件！

【危险操作须知】
1. 将会永久删除所有原始图片文件
2. 所有BMP/PNG文件将被转换为JPG格式
3. 原目录结构中的CFOK文件夹将被清除
4. 此操作不可撤销，请务必提前备份！"""
        if not messagebox.askyesno("高危操作确认", warning_msg, icon='warning'):
            return

        directory = filedialog.askdirectory(title="选择要处理的根目录")
        if not directory:
            return

        all_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    all_files.append(os.path.join(root, file))

        if not all_files:
            messagebox.showinfo("提示", "所选目录中没有找到图片文件")
            return

        confirm_msg = f"共发现 {len(all_files)} 个图片文件，是否开始批量处理？"
        if not messagebox.askyesno("确认操作", confirm_msg):
            return

        self.disable_buttons()
        self.processing = True
        self.start_time = time.time()
        self.show_batch_progress(len(all_files))
        Thread(target=self.process_batch_files, args=(all_files, directory)).start()

    def disable_buttons(self):
        for btn in [self.select_btn, self.clear_btn,
                    self.optimize_btn, self.replace_btn, self.replace_all_btn]:
            btn.config(state=tk.DISABLED)

    def show_batch_progress(self, total_files):
        self.batch_progress = tk.Toplevel(self.root)
        self.batch_progress.title("批量处理进度")
        self.batch_progress.geometry("500x250")

        self.batch_bar = ttk.Progressbar(self.batch_progress,
                                         orient="horizontal", length=450, mode="determinate")
        self.batch_bar.pack(pady=10)
        self.batch_bar["maximum"] = total_files

        info_frame = ttk.Frame(self.batch_progress)
        info_frame.pack(pady=5)
        ttk.Label(info_frame, text="总文件数:").pack(side=tk.LEFT)
        self.total_files_label = ttk.Label(info_frame, text=str(total_files))
        self.total_files_label.pack(side=tk.LEFT, padx=5)
        ttk.Label(info_frame, text="已处理:").pack(side=tk.LEFT, padx=10)
        self.processed_label = ttk.Label(info_frame, text="0")
        self.processed_label.pack(side=tk.LEFT)

        time_frame = ttk.Frame(self.batch_progress)
        time_frame.pack(pady=5)
        ttk.Label(time_frame, text="已用时间:").pack(side=tk.LEFT)
        self.batch_elapsed = ttk.Label(time_frame, text="00:00:00")
        self.batch_elapsed.pack(side=tk.LEFT, padx=5)
        ttk.Label(time_frame, text="剩余时间:").pack(side=tk.LEFT, padx=10)
        self.batch_remaining = ttk.Label(time_frame, text="--:--:--")
        self.batch_remaining.pack()

        self.current_file = ttk.Label(self.batch_progress,
                                      text="当前文件：无", wraplength=400)
        self.current_file.pack(pady=5)

        self.cancel_btn = ttk.Button(self.batch_progress,
                                     text="取消处理", command=self.cancel_batch_processing)
        self.cancel_btn.pack(pady=5)

        self.batch_progress.protocol("WM_DELETE_WINDOW", self.cancel_batch_processing)

    # ===================== 核心优化逻辑 =====================
    def start_optimization(self):
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要优化的图片文件！")
            return

        self.processing = True
        self.start_time = time.time()

        self.progress = tk.Toplevel(self.root)
        self.progress.title("优化进度")
        self.progress.geometry("450x180")

        self.progress_bar = ttk.Progressbar(self.progress,
                                            orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        time_frame = ttk.Frame(self.progress)
        time_frame.pack(pady=5)
        ttk.Label(time_frame, text="已用时间:").pack(side=tk.LEFT)
        self.elapsed_label = ttk.Label(time_frame, text="00:00:00")
        self.elapsed_label.pack(side=tk.LEFT, padx=10)
        ttk.Label(time_frame, text="剩余时间:").pack(side=tk.LEFT)
        self.remaining_label = ttk.Label(time_frame, text="--:--:--")
        self.remaining_label.pack(side=tk.LEFT)

        self.file_counter = ttk.Label(self.progress, text="正在处理第 0 / 0 个文件")
        self.file_counter.pack(pady=5)

        self.disable_buttons()
        self.root.after(100, self.process_images)

    def process_images(self):
        total_files = len(self.selected_files)
        processed_count = 0
        saved_gb = 0.0
        output_dirs = set()

        while processed_count < total_files and self.processing:
            index = processed_count
            file_path = self.selected_files[index]
            try:
                # 准备输出路径
                file_dir = os.path.dirname(file_path)
                output_dir = os.path.join(file_dir, self.output_folder)
                os.makedirs(output_dir, exist_ok=True)
                output_dirs.add(output_dir)

                file_name = os.path.basename(file_path)
                name, ext = os.path.splitext(file_name)
                output_path = os.path.join(output_dir, f"{name}.jpg")

                # 转换并优化图片
                with Image.open(file_path) as img:
                    original_size = os.path.getsize(file_path)
                    img.convert("RGB").save(
                        output_path,
                        "JPEG",
                        quality=self.quality_var.get(),
                        optimize=True,
                        progressive=True
                    )
                    optimized_size = os.path.getsize(output_path)
                    saved_gb += (original_size - optimized_size) / (1024 ** 3)

                    # 更新列表
                    item_id = self.file_list.get_children()[index]
                    self.file_list.set(item_id, "优化后大小", f"{optimized_size / 1024:.2f} KB")
                    self.file_list.set(item_id, "压缩率",
                                       f"{(original_size - optimized_size) / original_size * 100:.1f}%")

                # 更新进度
                processed_count += 1
                progress = (processed_count / total_files) * 100
                self.progress_bar["value"] = progress
                self.file_counter.config(text=f"正在处理第 {processed_count} / {total_files} 个文件")
                self.root.update()  # 强制更新GUI

                # 计算时间
                elapsed = time.time() - self.start_time
                avg_time = elapsed / processed_count
                remaining = avg_time * (total_files - processed_count)
                self.update_time_display(elapsed, remaining)

            except Exception as e:
                logging.error(f"处理文件 {file_name} 时出错：{str(e)}")
                continue

        if self.processing:
            self.finish_optimization(saved_gb, output_dirs)

    # ===================== 共用方法 =====================
    def finish_optimization(self, saved_gb, output_dirs):
        self.processing = False
        self.progress.destroy()

        # 更新累计数据
        self.total_saved_gb += saved_gb
        self.save_total_saved(self.total_saved_gb)
        self.usage_count += 1
        self.save_usage_count()

        # 生成报告
        report_path = self.generate_summary_report(saved_gb)
        self.show_report_window(report_path)

        # 打开目录
        for directory in output_dirs:
            self.open_file(directory)
        self.enable_buttons()

    def generate_summary_report(self, saved_gb):
        """生成统计报告"""
        root_dir = self.get_root_dir()
        report_path = os.path.join(root_dir, "summary.txt")

        saved_mb = saved_gb * 1024  # 转换为MB
        content = [
            "=" * 40,
            "尘飞图片优化统计报告",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 40,
            f"本次节省空间：{saved_mb:.2f} MB",
            f"累计节省空间：{self.total_saved_gb:.4f} GB",
            f"总使用次数：{self.usage_count} 次",
            "=" * 40
        ]

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        return report_path

    def show_report_window(self, report_path):
        """显示报告窗口"""
        report_win = tk.Toplevel(self.root)
        report_win.title("优化报告详情")
        report_win.geometry("600x400")

        scrollbar = ttk.Scrollbar(report_win)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_box = tk.Text(report_win, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                           padx=15, pady=15, font=('微软雅黑', 10))
        text_box.pack(fill=tk.BOTH, expand=True)

        with open(report_path, "r", encoding="utf-8") as f:
            text_box.insert(tk.END, f.read())
        text_box.configure(state=tk.DISABLED)
        scrollbar.config(command=text_box.yview)

        # 添加关闭按钮
        btn_frame = ttk.Frame(report_win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="关闭", command=report_win.destroy).pack()

    def update_time_display(self, elapsed, remaining):
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        self.elapsed_label.config(text=elapsed_str)
        if remaining >= 0:
            self.remaining_label.config(text=time.strftime("%H:%M:%S", time.gmtime(remaining)))
        else:
            self.remaining_label.config(text="--:--:--")

    def replace_original_files(self):
        if not messagebox.askyesno("确认", "确定要替换原始文件并删除CFOK目录吗？"):
            return

        try:
            processed_dirs = set()
            for file_path in self.selected_files:
                file_dir = os.path.dirname(file_path)
                cfok_dir = os.path.join(file_dir, self.output_folder)
                if os.path.exists(cfok_dir):
                    # 移动并替换文件
                    for opt_file in os.listdir(cfok_dir):
                        src_path = os.path.join(cfok_dir, opt_file)
                        base_name = os.path.splitext(opt_file)[0]

                        # 删除原始文件
                        for old_file in glob.glob(os.path.join(file_dir, f"{base_name}.*")):
                            if old_file != src_path and os.path.isfile(old_file):
                                try:
                                    os.remove(old_file)
                                except Exception as e:
                                    logging.error(f"删除失败: {e}")

                        # 移动优化文件
                        dest_path = os.path.join(file_dir, opt_file)
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        shutil.move(src_path, dest_path)

                    # 删除CFOK目录
                    shutil.rmtree(cfok_dir)
                    processed_dirs.add(file_dir)

            # 完成操作
            self.clear_files()
            messagebox.showinfo("完成", "文件替换完成，CFOK目录已删除")
            for directory in processed_dirs:
                self.open_file(directory)

        except Exception as e:
            messagebox.showerror("错误", f"替换失败：{str(e)}")

    def process_batch_files(self, file_list, directory):
        """批量处理线程方法"""
        total = len(file_list)
        processed = 0
        saved_gb = 0.0
        output_dirs = set()

        for i, file_path in enumerate(file_list):
            if not self.processing:
                break
            try:
                # 更新当前文件显示
                self.current_file.config(text=f"正在处理：{os.path.basename(file_path)}")

                # 处理逻辑（与单文件处理相同）
                file_dir = os.path.dirname(file_path)
                output_dir = os.path.join(file_dir, self.output_folder)
                os.makedirs(output_dir, exist_ok=True)
                output_dirs.add(output_dir)

                name, ext = os.path.splitext(os.path.basename(file_path))
                output_path = os.path.join(output_dir, f"{name}.jpg")

                with Image.open(file_path) as img:
                    original_size = os.path.getsize(file_path)
                    img.convert("RGB").save(
                        output_path,
                        "JPEG",
                        quality=self.quality_var.get(),
                        optimize=True
                    )
                    optimized_size = os.path.getsize(output_path)
                    saved_gb += (original_size - optimized_size) / (1024 ** 3)

                # 删除原始文件
                os.remove(file_path)
                # 移动优化文件
                shutil.move(output_path, file_path)

                # 更新进度
                processed += 1
                self.batch_bar.step(1)
                self.processed_label.config(text=str(processed))

                # 计算时间
                elapsed = time.time() - self.start_time
                avg_time = elapsed / processed if processed > 0 else 0
                remaining = avg_time * (total - processed)
                self.update_batch_time(elapsed, remaining)

            except Exception as e:
                logging.error(f"批量处理失败：{str(e)}")
                continue

        # 完成处理
        self.finish_batch_processing(saved_gb, output_dirs, directory)

    def update_batch_time(self, elapsed, remaining):
        """更新批量处理时间显示"""
        self.batch_elapsed.config(text=time.strftime("%H:%M:%S", time.gmtime(elapsed)))
        self.batch_remaining.config(text=time.strftime("%H:%M:%S", time.gmtime(remaining)))

    def cancel_batch_processing(self):
        """取消批量处理"""
        self.processing = False
        self.batch_progress.destroy()
        messagebox.showinfo("提示", "已取消批量处理")
        self.enable_buttons()

    def finish_batch_processing(self, saved_gb, output_dirs, directory):
        """完成批量处理"""
        self.processing = False
        self.batch_progress.destroy()

        # 更新累计数据
        self.total_saved_gb += saved_gb
        self.save_total_saved(self.total_saved_gb)
        self.usage_count += 1
        self.save_usage_count()

        # 生成报告
        report_path = self.generate_summary_report(saved_gb)
        self.show_report_window(report_path)

        # 删除所有子目录下的CFOK目录
        for root, dirs, _ in os.walk(directory):
            for dir_name in dirs:
                if dir_name == self.output_folder:
                    cfok_dir = os.path.join(root, dir_name)
                    if os.path.exists(cfok_dir):
                        shutil.rmtree(cfok_dir)

        messagebox.showinfo("完成", "批量处理已完成，所有子目录下的CFOK目录已删除！")
        self.enable_buttons()

    def enable_buttons(self):
        """恢复按钮状态"""
        for btn in [self.select_btn, self.clear_btn,
                    self.optimize_btn, self.replace_btn, self.replace_all_btn]:
            btn.config(state=tk.NORMAL)

    def open_file(self, path):
        """打开文件/目录"""
        if os.path.isdir(path):
            if sys.platform == "win32":
                os.startfile(path)
            else:
                os.system(f'open "{path}"' if sys.platform == "darwin" else f'xdg-open "{path}"')

    def show_usage_instructions(self):
        """显示使用说明窗口"""
        usage_win = tk.Toplevel(self.root)
        usage_win.title("使用说明")
        usage_win.geometry("600x400")

        scrollbar = ttk.Scrollbar(usage_win)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_box = tk.Text(usage_win, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                           padx=15, pady=15, font=('微软雅黑', 10))
        text_box.pack(fill=tk.BOTH, expand=True)

        usage_text = """尘飞图片压缩工具 使用说明和注意事项
一、概述
尘飞图片压缩工具是一款用于批量压缩优化图片的工具。可以大大节省您的硬盘空间，它支持选择单个或多个图片文件进行优化，并提供了批量处理整个目录及其子目录中的图片压缩优化的功能。此外，该工具还具备自动更新功能，确保用户始终使用最新版本。

二、安装与启动
1.下载：尘飞航模淘宝店下载最新的安装包。
2.安装：直接运行EXE。

三、界面介绍
.主界面：
  .左侧操作面板：包含文件选择、清空列表、优化选项和操作按钮。
  .右侧说明面板：显示使用说明和操作提醒。
.文件选择区域：
  .选择图片文件：点击“选择图片文件”按钮，选择需要优化的图片文件。
  .清空列表：点击“清空列表”按钮，清空已选择的文件列表。
.文件列表：
  .显示已选择的文件及其原始大小、优化后大小和压缩率。
.优化选项：
  .压缩质量：设置压缩质量（1-100），默认为60。
.操作按钮：
  .开始优化：开始优化已选择的图片文件。
  .替换原文件：将优化后的文件替换原文件，并删除CFOK目录。
  .替换目录所有：批量处理选定目录及其所有子目录中的图片文件。

四、功能说明
1.选择图片文件：
  .点击“选择图片文件”按钮，选择一个或多个图片文件（支持JPG、JPEG、PNG、BMP格式）。
  .选择的文件会显示在文件列表中。
2.清空列表：
  .点击“清空列表”按钮，清空已选择的文件列表。
3.开始优化：
  .点击“开始优化”按钮，开始优化已选择的图片文件。
  .优化过程中会显示进度条和时间估计。
  .优化完成后，会生成统计报告并显示单次&累计节省的空间和总共使用次数。
4.替换原文件：
  .点击“替换原文件”按钮，将优化后的文件替换原文件，并删除CFOK目录。
  .请谨慎操作，此操作不可撤销。
5.替换目录所有：  
  .点击“替换目录所有”按钮，批量处理选定目录及其所有子目录中的图片文件。
  .会弹出警告对话框，确认操作后开始批量处理。
  .批量处理过程中会显示进度条和时间估计。
  .处理完成后，会生成统计报告。

五、注意事项
1.数据备份：
  .在执行替换原文件或批量处理操作前，请务必对重要数据进行备份，以防误操作导致数据丢失。
2.文件格式转换：
  .非JPG格式的图片文件（如PNG、BMP）在优化过程中会被转换为JPG格式。
3.文件删除：
  .替换原文件和批量处理操作会永久删除原始图片文件，请谨慎操作。
4.网络连接：
  .自动更新功能需要网络连接，确保在有网络的情况下运行程序以检查更新。
异常处理：
如果在优化过程中遇到错误，请查看日志文件 image_optimizer.log 以获取详细信息。

六、日志记录
日志文件路径：image_optimizer.log
日志文件记录了程序运行过程中的关键信息和错误信息，便于调试和维护。

七、技术支持
如果在使用过程中遇到问题，请联系尘飞航模淘宝店。
联系方式：[9597890@qq.com]。"""

        text_box.insert(tk.END, usage_text)
        text_box.configure(state=tk.DISABLED)
        scrollbar.config(command=text_box.yview)

        # 添加关闭按钮
        btn_frame = ttk.Frame(usage_win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="关闭", command=usage_win.destroy).pack()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageOptimizer(root)
    root.mainloop()
