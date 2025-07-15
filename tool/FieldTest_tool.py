# -----------------------------------------------------------------------------
# 此脚本用于控制安卓手机，实现自动执行测试项
# by ThunderSoft29749
# -----------------------------------------------------------------------------
import win32gui
import win32con
from tkinter import *
# from tkinter import ttk
import ttkbootstrap as ttk
from tkinter import messagebox
import time, pyperclip, configparser, keyboard#, pyautogui
import threading, subprocess
import os, re, sys, random, string
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from enum import Enum
	
import QutsClient
import Common.ttypes
import DiagService.DiagService
import DiagService.constants
import DiagService.ttypes
import QXDMService.QxdmService
import QXDMService.constants
import QXDMService.ttypes

# 防止嵌入版python修改窗口缩放
import ctypes
try:
    ctypes.OleDLL('shcore').SetProcessDpiAwareness(1)  # Windows 8.1+
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Windows 7
    except:
        pass

LTE = "LTE"
NSA = "NSA"
SA  = "SA"
RESET_NV = "RESET_NV"
TIMER = 1000*60*60*5

class ProcessState(Enum):
    WAIT_CALL_ENABLE = 0
    WAIT_CALL_PICKUP = 1
    WAIT_CALL_INCOME = 2
    WAIT_DATA_ENABLE = 3
    FAST_TESTING = 4
    WAIT_RELEASE = 5
    RELEASED = 6
    READY_OFF_AIRPLANE_MODE = 7

