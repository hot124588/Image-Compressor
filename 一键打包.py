import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import sys
import re
import time
import threading
import json
import glob
from datetime import timedelta


class PyInstallerPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("专业EXE打包工具 v4.1")
        self.geometry("850x700")
        self.config_file = os.path.join(os.getcwd(), "pyinstaller_pro_config.json")
        self.history_file = os.path.join(os.getcwd(), "pyinstaller_pro_history.json")
        self.load_history()
        self.create_widgets()
        self.setup_validations()
        self.check_environment()

    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 文件设置区
        file_frame = ttk.LabelFrame(main_frame, text="核心配置")
        file_frame.grid(row=0, column=0, sticky="ew", pady=5)
        self.create_file_section(file_frame)

        # 产品信息区
        product_frame = ttk.LabelFrame(main_frame, text="产品信息")
        product_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.create_product_section(product_frame)

        # 高级设置区
        advanced_frame = ttk.LabelFrame(main_frame, text="高级选项")
        advanced_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.create_advanced_section(advanced_frame)
        
        # 进度显示区
        progress_frame = ttk.LabelFrame(main_frame, text="打包进度")
        progress_frame.grid(row=3, column=0, sticky="ew", pady=5)
        self.create_progress_section(progress_frame)

        # 操作按钮区
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, pady=15)
        ttk.Button(btn_frame, text="开始打包", command=self.start_build, width=15).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="清理缓存", command=self.clean_build, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="加载配置", command=self.load_config, width=15).grid(row=0, column=3, padx=5)
        ttk.Button(btn_frame, text="查看日志", command=self.show_log_viewer, width=15).grid(row=0, column=4, padx=5)
        ttk.Button(btn_frame, text="帮助说明", command=self.show_help, width=15).grid(row=0, column=5, padx=5)

    def create_file_section(self, parent):
        # Python文件选择
        ttk.Label(parent, text="主程序文件*:").grid(row=0, column=0, padx=5, sticky="w")
        self.py_entry = ttk.Entry(parent, width=65)
        self.py_entry.grid(row=0, column=1, padx=5)
        ttk.Button(parent, text="浏览", command=lambda: self.select_file(self.py_entry, [("Python文件", "*.py")])).grid(
            row=0, column=2)

        # 输出目录
        ttk.Label(parent, text="输出路径*:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.output_entry = ttk.Entry(parent, width=65)
        self.output_entry.insert(0, os.path.join(os.getcwd(), "dist"))
        self.output_entry.grid(row=1, column=1, padx=5)
        ttk.Button(parent, text="选择", command=self.select_output_dir).grid(row=1, column=2)
        
        # 历史记录下拉菜单
        ttk.Label(parent, text="历史记录:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.history_var = tk.StringVar()
        self.history_combo = ttk.Combobox(parent, textvariable=self.history_var, width=63)
        self.history_combo.grid(row=2, column=1, padx=5, sticky="w")
        self.update_history_combo()
        self.history_combo.bind("<<ComboboxSelected>>", self.load_from_history)

    def create_product_section(self, parent):
        # 产品名称
        ttk.Label(parent, text="产品名称*:").grid(row=0, column=0, padx=5, sticky="w")
        self.product_entry = ttk.Entry(parent, width=40)
        self.product_entry.grid(row=0, column=1, padx=5)

        # 公司信息
        ttk.Label(parent, text="公司名称*:").grid(row=1, column=0, padx=5, sticky="w")
        self.company_entry = ttk.Entry(parent, width=40)
        self.company_entry.grid(row=1, column=1, padx=5)

        # 版本信息
        ttk.Label(parent, text="产品版本*:").grid(row=2, column=0, padx=5, sticky="w")
        self.version_entry = ttk.Entry(parent, width=40)
        self.version_entry.insert(0, "1.0.0.0")
        self.version_entry.grid(row=2, column=1, padx=5)

        # 版权信息
        ttk.Label(parent, text="版权声明*:").grid(row=3, column=0, padx=5, sticky="w")
        self.copyright_entry = ttk.Entry(parent, width=40)
        self.copyright_entry.grid(row=3, column=1, padx=5)

    def create_advanced_section(self, parent):
        # 图标设置
        ttk.Label(parent, text="程序图标:").grid(row=0, column=0, padx=5, sticky="w")
        self.icon_entry = ttk.Entry(parent, width=65)
        self.icon_entry.grid(row=0, column=1, padx=5)
        ttk.Button(parent, text="上传",
                   command=lambda: self.select_file(self.icon_entry, [("图标文件", "*.ico")])).grid(row=0, column=2)

        # 优化选项
        self.optimize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="优化EXE大小", variable=self.optimize_var).grid(row=1, column=0, padx=5, sticky="w")

        # 加密选项 - 使用PyInstaller的--key选项
        self.encrypt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="加密打包", variable=self.encrypt_var).grid(row=1, column=1, padx=5, sticky="w")
        
        # 添加额外的打包选项
        ttk.Label(parent, text="额外选项:").grid(row=2, column=0, padx=5, sticky="w")
        self.extra_options_entry = ttk.Entry(parent, width=65)
        self.extra_options_entry.grid(row=2, column=1, padx=5, columnspan=2, sticky="ew")
        ttk.Label(parent, text="(例如: --uac-admin --win-private-assemblies)").grid(row=3, column=1, padx=5, sticky="w")
        
        # 添加额外的导入模块
        ttk.Label(parent, text="额外导入模块:").grid(row=4, column=0, padx=5, sticky="w")
        self.extra_imports_entry = ttk.Entry(parent, width=65)
        self.extra_imports_entry.grid(row=4, column=1, padx=5, columnspan=2, sticky="ew")
        ttk.Label(parent, text="(用逗号分隔，例如: PIL,requests,numpy)").grid(row=5, column=1, padx=5, sticky="w")
        
    def create_progress_section(self, parent):
        # 进度条
        ttk.Label(parent, text="打包进度:").grid(row=0, column=0, padx=5, sticky="w")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, orient="horizontal", length=600, mode="determinate", variable=self.progress_var)
        self.progress_bar.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 状态标签
        ttk.Label(parent, text="状态:").grid(row=1, column=0, padx=5, sticky="w")
        self.status_var = tk.StringVar(value="等待开始")
        ttk.Label(parent, textvariable=self.status_var).grid(row=1, column=1, padx=5, sticky="w")
        
        # 计时器标签
        ttk.Label(parent, text="用时:").grid(row=2, column=0, padx=5, sticky="w")
        self.time_var = tk.StringVar(value="00:00:00")
        ttk.Label(parent, textvariable=self.time_var).grid(row=2, column=1, padx=5, sticky="w")

    def select_file(self, entry_widget, file_types):
        filename = filedialog.askopenfilename(filetypes=file_types)
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def select_output_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirname)

    def setup_validations(self):
        # 版本号四段式验证
        version_val = self.register(lambda s: re.match(r"^\d+\.\d+\.\d+\.\d+$", s) is not None)
        self.version_entry.config(validate="focusout", validatecommand=(version_val, '%P'))

        # 产品名称格式验证
        product_val = self.register(lambda s: re.match(r"^[\w\-\s]{3,50}$", s) is not None)
        self.product_entry.config(validate="focusout", validatecommand=(product_val, '%P'))

    def validate_inputs(self):
        """输入校验[3,9](@ref)"""
        errors = []
        required_fields = {
            "主程序文件": self.py_entry.get(),
            "输出路径": self.output_entry.get(),
            "产品名称": self.product_entry.get(),
            "公司名称": self.company_entry.get(),
            "产品版本": self.version_entry.get(),
            "版权声明": self.copyright_entry.get()
        }

        for field, value in required_fields.items():
            if not value.strip():
                errors.append(f"{field}不能为空")

        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", self.version_entry.get()):
            errors.append("版本号必须为四段式格式（例如1.0.0.0）")

        if self.py_entry.get() and not os.path.exists(self.py_entry.get()):
            errors.append("主程序文件路径不存在")

        return errors

    def generate_version_info(self):
        """生成Windows版本资源文件[1,3](@ref)"""
        version_tuple = tuple(map(int, self.version_entry.get().split(".")))
        return f"""# UTF-8
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={version_tuple},
        prodvers={version_tuple},
        mask=0x3f,
        flags=0x0,
        OS=0x4,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable(
                '040904B0', [
                    StringStruct('ProductName', '{self.product_entry.get()}'),
                    StringStruct('CompanyName', '{self.company_entry.get()}'),
                    StringStruct('FileDescription', '专业打包工具生成'),
                    StringStruct('FileVersion', '{self.version_entry.get()}'),
                    StringStruct('LegalCopyright', '{self.copyright_entry.get()}'),
                    StringStruct('ProductVersion', '{self.version_entry.get()}')
                ])
        ]),
        VarFileInfo([VarStruct('Translation', [0x409, 1200])])
    ]
)
"""

    def start_build(self):
        """执行打包流程[4,7](@ref)"""
        if errors := self.validate_inputs():
            messagebox.showerror("输入错误", "\n".join(errors))
            return

        # 保存当前配置到历史记录
        self.save_to_history()

        # 重置进度条和状态
        self.progress_var.set(0)
        self.status_var.set("准备打包...")
        self.time_var.set("00:00:00")
        
        # 在新线程中执行打包，避免UI卡顿
        threading.Thread(target=self._build_process, daemon=True).start()
    
    def _build_process(self):
        """在后台线程中执行打包过程"""
        start_time = time.time()
        timer_running = True
        
        # 启动计时器线程
        def update_timer():
            while timer_running:
                elapsed = time.time() - start_time
                time_str = str(timedelta(seconds=int(elapsed)))
                self.time_var.set(time_str)
                time.sleep(0.5)
        
        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
        
        try:
            # 更新状态
            self.status_var.set("生成版本信息...")
            self.progress_var.set(5)
            
            # 生成临时版本文件
            with open("version_info.txt", "w", encoding="utf-8") as f:
                f.write(self.generate_version_info())
            
            self.status_var.set("构建打包命令...")
            self.progress_var.set(10)
            
            # 构建打包命令
            # 添加Tcl/Tk资源路径
            tcl_dir = os.path.join(sys.base_exec_prefix, 'tcl')
            tk_dir = os.path.join(sys.base_exec_prefix, 'tk')
            
            # 检查Tcl/Tk目录是否存在，如果不存在则尝试替代路径
            if not os.path.exists(tcl_dir):
                # 尝试在lib目录下查找
                lib_tcl_dir = os.path.join(sys.base_exec_prefix, 'lib', 'tcl')
                if os.path.exists(lib_tcl_dir):
                    tcl_dir = lib_tcl_dir
                else:
                    # 如果找不到，使用tkinter目录
                    tkinter_dir = os.path.join(sys.base_exec_prefix, 'lib', 'tkinter')
                    if os.path.exists(tkinter_dir):
                        tcl_dir = tkinter_dir
                    else:
                        raise FileNotFoundError(f"Tcl目录不存在: {tcl_dir}")
            
            if not os.path.exists(tk_dir):
                # 尝试在lib目录下查找
                lib_tk_dir = os.path.join(sys.base_exec_prefix, 'lib', 'tk')
                if os.path.exists(lib_tk_dir):
                    tk_dir = lib_tk_dir
                else:
                    # 如果找不到，使用tkinter目录
                    tkinter_dir = os.path.join(sys.base_exec_prefix, 'lib', 'tkinter')
                    if os.path.exists(tkinter_dir):
                        tk_dir = tkinter_dir
                    else:
                        # 如果还是找不到，使用tcl目录（因为有些系统中tk资源可能包含在tcl目录中）
                        tk_dir = tcl_dir
            
            # 修改资源路径的指定方式，确保在Windows上正确工作
            if os.name == 'nt':  # Windows系统
                tcl_data = f"{tcl_dir};tcl"
                tk_data = f"{tk_dir};tk"
            else:  # 类Unix系统
                tcl_data = f"{tcl_dir}{os.pathsep}tcl"
                tk_data = f"{tk_dir}{os.pathsep}tk"
            
            cmd = [
                "pyinstaller",
                "--onefile",
                f"--add-data={tcl_data}",
                f"--add-data={tk_data}",
                f"--distpath={self.output_entry.get()}",
                f"--workpath={os.path.join(self.output_entry.get(), 'build')}",
                "--clean",
                "--collect-all", "tkinter",
                "--hidden-import", "tkinter",
                "--hidden-import", "_tkinter"
            ]
            
            # 添加优化选项
            if self.optimize_var.get():
                cmd.extend([
                    "--noupx",  # 禁用UPX压缩，有时会导致文件变大
                    "--exclude-module=matplotlib",  # 只排除不需要的大型模块
                    # 不再排除numpy，因为它是必需的
                    "--exclude-module=scipy",
                    "--exclude-module=pandas"
                ])
            
            # 始终添加numpy作为隐藏导入
            cmd.extend(["--hidden-import", "numpy"])

            # 移除加密选项的实现，因为PyInstaller不支持--key参数
            
            # 添加基本选项
            cmd.extend([
                f"--name={self.product_entry.get().replace(' ', '_')}",
                f"--version-file=version_info.txt",
                f"--icon={self.icon_entry.get()}" if self.icon_entry.get() else ""
            ])
            
            # 始终添加无控制台参数
            cmd.append("--noconsole")
            
            # 添加额外的打包选项
            if self.extra_options_entry.get().strip():
                cmd.extend(self.extra_options_entry.get().strip().split())
            
            # 添加额外的导入模块
            if self.extra_imports_entry.get().strip():
                for module in self.extra_imports_entry.get().strip().split(','):
                    cmd.extend(['--hidden-import', module.strip()])
            
            # 添加主程序文件
            cmd.append(self.py_entry.get())
            
            # 过滤掉空字符串
            cmd = [item for item in cmd if item]
            
            self.status_var.set("开始打包...")
            self.progress_var.set(15)
            
            # 创建进程并监控输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 监控进程输出并更新进度
            output_lines = []
            for line in process.stdout:
                output_lines.append(line.strip())
                
                # 根据输出更新进度条
                if "COLLECT" in line:
                    self.progress_var.set(50)
                    self.status_var.set("收集依赖项...")
                elif "BUNDLE" in line:
                    self.progress_var.set(70)
                    self.status_var.set("打包文件...")
                elif "BOOTLOADER" in line:
                    self.progress_var.set(85)
                    self.status_var.set("添加启动程序...")
                
                # 更新UI
                self.update()
            
            # 等待进程完成
            process.wait()
            
            # 停止计时器
            timer_running = False
            
            # 检查结果
            if process.returncode == 0:
                self.progress_var.set(100)
                self.status_var.set("打包完成")
                
                # 成功处理
                output_dir = self.output_entry.get()
                if os.path.exists(output_dir):
                    os.startfile(output_dir)
                messagebox.showinfo("打包成功", f"生成路径：{output_dir}\n用时：{self.time_var.get()}")
            else:
                self.status_var.set("打包失败")
                error_msg = "\n".join(output_lines[-10:]) if output_lines else "未知错误"
                messagebox.showerror("打包错误", error_msg)
                
        except Exception as e:
            self.status_var.set("系统错误")
            messagebox.showerror("系统错误", str(e))
        finally:
            # 清理临时文件
            if os.path.exists("version_info.txt"):
                os.remove("version_info.txt")
            
            # 清理spec文件
            product_name = self.product_entry.get().replace(' ', '_')
            spec_file = f"{product_name}.spec"
            if os.path.exists(spec_file):
                try:
                    os.remove(spec_file)
                except Exception as e:
                    print(f"清理spec文件失败: {e}")

            # 清理__pycache__目录
            if os.path.exists("__pycache__"):
                try:
                    for root, dirs, files in os.walk("__pycache__", topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    os.rmdir("__pycache__")
                except Exception as e:
                    print(f"清理__pycache__目录失败: {e}")
            
            # 清理其他临时文件
            temp_files = ["warn-*.txt", "xref-*.html", "*.log"]
            for pattern in temp_files:
                for file in glob.glob(pattern):
                    try:
                        os.remove(file)
                    except Exception as e:
                        print(f"清理临时文件{file}失败: {e}")
            
            # 清理JSON配置文件
            json_files = [self.config_file, self.history_file]
            for json_file in json_files:
                if os.path.exists(json_file):
                    try:
                        os.remove(json_file)
                        print(f"已删除配置文件: {json_file}")
                    except Exception as e:
                        print(f"删除配置文件{json_file}失败: {e}")
            
            self.status_var.set("清理完成")
            self.progress_var.set(100)

    def clean_build(self):
        """清理构建缓存[3](@ref)"""
        build_dir = os.path.join(self.output_entry.get(), "build")
        if os.path.exists(build_dir):
            try:
                for root, dirs, files in os.walk(build_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(build_dir)
                messagebox.showinfo("清理完成", "临时文件已清除")
            except Exception as e:
                messagebox.showerror("清理失败", str(e))

    def check_environment(self):
        """检查Python环境和PyInstaller是否正确安装"""
        try:
            # 检查PyInstaller是否安装
            subprocess.run(["pyinstaller", "--version"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE, 
                         check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("环境错误", 
                               "未检测到PyInstaller，请先安装：\n" +
                               "pip install pyinstaller")

    def save_config(self):
        """保存当前配置到文件"""
        config = {
            "py_file": self.py_entry.get(),
            "output_dir": self.output_entry.get(),
            "product_name": self.product_entry.get(),
            "company_name": self.company_entry.get(),
            "version": self.version_entry.get(),
            "copyright": self.copyright_entry.get(),
            "icon_file": self.icon_entry.get(),
            "optimize": self.optimize_var.get(),
            "encrypt": self.encrypt_var.get(),
            "extra_options": self.extra_options_entry.get(),
            "extra_imports": self.extra_imports_entry.get()
        }
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("保存成功", "配置已保存")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def load_config(self):
        """从文件加载配置"""
        if not os.path.exists(self.config_file):
            messagebox.showwarning("加载失败", "未找到配置文件")
            return
            
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            self.py_entry.delete(0, tk.END)
            self.py_entry.insert(0, config.get("py_file", ""))
            
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, config.get("output_dir", ""))
            
            self.product_entry.delete(0, tk.END)
            self.product_entry.insert(0, config.get("product_name", ""))
            
            self.company_entry.delete(0, tk.END)
            self.company_entry.insert(0, config.get("company_name", ""))
            
            self.version_entry.delete(0, tk.END)
            self.version_entry.insert(0, config.get("version", "1.0.0.0"))
            
            self.copyright_entry.delete(0, tk.END)
            self.copyright_entry.insert(0, config.get("copyright", ""))
            
            self.icon_entry.delete(0, tk.END)
            self.icon_entry.insert(0, config.get("icon_file", ""))
            
            self.optimize_var.set(config.get("optimize", True))
            self.encrypt_var.set(config.get("encrypt", False))
            
            self.extra_options_entry.delete(0, tk.END)
            self.extra_options_entry.insert(0, config.get("extra_options", ""))
            
            self.extra_imports_entry.delete(0, tk.END)
            self.extra_imports_entry.insert(0, config.get("extra_imports", ""))
            
            messagebox.showinfo("加载成功", "配置已加载")
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    def show_log_viewer(self):
        """显示日志查看器窗口"""
        log_window = tk.Toplevel(self)
        log_window.title("打包日志查看器")
        log_window.geometry("800x600")
        
        # 创建文本框
        log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD)
        log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加关闭按钮
        ttk.Button(log_window, text="关闭", command=log_window.destroy).pack(pady=5)
        
        # 尝试读取日志文件
        try:
            with open("pyinstaller.log", "r", encoding="utf-8") as f:
                log_text.insert(tk.END, f.read())
        except FileNotFoundError:
            log_text.insert(tk.END, "未找到日志文件")
        except Exception as e:
            log_text.insert(tk.END, f"读取日志失败: {e}")
    
    def show_help(self):
        """显示帮助说明窗口"""
        # 导入帮助模块
        try:
            from help import HelpViewer
            help_window = HelpViewer(self)
        except Exception as e:
            messagebox.showerror("帮助加载失败", f"无法加载帮助文档: {e}")

    def save_to_history(self):
        """保存当前配置到历史记录"""
        current_config = {
            "py_file": self.py_entry.get(),
            "output_dir": self.output_entry.get(),
            "product_name": self.product_entry.get(),
            "company_name": self.company_entry.get(),
            "version": self.version_entry.get(),
            "copyright": self.copyright_entry.get(),
            "icon_file": self.icon_entry.get(),
            "optimize": self.optimize_var.get(),
            "encrypt": self.encrypt_var.get(),
            "extra_options": self.extra_options_entry.get(),
            "extra_imports": self.extra_imports_entry.get(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 检查是否已存在相同配置
        for i, item in enumerate(self.history):
            if item.get("product_name") == current_config["product_name"] and \
               item.get("version") == current_config["version"]:
                # 更新已存在的配置
                self.history[i] = current_config
                break
        else:
            # 添加新配置到历史记录
            self.history.insert(0, current_config)
            # 保持最多10条记录
            self.history = self.history[:10]
        
        # 保存到文件
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
            self.update_history_combo()
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def load_history(self):
        """加载历史记录"""
        self.history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"加载历史记录失败: {e}")

    def update_history_combo(self):
        """更新历史记录下拉菜单"""
        if hasattr(self, 'history_combo'):
            self.history_combo['values'] = [f"{h.get('product_name', '未命名')} - {h.get('version', '1.0.0.0')}" for h in self.history]

    def load_from_history(self, event=None):
        """从历史记录加载配置"""
        if not self.history or self.history_combo.current() < 0:
            return
            
        selected = self.history[self.history_combo.current()]
        
        # 加载配置
        self.py_entry.delete(0, tk.END)
        self.py_entry.insert(0, selected.get("py_file", ""))
        
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, selected.get("output_dir", ""))
        
        self.product_entry.delete(0, tk.END)
        self.product_entry.insert(0, selected.get("product_name", ""))
        
        self.company_entry.delete(0, tk.END)
        self.company_entry.insert(0, selected.get("company_name", ""))
        
        self.version_entry.delete(0, tk.END)
        self.version_entry.insert(0, selected.get("version", "1.0.0.0"))
        
        self.copyright_entry.delete(0, tk.END)
        self.copyright_entry.insert(0, selected.get("copyright", ""))
        
        self.icon_entry.delete(0, tk.END)
        self.icon_entry.insert(0, selected.get("icon_file", ""))
        
        self.optimize_var.set(selected.get("optimize", True))
        self.encrypt_var.set(selected.get("encrypt", False))
        
        self.extra_options_entry.delete(0, tk.END)
        self.extra_options_entry.insert(0, selected.get("extra_options", ""))
        
        self.extra_imports_entry.delete(0, tk.END)
        self.extra_imports_entry.insert(0, selected.get("extra_imports", ""))


if __name__ == "__main__":
    app = PyInstallerPro()
    app.mainloop()