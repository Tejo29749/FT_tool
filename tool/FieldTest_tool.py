# -----------------------------------------------------------------------------
# 此脚本用于控制安卓手机，实现自动执行测试项
# by ThunderSoft29749
# -----------------------------------------------------------------------------
import win32gui
import win32con
import win32api
import win32clipboard
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import time, pyperclip, configparser
import threading
import os, re, sys
import subprocess
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

sys.path.append('C:\Program Files (x86)\Qualcomm\QUTS\Support\python')
	
import QutsClient
import Common.ttypes

import DiagService.DiagService
import DiagService.constants
import DiagService.ttypes

import QXDMService.QxdmService
import QXDMService.constants
import QXDMService.ttypes

LTE = "LTE"
NSA = "NSA"
SA  = "SA"
RESET_NV = "RESET_NV"
TIMER = 1000*60*60*5

class MultipleTest():
    def __init__(self,main_window):
        self.main_window = main_window
        # 从顶层窗口向下搜索主窗口，无法搜索子窗口
        # FindWindow(lpClassName=None, lpWindowName=None)  窗口类名 窗口标题名
        # self.vysor_handle = win32gui.FindWindow("Chrome_WidgetWin_1", "SD0A2") #E9-SE0C4
        # self.qxdm_handle = win32gui.FindWindow("Qt5152QWindowIcon", "QXDM_Pro_5.2.520 [LOGGING] - Qualcomm HS-USB Diagnostics 90DB (COM14) - Legacy Diag")
        # savelog_handle = win32gui.FindWindow("#32770", "Save Item Store (Cancel To Discard)?")
        # print(win32gui.GetClassName(handle))
        self.counter = 0
        self.complete = 0
        self.auto_timer_id = None
        self.wait_timer_id = None
        self.device_connect_check_timer = None
        self.is_run = BooleanVar()

        self.qxdm_save_pos = (128/1936,68/1056)
        self.send_SMS_pos = (990/1080, 2160/2340)

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
            self.start_button.config(command=self.begin)
        else:
            self.off_airplane_mode_checkbutton.config(command=self.disable_airplane_mode)
            self.make_call_checkbutton.config(command=self.make_call)
            self.pickup_call_checkbutton.config(command=self.pickup_call)
            self.fast_test_checkbutton.config(command=lambda: self.in_run(self.fast_test))
            self.terminate_call_checkbutton.config(command=self.terminate_call)
            self.on_airplane_mode_checkbutton.config(command=self.enable_airplane_mode)
            self.save_log_checkbutton.config(command=self.save_log)
            self.start_button.config(command=self.skip)

    def set_init_window(self):
        self.main_window.title("FT多次测试工具")
        self.main_window.geometry('350x600')
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建 Notebook 组件
        self.notebook = ttk.Notebook(self.main_window)
        self.notebook.pack(padx=5, expand=True)

        # 创建场测标签页
        self.fieldtest = ttk.Frame(self.notebook, width=400, height=900)
        self.fieldtest.pack(fill='both', expand=True)
        self.notebook.add(self.fieldtest, text='  场测  ')

        # 创建其他工具标签页
        self.othertools = ttk.Frame(self.notebook, width=400, height=900)
        self.othertools.pack(fill='both', expand=True)
        self.notebook.add(self.othertools, text='  其他工具  ')

        # 创建仪表盘标签页
        self.dashboard = ttk.Frame(self.notebook, width=400, height=900)
        self.dashboard.pack(fill='both', expand=True)
        self.notebook.add(self.dashboard, text=' 网络状态 ')

        # 创建日志分析标签页
        self.loganalyze = ttk.Frame(self.notebook, width=400, height=900)
        self.loganalyze.pack(fill='both', expand=True)
        self.notebook.add(self.loganalyze, text=' 日志分析 ')

        # 创建帮助标签页
        self.help = ttk.Frame(self.notebook, width=400, height=900)
        self.help.pack(fill='both', expand=True)
        self.notebook.add(self.help, text=' 帮助 ')

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
        self.is_off_airplane_mode = BooleanVar()
        self.is_make_call = BooleanVar()
        self.is_pickup_call = BooleanVar()
        self.is_fast_test = BooleanVar()
        self.is_terminate_call = BooleanVar()
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

        #各项功能部件
        self.USBdebug_label = Label(self.main_window, text="设备连接异常!\n请确保设备已连接\n并开启USB Debug", font=("Arial", 15), fg="red")
        def device_connect_check():
            if os.popen('adb shell settings get global adb_enabled').read().strip() == "1":
                self.USBdebug_label.pack_forget()
            else:
                self.USBdebug_label.pack(anchor='w', before=self.notebook, fill='both', expand=True)
            self.device_connect_check_timer = self.main_window.after(5000,lambda: self.new_thread_to_do(device_connect_check))
        device_connect_check()

        self.auto_checkbutton = Checkbutton(self.fieldtest, text="F9> 全自动", variable = self.is_auto, command=self.update_command)
        self.auto_checkbutton.pack(anchor='w',padx=5,pady=2)

        self.airplanemode_status_label = Label(self.fieldtest, text="")
        self.airplanemode_status_label.pack(anchor='w',padx=20,pady=2)
        self.load_airplane_mode_status()

        self.off_airplane_mode_checkbutton = Checkbutton(self.fieldtest, text="F1> 关闭飞行模式", variable = self.is_off_airplane_mode, command=self.disable_airplane_mode)
        self.off_airplane_mode_checkbutton.pack(anchor='w',padx=20,pady=2)  

        self.make_call_checkbutton = Checkbutton(self.fieldtest, text="F2> 拨打电话", variable = self.is_make_call, command=self.make_call)
        self.make_call_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.call_number_label = Label(self.fieldtest, text="电话号码:")
        self.call_number_label.pack(anchor='w',padx=20,pady=2)
        call_number = StringVar()
        call_number.set(self.config.get('Settings', 'call_number'))
        self.call_number_entry = Entry(self.fieldtest, textvariable=call_number)
        self.call_number_entry.pack(anchor='w',padx=25,pady=2)

        self.pickup_call_checkbutton = Checkbutton(self.fieldtest, text="F3> 接听电话", variable = self.is_pickup_call, command=self.pickup_call)
        self.pickup_call_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.fast_test_checkbutton = Checkbutton(self.fieldtest, text="F4> 开启fast测速", variable = self.is_fast_test, command=lambda: self.in_run(self.fast_test))
        self.fast_test_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.wait_time_label = Label(self.fieldtest, text="等待时长(秒):")
        self.wait_time_label.pack(anchor='w',padx=20,pady=2)
        wait_time = StringVar()
        wait_time.set(self.config.get('Settings', 'wait_time'))
        self.wait_time_entry = Entry(self.fieldtest, textvariable=wait_time)
        self.wait_time_entry.pack(anchor='w',padx=25,pady=2)

        self.terminate_call_checkbutton = Checkbutton(self.fieldtest, text="F5> 挂断电话", variable = self.is_terminate_call, command=self.terminate_call)
        self.terminate_call_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.on_airplane_mode_checkbutton = Checkbutton(self.fieldtest, text="F6> 开启飞行模式", variable = self.is_on_airplane_mode, command=self.enable_airplane_mode)
        self.on_airplane_mode_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.save_log_checkbutton = Checkbutton(self.fieldtest, text="F7> 复制日志名到剪切板", variable = self.is_save_log, command=self.save_log)
        self.save_log_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.log_name_label = Label(self.fieldtest, text="日志命名:")
        self.log_name_label.pack(anchor='w',padx=20,pady=2)
        log_name = StringVar()
        log_name.set(self.config.get('Settings', 'log_name'))
        self.log_name_entry = Entry(self.fieldtest, width = 40, textvariable=log_name)
        self.log_name_entry.pack(anchor='w',padx=25,pady=2)

        self.repeat_times_label = Label(self.fieldtest, text="重复次数:")
        self.repeat_times_label.pack(anchor='w',padx=5,pady=2)
        repeat_times = StringVar()
        repeat_times.set("1")
        self.repeat_times_entry = Entry(self.fieldtest, textvariable=repeat_times)
        self.repeat_times_entry.pack(anchor='w',padx=10,pady=2)

        self.startstop_button_frame = Frame(self.fieldtest)
        self.startstop_button_frame.pack(anchor='w', padx=10, pady=10)

        self.start_button = Button(self.startstop_button_frame, text='F11> 开始', command=None)
        self.start_button.pack(side=LEFT,padx=15,pady=2)

        self.stop_button = Button(self.startstop_button_frame, text='F12> 中止', command=self.cancel_timer)
        self.stop_button.pack(side=LEFT,padx=15,pady=2)

        self.progress_label = Label(self.fieldtest, text="进度: ", font=("Arial", 15))
        self.progress_label.pack(anchor='w',padx=20,pady=2)

        self.window_on_top_checkbutton = Checkbutton(self.othertools, text="保持此窗口在最前显示", variable = self.is_window_on_top, command=self.set_window_on_top)
        self.window_on_top_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.func_button_frame = Frame(self.othertools)
        self.func_button_frame.pack(anchor='w', padx=5, pady=5)

        self.open_port_button = Button(self.func_button_frame, text=' 开端口 ', command=self.open_port)
        self.open_port_button.pack(side=LEFT,padx=15,pady=2)

        self.off_temp_protect_button = Button(self.func_button_frame, text=' 禁用高温保护 ', command=self.off_temp_protect)
        self.off_temp_protect_button.pack(side=LEFT,padx=15,pady=2)

        self.screen_off_timeout_lable = Label(self.othertools, text="屏幕常亮(分钟): ")
        self.screen_off_timeout_lable.pack(anchor='w',padx=10,pady=2)
        self.screen_off_timeout_scale = ttk.Scale(self.othertools, orient="horizontal", length=300, from_=1, to=100, command=self.set_screen_off_timeout)
        self.screen_off_timeout_scale.pack(anchor='w',padx=10,pady=2)
        screen_off_timeout_str = os.popen('adb shell settings get system screen_off_timeout').read().strip()
        if screen_off_timeout_str.isdigit():
            screen_off_timeout_minute = str(int(screen_off_timeout_str)/60000)
            self.screen_off_timeout_lable.config(text = "屏幕常亮(分钟): " + screen_off_timeout_minute)
            self.screen_off_timeout_scale.set(screen_off_timeout_minute)

        self.screen_brightness_lable = Label(self.othertools, text="屏幕亮度: ")
        self.screen_brightness_lable.pack(anchor='w',padx=10,pady=2)
        self.screen_brightness_scale = ttk.Scale(self.othertools, orient="horizontal", length=300, from_=1, to=150, command=self.set_screen_brightness)
        self.screen_brightness_scale.pack(anchor='w',padx=10,pady=2)
        screen_brightness_str = os.popen('adb shell settings get system screen_brightness').read().strip()
        if screen_brightness_str.isdigit():
            self.screen_brightness_lable.config(text = "屏幕亮度: " + screen_brightness_str)
            self.screen_brightness_scale.set(screen_brightness_str)
        
        accelerometer_rotation_str = os.popen('adb shell settings get system screen_brightness').read().strip()
        if accelerometer_rotation_str == "1":
            self.is_accelerometer_rotation.set(True)
        else:
            self.is_accelerometer_rotation.set(False)
        self.accelerometer_rotation_checkbutton = Checkbutton(self.othertools, text="屏幕自动旋转", variable = self.is_accelerometer_rotation, command=self.set_accelerometer_rotation)
        self.accelerometer_rotation_checkbutton.pack(anchor='w',padx=20,pady=2)

        self.SMS_number_lable = Label(self.othertools, text="短信号码: ")
        self.SMS_number_lable.pack(anchor='w',padx=10,pady=2)
        SMS_number = StringVar()
        SMS_number.set(self.config.get('Settings', 'SMS_number'))
        self.SMS_number_entry = Entry(self.othertools, width = 40, textvariable=SMS_number)
        self.SMS_number_entry.pack(anchor='w',padx=25,pady=2)
        self.SMS_content_lable = Label(self.othertools, text="短信内容: ")
        self.SMS_content_lable.pack(anchor='w',padx=10,pady=2)
        SMS_content = StringVar()
        SMS_content.set(self.config.get('Settings', 'SMS_content'))
        self.SMS_content_entry = Entry(self.othertools, width = 40, textvariable=SMS_content)
        self.SMS_content_entry.pack(anchor='w',padx=25,pady=2)
        self.SMS_send_button = Button(self.othertools, text='发送短信', command=self.send_SMS)
        self.SMS_send_button.pack(anchor='w',padx=15,pady=5)

        self.Band2NV_lable = Label(self.othertools, text="高通专用锁Band: (输入例:3-18-28)")
        self.Band2NV_lable.pack(anchor='w',padx=10,pady=10)
        # self.lockBandtip1_lable = Label(self.othertools, text="LTE:修改 NV 65633")
        # self.lockBandtip1_lable.pack(anchor='w',padx=10,pady=5)
        # self.lockBandtip2_lable = Label(self.othertools, text="NSA:修改 NV 74213")
        # self.lockBandtip2_lable.pack(anchor='w',padx=10,pady=5)
        # self.lockBandtip3_lable = Label(self.othertools, text="SA: 修改 NV 74087")
        # self.lockBandtip3_lable.pack(anchor='w',padx=10,pady=5)
        self.Band2NV_entry = Entry(self.othertools, width = 40)
        self.Band2NV_entry.pack(anchor='w',padx=25,pady=2)
        self.Band2NV_entry.bind("<FocusIn>", self.on_focus_in_Band2NV_entry)
        self.Band2NV_button_frame = Frame(self.othertools)
        self.Band2NV_button_frame.pack(anchor='w', padx=5, pady=5)
        self.LTE_button = Button(self.Band2NV_button_frame, text=' LTE ', command=lambda: self.set_NV(LTE))
        self.LTE_button.pack(side=LEFT,padx=15,pady=2)
        self.NSAorSA_button = Button(self.Band2NV_button_frame, text=' NSA ', command=lambda: self.set_NV(NSA))
        self.NSAorSA_button.pack(side=LEFT,padx=10,pady=2)
        self.NSAorSA_button = Button(self.Band2NV_button_frame, text=' SA ', command=lambda: self.set_NV(SA))
        self.NSAorSA_button.pack(side=LEFT,padx=10,pady=2)
        self.NSAorSA_button = Button(self.Band2NV_button_frame, text=' 重启 ', command= self.reboot_devices)
        self.NSAorSA_button.pack(side=LEFT,padx=10,pady=2)
        self.NSAorSA_button = Button(self.Band2NV_button_frame, text='重置NV', command=lambda: self.set_NV(RESET_NV))
        self.NSAorSA_button.pack(side=LEFT,padx=10,pady=2)

        self.dcmSMS_button_frame = Frame(self.othertools)
        self.dcmSMS_button_frame.pack(anchor='w', padx=5, pady=5)
        self.NSAorSA_button = Button(self.dcmSMS_button_frame, text=' 禁包 ', command=self.banned_Packages)
        self.NSAorSA_button.pack(side=LEFT,padx=10,pady=2)
        self.NSAorSA_button = Button(self.dcmSMS_button_frame, text=' 解包 ', command=self.unbanned_Packages)
        self.NSAorSA_button.pack(side=LEFT,padx=10,pady=2)

        #网络状态
        self.refresh_checkbutton = Checkbutton(self.dashboard, text="每秒自动刷新", variable = self.is_refresh, command=self.refresh)
        self.refresh_checkbutton.pack(anchor='w',padx=10,pady=2)

        self.operator_lable = Label(self.dashboard, text="运营商: ")
        self.operator_lable.pack(anchor='w',padx=10,pady=2)

        self.VoiceRadioTechnology_lable = Label(self.dashboard, text="CALL网络: ")
        self.VoiceRadioTechnology_lable.pack(anchor='w',padx=10,pady=2)

        self.DataRadioTechnology_lable = Label(self.dashboard, text="DATA网络: ")
        self.DataRadioTechnology_lable.pack(anchor='w',padx=10,pady=2)

        self.isUsingCarrierAggregation_lable = Label(self.dashboard, text="CA状态: ")
        self.isUsingCarrierAggregation_lable.pack(anchor='w',padx=10,pady=2)

        self.Bands_lable = Label(self.dashboard, text="Bands: ")
        self.Bands_lable.pack(anchor='w',padx=10,pady=2)

        self.PCI_lable = Label(self.dashboard, text="PCI: ")
        self.PCI_lable.pack(anchor='w',padx=10,pady=2)

        self.RSRP_lable = Label(self.dashboard, text="信号强度RSRP: ")
        self.RSRP_lable.pack(anchor='w',padx=10,pady=2)

        self.RSRQ_lable = Label(self.dashboard, text="信号质量RSRQ: ")
        self.RSRQ_lable.pack(anchor='w',padx=10,pady=2)


        #日志分析
        self.raw_data_label = Label(self.loganalyze, text='输入待分析的QXDM log: ', anchor=W)
        self.raw_data_label.pack(anchor='w',padx=10,pady=5)

        self.raw_data_input = Text(self.loganalyze, height=5, wrap=NONE)
        self.raw_data_input.pack(anchor='w',padx=10,pady=5)

        self.throughputs_chart_button = Button(self.loganalyze, text=' 吞吐量 ', command=self.throughputs_analyze)
        self.throughputs_chart_button.pack(anchor='w',padx=10,pady=5)

        self.tips_label = Label(self.help, anchor="w", justify="left", text="提示：\n\n1.未勾选全自动时, 每项功能为通过点击或快捷键单独\n    执行\n\n"
                                +"2.勾选全自动后选择希望自动执行的功能，点击开始会\n    从上到下依次执行被勾选的各项功能\n\n"
                                +"3.推荐将等待时长填写为 单次测试时长+冗余等待时长\n\n"
                                +"4.日志命名会将输入框的文字复制到剪切板即可直接粘贴\n    并会将名称末尾的数字自动加1以供下次使用\n\n"
                                +"5.涉及到保存log操作时, 建议将重复次数设置为 1\n\n"
                                +"6.锁band时需要提前开端口, 输入 0 即为屏蔽对应网络\n\n"
                                +"7.默认Band可从policy.xml获取(PCAT/EFSExplorer\n/policyman/carrier_policy.xml)后填写在config.ini\n进行重置\n\n"
                                +"8.网络状态刷新会占用电脑性能，建议不用时关闭\n\n"
                                +"by ThunderSoft29749")
        self.tips_label.pack(anchor='w',padx=10,pady=10)


    def click_it(self, handle, pos):  # 可后台
        # 获取窗口位置
        left, top, right, bottom = win32gui.GetWindowRect(handle)
        tmp = win32api.MAKELONG(int((right - left) * pos[0]), int((bottom - top) * pos[1]))
        win32gui.SendMessage(handle, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
        win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, tmp)
        win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, tmp)

    def move_it(self, handle, start_pos, end_pos):  # 可后台
        # 获取窗口位置
        left, top, right, bottom = win32gui.GetWindowRect(handle)
        start_tmp = win32api.MAKELONG(int((right - left) * start_pos[0]), int((bottom - top) * start_pos[1]))
        end_tmp   = win32api.MAKELONG(int((right - left) * end_pos[0]), int((bottom - top) * end_pos[1]))
        win32gui.SendMessage(handle, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
        win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, start_tmp)
        win32gui.SendMessage(handle, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, end_tmp)
        time.sleep(0.1)
        win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, end_tmp)

    def in_run(self, callback):
        self.is_run.set(True)
        callback()

    def enable_airplane_mode(self):
        if os.popen('adb shell settings get global airplane_mode_on').read().strip() == "0":  #airplane_mode_off
            os.system('adb root')
            os.system('adb shell settings put global airplane_mode_on 1')
            os.system('adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true')
        self.load_airplane_mode_status()

    def disable_airplane_mode(self):
        self.progress_label.config(text="进度: ")
        if os.popen('adb shell settings get global airplane_mode_on').read().strip() == "1":  #airplane_mode_on
            os.system('adb root')
            os.system('adb shell settings put global airplane_mode_on 0')
            os.system('adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false')
        self.load_airplane_mode_status()

    def load_airplane_mode_status(self):
        if os.popen('adb shell settings get global airplane_mode_on').read().strip() == "0":  #airplane_mode_off
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
                output = subprocess.check_output(["adb", "shell", "dumpsys", "telephony.registry"], universal_newlines=True)
                lines = output.splitlines()
                
                for line in lines:
                    if keyword in line:
                        call_state = line.split("=")[1].strip()
                        return int(call_state)
        
            except subprocess.CalledProcessError as e:
                print(f"Error executing adb command: {e}")

    def get_mVoiceRegState(self):
        mServiceState = os.popen('adb shell "dumpsys telephony.registry | grep mServiceState"').read().strip().split("\n")[0]
        return re.search(r"mVoiceRegState ?= ?(.*?),", mServiceState)[1]

    def make_call(self):
        if self.get_call_state() == 0:
            os.system('adb shell am start -a android.intent.action.CALL tel:' + self.call_number_entry.get())
    
    def pickup_call(self):
        if self.get_call_state() == 1:
            os.system('adb shell input keyevent KEYCODE_CALL')

    def fast_test(self):
        os.system('adb shell am start -a android.intent.action.VIEW -d https://fast.com --ez create_new_tab false')
        # os.system('adb shell input keyevent KEYCODE_EXPLORER')
        # os.system('adb shell input swipe 500 500 500 1000')
        self.complete = 0
        self.wait_progress()
        # TODO 关闭标签页
        # os.system('adb shell pm clear cn.com.test.mobile') 

    def wait_progress(self):
        count = 0
        def set_progress():
            nonlocal count
            count += 1
            if not self.is_run.get():
                self.progress_label.config(text="进度: 已中止")
            elif count <= int(self.wait_time_entry.get()):
                self.progress_label.config(text="进度: 已等待 " + str(count) + " 秒")
                self.wait_timer_id = self.main_window.after(1000, set_progress)
            else:
                self.progress_label.config(text="进度: 已完成等待 " + str(self.wait_time_entry.get()) + " 秒！")
                self.complete = 1
        
        set_progress()

    def terminate_call(self):
        if self.get_call_state() != 0:
            os.system('adb shell input keyevent KEYCODE_ENDCALL')

    def save_log(self):
        log_name = self.log_name_entry.get()
        pyperclip.copy(log_name)

        step = re.search(r'\d+$', log_name).group()
        new_log_name = log_name[0:-len(step)] + str(int(step) + 1)
        self.log_name_entry.delete(0, END)  # 清空输入框
        self.log_name_entry.insert(0, new_log_name)  # 插入新的值

    def begin(self):
        self.counter = 0
        self.is_run.set(True)

        def repeat():
            self.counter += 1
            if self.is_off_airplane_mode.get() and self.is_run.get():
                self.disable_airplane_mode()
            if self.is_make_call.get() and self.is_run.get():
                while self.get_mVoiceRegState() != "0(IN_SERVICE)" and self.is_run.get(): #等待语音服务至可用
                    time.sleep(1)
                self.make_call()
                while self.get_mForegroundCallState() != 1 and self.is_run.get(): #拨号后等待至开始通话
                    time.sleep(1)
                time.sleep(2)
            if self.is_pickup_call.get():
                while self.get_call_state() != 1 and self.is_run.get():
                    time.sleep(1)
                self.pickup_call() 
                time.sleep(2)
            if self.is_fast_test.get() and self.is_run.get():
                while self.get_data_state() == 0 and self.is_run.get():
                    time.sleep(1)
                self.fast_test()
            else:
                self.wait_progress()

            def delay_to_do():
                if self.is_run.get():
                    if self.is_terminate_call.get():
                        # print("is_terminate_call")
                        time.sleep(1)
                        self.terminate_call()
                    if self.is_on_airplane_mode.get():
                        # print("is_on_airplane_mode")
                        time.sleep(1)
                        self.enable_airplane_mode()
                    if self.is_save_log.get():
                        # print("is_save_log")
                        self.save_log()
                    
                    if self.counter < int(self.repeat_times_entry.get()):
                        repeat()
            self.auto_timer_id = self.main_window.after(int(self.wait_time_entry.get())*1000 + 500, delay_to_do)
                
        repeat()

    def cancel_timer(self):
        self.is_run.set(False)
        if self.auto_timer_id is not None:
            self.main_window.after_cancel(self.auto_timer_id)
            self.auto_timer_id = None
        if self.wait_timer_id is not None:
            self.main_window.after_cancel(self.wait_timer_id)
            self.wait_timer_id = None

    def set_window_on_top(self):
        if self.is_window_on_top.get():
            self.main_window.attributes('-topmost', True)
        else:
            self.main_window.attributes('-topmost', False)

    def open_port(self):
        os.system('adb root')
        os.system('adb shell setprop sys.usb.config \"diag,adb\"')

    def off_temp_protect(self):
        os.system('adb root')
        os.system('adb shell thermal_manager /vendor/etc/.tp/.ht120.mtc')
        os.system('adb shell stop thermal-engine')

    def set_screen_off_timeout(self,value):
        os.system('adb shell settings put system screen_off_timeout ' + str(int(float(value))*60000))
        self.screen_off_timeout_lable.config(text = "屏幕常亮(分钟):  " + str(int(float(value))))

    def set_screen_brightness(self,value):
        os.system('adb shell settings put system screen_brightness ' + str(int(float(value)))) 
        self.screen_brightness_lable.config(text = "屏幕亮度:  " + str(int(float(value))))

    def set_accelerometer_rotation(self):
        if self.is_accelerometer_rotation.get():
            os.system('adb shell settings put system accelerometer_rotation 1')
        else:
            os.system('adb shell settings put system accelerometer_rotation 0')

    def send_SMS(self):
        os.system('adb shell am start -a android.intent.action.SENDTO -d sms:'+ self.SMS_number_entry.get() 
                  +' --es sms_body \"' + self.SMS_content_entry.get() + '\" --ez exit_on_sent false')
        time.sleep(1)
        # os.system('adb shell input tap 990 2160')
        
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
        client = QutsClient.QutsClient("TestAutomation")
        devManager = client.getDeviceManager()

        # get only the devices that support Diag, because the current QXDM plugin commands are meant for Diag only.
        deviceList = devManager.getDevicesForService(DiagService.constants.DIAG_SERVICE_NAME)
        protList = devManager.getProtocolList(deviceList[0])
        # print("First device in device list: {}".format(deviceList[0]))
        diagProtocolHandle = -1

        for i in range(len(protList)):
            if (protList[i].protocolType == 0):  # diag type
                diagProtocolHandle = protList[i].protocolHandle
                print("Found diag Handle " + str(diagProtocolHandle) + " description " + protList[i].description)

        if (diagProtocolHandle == -1):
            print("No diag protocol handle found..returning")
            return

        ## create the QXDM for the device
        qxdmService = QXDMService.QxdmService.Client(client.createService(QXDMService.constants.QXDM_SERVICE_NAME, deviceList[0]))

        if (0 != qxdmService.startQXDM(diagProtocolHandle)):
            print("Error in start QXDM")  # Starts diag service on this prot handle
        else:
            # print("Diag Service started on handle " + str(diagProtocolHandle))
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
                else:
                    self.Band2NV_lable.config(text="高通专用锁Band: 重置失败,请重启PC及设备后再次尝试")
        else:
            if networkTechnology == LTE:
                command = b'RequestNVItemWrite /nv/item_files/modem/mmode/lte_bandpref ' + self.LTE2NV()
            elif networkTechnology == NSA:
                command = b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_nsa_band_pref ' + self.NSAorSA2NV()
            elif networkTechnology == SA:
                command = b'RequestNVItemWrite /nv/item_files/modem/mmode/nr_band_pref ' + self.NSAorSA2NV()

            if 0 == qxdmService.sendCommand(command):
                print("Send Command Successful: {}".format(command))
                self.Band2NV_lable.config(text="高通专用锁Band: 已修改 " + networkTechnology)
            else:
                self.Band2NV_lable.config(text="高通专用锁Band: 修改失败,请重启PC及设备后再次尝试")

        qxdmService.destroyService()

    def reboot_devices(self):
        os.system('adb reboot')   

    def banned_Packages(self):
        os.system('adb shell iptables -I OUTPUT -j DROP') 
    
    def unbanned_Packages(self):
        os.system('adb shell iptables -I OUTPUT -j ACCEPT') 

    #网络状态
    def refresh(self):
        if self.is_refresh.get():
            mServiceState = os.popen('adb shell "dumpsys telephony.registry | grep mServiceState"').read().strip().split("\n")[0]
            self.operator_lable.config(text="运营商:  " + re.search(r"mOperatorAlphaLong ?= ?(.*?),", mServiceState)[1])
            self.VoiceRadioTechnology_lable.config(text="CALL网络:  " + re.search(r"getRilVoiceRadioTechnology ?= ?(.*?),", mServiceState)[1])
            DataRadioTechnology = re.search(r"getRilDataRadioTechnology ?= ?(.*?),", mServiceState)[1]
            self.DataRadioTechnology_lable.config(text="DATA网络:  " + DataRadioTechnology)
            self.isUsingCarrierAggregation_lable.config(text="CA状态:  " + re.search(r"isUsingCarrierAggregation ?= ?(.*?),", mServiceState)[1])
            if Bands := re.search(r"mBands ?= ?\[(.*?)\] ", mServiceState):
                self.Bands_lable.config(text="Bands:  " + ("B" if LTE in DataRadioTechnology else "N") + Bands[1])
            else:
                self.Bands_lable.config(text="Bands:  ")
            if PCI := re.search(r"mPci ?= ?(.*?) ", mServiceState):
                self.PCI_lable.config(text="PCI:  " + PCI[1])
            else:
                self.PCI_lable.config(text="PCI:  ")

            mSignalStrength = os.popen('adb shell "dumpsys telephony.registry | grep -i mSignalStrength"').read().strip().split("\n")[0]
            if LTE in DataRadioTechnology:
                self.RSRP_lable.config(text="信号强度RSRP:  " + re.search(r"rsrp ?= ?(.*?) ", mSignalStrength)[1] + " dBm")
                self.RSRQ_lable.config(text="信号质量RSRQ:  " + re.search(r"rsrq ?= ?(.*?) ", mSignalStrength)[1] + " dB")
            else:
                self.RSRP_lable.config(text="信号强度RSRP:  " + re.search(r"ssRsrp ?= ?(.*?) ", mSignalStrength)[1] + " dBm")
                self.RSRQ_lable.config(text="信号质量RSRQ:  " + re.search(r"ssRsrq ?= ?(.*?) ", mSignalStrength)[1] + " dB")

            self.main_window.after(1000, lambda: self.new_thread_to_do(self.refresh))
        else:
            pass

    
    #日志分析
    def read_throughputs(self, raw_data:str):
        throughputs = {'DL_LTE': [], 'DL_NR': [], 'UL_LTE': [], 'UL_NR': []}

        data_list = raw_data.splitlines()
        for line in data_list:
            if 'QTRACE' in line:
                parts = line.split()
                timestamp = re.search(r'(\d{2}:\d{2}:\d{2})\.\d+', parts[1]).group(1)
                timestamp = datetime.strptime(timestamp, "%H:%M:%S")
                # direction = 'UL' if 'UL' in line else 'DL'
                throughput_search = re.search(r'tput\.[Kk]bps:\[.*?PHY:\s*(\d+)', line)
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
    def kbps_to_mbps(self, kbps):
        return kbps / 1000

    def kbpslist_to_mbpslist(self, throughputs):
        result = []
        for throughput in throughputs:
            result.append(self.kbps_to_mbps(throughput[1]))
        return result
    
    def UNIXtime_to_datetime(self, timelist):
        result = []
        for time in timelist:
            result.append(time[0].strftime("%H:%M:%S"))
        return result

    def throughputs_analyze(self):
        x_locator = 40
        dl_lte, dl_nr, ul_lte, ul_nr = self.read_throughputs(self.raw_data_input.get(1.0,END))

        plt.subplot(2,1,1)
        if len(dl_lte) > 0:
            dl_lte_line = plt.plot(self.UNIXtime_to_datetime(dl_lte),self.kbpslist_to_mbpslist(dl_lte),label='DL 4G PHY', color='orange', linestyle='-')
        if len(dl_nr) > 0:
            dl_nr_line  = plt.plot(self.UNIXtime_to_datetime(dl_nr),self.kbpslist_to_mbpslist(dl_nr),label='DL 5G PHY', color='red', linestyle='-')
        plt.legend()    # 添加图例
        dl_ax = plt.gca()
        if len(dl_nr) > len(dl_lte):
            dl_ax.xaxis.set_major_locator(MultipleLocator(int(len(dl_nr)/x_locator)))
        else:
            dl_ax.xaxis.set_major_locator(MultipleLocator(int(len(dl_lte)/x_locator)))

        plt.xticks(rotation = 45)
        plt.title('DL Throughput')
        plt.xlabel('Time (hh:mm:ss)')
        plt.ylabel('Throughput (Mbps)')
        # 启用默认网格
        plt.grid(True)
        # 自定义网格样式
        plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        plt.subplot(2,1,2)
        if len(ul_nr) > 0:
            ul_lte_line = plt.plot(self.UNIXtime_to_datetime(ul_lte),self.kbpslist_to_mbpslist(ul_lte),label='UL 4G PHY', color='green', linestyle='-')
        if len(ul_nr) > 0:
            ul_nr_line  = plt.plot(self.UNIXtime_to_datetime(ul_nr),self.kbpslist_to_mbpslist(ul_nr),label='UL 5G PHY', color='blue', linestyle='-')
        plt.legend()    # 添加图例
        ul_ax = plt.gca()
        if len(ul_nr) > len(ul_lte):
            ul_ax.xaxis.set_major_locator(MultipleLocator(int(len(ul_nr)/x_locator)))
        else:
            ul_ax.xaxis.set_major_locator(MultipleLocator(int(len(ul_lte)/x_locator)))
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
            'wait_time': self.wait_time_entry.get(),
            'log_name': self.log_name_entry.get(),
            'SMS_number': self.SMS_number_entry.get(),
            'SMS_content': self.SMS_content_entry.get(),
            'default_LTE_Band': self.config.get('Settings', 'default_LTE_Band'),
            'default_NSAorSA_Band': self.config.get('Settings', 'default_NSAorSA_Band'),
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
        self.main_window.destroy()

    def show_message(self):
        messagebox.showinfo("提示", "测试工具已连续使用很久了yo\n\n注意休息\n\nby ThunderSoft29749")
        self.main_window.after(TIMER, self.show_message)

    def on_f1(self, event): 
        self.is_off_airplane_mode.set(not self.is_off_airplane_mode.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.disable_airplane_mode)
            self.disable_airplane_mode()
        
    def on_f2(self, event): 
        self.is_make_call.set(not self.is_make_call.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.make_call)
            self.make_call()

    def on_f3(self, event): 
        self.is_pickup_call.set(not self.is_pickup_call.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.pickup_call)
            self.pickup_call()

    def on_f4(self, event): 
        self.is_fast_test.set(not self.is_fast_test.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.fast_test)
            self.in_run(self.fast_test)

    def on_f5(self, event): 
        self.is_terminate_call.set(not self.is_terminate_call.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.terminate_call)
            self.terminate_call()

    def on_f6(self, event): 
        self.is_on_airplane_mode.set(not self.is_on_airplane_mode.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.enable_airplane_mode)
            self.enable_airplane_mode()

    def on_f7(self, event): 
        self.is_save_log.set(not self.is_save_log.get())
        if not self.is_auto.get():
            # self.new_thread_to_do(self.save_log)
            self.save_log()

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
    multipleTest = MultipleTest(init_window)
    multipleTest.set_init_window()
    init_window.mainloop()

start()