class MultipleTest():
    instances = []

    def __init__(self, master_window:Tk):
        self.master_window = master_window
        self.main_window = Toplevel()
        self.counter = 1
        self.device_connect_check_timer = None
        self.device_serial_number = None
        self.process_status = None
        self.is_run = BooleanVar()

        MultipleTest.instances.append(self)

    def get_other_instances(self) -> list["MultipleTest"]:
        return [inst for inst in MultipleTest.instances if inst is not self]
    
    def get_other_serial_number(self):
        return [inst.device_serial_number for inst in self.get_other_instances()]

    def skip(self):
        pass

    def update_command(self):
        if self.is_auto.get():
            self.off_airplane_mode_checkbutton.config(command=self.skip)
            self.make_call_checkbutton.config(command=self.skip)
            self.pickup_call_checkbutton.config(command=self.skip)
            self.fast_test_checkbutton.config(command=self.skip)
            self.terminate_call_checkbutton.config(command=self.skip)
            self.on_airplane_mode_checkbutton.config(command=self.skip)
            self.save_log_checkbutton.config(command=self.skip)
            self.start_button.config(command=lambda: self.new_thread_to_do(self.begin))
        else:
            self.off_airplane_mode_checkbutton.config(command=self.disable_airplane_mode)
            self.make_call_checkbutton.config(command=self.make_call)
            self.pickup_call_checkbutton.config(command=self.pickup_call)
            self.fast_test_checkbutton.config(command=lambda:self.new_thread_to_do(self.fast_test))
            self.terminate_call_checkbutton.config(command=self.terminate_call)
            self.on_airplane_mode_checkbutton.config(command=self.enable_airplane_mode)
            self.save_log_checkbutton.config(command=self.save_log)
            self.start_button.config(command=self.skip)

    def set_global_hotkey(self):
        if self.is_global_hotkey.get():
            keyboard.add_hotkey("f1", self.on_f1, args=(' '), suppress=True)
            keyboard.add_hotkey("f2", self.on_f2, args=(' '), suppress=True)
            keyboard.add_hotkey("f3", self.on_f3, args=(' '), suppress=True)
            keyboard.add_hotkey("f4", self.on_f4, args=(' '), suppress=True)
            keyboard.add_hotkey("f5", self.on_f5, args=(' '), suppress=True)
            keyboard.add_hotkey("f6", self.on_f6, args=(' '), suppress=True)
            keyboard.add_hotkey("f7", self.on_f7, args=(' '), suppress=True)
            keyboard.add_hotkey("f9", self.on_f9, args=(' '), suppress=True)
            keyboard.add_hotkey("f11", self.on_f11, args=(' '), suppress=True)
            keyboard.add_hotkey("f12", self.on_f12, args=(' '), suppress=True)
        else:
            keyboard.clear_all_hotkeys()

    def set_init_window(self):
        self.main_window.title("FT多次测试工具")
        # self.main_window.geometry('400x680')
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建 Notebook 组件
        self.notebook = ttk.Notebook(self.main_window, padding=10)
        self.notebook.pack(expand=True, fill=BOTH)

        # 创建场测标签页
        self.fieldtest = ttk.Frame(self.notebook, padding=2)
        self.fieldtest.pack(expand=True, fill=BOTH)
        self.notebook.add(self.fieldtest, text='  场测  ')

        # 创建其他工具标签页
        self.othertools = ttk.Frame(self.notebook, padding=2)
        self.othertools.pack(expand=True, fill=BOTH)
        self.notebook.add(self.othertools, text=' 其他工具 ')

        # 创建仪表盘标签页
        self.dashboard = ttk.Frame(self.notebook, padding=2)
        self.dashboard.pack(expand=True, fill=BOTH)
        self.notebook.add(self.dashboard, text=' 网络状态 ')

        # 创建日志分析标签页
        self.loganalyze = ttk.Frame(self.notebook, padding=2)
        self.loganalyze.pack(expand=True, fill=BOTH)
        self.notebook.add(self.loganalyze, text=' 日志分析 ')

        # 创建帮助标签页
        self.help = ttk.Frame(self.notebook, padding=2)
        self.help.pack(expand=True, fill=BOTH)
        self.notebook.add(self.help, text=' 帮助 ')
        self.notebook.bind("<<NotebookTabChanged>>", self.clear_selection)

        self.main_window.bind('<F1>', self.on_f1)
        self.main_window.bind('<F2>', self.on_f2)
        self.main_window.bind('<F3>', self.on_f3)
        self.main_window.bind('<F4>', self.on_f4)
        self.main_window.bind('<F5>', self.on_f5)
        self.main_window.bind('<F6>', self.on_f6)
        self.main_window.bind('<F7>', self.on_f7)
        self.main_window.bind('<F9>', self.on_f9)
        self.main_window.bind('<F11>', self.on_f11)
        self.main_window.bind('<F12>', self.on_f12)

        # 创建变量用于保存多选框的状态
        self.is_auto = BooleanVar()
        self.is_global_hotkey = BooleanVar()
        self.is_off_airplane_mode = BooleanVar()
        self.is_make_call = BooleanVar()
        self.is_pickup_call = BooleanVar()
        self.is_fast_test = BooleanVar()
        self.is_terminate_call = BooleanVar()
        self.is_wait_release = BooleanVar()
        self.is_wait_release_time = BooleanVar()
        self.is_return_SA = BooleanVar()
        self.is_on_airplane_mode = BooleanVar()
        self.is_save_log = BooleanVar()
        self.is_accelerometer_rotation = BooleanVar()
        self.is_window_on_top = BooleanVar()
        self.is_refresh = BooleanVar()

        self.main_window.after(TIMER, self.show_message)
        self.config = configparser.ConfigParser()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.ini')
        self.config.read(config_path)

        # 各项功能部件
        self.USBdebug_label = ttk.Label(self.main_window, text="设备连接异常!\n请确保设备已连接\n并开启USB Debug", font=("Arial", 15), bootstyle="danger",  anchor="center", justify="center")
        def device_connect_check():
            if self.device_serial_number is None:
                used_devices = self.get_other_serial_number()
                device_lines = os.popen('adb devices').read().strip().split('\n')[1:]
                for line in device_lines:
                    parts = line.strip().split('\t')
                    if parts[0] not in used_devices:
                        self.device_serial_number = parts[0]
                        self.main_window.title(f"FT多次测试工具-{self.device_serial_number}")
                        break

            if os.popen(f'adb -s {self.device_serial_number} shell settings get global adb_enabled').read().strip() == "1":
                self.USBdebug_label.pack_forget()
            else:
                self.USBdebug_label.pack(anchor='w', before=self.notebook, fill='both', expand=True)
                self.device_serial_number = None
                self.main_window.title(f"FT多次测试工具")
            self.device_connect_check_timer = self.main_window.after(5000,lambda: self.new_thread_to_do(device_connect_check))
        device_connect_check()
        # print(f"{self.device_serial_number} tkinter thread ID: {threading.get_ident()}")

        self.hotkey_button_frame = ttk.Frame(self.fieldtest)
        self.hotkey_button_frame.pack(anchor='w', padx=5, pady=2)

        self.auto_checkbutton = ttk.Checkbutton(self.hotkey_button_frame, text="F9> 全自动", variable = self.is_auto, command=self.update_command, bootstyle="primary-round-toggle")
        self.auto_checkbutton.pack(side=LEFT, padx=5, pady=2)

        self.global_hotkey_checkbutton = ttk.Checkbutton(self.hotkey_button_frame, text="全局快捷键", variable = self.is_global_hotkey, command=self.set_global_hotkey, bootstyle="success-round-toggle")
        self.global_hotkey_checkbutton.pack(side=LEFT,padx=70,pady=2)

        self.airplanemode_status_label = ttk.Label(self.fieldtest, text="")
        self.airplanemode_status_label.pack(anchor='w',padx=20,pady=5)
        self.load_airplane_mode_status()

        self.off_airplane_mode_checkbutton = ttk.Checkbutton(self.fieldtest, text="F1> 关闭飞行模式", variable = self.is_off_airplane_mode, command=self.disable_airplane_mode)
        self.off_airplane_mode_checkbutton.pack(anchor='w',padx=20,pady=5)  

        self.make_call_frame = ttk.Frame(self.fieldtest)
        self.make_call_frame.pack(anchor='w', padx=20, pady=2)
        self.make_call_checkbutton = ttk.Checkbutton(self.make_call_frame, text="F2> 拨打电话:", variable = self.is_make_call, command=self.make_call)
        self.make_call_checkbutton.pack(side=LEFT,padx=0,pady=2)
        call_number = StringVar()
        call_number.set(self.config.get('Settings', 'call_number'))
        self.call_number_entry = ttk.Entry(self.make_call_frame, width=15)
        self.call_number_entry.pack(side=LEFT,padx=5,pady=0)
        self.call_number_entry.insert(END, call_number.get())

        self.pickup_call_checkbutton = ttk.Checkbutton(self.fieldtest, text="F3> 接听电话", variable = self.is_pickup_call, command=self.pickup_call)
        self.pickup_call_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.fast_test_checkbutton = ttk.Checkbutton(self.fieldtest, text="F4> 开启fast测速", variable = self.is_fast_test, command=lambda:self.new_thread_to_do(self.fast_test))
        self.fast_test_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.wait_time_frame = ttk.Frame(self.fieldtest)
        self.wait_time_frame.pack(anchor='w', padx=20, pady=2)
        self.wait_time_label = ttk.Label(self.wait_time_frame, text="等待时长(秒):")
        self.wait_time_label.pack(side=LEFT,padx=0,pady=0)
        wait_time = StringVar()
        wait_time.set(self.config.get('Settings', 'wait_time'))
        self.wait_time_spinbox = ttk.Spinbox(self.wait_time_frame, from_=0, to=10000, increment=1, width=5)
        self.wait_time_spinbox.pack(side=LEFT,padx=5,pady=2)
        self.wait_time_spinbox.set(wait_time.get())
        self.wait_time_spinbox.bind("<<Increment>>", self.clear_selection)
        self.wait_time_spinbox.bind("<<Decrement>>", self.clear_selection)

        self.terminate_call_checkbutton = ttk.Checkbutton(self.fieldtest, text="F5> 挂断电话", variable = self.is_terminate_call, command=self.terminate_call)
        self.terminate_call_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.release_frame = ttk.Frame(self.fieldtest)
        self.release_frame.pack(anchor='w', padx=20, pady=2)
        self.wait_release_checkbutton = ttk.Checkbutton(self.release_frame, text="等待release(不稳定)", variable = self.is_wait_release)
        self.wait_release_checkbutton.pack(side=LEFT,padx=0,pady=2)
        self.network_technology = IntVar(value=1)  # 默认选中选项 1
        self.LTE_radio = ttk.Radiobutton(self.release_frame, text="LTE", variable=self.network_technology, value=1)
        self.LTE_radio.pack(side=LEFT,padx=5,pady=2)
        self.NR_radio = ttk.Radiobutton(self.release_frame, text="NR", variable=self.network_technology, value=2)
        self.NR_radio.pack(side=LEFT,padx=5,pady=2)

        self.release_time_frame = ttk.Frame(self.fieldtest)
        self.release_time_frame.pack(anchor='w', padx=20, pady=2)
        self.wait_release_time_checkbutton = ttk.Checkbutton(self.release_time_frame, text="等待release时长上限", variable = self.is_wait_release_time)
        self.wait_release_time_checkbutton.pack(side=LEFT,padx=0,pady=2)
        wait_release_max_time = StringVar()
        wait_release_max_time.set(self.config.get('Settings', 'wait_release_max_time'))
        self.wait_release_max_time_spinbox = ttk.Spinbox(self.release_time_frame, from_=0, to=10000, increment=1, width=5)
        self.wait_release_max_time_spinbox.pack(side=LEFT,padx=2,pady=0)
        self.wait_release_max_time_spinbox.set(wait_release_max_time.get())
        self.wait_release_max_time_spinbox.bind("<<Increment>>", self.clear_selection)
        self.wait_release_max_time_spinbox.bind("<<Decrement>>", self.clear_selection)
        self.wait_release_max_time_label = Label(self.release_time_frame, text="秒")
        self.wait_release_max_time_label.pack(side=LEFT,padx=0,pady=2)

        self.return_SA_checkbutton = ttk.Checkbutton(self.fieldtest, text="等待回到 SA", variable = self.is_return_SA)
        self.return_SA_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.on_airplane_mode_checkbutton = ttk.Checkbutton(self.fieldtest, text="F6> 开启飞行模式", variable = self.is_on_airplane_mode, command=self.enable_airplane_mode)
        self.on_airplane_mode_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.save_log_checkbutton = ttk.Checkbutton(self.fieldtest, text="F7> 复制日志名到剪切板", variable = self.is_save_log, command=self.save_log)
        self.save_log_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.log_name_label = ttk.Label(self.fieldtest, text="日志命名:")
        self.log_name_label.pack(anchor='w',padx=20,pady=5)
        log_name = StringVar()
        log_name.set(self.config.get('Settings', 'log_name'))
        self.log_name_entry = ttk.Entry(self.fieldtest, width = 30)
        self.log_name_entry.pack(anchor='w',padx=25,pady=2,fill=X)
        self.log_name_entry.insert(END, log_name.get())

        self.repeat_frame = ttk.Frame(self.fieldtest)
        self.repeat_frame.pack(anchor='w', padx=10, pady=2)
        self.repeat_times_label = ttk.Label(self.repeat_frame, text="重复次数:")
        self.repeat_times_label.pack(side=LEFT,padx=0,pady=2)
        repeat_times = StringVar()
        repeat_times.set("1")
        self.repeat_times_spinbox = ttk.Spinbox(self.repeat_frame, from_=1, to=10000, increment=1, width=5)
        self.repeat_times_spinbox.pack(side=LEFT,padx=5,pady=2)
        self.repeat_times_spinbox.set(repeat_times.get())
        self.repeat_times_spinbox.bind("<<Increment>>", self.clear_selection)
        self.repeat_times_spinbox.bind("<<Decrement>>", self.clear_selection)

        self.startstop_button_frame = ttk.Frame(self.fieldtest)
        self.startstop_button_frame.pack(anchor='w', padx=10, pady=5)
        self.start_button = ttk.Button(self.startstop_button_frame, text='F11> 开始', command=None, bootstyle="primary-outline")
        self.start_button.pack(side=LEFT,padx=15,pady=2)
        self.stop_button = ttk.Button(self.startstop_button_frame, text='F12> 中止', command=self.cancel_timer, bootstyle="danger-outline")
        self.stop_button.pack(side=LEFT,padx=15,pady=2)
        self.multiple_windows_button = ttk.Button(self.startstop_button_frame, text=' 多开 ', command=self.open_multiple_windows, bootstyle="info-outline")
        self.multiple_windows_button.pack(side=LEFT,padx=30,pady=2)

        self.progress_label = ttk.Label(self.fieldtest, text="进度: ", font=("Arial", 15))
        self.progress_label.pack(anchor='w',padx=20,pady=5)

        # 其他工具
        self.window_on_top_checkbutton = ttk.Checkbutton(self.othertools, text="保持此窗口在最前显示", variable = self.is_window_on_top, command=self.set_window_on_top, bootstyle="success-round-toggle")
        self.window_on_top_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.func_button_frame = ttk.Frame(self.othertools)
        self.func_button_frame.pack(anchor='w', padx=5, pady=5)
        self.open_port_button = ttk.Button(self.func_button_frame, text=' 开端口 ', command=self.open_port, bootstyle="outline")
        self.open_port_button.pack(side=LEFT,padx=15,pady=2)
        self.off_temp_protect_button = ttk.Button(self.func_button_frame, text=' 禁用高温保护 ', command=self.off_temp_protect, bootstyle="outline")
        self.off_temp_protect_button.pack(side=LEFT,padx=15,pady=2)

        self.screen_off_timeout_lable = ttk.Label(self.othertools, text="屏幕常亮(分钟): ")
        self.screen_off_timeout_lable.pack(anchor='w',padx=10,pady=2)
        self.screen_off_timeout_scale = ttk.Scale(self.othertools, orient="horizontal", length=300, from_=1, to=200, command=self.set_screen_off_timeout)
        self.screen_off_timeout_scale.pack(anchor='w',padx=10,pady=2)
        screen_off_timeout_str = os.popen(f'adb -s {self.device_serial_number} shell settings get system screen_off_timeout').read().strip()
        if screen_off_timeout_str.isdigit():
            screen_off_timeout_minute = str(int(screen_off_timeout_str)/60000)
            self.screen_off_timeout_lable.config(text = f"屏幕常亮(分钟): {screen_off_timeout_minute}")
            self.screen_off_timeout_scale.set(screen_off_timeout_minute)

        self.screen_brightness_lable = ttk.Label(self.othertools, text="屏幕亮度: ")
        self.screen_brightness_lable.pack(anchor='w',padx=10,pady=2)
        self.screen_brightness_scale = ttk.Scale(self.othertools, orient="horizontal", length=300, from_=1, to=150, command=self.set_screen_brightness)
        self.screen_brightness_scale.pack(anchor='w',padx=10,pady=2)
        screen_brightness_str = os.popen(f'adb -s {self.device_serial_number} shell settings get system screen_brightness').read().strip()
        if screen_brightness_str.isdigit():
            self.screen_brightness_lable.config(text = f"屏幕亮度: {screen_brightness_str}")
            self.screen_brightness_scale.set(screen_brightness_str)
        
        accelerometer_rotation_str = os.popen(f'adb -s {self.device_serial_number} shell settings get system accelerometer_rotation').read().strip()
        if accelerometer_rotation_str == "1":
            self.is_accelerometer_rotation.set(True)
        else:
            self.is_accelerometer_rotation.set(False)
        self.accelerometer_rotation_checkbutton = ttk.Checkbutton(self.othertools, text="屏幕自动旋转", variable = self.is_accelerometer_rotation, command=self.set_accelerometer_rotation, bootstyle="success-round-toggle")
        self.accelerometer_rotation_checkbutton.pack(anchor='w',padx=20,pady=5)

        self.SMS_number_frame = ttk.Frame(self.othertools)
        self.SMS_number_frame.pack(anchor='w', padx=10, pady=2)
        self.SMS_number_lable = ttk.Label(self.SMS_number_frame, text="短信号码: ")
        self.SMS_number_lable.pack(side=LEFT,padx=0,pady=0)
        SMS_number = StringVar()
        SMS_number.set(self.config.get('Settings', 'SMS_number'))
        self.SMS_number_entry = ttk.Entry(self.SMS_number_frame, width=20)
        self.SMS_number_entry.pack(side=LEFT,padx=5,pady=0)
        self.SMS_number_entry.insert(END, SMS_number.get())

        self.SMS_content_frame = ttk.Frame(self.othertools)
        self.SMS_content_frame.pack(anchor='w', padx=10, pady=2)
        self.SMS_content_lable = ttk.Label(self.SMS_content_frame, text="短信内容: ")
        self.SMS_content_lable.pack(side=LEFT,padx=0,pady=0)
        SMS_content = StringVar()
        SMS_content.set(self.config.get('Settings', 'SMS_content'))
        self.SMS_content_entry = ttk.Entry(self.SMS_content_frame, width=20)
        self.SMS_content_entry.pack(side=LEFT,padx=5,pady=0)
        self.SMS_content_entry.insert(END, SMS_content.get())
        self.SMS_send_button = ttk.Button(self.othertools, text='发送短信', command=self.send_SMS, bootstyle="outline")
        self.SMS_send_button.pack(anchor='w',padx=15,pady=5)

        self.push_file_frame = ttk.Frame(self.othertools)
        self.push_file_frame.pack(anchor='w', padx=10, pady=2)
        self.push_file_lable = ttk.Label(self.push_file_frame, text="生成大文件到设备(GB):")
        self.push_file_lable.pack(side=LEFT,padx=0,pady=2)
        testfile_size = StringVar()
        testfile_size.set(self.config.get('Settings', 'testfile_size'))
        self.file_size_entry = ttk.Entry(self.push_file_frame, width = 6)
        self.file_size_entry.pack(side=LEFT,padx=5,pady=2)
        self.file_size_entry.insert(END, testfile_size.get())
        self.push_file_button = ttk.Button(self.push_file_frame, text=' 生成 ', command=self.push_file, bootstyle="outline")
        self.push_file_button.pack(side=LEFT,padx=5,pady=2)

        # LTE: 65633; NSA: 74213; SA: 74087
        self.Band2NV_lable = ttk.Label(self.othertools, text="高通专用锁Band: (输入例:3-18-28)")
        self.Band2NV_lable.pack(anchor='w',padx=10,pady=5)
        self.Band2NV_entry = ttk.Entry(self.othertools, width = 30)
        self.Band2NV_entry.pack(anchor='w',padx=15,pady=2)
        self.Band2NV_entry.bind("<FocusIn>", self.on_focus_in_Band2NV_entry)
        self.Band2NV_button_frame = ttk.Frame(self.othertools)
        self.Band2NV_button_frame.pack(anchor='w', padx=5, pady=5)
        self.LTE_button = ttk.Button(self.Band2NV_button_frame, text='LTE', command=lambda: self.set_NV(LTE), bootstyle="outline")
        self.LTE_button.pack(side=LEFT,padx=5,pady=2)
        self.NSAorSA_button = ttk.Button(self.Band2NV_button_frame, text='NSA', command=lambda: self.set_NV(NSA), bootstyle="outline")
        self.NSAorSA_button.pack(side=LEFT,padx=5,pady=2)
        self.NSAorSA_button = ttk.Button(self.Band2NV_button_frame, text='SA', command=lambda: self.set_NV(SA), bootstyle="outline")
        self.NSAorSA_button.pack(side=LEFT,padx=5,pady=2)
        self.NSAorSA_button = ttk.Button(self.Band2NV_button_frame, text='重启', command= self.reboot_devices, bootstyle="outline")
        self.NSAorSA_button.pack(side=LEFT,padx=5,pady=2)
        self.NSAorSA_button = ttk.Button(self.Band2NV_button_frame, text='重置NV', command=lambda: self.set_NV(RESET_NV), bootstyle="outline")
        self.NSAorSA_button.pack(side=LEFT,padx=5,pady=2)

        self.dcmSMS_button_frame = ttk.Frame(self.othertools)
        self.dcmSMS_button_frame.pack(anchor='w', padx=5, pady=5)
        self.NSAorSA_button = ttk.Button(self.dcmSMS_button_frame, text=' 禁包 ', command=self.banned_Packages, bootstyle="outline")
        self.NSAorSA_button.pack(side=LEFT,padx=5,pady=2)
        self.NSAorSA_button = ttk.Button(self.dcmSMS_button_frame, text=' 解包 ', command=self.unbanned_Packages, bootstyle="outline")
        self.NSAorSA_button.pack(side=LEFT,padx=5,pady=2)

        # 网络状态
        self.refresh_checkbutton = ttk.Checkbutton(self.dashboard, text="每秒自动刷新", variable = self.is_refresh, command=self.refresh, bootstyle="success-round-toggle")
        self.refresh_checkbutton.pack(anchor='w',padx=10,pady=5)

        self.operator_lable = ttk.Label(self.dashboard, text="运营商: ")
        self.operator_lable.pack(anchor='w',padx=10,pady=5)
        self.VoiceRadioTechnology_lable = ttk.Label(self.dashboard, text="CALL网络: ")
        self.VoiceRadioTechnology_lable.pack(anchor='w',padx=10,pady=5)
        self.DataRadioTechnology_lable = ttk.Label(self.dashboard, text="DATA网络: ")
        self.DataRadioTechnology_lable.pack(anchor='w',padx=10,pady=5)
        self.isUsingCarrierAggregation_lable = ttk.Label(self.dashboard, text="CA状态: ")
        self.isUsingCarrierAggregation_lable.pack(anchor='w',padx=10,pady=5)
        self.Bands_lable = ttk.Label(self.dashboard, text="Bands: ")
        self.Bands_lable.pack(anchor='w',padx=10,pady=5)
        self.PCI_lable = ttk.Label(self.dashboard, text="PCI: ")
        self.PCI_lable.pack(anchor='w',padx=10,pady=5)
        self.RSRP_lable = ttk.Label(self.dashboard, text="信号强度RSRP: ")
        self.RSRP_lable.pack(anchor='w',padx=10,pady=5)
        self.RSRQ_lable = ttk.Label(self.dashboard, text="信号质量RSRQ: ")
        self.RSRQ_lable.pack(anchor='w',padx=10,pady=5)

        # 日志分析
        self.raw_data_label = ttk.Label(self.loganalyze, text='输入待分析的QXDM log: ', anchor=W)
        self.raw_data_label.pack(anchor='w',padx=10,pady=5)
        self.raw_data_input = ttk.ScrolledText(self.loganalyze, height=10, width=40, wrap=NONE)
        self.raw_data_input.pack(anchor='w',padx=10,pady=5, fill=X)
        self.throughputs_chart_button = ttk.Button(self.loganalyze, text=' 吞吐量 ', command=self.throughputs_analyze, bootstyle="outline")
        self.throughputs_chart_button.pack(anchor='w',padx=10,pady=5)

        # 帮助
        self.theme_selection_frame = ttk.Frame(self.help)
        self.theme_selection_frame.pack(anchor='w', padx=5, pady=5)
        self.theme_selection_lable = ttk.Label(self.theme_selection_frame, text="主题:")
        self.theme_selection_lable.pack(side=LEFT)
        self.allowed_themes_map = {
            "默认": "litera",
            "明亮": "cosmo",
            "坚实": "sandstone",
            "质朴": "yeti",
            "稳重": "superhero",
            "黑暗": "cyborg",}
        theme = int(self.config.get('Settings', 'theme'))
        ttk.Style().theme_use(list(self.allowed_themes_map.values())[theme])
        self.theme_combobox = ttk.Combobox(self.theme_selection_frame, values=list(self.allowed_themes_map.keys()))
        self.theme_combobox.pack(side=LEFT, padx=10)
        self.theme_combobox.current(theme)
        self.theme_combobox.bind("<<ComboboxSelected>>", self.change_theme)

        self.tips_label = ttk.Label(self.help, anchor="w", justify="left", text="1.未勾选全自动时, 每项功能为通过点击或快捷键单独\n    执行\n\n"
                                +"2.勾选全自动后选择希望自动执行的功能，点击开始会\n    从上到下依次执行被勾选的各项功能\n\n"
                                +"3.推荐将等待时长填写为 单次测试时长+冗余等待时长\n\n"
                                +"4.日志命名会将输入框的文字复制到剪切板即可直接粘贴\n    并会将名称末尾的数字自动加1以供下次使用\n\n"
                                +"5.涉及到保存log操作时, 建议将重复次数设置为 1\n\n"
                                +"6.锁band时需要提前开端口, 输入 0 即为屏蔽对应网络\n\n"
                                +"7.默认Band可从policy.xml获取(PCAT/EFSExplorer\n/policyman/carrier_policy.xml)后填写在config.ini\n进行重置\n\n"
                                +"8.网络状态刷新会占用电脑性能,建议不用时关闭\n\n"
                                +"9.勾选全局快捷键后,可在任意界面触发快捷键\n\n"
                                +"10.多开窗口时全局快捷键是相同的,建议只使用F11和F12\n\n"
                                +"by ThunderSoft29749")
        self.tips_label.pack(anchor='w',padx=10,pady=10)
        
    def change_theme(self, event):
        ttk.Style().theme_use(self.allowed_themes_map[self.theme_combobox.get()])
        self.theme_combobox.selection_clear()
        pair_instances = self.get_other_instances()
        if pair_instances:
            pair_instances[0].theme_combobox.current(list(self.allowed_themes_map.keys()).index(self.theme_combobox.get()))

    def clear_selection(self, event:Event):
        event.widget.after_idle(lambda: event.widget.selection_clear())  # 取消选中

    def enable_airplane_mode(self):
        if os.popen(f'adb -s {self.device_serial_number} shell settings get global airplane_mode_on').read().strip() == "0":  #airplane_mode_off
            os.system(f'adb -s {self.device_serial_number} root')
            os.system(f'adb -s {self.device_serial_number} shell settings put global airplane_mode_on 1')
            os.system(f'adb -s {self.device_serial_number} shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true')
        self.load_airplane_mode_status()

    def disable_airplane_mode(self):
        if os.popen(f'adb -s {self.device_serial_number} shell settings get global airplane_mode_on').read().strip() == "1":  #airplane_mode_on
            os.system(f'adb -s {self.device_serial_number} root')
            os.system(f'adb -s {self.device_serial_number} shell settings put global airplane_mode_on 0')
            os.system(f'adb -s {self.device_serial_number} shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false')
        self.load_airplane_mode_status()

    def load_airplane_mode_status(self):
        if os.popen(f'adb -s {self.device_serial_number} shell settings get global airplane_mode_on').read().strip() == "0":  #airplane_mode_off
            self.airplanemode_status_label.config(text = "当前飞行模式: 关, 正常联网")
        else:
            self.airplanemode_status_label.config(text = "当前飞行模式: 开, 断网啦")

    def get_call_state(self):  #0表示待机状态、1表示来电未接听状态、2表示电话占线状态
        return self.check_state("mCallState")
    
    def get_data_state(self):  #0：无数据连接 1：正在创建数据连接 2：已连接
        return self.check_state("mDataConnectionState")
    
    def get_accessNetworkTechnology(self):  #
        return self.check_state("accessNetworkTechnology")
    
    def get_mForegroundCallState(self):  #拨打电话状态：0：待机，1：正在通话，4：正在拨打
        return self.check_state("mForegroundCallState")

    def check_state(self, keyword):
            try:
                output = subprocess.check_output(["adb", "-s", self.device_serial_number, "shell", "dumpsys", "telephony.registry"], universal_newlines=True)
                lines = output.splitlines()
                
                for line in lines:
                    if keyword in line:
                        call_state = line.split("=")[1].strip()
                        return int(call_state)
        
            except subprocess.CalledProcessError as e:
                print(f"Error executing adb command: {e}")

    def get_mVoiceRegState(self):
        mServiceState = os.popen(f'adb -s {self.device_serial_number} shell "dumpsys telephony.registry | grep mServiceState"').read().strip().split("\n")[0]
        return re.search(r"mVoiceRegState ?= ?(.*?),", mServiceState)[1]

    def make_call(self):
        if self.get_call_state() == 0:
            os.system(f'adb -s {self.device_serial_number} shell am start -a android.intent.action.CALL tel:{self.call_number_entry.get()}')
    
    def pickup_call(self):
        if self.get_call_state() == 1:
            os.system(f'adb -s {self.device_serial_number} shell input keyevent KEYCODE_CALL')

    def fast_test(self):
        self.process_status = ProcessState.FAST_TESTING
        os.system(f'adb -s {self.device_serial_number} shell am start -a android.intent.action.VIEW -d https://fast.com --ez create_new_tab false')
        # os.system(f'adb -s {self.device_serial_number} shell input keyevent KEYCODE_EXPLORER')
        # os.system(f'adb -s {self.device_serial_number} shell input keyevent KEYCODE_F5')
        self.wait_progress()
        # os.system(f'adb -s {self.device_serial_number} shell pm clear cn.com.test.mobile') 

    def wait_progress(self):
        if not self.is_auto.get():
            self.is_run.set(True)
        count = 0
        while count < int(self.wait_time_spinbox.get()) and self.is_run.get():
            count += 1
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 已等待 {str(count)} 秒")
            time.sleep(1)
        if count >= int(self.wait_time_spinbox.get()):
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 已完成等待 {str(self.wait_time_spinbox.get())} 秒！")
        if not self.is_auto.get():
            self.is_run.set(False)

    def terminate_call(self):
        if self.get_call_state() != 0:
            os.system(f'adb -s {self.device_serial_number} shell input keyevent KEYCODE_ENDCALL')

    def wait_release(self):
        self.process_status = ProcessState.WAIT_RELEASE
        os.system(f'adb -s {self.device_serial_number} logcat -b all -c')
        platform = os.popen(f'adb -s {self.device_serial_number} shell getprop ro.soc.manufacturer').read().strip()
        network_technology = self.network_technology.get()
        output1 = None
        #QXDM
        if platform == "QTI":
            if network_technology == 1: # LTE 
                output1 = subprocess.Popen(["adb", "-s", self.device_serial_number, "logcat", "-b", "radio", "-m", "1", "-e", "mDownlinkCapacityKbps=-1, mUplinkCapacityKbps=-1"])
                # output2 = subprocess.check_output(["adb", "-s", self.device_serial_number, "logcat", "-b", "radio", "-m", "1", "-e", "Unknown dns: "], universal_newlines=True)
            if network_technology == 2: # NR
                output1 = subprocess.Popen(["adb", "-s", self.device_serial_number, "logcat", "-b", "radio", "-m", "1", "-e", "mDownlinkCapacityKbps=-1, mUplinkCapacityKbps=-1"])
        #MTK
        if platform == "Mediatek":
            if network_technology == 1: # LTE 
                # handleConnectionStateReportInd: 1, 7, 4
                output1 = subprocess.Popen(["adb", "-s", self.device_serial_number, "logcat", "-b", "radio", "-m", "1", "-e", "handleConnectionStateReportInd: 0, 255, 4"])
            if network_technology == 2: # NR
                # handleConnectionStateReportInd: 1, 8, 5
                output1 = subprocess.Popen(["adb", "-s", self.device_serial_number, "logcat", "-b", "radio", "-m", "1", "-e", "handleConnectionStateReportInd: 0, 255, 5"])
        time.sleep(1) # 延长等待release

        count = 0
        while ((self.is_wait_release.get() and output1.poll() is None and not self.is_wait_release_time.get()) \
        or (not self.is_wait_release.get() and self.is_wait_release_time.get() and count < int(self.wait_release_max_time_spinbox.get())) \
        or (self.is_wait_release.get() and output1.poll() is None and self.is_wait_release_time.get() and count < int(self.wait_release_max_time_spinbox.get()))) \
        and self.is_run.get():
            count += 1
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 等待 release {str(count)} 秒")
            time.sleep(1)
        if ((self.is_wait_release.get() and not self.is_wait_release_time.get()) or count < int(self.wait_release_max_time_spinbox.get())) and self.is_run.get():
            time.sleep(1) # 延长等待release
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 已经 release")
            time.sleep(1) # 延长等待release
        elif count >= int(self.wait_release_max_time_spinbox.get()):
            output1.terminate()
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 等待release时长上限")
        else:
            output1.terminate()
        self.process_status = ProcessState.RELEASED

    def wait_return_SA(self):
        count = 0
        while self.is_return_SA.get() and self.is_run.get():
            count += 1
            mServiceState = os.popen(f'adb -s {self.device_serial_number} shell "dumpsys telephony.registry | grep mServiceState"').read().strip().split("\n")[0]
            DataRadioTechnology = re.search(r"getRilDataRadioTechnology ?= ?(.*?),", mServiceState)[1]
            if SA in DataRadioTechnology:
                break
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 等待回到SA {str(count)} 秒")
            time.sleep(1)
        if self.is_return_SA.get() and self.is_run.get():
            self.progress_label.config(text=f"进度: 第{str(self.counter)}次 已回到SA")
            time.sleep(1)

    def save_log(self):
        log_name = self.log_name_entry.get()
        pyperclip.copy(log_name)

        step = re.search(r'\d+$', log_name).group()
        new_log_name = log_name[0:-len(step)] + str(int(step) + 1)
        self.log_name_entry.delete(0, END)  # 清空输入框
        self.log_name_entry.insert(0, new_log_name)  # 插入新的值

        # # hwnd = win32gui.GetForegroundWindow()
        # # if hwnd:
        # #     # 获取窗口类名
        # #     class_name = win32gui.GetClassName(hwnd)
        # #     print(f"当前窗口句柄: {hwnd}, 窗口类名: {class_name}")
        # # else:
        # #     print("未找到前台窗口")
        # if hwnd_QXDM := win32gui.FindWindow("Qt5152QWindowIcon", None):
        #     win32gui.ShowWindow(hwnd_QXDM, win32con.SW_SHOW)  # 先恢复窗口
        #     time.sleep(0.5)
        #     win32gui.SetForegroundWindow(hwnd_QXDM)  # 设置前台窗口
        #     time.sleep(0.5)
        #     # x, y = pyautogui.position()
        #     # pyautogui.click(100, 1)
        #     time.sleep(0.5)
        #     keyboard.press_and_release("ctrl+i")
        #     time.sleep(0.5)
        #     keyboard.press_and_release("ctrl+v")
        #     time.sleep(0.5)
        #     keyboard.press_and_release("enter")
        #     # pyautogui.moveTo(x, y)
        # elif hwnd_ELT := win32gui.FindWindow("WindowsForms10.Window.8.app.0.f96fc5_r7_ad1", None):
        #     win32gui.ShowWindow(hwnd_ELT, win32con.SW_RESTORE)  # 先恢复窗口
        #     win32gui.SetForegroundWindow(hwnd_ELT)  # 设置前台窗口
        #     time.sleep(0.5)
        #     # x, y = pyautogui.position()
        #     # pyautogui.click(100, 1)
        #     time.sleep(0.1)
        #     keyboard.press_and_release("ctrl+i")
        #     # pyautogui.moveTo(x, y)
        # else:
        #     print(f"自动保存失败")

    def get_pair_status(self):
        pair_instances = self.get_other_instances()
        if pair_instances and pair_instances[0].device_serial_number:
            return pair_instances[0].process_status
        else:
            return False
    
    def safe_configure(self, widget:Widget, **kwargs):
        widget.after(0, lambda: widget.configure(**kwargs))

    def button_flash(self):
        while self.flag_event.is_set():
            self.safe_configure(self.start_button, bootstyle="primary")
            time.sleep(0.5)
            self.safe_configure(self.start_button, bootstyle="primary-outline")
            time.sleep(0.5)

    def begin(self):
        self.main_window.focus_set()
        self.progress_label.config(text=f"进度: ")
        self.counter = 1
        self.is_run.set(True)
        self.flag_event = threading.Event()
        self.flag_event.set()
        self.new_thread_to_do(self.button_flash)

        def repeat():
            # print(f"{self.device_serial_number} func thread ID: {threading.get_ident()}")
            self.process_status = ProcessState.READY_OFF_AIRPLANE_MODE
            if self.is_off_airplane_mode.get() and self.is_run.get():
                self.safe_configure(self.off_airplane_mode_checkbutton, bootstyle="warning")
                while self.get_pair_status() != ProcessState.READY_OFF_AIRPLANE_MODE and self.get_pair_status() is not False and self.is_run.get(): #等待双开设备
                    time.sleep(0.5)
                self.process_status = None
                self.disable_airplane_mode()
                time.sleep(1)
                self.safe_configure(self.off_airplane_mode_checkbutton, bootstyle="success")

            if self.is_make_call.get() and self.is_run.get():
                self.safe_configure(self.make_call_checkbutton, bootstyle="warning")
                self.process_status = ProcessState.WAIT_CALL_ENABLE
                while self.get_mVoiceRegState() != "0(IN_SERVICE)" and self.is_run.get(): #等待语音服务至可用
                    time.sleep(1)
                time.sleep(1)

                while self.get_pair_status() != ProcessState.WAIT_CALL_INCOME and self.get_pair_status() is not False and self.is_run.get(): #等待双开设备
                    time.sleep(0.5)
                self.make_call()

                self.process_status = ProcessState.WAIT_CALL_PICKUP
                while self.get_mForegroundCallState() != 1 and self.is_run.get(): #拨号后等待至开始通话
                    time.sleep(0.1)
                self.process_status = None
                self.safe_configure(self.make_call_checkbutton, bootstyle="success")

            if self.is_pickup_call.get() and self.is_run.get():
                self.safe_configure(self.pickup_call_checkbutton, bootstyle="warning")
                self.process_status = ProcessState.WAIT_CALL_ENABLE
                while self.get_mVoiceRegState() != "0(IN_SERVICE)" and self.is_run.get(): #等待语音服务至可用
                    time.sleep(1)
                time.sleep(1)

                self.process_status = ProcessState.WAIT_CALL_INCOME
                while self.get_call_state() != 1 and self.is_run.get():
                    time.sleep(0.5)
                time.sleep(1)
                self.process_status = None
                self.pickup_call()
                self.safe_configure(self.pickup_call_checkbutton, bootstyle="success")

            if self.is_fast_test.get() and self.is_run.get():
                self.safe_configure(self.fast_test_checkbutton, bootstyle="warning")
                self.process_status = ProcessState.WAIT_DATA_ENABLE
                while self.get_data_state() == 0 and self.is_run.get():
                    time.sleep(0.5)
                time.sleep(1)
                self.process_status = None
                self.fast_test()
                self.safe_configure(self.fast_test_checkbutton, bootstyle="success")
            else:
                self.safe_configure(self.wait_time_spinbox, bootstyle="warning")
                self.wait_progress()
                self.safe_configure(self.wait_time_spinbox, bootstyle="success")

            if self.is_terminate_call.get() and self.is_run.get():
                self.safe_configure(self.terminate_call_checkbutton, bootstyle="warning")
                self.terminate_call()
                time.sleep(1)
                self.safe_configure(self.terminate_call_checkbutton, bootstyle="success")

            if (self.is_wait_release.get() or self.is_wait_release_time.get()) and self.is_run.get():
                if self.is_wait_release.get():
                    self.safe_configure(self.wait_release_checkbutton, bootstyle="warning")
                if self.is_wait_release_time.get():
                    self.safe_configure(self.wait_release_time_checkbutton, bootstyle="warning")
                self.wait_release()
                if self.is_wait_release.get():
                    self.safe_configure(self.wait_release_checkbutton, bootstyle="success")
                if self.is_wait_release_time.get():
                    self.safe_configure(self.wait_release_time_checkbutton, bootstyle="success")

            if self.is_return_SA.get() and self.is_run.get():
                self.safe_configure(self.return_SA_checkbutton, bootstyle="warning")
                self.wait_return_SA()
                self.safe_configure(self.return_SA_checkbutton, bootstyle="success")

            if self.is_on_airplane_mode.get() and self.is_run.get():
                self.safe_configure(self.on_airplane_mode_checkbutton, bootstyle="warning")
                time.sleep(1)
                self.enable_airplane_mode()
                self.safe_configure(self.on_airplane_mode_checkbutton, bootstyle="success")

            if self.is_save_log.get() and self.is_run.get():
                self.safe_configure(self.save_log_checkbutton, bootstyle="warning")
                time.sleep(1)
                self.save_log()
                self.safe_configure(self.save_log_checkbutton, bootstyle="success")
            
            if self.counter < int(self.repeat_times_spinbox.get()) and self.is_run.get():
                self.reset_checkbutton()
                self.counter += 1
                time.sleep(1)
                repeat()
        repeat()
        self.is_run.set(False)
        self.flag_event.clear()
        self.reset_checkbutton()
        self.counter = 1

    def reset_checkbutton(self):
        self.safe_configure(self.off_airplane_mode_checkbutton, bootstyle="default")
        self.safe_configure(self.make_call_checkbutton, bootstyle="default")
        self.safe_configure(self.pickup_call_checkbutton, bootstyle="default")
        self.safe_configure(self.fast_test_checkbutton, bootstyle="default")
        self.safe_configure(self.wait_time_spinbox, bootstyle="default")
        self.safe_configure(self.terminate_call_checkbutton, bootstyle="default")
        self.safe_configure(self.wait_release_checkbutton, bootstyle="default")
        self.safe_configure(self.wait_release_time_checkbutton, bootstyle="default")
        self.safe_configure(self.return_SA_checkbutton, bootstyle="default")
        self.safe_configure(self.on_airplane_mode_checkbutton, bootstyle="default")
        self.safe_configure(self.save_log_checkbutton, bootstyle="default")

    def cancel_timer(self):
        self.is_run.set(False)
        self.progress_label.config(text=f"进度: 第{str(self.counter)}次 已中止")

    def open_multiple_windows(self):
        if len(MultipleTest.instances) < 2:
            multipleTest2 = MultipleTest(self.master_window)
            multipleTest2.set_init_window()
        else:
            messagebox.showinfo("提示", "最多开启两个窗口")

    def set_window_on_top(self):
        if self.is_window_on_top.get():
            self.main_window.attributes('-topmost', True)
        else:
            self.main_window.attributes('-topmost', False)

    def open_port(self):
        os.system(f'adb -s {self.device_serial_number} root')
        os.system(f'adb -s {self.device_serial_number} shell setprop sys.usb.config \"diag,adb\"')

    def off_temp_protect(self):
        os.system(f'adb -s {self.device_serial_number} root')
        os.system(f'adb -s {self.device_serial_number} shell thermal_manager /vendor/etc/.tp/.ht120.mtc')
        os.system(f'adb -s {self.device_serial_number} shell stop thermal-engine')
        messagebox.showinfo("提示", "已禁用高温保护, 重启可恢复")

    def set_screen_off_timeout(self,value):
        os.system(f'adb -s {self.device_serial_number} shell settings put system screen_off_timeout {str(int(float(value))*60000)}')
        self.screen_off_timeout_lable.config(text = f"屏幕常亮(分钟):  {str(int(float(value)))}")

    def set_screen_brightness(self,value):
        os.system(f'adb -s {self.device_serial_number} shell settings put system screen_brightness {str(int(float(value)))}') 
        self.screen_brightness_lable.config(text = f"屏幕亮度:  {str(int(float(value)))}")

    def set_accelerometer_rotation(self):
        if self.is_accelerometer_rotation.get():
            os.system(f'adb -s {self.device_serial_number} shell settings put system accelerometer_rotation 1')
        else:
            os.system(f'adb -s {self.device_serial_number} shell settings put system accelerometer_rotation 0')

    def send_SMS(self):
        os.system(f'adb -s {self.device_serial_number} shell am start -a android.intent.action.SENDTO -d sms:{self.SMS_number_entry.get()}' 
                  + f' --es sms_body \"{self.SMS_content_entry.get()}\" --ez exit_on_sent false')
        time.sleep(1)
        wm_size = os.popen(f'adb -s {self.device_serial_number} shell wm size').read().strip()
        size = re.search(r'(\d+)x(\d+)', wm_size)
        os.system(f'adb -s {self.device_serial_number} shell input tap {int(int(size.group(1)) * 11/12)} {int(int(size.group(2)) * 12/13)}')

    def random_alphanum(self, n=3):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

    def push_file(self):
        self.main_window.focus_set()
        file_size = self.file_size_entry.get()
        file_name = f"testfile_{file_size}GB_{self.random_alphanum()}"
        os.system(f"adb -s {self.device_serial_number} shell fallocate -l {int(float(file_size)*10**9)} /sdcard/{file_name}")
        messagebox.showinfo("提示",f"已生成大文件 {file_name} 到设备")
        
    def on_focus_in_Band2NV_entry(self,event):
        self.Band2NV_lable.config(text="高通专用锁Band: (输入例:3-18-28)")

    def LTE2NV(self):
        LTEbandList_int = list(set(list(map(int, self.Band2NV_entry.get().split("-")))))
        LTENV_int = 0
        for i in LTEbandList_int:
            if i > 0:
                LTENV_int = LTENV_int + int("1"+"0"*(i-1),2)
        return str(hex(LTENV_int)).encode('utf-8')

    def NSAorSA2NV(self):
        NSAorSAband_int_list = list(set(list(map(int, self.Band2NV_entry.get().split("-")))))
        NSAorSANV_int_list = [0,0,0,0,0,0,0,0]
        for NSAorSAband_int in NSAorSAband_int_list:
            for i in range(len(NSAorSANV_int_list)):
                if NSAorSAband_int > 64*i and NSAorSAband_int <= 64*(i+1):
                    NSAorSANV_int_list[i] = NSAorSANV_int_list[i] + int("1"+"0"*(NSAorSAband_int-64*i-1),2)
                    break
        return " ".join(map(str, NSAorSANV_int_list)).encode('utf-8')
    
    def LTE2NV_for_RESET(self): 
        LTEbandList_int = list(set(list(map(int, self.config.get('Settings', 'default_LTE_Band').split(" ")))))
        LTENV_int = 0
        for i in LTEbandList_int:
            i = i + 1
            if i > 0:
                LTENV_int = LTENV_int + int("1"+"0"*(i-1),2)
        return str(hex(LTENV_int)).encode('utf-8')

    def NSAorSA2NV_for_RESET(self):
        NSAorSAband_int_list = list(set(list(map(int, self.config.get('Settings', 'default_NSAorSA_Band').split(" ")))))
        NSAorSANV_int_list = [0,0,0,0,0,0,0,0]
        for NSAorSAband_int in NSAorSAband_int_list:
            NSAorSAband_int = NSAorSAband_int + 1
            for i in range(len(NSAorSANV_int_list)):
                if NSAorSAband_int > 64*i and NSAorSAband_int <= 64*(i+1):
                    NSAorSANV_int_list[i] = NSAorSANV_int_list[i] + int("1"+"0"*(NSAorSAband_int-64*i-1),2)
                    break
        return " ".join(map(str, NSAorSANV_int_list)).encode('utf-8')

    def set_NV(self, networkTechnology):
        self.main_window.focus_set()
        client = QutsClient.QutsClient("TestAutomation")
        devManager = client.getDeviceManager()

        # get only the devices that support Diag, because the current QXDM plugin commands are meant for Diag only.
        deviceList = devManager.getDevicesForService(DiagService.constants.DIAG_SERVICE_NAME)
        try:
            protList = devManager.getProtocolList(deviceList[0])
        except IndexError:
            messagebox.showerror("注意", "没有识别到设备端口, 请确保已经开端口")
            return
        # print("First device in device list: {}".format(deviceList[0]))
        diagProtocolHandle = -1

        for i in range(len(protList)):
            if (protList[i].protocolType == 0):  # diag type
                diagProtocolHandle = protList[i].protocolHandle
                print(f"Found diag Handle {str(diagProtocolHandle)} description {protList[i].description}")

        if (diagProtocolHandle == -1):
            print("No diag protocol handle found..returning")
            return

        ## create the QXDM for the device
        qxdmService = QXDMService.QxdmService.Client(client.createService(QXDMService.constants.QXDM_SERVICE_NAME, deviceList[0]))

        if (0 != qxdmService.startQXDM(diagProtocolHandle)):
            print("Error in start QXDM")  # Starts diag service on this prot handle
        else:
            # print(f"Diag Service started on handle {str(diagProtocolHandle)}")
            pass

        if networkTechnology == RESET_NV:
            # commands = [b'RequestNVItemWrite /nv/item_files/modem/mmode/lte_bandpref 0x3e0090108df',
            #             b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_nsa_band_pref 1649401659525 28672 0 0 11 0 0 0',
            #             b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_band_pref 1649401659525 28672 0 0 11 0 0 0',]
            commands = [b'RequestNVItemWrite /nv/item_files/modem/mmode/lte_bandpref ' + self.LTE2NV_for_RESET(),
                        b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_nsa_band_pref ' + self.NSAorSA2NV_for_RESET(),
                        b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_band_pref ' + self.NSAorSA2NV_for_RESET(),]
            for command in commands:
                if 0 == qxdmService.sendCommand(command):
                    print("Send Command Successful: {}".format(command))
                    self.Band2NV_lable.config(text="高通专用锁Band: 重置成功")
                    messagebox.showinfo("提示", f"Band重置成功\n请重启设备, 使重置生效!")
                else:
                    self.Band2NV_lable.config(text="高通专用锁Band: 重置失败,请重启PC及设备后再次尝试")
                    messagebox.showwarning("提示", f"Band重置失败, 请重启PC及设备后再次尝试\n确保仅有一台设备连接到PC!")
        else:
            if networkTechnology == LTE:
                command = b'RequestNVItemWrite /nv/item_files/modem/mmode/lte_bandpref ' + self.LTE2NV()
            elif networkTechnology == NSA:
                command = b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_nsa_band_pref ' + self.NSAorSA2NV()
            elif networkTechnology == SA:
                command = b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_band_pref ' + self.NSAorSA2NV()

            if 0 == qxdmService.sendCommand(command):
                print("Send Command Successful: {}".format(command))
                self.Band2NV_lable.config(text=f"高通专用锁Band: 已修改 {networkTechnology}")
                messagebox.showinfo("提示", f"已锁定 {networkTechnology} 为【{self.Band2NV_entry.get()}】 \n请重启设备, 使锁定生效!")
            else:
                self.Band2NV_lable.config(text="高通专用锁Band: 修改失败,请重启PC及设备后再次尝试")
                messagebox.showwarning("提示", f"锁Band失败, 请重启PC及设备后再次尝试\n确保仅有一台设备连接到PC!")

        qxdmService.destroyService()

    def reboot_devices(self):
        os.system(f'adb -s {self.device_serial_number} reboot')

    def banned_Packages(self):
        os.system(f'adb -s {self.device_serial_number} shell iptables -I OUTPUT -j DROP')
        os.system(f'adb -s {self.device_serial_number} shell ip6tables -I OUTPUT -j DROP')
        messagebox.showinfo("提示", f"已禁包!")
    
    def unbanned_Packages(self):
        os.system(f'adb -s {self.device_serial_number} shell iptables -I OUTPUT -j ACCEPT')
        os.system(f'adb -s {self.device_serial_number} shell ip6tables -I OUTPUT -j ACCEPT')
        messagebox.showinfo("提示", f"已解包!")

    #网络状态
    def refresh(self):
        if self.is_refresh.get():
            mServiceState = os.popen(f'adb -s {self.device_serial_number} shell "dumpsys telephony.registry | grep mServiceState"').read().strip().split("\n")[0]
            self.operator_lable.config(text=f'运营商:  {re.search(r"mOperatorAlphaLong ?= ?(.*?),", mServiceState)[1]}')
            self.VoiceRadioTechnology_lable.config(text=f'CALL网络:  {re.search(r"getRilVoiceRadioTechnology ?= ?(.*?),", mServiceState)[1]}')
            DataRadioTechnology = re.search(r"getRilDataRadioTechnology ?= ?(.*?),", mServiceState)[1]
            self.DataRadioTechnology_lable.config(text=f"DATA网络:  {DataRadioTechnology}")
            self.isUsingCarrierAggregation_lable.config(text=f'CA状态:  {re.search(r"isUsingCarrierAggregation ?= ?(.*?),", mServiceState)[1]}')
            if Bands := re.search(r"mBands ?= ?\[(.*?)\] ", mServiceState):
                self.Bands_lable.config(text=f'Bands:  {"B" if LTE in DataRadioTechnology else "N"}{Bands[1]}')
            else:
                self.Bands_lable.config(text="Bands:  ")
            if PCI := re.search(r"mPci ?= ?(.*?) ", mServiceState):
                self.PCI_lable.config(text=f"PCI:  {PCI[1]}")
            else:
                self.PCI_lable.config(text="PCI:  ")

            mSignalStrength = os.popen(f'adb -s {self.device_serial_number} shell "dumpsys telephony.registry | grep -i mSignalStrength"').read().strip().split("\n")[0]
            if LTE in DataRadioTechnology:
                self.RSRP_lable.config(text=f'信号强度RSRP:  {re.search(r"rsrp ?= ?(.*?) ", mSignalStrength)[1]} dBm')
                self.RSRQ_lable.config(text=f'信号质量RSRQ:  {re.search(r"rsrq ?= ?(.*?) ", mSignalStrength)[1]} dB')
            else:
                self.RSRP_lable.config(text=f'信号强度RSRP:  {re.search(r"ssRsrp ?= ?(.*?) ", mSignalStrength)[1]} dBm')
                self.RSRQ_lable.config(text=f'信号质量RSRQ:  {re.search(r"ssRsrq ?= ?(.*?) ", mSignalStrength)[1]} dB')

            self.main_window.after(1000, lambda: self.new_thread_to_do(self.refresh))
        else:
            self.operator_lable.config(text="运营商: ")
            self.VoiceRadioTechnology_lable.config(text="CALL网络: ")
            self.DataRadioTechnology_lable.config(text="DATA网络: ")
            self.isUsingCarrierAggregation_lable.config(text="CA状态: ")
            self.Bands_lable.config(text="Bands: ")
            self.PCI_lable.config(text="PCI: ")
            self.RSRP_lable.config(text="信号强度RSRP: ")
            self.RSRQ_lable.config(text="信号质量RSRQ: ")

    
    #日志分析
    def read_throughputs(self, raw_data:str):
        throughputs = {'DL_LTE': [], 'DL_NR': [], 'UL_LTE': [], 'UL_NR': []}

        data_list = raw_data.splitlines()
        for line in data_list:
            if 'QTRACE' in line:
                parts = line.split()
                timestamp = re.search(r'(\d{2}:\d{2}:\d{2})\.\d+', parts[1]).group(1)
                timestamp = datetime.strptime(timestamp, "%H:%M:%S")
                throughput_search = re.search(r'tput\.[Kk]bps:\[.*?PHY:\s*(\d+)', line)
                if not throughput_search:
                    throughput_search = re.search(r'PHY\|\s*(\d+)\s*Kbps', line)
                if throughput_search:
                    throughput = int(throughput_search.group(1))
                    if 'DL' in line:
                        if 'LT' in line:
                            throughputs['DL_LTE'].append((timestamp, throughput))
                        elif 'NR' in line:
                            throughputs['DL_NR'].append((timestamp, throughput))
                    elif 'UL' in line:
                        if 'LT' in line:
                            throughputs['UL_LTE'].append((timestamp, throughput))
                        elif 'NR' in line:
                            throughputs['UL_NR'].append((timestamp, throughput))
                
        return throughputs['DL_LTE'], throughputs['DL_NR'], throughputs['UL_LTE'], throughputs['UL_NR']
    
    # MBps转换函数
    def kbpslist_to_mbpslist(self, throughputs):
        result = []
        for throughput in throughputs:
            result.append(throughput[1]/1000)
        return result

    def throughputs_analyze(self):
        dl_lte, dl_nr, ul_lte, ul_nr = self.read_throughputs(self.raw_data_input.get(1.0,END))

        plt.subplot(2,1,1)
        if dl_lte:
            plt.plot([t for t, _ in dl_lte], self.kbpslist_to_mbpslist(dl_lte), label='DL 4G PHY', color='orange', linestyle='-')
        if dl_nr:
            plt.plot([t for t, _ in dl_nr], self.kbpslist_to_mbpslist(dl_nr), label='DL 5G PHY', color='red', linestyle='-')
        plt.legend()    # 添加图例
        dl_ax = plt.gca()
        dl_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        dl_ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=20, maxticks=40))
        plt.xticks(rotation = 45)
        plt.title('DL Throughput')
        plt.xlabel('Time (hh:mm:ss)')
        plt.ylabel('Throughput (Mbps)')
        # 启用默认网格
        plt.grid(True)
        # 自定义网格样式
        plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        plt.subplot(2,1,2)
        if ul_lte:
            plt.plot([t for t, _ in ul_lte], self.kbpslist_to_mbpslist(ul_lte), label='UL 4G PHY', color='green', linestyle='-')
        if ul_nr:
            plt.plot([t for t, _ in ul_nr], self.kbpslist_to_mbpslist(ul_nr), label='UL 5G PHY', color='blue', linestyle='-')
        plt.legend()    # 添加图例
        ul_ax = plt.gca()
        ul_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ul_ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=20, maxticks=40))
        plt.xticks(rotation = 45)
        plt.title('UL Throughput')
        plt.xlabel('Time (hh:mm:ss)')
        plt.ylabel('Throughput (Mbps)')
        # 启用默认网格
        plt.grid(True)
        # 自定义网格样式
        plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        plt.subplots_adjust(hspace=0.4)
        plt.show()  

    def new_thread_to_do(self, func):
        threading.Thread(target = func).start()

    def save_config(self):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'call_number': self.call_number_entry.get(),
            'wait_time': self.wait_time_spinbox.get(),
            'wait_release_max_time': self.wait_release_max_time_spinbox.get(),
            'log_name': self.log_name_entry.get(),
            'SMS_number': self.SMS_number_entry.get(),
            'SMS_content': self.SMS_content_entry.get(),
            'testfile_size': self.file_size_entry.get(),
            'default_LTE_Band': self.config.get('Settings', 'default_LTE_Band'),
            'default_NSAorSA_Band': self.config.get('Settings', 'default_NSAorSA_Band'),
            'theme': list(self.allowed_themes_map.keys()).index(self.theme_combobox.get()),
        }
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.ini')
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        # print("配置已保存到config.ini")

    def on_closing(self):
        if self.device_connect_check_timer:
            self.main_window.after_cancel(self.device_connect_check_timer)
            self.device_connect_check_timer = None
        self.save_config()
        self.device_sn = None
        if self in MultipleTest.instances:
            MultipleTest.instances.remove(self)
        self.main_window.destroy()

        if not MultipleTest.instances:
            self.master_window.destroy()

    def show_message(self):
        messagebox.showinfo("提示", "测试工具已连续使用很久了yo\n\n注意休息\n\nby ThunderSoft29749")
        self.main_window.after(TIMER, self.show_message)

    def on_f1(self, event): 
        self.is_off_airplane_mode.set(not self.is_off_airplane_mode.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.disable_airplane_mode)
            # self.disable_airplane_mode()
        
    def on_f2(self, event): 
        self.is_make_call.set(not self.is_make_call.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.make_call)
            # self.make_call()

    def on_f3(self, event): 
        self.is_pickup_call.set(not self.is_pickup_call.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.pickup_call)
            # self.pickup_call()

    def on_f4(self, event): 
        self.is_fast_test.set(not self.is_fast_test.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.fast_test)
            # self.fast_test()

    def on_f5(self, event): 
        self.is_terminate_call.set(not self.is_terminate_call.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.terminate_call)
            # self.terminate_call()

    def on_f6(self, event): 
        self.is_on_airplane_mode.set(not self.is_on_airplane_mode.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.enable_airplane_mode)
            # self.enable_airplane_mode()

    def on_f7(self, event): 
        self.is_save_log.set(not self.is_save_log.get())
        if not self.is_auto.get():
            self.new_thread_to_do(self.save_log)
            # self.save_log()

    def on_f9(self, event): 
        self.is_auto.set(not self.is_auto.get())
        self.update_command()

    def on_f11(self, event): 
        if self.is_auto.get():
            self.new_thread_to_do(self.begin)
            # self.begin()

    def on_f12(self, event): 
        self.cancel_timer()


def start():
    init_window = Tk()
    init_window.withdraw()
    multipleTest = MultipleTest(init_window)
    multipleTest.set_init_window()
    init_window.mainloop()

start()