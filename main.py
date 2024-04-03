import select
from unittest import case
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.config import Config
from kivy.core.window import Window
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.filemanager import MDFileManager
from kivymd.app import MDApp
from kivymd.toast import toast
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from pymodbus.client import ModbusTcpClient
from pymodbus.client import AsyncModbusTcpClient
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
import os

modbus_client = ModbusTcpClient('192.168.1.111')

plt.style.use('bmh')

colors = {
    "Red": {
        "A200": "#EE2222",
        "A500": "#EE2222",
        "A700": "#EE2222",
    },

    "Gray": {
        "200": "#999999",
        "500": "#999999",
        "700": "#999999",
    },

    "Blue": {
        "200": "#196BA5",
        "500": "#196BA5",
        "700": "#196BA5",
    },

    "Light": {
        "StatusBar": "E0E0E0",
        "AppBar": "#202020",
        "Background": "#EEEEEE",
        "CardsDialogs": "#FFFFFF",
        "FlatButtonDown": "#CCCCCC",
    },

    "Dark": {
        "StatusBar": "101010",
        "AppBar": "#E0E0E0",
        "Background": "#111111",
        "CardsDialogs": "#000000",
        "FlatButtonDown": "#333333",
    },
}

val_pipe_length = 6000.0
val_pipe_diameter = 60.3
val_pipe_thickness = 3.0

val_machine_eff_length = 200.
val_machine_supp_pos = 200.
val_machine_clamp_front_delay = 5.
val_machine_clamp_rear_delay = 5.
val_machine_press_front_delay = 5.
val_machine_press_rear_delay = 5.
val_machine_collet_clamp_delay = 5.
val_machine_collet_open_delay = 5.
val_machine_die_radius = 100.0

val_advanced_pipe_head = 200.
val_advanced_start_mode = 0
val_advanced_first_line = 0
val_advanced_finish_job = 0
val_advanced_receive_pos_x = 0.
val_advanced_receive_pos_b = 1000.
val_advanced_prod_qty = 0
val_advanced_press_semiclamp_time = 5.
val_advanced_press_semiopen_time = 5.
val_advanced_clamp_semiclamp_time = 5.
val_advanced_springback_20 = 5.
val_advanced_springback_120 = 5.
val_advanced_max_bend = 180.
val_advanced_press_start_angle = 0.
val_advanced_press_stop_angle = 180.

val_feed_present = 0.
val_bend_preset = 0.
val_turn_preset = 0.
val_feed_set = 0.
val_bend_set = 0.
val_turn_set = 0.

val_feed_step = np.zeros(10)
val_bend_step = np.zeros(10)
val_turn_step = np.zeros(10)
data_base_process = np.zeros([3, 10])

flag_conn_stat = False
flag_mode = False
flag_run = False
flag_alarm = False
flag_reset = False

flag_cylinder_press = False
flag_cylinder_clamp = False
flag_cylinder_table_up = False
flag_cylinder_table_shift = False

flag_jog_enable = False
flag_jog_req_feed = False
flag_jog_req_bend = False
flag_jog_req_turn = False
flag_operate_req_feed = False
flag_operate_req_bend = False
flag_operate_req_turn = False

flag_origin_req = False

view_camera = np.array([45, 0, 0])

class ScreenSplash(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    screen_main_menu = ObjectProperty(None)
    app_window = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(ScreenSplash, self).__init__(**kwargs)
        Clock.schedule_interval(self.update_progress_bar, .01)

    def update_progress_bar(self, *args):
        if (self.ids.progress_bar.value + 1) < 100:
            raw_value = self.ids.progress_bar_label.text.split('[')[-1]
            value = raw_value[:-2]
            value = eval(value.strip())
            new_value = value + 1
            self.ids.progress_bar.value = new_value
            self.ids.progress_bar_label.text = 'Loading.. [{:} %]'.format(new_value)
        else:
            self.ids.progress_bar.value = 100
            self.ids.progress_bar_label.text = 'Loading.. [{:} %]'.format(100)
            time.sleep(0.5)
            Clock.unschedule(self.update_progress_bar)
            self.screen_manager.current = 'screen_main_menu'
            return False
        
class ScreenMainMenu(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(ScreenMainMenu, self).__init__(**kwargs)
        self.scrOpManual = ScreenOperateManual()
        Clock.schedule_once(self.delayed_init, 5)
        
    def delayed_init(self, dt):
        Clock.schedule_interval(self.regular_comm_slave, 10)

    def regular_comm_slave(self, dt):
        modbus_client = AsyncModbusTcpClient
        global flag_conn_stat

        try: 
            modbus_client.connect()
            flag_conn_stat = modbus_client.connected
            modbus_client.close()
        except:
            toast("error communication to PLC Slave")
        
        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"
        

        # try:
        #     modbus_client.connect()
        #     modbus_client.write_coils(1536, [True, True, True, True, True, True, True, True], slave=1)

        #     modbus_client.write_coils(1536, [False, False, False, False, True, True, True, True], slave=1)

        #     modbus_client.write_coils(1536, [False, False, False, False, False, False, False, False], slave=1)

        #     reading_coil = modbus_client.read_coils(1536, 8, slave=1)
        #     print(reading_coil.bits)
        #     modbus_client.close()
        # except:
        #     toast("error communication to PLC Slave")
        

    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h now")


class ScreenPipeSetting(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    global modbus_client

    def __init__(self, **kwargs):
        super(ScreenPipeSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        self.ids.input_pipe_length.text = str(val_pipe_length)
        self.ids.input_pipe_diameter.text = str(val_pipe_diameter)
        self.ids.input_pipe_thickness.text = str(val_pipe_thickness)

        self.update_graph()
        Clock.schedule_interval(self.regular_comm_slave, 1)

    def regular_comm_slave(self, dt):
        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"

    def update(self):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        val_pipe_length = float(self.ids.input_pipe_length.text)
        val_pipe_diameter = float(self.ids.input_pipe_diameter.text)
        val_pipe_thickness = float(self.ids.input_pipe_thickness.text)

        self.update_graph()

    def update_view(self, direction):
        global view_camera

        elev, azim, roll = view_camera
        
        if(direction == 0):
            print(elev)
            elev += 20

        if(direction == 1):
            print(elev)
            elev -= 20
        
        if(direction == 2):
            azim += 20
        
        if(direction == 3):
            azim -= 20
        
        view_camera = np.array([elev, azim, roll])        
        self.update_graph(elev, azim, roll)

    def update_graph(self, elev=45, azim=60, roll=0):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness
        global view_camera

        view_camera = elev, azim, roll

        try:
            self.ids.pipe_illustration.clear_widgets()
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")

            val_pipe_length = float(self.ids.input_pipe_length.text)
            val_pipe_diameter = float(self.ids.input_pipe_diameter.text)
            val_pipe_thickness = float(self.ids.input_pipe_thickness.text)

            Xr, Yr, Zr = self.simulate(val_pipe_length, val_pipe_diameter, val_pipe_thickness)

            self.ax.plot_surface(Xr, Yr, Zr, color='gray')
            self.ax.set_box_aspect(aspect=(1, 1, 1))
            self.ax.view_init(elev=view_camera[0], azim=view_camera[1], roll=view_camera[2])

            self.ids.pipe_illustration.add_widget(FigureCanvasKivyAgg(self.fig))
        except:
            toast("error update pipe illustration")

    def simulate(self, val_pipe_length, val_pipe_diameter, val_pipe_thickness):
        Uc = np.linspace(0, 2 * np.pi, 50)
        Xc = np.linspace(0, val_pipe_length, 2)

        Uc_inner = np.linspace(0, 2 * np.pi, 50)
        Xc_inner = np.linspace(0, val_pipe_length, 2)

        Uc, Xc = np.meshgrid(Uc, Xc)
        Uc_inner, Xc_inner = np.meshgrid(Uc_inner, Xc_inner)
        
        pipe_radius = val_pipe_diameter / 2
        pipe_radius_inner = (val_pipe_diameter / 2) - val_pipe_thickness

        Yc = pipe_radius * np.cos(Uc)
        Zc = pipe_radius * np.sin(Uc)

        Yc_inner = pipe_radius_inner * np.cos(Uc_inner)
        Zc_inner = pipe_radius_inner * np.sin(Uc_inner)

        Xr = np.append(Xc, Xc_inner, axis=0)
        Yr = np.append(Yc, Yc_inner, axis=0)
        Zr = np.append(Zc, Zc_inner, axis=0)

        Xr = np.append(Xr, Xc, axis=0)
        Yr = np.append(Yr, Yc, axis=0)
        Zr = np.append(Zr, Zc, axis=0)

        return Xr, Yr, Zr

    def menu_callback(self, text_item):
        print(text_item)

    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h 1")

class ScreenMachineSetting(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    global modbus_client

    def __init__(self, **kwargs):
        super(ScreenMachineSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global val_machine_eff_length
        global val_machine_supp_pos
        global val_machine_clamp_front_delay
        global val_machine_clamp_rear_delay
        global val_machine_press_front_delay
        global val_machine_press_rear_delay
        global val_machine_collet_clamp_delay
        global val_machine_collet_open_delay
        global val_machine_die_radius

        self.ids.input_machine_eff_length.text = str(val_machine_eff_length)
        self.ids.input_machine_supp_pos.text = str(val_machine_supp_pos)
        self.ids.input_machine_clamp_front_delay.text = str(val_machine_clamp_front_delay)
        self.ids.input_machine_clamp_rear_delay.text = str(val_machine_clamp_rear_delay)
        self.ids.input_machine_press_front_delay.text = str(val_machine_press_front_delay)
        self.ids.input_machine_press_rear_delay.text = str(val_machine_press_rear_delay)
        self.ids.input_machine_collet_clamp_delay.text = str(val_machine_collet_clamp_delay)
        self.ids.input_machine_collet_open_delay.text = str(val_machine_collet_open_delay)
        self.ids.input_machine_die_radius.text = str(val_machine_die_radius)

        Clock.schedule_interval(self.regular_comm_slave, 1)

    def regular_comm_slave(self, dt):
        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"

    async def update(self):
        global val_machine_eff_length
        global val_machine_supp_pos
        global val_machine_clamp_front_delay
        global val_machine_clamp_rear_delay
        global val_machine_press_front_delay
        global val_machine_press_rear_delay
        global val_machine_collet_clamp_delay
        global val_machine_collet_open_delay
        global val_machine_die_radius

        val_machine_eff_length = float(self.ids.input_machine_eff_length.text)
        val_machine_supp_pos = float(self.ids.input_machine_supp_pos.text)
        val_machine_clamp_front_delay = float(self.ids.input_machine_clamp_front_delay.text)
        val_machine_clamp_rear_delay = float(self.ids.input_machine_clamp_rear_delay.text)
        val_machine_press_front_delay = float(self.ids.input_machine_press_front_delay.text)
        val_machine_press_rear_delay = float(self.ids.input_machine_press_rear_delay.text)
        val_machine_collet_clamp_delay = float(self.ids.input_machine_collet_clamp_delay.text)
        val_machine_collet_open_delay = float(self.ids.input_machine_collet_open_delay.text)
        val_machine_die_radius = float(self.ids.input_machine_die_radius.text)

        try:
            await modbus_client.connect()

            if flag_conn_stat:
                modbus_client.write_register(2512, int(val_machine_eff_length), slave=1) #V2000
                modbus_client.write_register(2513, int(val_machine_supp_pos), slave=1) #V2001
                modbus_client.write_register(2514, int(val_machine_clamp_front_delay), slave=1) #V2002
                modbus_client.write_register(2515, int(val_machine_clamp_rear_delay), slave=1) #V2003
                modbus_client.write_register(2516, int(val_machine_press_front_delay), slave=1) #V2004
                modbus_client.write_register(2517, int(val_machine_press_rear_delay), slave=1) #V2005
                modbus_client.write_register(2518, int(val_machine_collet_clamp_delay), slave=1) #V2006
                modbus_client.write_register(2519, int(val_machine_collet_open_delay), slave=1) #V2007
                modbus_client.write_register(2520, int(val_machine_die_radius), slave=1) #V2008
            else:
                toast("PLC Slave is not connected")  

            modbus_client.close()
        except:
            toast("error send machine_setting data to PLC Slave")    

    def update_image(self, image_num):
        if image_num == 0:
            self.ids.machine_image.source = 'asset/machine_setting_eff_length.png'
        elif image_num == 1:
            self.ids.machine_image.source = 'asset/machine_setting_supp_pos.png'
        elif image_num == 2:
            self.ids.machine_image.source = 'asset/machine_setting_clamp_front_delay.png'
        elif image_num == 3:
            self.ids.machine_image.source = 'asset/machine_setting_clamp_rear_delay.png'
        elif image_num == 4:
            self.ids.machine_image.source = 'asset/machine_setting_press_front_delay.png'
        elif image_num == 5:
            self.ids.machine_image.source = 'asset/machine_setting_press_rear_delay.png'
        elif image_num == 6:
            self.ids.machine_image.source = 'asset/machine_setting_collet_clamp_delay.png'
        elif image_num == 7:
            self.ids.machine_image.source = 'asset/machine_setting_collet_open_delay.png'
        
    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h 1")

class ScreenAdvancedSetting(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    global modbus_client

    def __init__(self, **kwargs):
        super(ScreenAdvancedSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global val_advanced_pipe_head
        global val_advanced_start_mode
        global val_advanced_first_line
        global val_advanced_finish_job
        global val_advanced_receive_pos_x
        global val_advanced_receive_pos_b
        global val_advanced_prod_qty
        global val_advanced_press_semiclamp_time
        global val_advanced_press_semiopen_time
        global val_advanced_clamp_semiclamp_time
        global val_advanced_springback_20
        global val_advanced_springback_120
        global val_advanced_max_bend
        global val_advanced_press_start_angle
        global val_advanced_press_stop_angle

        self.ids.input_advanced_pipe_head.text = str(val_advanced_pipe_head)
        self.ids.input_advanced_start_mode.text = str(val_advanced_start_mode)
        self.ids.input_advanced_first_line.text = str(val_advanced_first_line)
        self.ids.input_advanced_finish_job.text = str(val_advanced_finish_job)
        self.ids.input_advanced_receive_pos_x.text = str(val_advanced_receive_pos_x)
        self.ids.input_advanced_receive_pos_b.text = str(val_advanced_receive_pos_b)
        self.ids.input_advanced_prod_qty.text = str(val_advanced_prod_qty)
        self.ids.input_advanced_press_semiclamp_time.text = str(val_advanced_press_semiclamp_time)
        self.ids.input_advanced_press_semiopen_time.text = str(val_advanced_press_semiopen_time)
        self.ids.input_advanced_clamp_semiclamp_time.text = str(val_advanced_clamp_semiclamp_time)
        self.ids.input_advanced_springback_20.text = str(val_advanced_springback_20)
        self.ids.input_advanced_springback_120.text = str(val_advanced_springback_120)
        self.ids.input_advanced_max_bend.text = str(val_advanced_max_bend)
        self.ids.input_advanced_press_start_angle.text = str(val_advanced_press_start_angle)
        self.ids.input_advanced_press_stop_angle.text = str(val_advanced_press_stop_angle)

        Clock.schedule_interval(self.regular_comm_slave, 1)

    def regular_comm_slave(self, dt):
        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"
            
    async def update(self):
        global val_advanced_pipe_head
        global val_advanced_start_mode
        global val_advanced_first_line
        global val_advanced_finish_job
        global val_advanced_receive_pos_x
        global val_advanced_receive_pos_b
        global val_advanced_prod_qty
        global val_advanced_press_semiclamp_time
        global val_advanced_press_semiopen_time
        global val_advanced_clamp_semiclamp_time
        global val_advanced_springback_20
        global val_advanced_springback_120
        global val_advanced_max_bend
        global val_advanced_press_start_angle
        global val_advanced_press_stop_angle

        val_advanced_pipe_head = float(self.ids.input_advanced_pipe_head.text)
        val_advanced_start_mode = int(self.ids.input_advanced_start_mode.text)
        val_advanced_first_line = int(self.ids.input_advanced_first_line.text)
        val_advanced_finish_job = int(self.ids.input_advanced_finish_job.text)
        val_advanced_receive_pos_x = float(self.ids.input_advanced_receive_pos_x.text)
        val_advanced_receive_pos_b = float(self.ids.input_advanced_receive_pos_b.text)
        val_advanced_prod_qty = int(self.ids.input_advanced_prod_qty.text)
        val_advanced_press_semiclamp_time = float(self.ids.input_advanced_press_semiclamp_time.text)
        val_advanced_press_semiopen_time = float(self.ids.input_advanced_press_semiopen_time.text)
        val_advanced_clamp_semiclamp_time = float(self.ids.input_advanced_clamp_semiclamp_time.text)
        val_advanced_springback_20 = float(self.ids.input_advanced_springback_20.text)
        val_advanced_springback_120 = float(self.ids.input_advanced_springback_120.text)
        val_advanced_max_bend = float(self.ids.input_advanced_max_bend.text)
        val_advanced_press_start_angle = float(self.ids.input_advanced_press_start_angle.text)
        val_advanced_press_stop_angle = float(self.ids.input_advanced_press_stop_angle.text)

        try:
            await modbus_client.connect()

            if flag_conn_stat:
                modbus_client.write_register(2522, int(val_advanced_pipe_head), slave=1) #V2010
                modbus_client.write_register(2523, val_advanced_start_mode, slave=1) #V2011
                modbus_client.write_register(2524, val_advanced_first_line, slave=1) #V2012
                modbus_client.write_register(2525, val_advanced_finish_job, slave=1) #V2013
                modbus_client.write_register(2526, int(val_advanced_receive_pos_x), slave=1) #V2014
                modbus_client.write_register(2527, int(val_advanced_receive_pos_b), slave=1) #V2015
                modbus_client.write_register(2528, val_advanced_prod_qty, slave=1) #V2016
                modbus_client.write_register(2529, int(val_advanced_press_semiclamp_time), slave=1) #V2017
                modbus_client.write_register(2530, int(val_advanced_press_semiopen_time), slave=1) #V2018
                modbus_client.write_register(2531, int(val_advanced_clamp_semiclamp_time), slave=1) #V2019
                modbus_client.write_register(2532, int(val_advanced_springback_20), slave=1) #V2020
                modbus_client.write_register(2533, int(val_advanced_springback_120), slave=1) #V2021
                modbus_client.write_register(2534, int(val_advanced_max_bend), slave=1) #V2022
                modbus_client.write_register(2535, int(val_advanced_press_start_angle), slave=1) #V2023
                modbus_client.write_register(2536, int(val_advanced_press_stop_angle), slave=1) #V2024
            else:
                toast("PLC Slave is not connected")  

            modbus_client.close()
        except:
            toast("error send machine_setting data to PLC Slave") 

    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h 1")

class ScreenOperateManual(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    global modbus_client

    def __init__(self, **kwargs):      
        super(ScreenOperateManual, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        Clock.schedule_interval(self.regular_comm_slave, 1)

    def regular_comm_slave(self, dt):
        global flag_mode
        flag_mode = False

        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"

    def exec_press(self):
        global flag_cylinder_press

        if flag_cylinder_press:
            flag_cylinder_press = False
            self.ids.bt_press.md_bg_color = "#196BA5"
        else:
            flag_cylinder_press = True
            self.ids.bt_press.md_bg_color = "#ee2222"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3082, flag_cylinder_press, slave=1) #M10
            modbus_client.close()
        except:
            toast("error send flag_cylinder_press data to PLC Slave") 

    def exec_clamp(self):
        global flag_cylinder_clamp

        if flag_cylinder_clamp:
            flag_cylinder_clamp = False
            self.ids.bt_clamp.md_bg_color = "#196BA5"
        else:
            flag_cylinder_clamp = True
            self.ids.bt_clamp.md_bg_color = "#ee2222"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3083, flag_cylinder_clamp, slave=1) #M11
            modbus_client.close()
        except:
            toast("error send flag_cylinder_clamp data to PLC Slave") 

    def exec_table_up(self):
        global flag_cylinder_table_up

        if flag_cylinder_table_up:
            flag_cylinder_table_up = False
            self.ids.bt_table_up.md_bg_color = "#196BA5"
        else:
            flag_cylinder_table_up = True
            self.ids.bt_table_up.md_bg_color = "#ee2222"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3084, flag_cylinder_table_up, slave=1) #M12
            modbus_client.close()
        except:
            toast("error send flag_cylinder_table_up data to PLC Slave") 

    def exec_table_shift(self):
        global flag_cylinder_table_shift

        if flag_cylinder_table_shift:
            flag_cylinder_table_shift = False
            self.ids.bt_table_shift.md_bg_color = "#196BA5"
        else:
            flag_cylinder_table_shift = True
            self.ids.bt_table_shift.md_bg_color = "#ee2222"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3085, flag_cylinder_table_shift, slave=1) #M13
            modbus_client.close()
        except:
            toast("error send flag_cylinder_table_shift data to PLC Slave") 

    def exec_jog_enable(self):
        global flag_jog_enable

        if flag_jog_enable:
            flag_jog_enable = False
            self.ids.bt_jog_enable.md_bg_color = "#196BA5"
        else:
            flag_jog_enable = True
            self.ids.bt_jog_enable.md_bg_color = "#ee2222"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3092, flag_jog_enable, slave=1) #M20
            modbus_client.close()
        except:
            toast("error send flag_jog_enable data to PLC Slave")  

    def stop_jog(self):
        try:
            modbus_client.connect()
            modbus_client.write_coils(3093, [False, False, False, False, False, False], slave=1) #M21 - M26
            modbus_client.close()
        except:
            toast("error send stop_jog data to PLC Slave")  

    def exec_jog_feed_p(self):
        global flag_jog_req_feed
        flag_jog_req_feed = True
        self.ids.bt_jog_feed_p.md_bg_color = "#ee2222"
        try:
            modbus_client.connect()
            modbus_client.write_coil(3093, True, slave=1) #M21
            modbus_client.close()
        except:
            toast("error send exec_jog_feed_p data to PLC Slave")  

    def exec_jog_feed_n(self):
        global flag_jog_req_feed
        flag_jog_req_feed = True
        self.ids.bt_jog_feed_n.md_bg_color = "#ee2222"
        try:
            modbus_client.connect()
            modbus_client.write_coil(3094, True, slave=1) #M22
            modbus_client.close()
        except:
            toast("error send exec_jog_feed_n data to PLC Slave")     

    def stop_jog_feed(self):
        global flag_jog_req_feed
        flag_jog_req_feed = False
        self.ids.bt_jog_feed_p.md_bg_color = "#196BA5"
        self.ids.bt_jog_feed_n.md_bg_color = "#196BA5"
        self.stop_jog()

    def exec_jog_bend_p(self):
        global flag_jog_req_bend
        flag_jog_req_bend = True
        self.ids.bt_jog_bend_p.md_bg_color = "#ee2222"
        try:
            modbus_client.connect()
            modbus_client.write_coil(3095, True, slave=1) #M23
            modbus_client.close()
        except:
            toast("error send exec_jog_bend_p data to PLC Slave")  

    def exec_jog_bend_n(self):
        global flag_jog_req_bend
        flag_jog_req_bend = True
        self.ids.bt_jog_bend_n.md_bg_color = "#ee2222"
        try:
            modbus_client.connect()
            modbus_client.write_coil(3096, True, slave=1) #M24
            modbus_client.close()
        except:
            toast("error send exec_jog_bend_n data to PLC Slave")  

    def stop_jog_bend(self):
        global flag_jog_req_bend
        flag_jog_req_bend = False
        self.ids.bt_jog_bend_p.md_bg_color = "#196BA5"
        self.ids.bt_jog_bend_n.md_bg_color = "#196BA5"
        self.stop_jog()

    def exec_jog_turn_p(self):
        global flag_jog_req_turn
        flag_jog_req_turn = True
        self.ids.bt_jog_turn_p.md_bg_color = "#ee2222"
        try:
            modbus_client.connect()
            modbus_client.write_coil(3097, True, slave=1) #M25
            modbus_client.close()
        except:
            toast("error send exec_jog_turn_p data to PLC Slave")  

    def exec_jog_turn_n(self):
        global flag_jog_req_turn
        flag_jog_req_turn = True
        self.ids.bt_jog_turn_n.md_bg_color = "#ee2222"
        try:
            modbus_client.connect()
            modbus_client.write_coil(3098, True, slave=1) #M26
            modbus_client.close()
        except:
            toast("error send exec_jog_turn_n data to PLC Slave")  

    def stop_jog_turn(self):
        global flag_jog_req_turn
        flag_jog_req_turn = False
        self.ids.bt_jog_turn_p.md_bg_color = "#196BA5"
        self.ids.bt_jog_turn_n.md_bg_color = "#196BA5"
        self.stop_jog()

    def exec_operate_feed(self):
        global flag_operate_req_feed
        global val_feed_set

        flag_operate_req_feed = True
        self.ids.bt_operate_feed.md_bg_color = "#ee2222"
        val_feed_set = float(self.ids.input_operate_feed.text)

        try:
            modbus_client.connect()
            modbus_client.write_coil(3099, flag_operate_req_feed, slave=1) #M27
            modbus_client.write_register(3513, int(val_feed_set), slave=1) #V3001
            msg = f'send data {val_feed_set}'
            toast(msg)
            modbus_client.close()
        except:
            toast("error send exec_operate_feed and val_operate_feed data to PLC Slave") 

    def stop_operate_feed(self):
        global flag_operate_req_feed
        flag_operate_req_feed = False
        self.ids.bt_operate_feed.md_bg_color = "#196BA5"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3099, flag_operate_req_feed, slave=1) #M27
            modbus_client.close()
        except:
            toast("error send stop_operate_feed data to PLC Slave") 

    def exec_operate_bend(self):
        global flag_operate_req_bend
        global val_bend_set

        flag_operate_req_bend = True
        self.ids.bt_operate_bend.md_bg_color = "#ee2222"
        val_bend_set = float(self.ids.input_operate_bend.text)

        try:
            modbus_client.connect()
            modbus_client.write_coil(3100, flag_operate_req_bend, slave=1) #M28
            modbus_client.write_register(3543, int(val_bend_set), slave=1) #V3031
            msg = f'send data {val_bend_set}'
            toast(msg)
            modbus_client.close()
        except:
            toast("error send exec_operate_bend and val_operate_bend data to PLC Slave") 

    def stop_operate_bend(self):
        global flag_operate_req_bend
        flag_operate_req_bend = False
        self.ids.bt_operate_bend.md_bg_color = "#196BA5"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3100, flag_operate_req_bend, slave=1) #M28
            modbus_client.close()
        except:
            toast("error send stop_operate_bend data to PLC Slave") 

    def exec_operate_turn(self):
        global flag_operate_req_turn
        global val_turn_set

        flag_operate_req_turn = True
        self.ids.bt_operate_turn.md_bg_color = "#ee2222"
        val_turn_set = float(self.ids.input_operate_turn.text)

        try:
            modbus_client.connect()
            modbus_client.write_coil(3101, flag_operate_req_bend, slave=1) #M29
            modbus_client.write_register(3573, int(val_turn_set), slave=1) #V3061
            msg = f'send data {val_turn_set}'
            toast(msg)
            modbus_client.close()
        except:
            toast("error send exec_operate_turn and val_operate_turn data to PLC Slave")

    def stop_operate_turn(self):
        global flag_operate_req_turn
        flag_operate_req_turn = False
        self.ids.bt_operate_turn.md_bg_color = "#196BA5"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3101, flag_operate_req_bend, slave=1) #M29
            modbus_client.close()
        except:
            toast("error send stop_operate_turn data to PLC Slave")

    def exec_origin(self):
        global flag_origin_req
        flag_origin_req = True
        self.ids.bt_origin.md_bg_color = "#ee2222"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3102, flag_origin_req, slave=1) #M30
            modbus_client.close()
        except:
            toast("error send flag_origin_req data to PLC Slave")

    def stop_origin(self):
        global flag_origin_req
        flag_origin_req = False
        self.ids.bt_origin.md_bg_color = "#196BA5"

        try:
            modbus_client.connect()
            modbus_client.write_coil(3102, flag_origin_req, slave=1) #M30
            modbus_client.close()
        except:
            toast("error send flag_origin_req data to PLC Slave")

    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_manual(self):
        self.screen_manager.current = 'screen_operate_manual'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h 1")

class ScreenOperateAuto(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    global modbus_client

    def __init__(self, **kwargs):       
        super(ScreenOperateAuto, self).__init__(**kwargs)
        self.file_manager = MDFileManager(exit_manager=self.exit_manager, select_path=self.select_path)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        Clock.schedule_interval(self.regular_comm_slave, 1)

    def regular_comm_slave(self, dt):
        global flag_mode
        flag_mode = True

        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"

    def update_view(self, direction):
        global view_camera

        elev, azim, roll = view_camera
        
        if(direction == 0):
            print(elev)
            elev += 20

        if(direction == 1):
            print(elev)
            elev -= 20
        
        if(direction == 2):
            azim += 20
        
        if(direction == 3):
            azim -= 20
        
        view_camera = np.array([elev, azim, roll])        
        self.update_graph(elev, azim, roll)

    def reload(self):
        global data_base_process
        print(data_base_process)
        self.update_graph()

    def file_manager_open(self):
        self.file_manager.show(os.path.expanduser(os.getcwd() + "\data"))  # output manager to the screen
        self.manager_open = True

    def select_path(self, path: str):
        try:
            self.exit_manager(path)
        except:
            toast("error select file path")

    def exit_manager(self, *args):
        global data_base_process
        '''Called when the user reaches the root of the directory tree.'''
        try:
            data_set = np.loadtxt(*args, delimiter="\t", encoding=None, skiprows=1)
            data_base_process = data_set.T
            self.update_graph()

            self.manager_open = False
            self.file_manager.close()
        except:
            toast("error open file")
        
    def update_graph(self, elev=45, azim=60, roll=0):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        global val_feed_step
        global val_bend_step
        global val_turn_step

        global data_base_process
        view_camera = elev, azim, roll
        try:
            val_feed_step = data_base_process[0,:]
            val_bend_step = data_base_process[1,:] 
            val_turn_step = data_base_process[2,:] 

            self.ids.pipe_bended_illustration.clear_widgets()

            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            # self.fig.tight_layout()

            offset_length = val_feed_step
            bend_angle = val_bend_step / 180 * np.pi
            turn_angle = val_turn_step / 180 * np.pi
            pipe_radius = val_pipe_diameter / 2

            Uo = np.linspace(0, 2 * np.pi, 30)
            Yo = np.linspace(0, 0, 5)
            Uo, Yo = np.meshgrid(Uo, Yo)
            Xo = pipe_radius * np.cos(Uo) - val_machine_die_radius
            Zo = pipe_radius * np.sin(Uo)
            
            X0, Y0, Z0 = self.simulate(Xo, Yo, Zo, offset_length[0], bend_angle[0], turn_angle[0])
            X1, Y1, Z1 = self.simulate(X0, Y0, Z0, offset_length[1], bend_angle[1], turn_angle[1])
            X2, Y2, Z2 = self.simulate(X1, Y1, Z1, offset_length[2], bend_angle[2], turn_angle[2])
            X3, Y3, Z3 = self.simulate(X2, Y2, Z2, offset_length[3], bend_angle[3], turn_angle[3])
            X4, Y4, Z4 = self.simulate(X3, Y3, Z3, offset_length[4], bend_angle[4], turn_angle[4])
            X5, Y5, Z5 = self.simulate(X4, Y4, Z4, offset_length[5], bend_angle[5], turn_angle[5])
            X6, Y6, Z6 = self.simulate(X5, Y5, Z5, offset_length[6], bend_angle[6], turn_angle[6])
            X7, Y7, Z7 = self.simulate(X6, Y6, Z6, offset_length[7], bend_angle[7], turn_angle[7])
            X8, Y8, Z8 = self.simulate(X7, Y7, Z7, offset_length[8], bend_angle[8], turn_angle[8])
            X9, Y9, Z9 = self.simulate(X8, Y8, Z8, offset_length[9], bend_angle[9], turn_angle[9])

            self.ax.plot_surface(X9, Y9, Z9, color='gray', alpha=1)
            # self.ax.set_box_aspect(aspect=(1, 1, 1))
            self.ax.set_aspect('equal')
            # self.ax.set_xlim([0, 6000])
            # self.ax.set_ylim([-100, 100])
            # self.ax.set_zlim([-100, 100])
            # self.ax.axis('off')
            self.ax.view_init(elev=view_camera[0], azim=view_camera[1], roll=view_camera[2])
            self.ids.pipe_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))   
        except:
            toast("error update pipe bending process illustration")
   
    def simulate(self, prev_X, prev_Y, prev_Z, offset_length, bend_angle, turn_angle):
        global flag_run
        global val_feed_step
        global val_bend_step
        global val_turn_step

        global val_pipe_diameter
        global val_machine_die_radius

        pipe_radius = val_pipe_diameter / 2
        # step 1 : create straight pipe
        # straight pipe
        Ua = np.linspace(0, 2 * np.pi, 30)
        Ya = np.linspace(offset_length, 0, 5)
        Ua, Ya = np.meshgrid(Ua, Ya)
        Xa = pipe_radius * np.cos(Ua) - val_machine_die_radius
        Za = pipe_radius * np.sin(Ua)
        # combine become one object with previous mesh
        Xa = np.append(prev_X, Xa, axis=0)
        Ya = np.append(prev_Y + offset_length, Ya, axis=0)
        Za = np.append(prev_Z, Za, axis=0)

        # step 2 : create bended pipe
        # theta: poloidal angle; phi: toroidal angle 
        theta = np.linspace(0, 2 * np.pi, 30) 
        phi   = np.linspace(0, bend_angle, 30) 
        theta, phi = np.meshgrid(theta, phi) 
        # torus parametrization 
        Xb = (val_machine_die_radius + pipe_radius * np.cos(theta)) * -np.cos(phi)
        Yb = (val_machine_die_radius + pipe_radius * np.cos(theta)) * -np.sin(phi)
        Zb = pipe_radius * np.sin(theta) 

        # step 3 : combine become one object
        Xc = np.append(Xa, Xb, axis=0)
        Yc = np.append(Ya, Yb, axis=0)
        Zc = np.append(Za, Zb, axis=0)

        # step 4 : rotate  object at Z axis (C axis)
        Xd = np.cos(bend_angle) * Xc + np.sin(bend_angle) * Yc
        Yd = -np.sin(bend_angle) * Xc + np.cos(bend_angle) * Yc
        Zd = Zc

        # step 5 : translate to origin, rotate  object at Y axis (B axis), translate back to previous position
        # translate
        Xe = Xd + val_machine_die_radius
        Ze = Zd
        # rotate
        Xf = np.cos(turn_angle) * Xe + -np.sin(turn_angle) * Ze
        Zf = np.sin(turn_angle) * Xe + np.cos(turn_angle) * Ze
        # translate back
        Xf = Xf - val_machine_die_radius
        Yf = Yd

        return Xf, Yf, Zf
    
    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_manual(self):
        self.screen_manager.current = 'screen_operate_manual'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h 1")

class ScreenCompile(MDBoxLayout):
    screen_manager = ObjectProperty(None)
    global modbus_client

    def __init__(self, **kwargs):
        super(ScreenCompile, self).__init__(**kwargs)
        self.file_manager = MDFileManager(exit_manager=self.exit_manager, select_path=self.select_path)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        Clock.schedule_interval(self.regular_comm_slave, 1)

    def regular_comm_slave(self, dt):
        if flag_conn_stat:
            self.ids.comm_status.text = "Status: Connected"
            self.ids.comm_status.color = "#196BA5"
        else:
            self.ids.comm_status.text = "Status: Disconnected"
            self.ids.comm_status.color = "#ee2222"

    def file_manager_open(self):
        self.file_manager.show(os.path.expanduser(os.getcwd() + "\data"))  # output manager to the screen
        self.manager_open = True

    def select_path(self, path: str):
        try:
            path_name = os.path.expanduser(os.getcwd() + "\data\\")
            filename = path.replace(path_name, "")
            self.ids.input_file_name.text = filename
            self.exit_manager(path)
        except:
            toast("error select file path")

    def exit_manager(self, *args):
        global data_base_process
        '''Called when the user reaches the root of the directory tree.'''
        try:
            data_set = np.loadtxt(*args, delimiter="\t", encoding=None, skiprows=1)
            data_base_process = data_set.T
            self.update_data()

            self.manager_open = False
            self.file_manager.close()
        except:
            toast("error open file")

    def update_data(self):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        global val_feed_step
        global val_bend_step
        global val_turn_step
        
        global data_base_process

        val_feed_step = data_base_process[0,:]
        val_bend_step = data_base_process[1,:] 
        val_turn_step = data_base_process[2,:] 
    
        self.ids.input_step_length0.text = str(val_feed_step[0])
        self.ids.input_step_bend0.text = str(val_bend_step[0])
        self.ids.input_step_turn0.text = str(val_turn_step[0])

        self.ids.input_step_length1.text = str(val_feed_step[1])
        self.ids.input_step_bend1.text = str(val_bend_step[1])
        self.ids.input_step_turn1.text = str(val_turn_step[1])

        self.ids.input_step_length2.text = str(val_feed_step[2])
        self.ids.input_step_bend2.text = str(val_bend_step[2])
        self.ids.input_step_turn2.text = str(val_turn_step[2])

        self.ids.input_step_length3.text = str(val_feed_step[3])
        self.ids.input_step_bend3.text = str(val_bend_step[3])
        self.ids.input_step_turn3.text = str(val_turn_step[3])

        self.ids.input_step_length4.text = str(val_feed_step[4])
        self.ids.input_step_bend4.text = str(val_bend_step[4])
        self.ids.input_step_turn4.text = str(val_turn_step[4])

        self.ids.input_step_length5.text = str(val_feed_step[5])
        self.ids.input_step_bend5.text = str(val_bend_step[5])
        self.ids.input_step_turn5.text = str(val_turn_step[5])

        self.ids.input_step_length6.text = str(val_feed_step[6])
        self.ids.input_step_bend6.text = str(val_bend_step[6])
        self.ids.input_step_turn6.text = str(val_turn_step[6])

        self.ids.input_step_length7.text = str(val_feed_step[7])
        self.ids.input_step_bend7.text = str(val_bend_step[7])
        self.ids.input_step_turn7.text = str(val_turn_step[7])

        self.ids.input_step_length8.text = str(val_feed_step[8])
        self.ids.input_step_bend8.text = str(val_bend_step[8])
        self.ids.input_step_turn8.text = str(val_turn_step[8])

        self.ids.input_step_length9.text = str(val_feed_step[9])
        self.ids.input_step_bend9.text = str(val_bend_step[9])
        self.ids.input_step_turn9.text = str(val_turn_step[9]) 

        try:
            modbus_client.connect()
            modbus_client.write_registers(3523, val_feed_step, slave=1) #V3011
            modbus_client.write_registers(3553, val_bend_step, slave=1) #V3041
            modbus_client.write_registers(3583, val_turn_step, slave=1) #V3071
            modbus_client.close()
        except:
            toast("error send setpoint feed, bend, turn data for all steps to PLC Slave") 

        self.update_graph()

    def update_view(self, direction):
        global view_camera

        elev, azim, roll = view_camera
        
        if(direction == 0):
            print(elev)
            elev += 20

        if(direction == 1):
            print(elev)
            elev -= 20
        
        if(direction == 2):
            azim += 20
        
        if(direction == 3):
            azim -= 20
        
        view_camera = np.array([elev, azim, roll])        
        self.update_graph(elev, azim, roll)
        
    def update_graph(self, elev=45, azim=60, roll=0):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        global val_feed_step
        global val_bend_step
        global val_turn_step

        global data_base_process
        global view_camera

        view_camera = elev, azim, roll
        try:
            val_feed_step[0] = float(self.ids.input_step_length0.text)
            val_bend_step[0] = float(self.ids.input_step_bend0.text)
            val_turn_step[0] = float(self.ids.input_step_turn0.text)

            val_feed_step[1] = float(self.ids.input_step_length1.text)
            val_bend_step[1] = float(self.ids.input_step_bend1.text)
            val_turn_step[1] = float(self.ids.input_step_turn1.text)

            val_feed_step[2] = float(self.ids.input_step_length2.text)
            val_bend_step[2] = float(self.ids.input_step_bend2.text)
            val_turn_step[2] = float(self.ids.input_step_turn2.text)

            val_feed_step[3] = float(self.ids.input_step_length3.text)
            val_bend_step[3] = float(self.ids.input_step_bend3.text)
            val_turn_step[3] = float(self.ids.input_step_turn3.text)

            val_feed_step[4] = float(self.ids.input_step_length4.text)
            val_bend_step[4] = float(self.ids.input_step_bend4.text)
            val_turn_step[4] = float(self.ids.input_step_turn4.text)

            val_feed_step[5] = float(self.ids.input_step_length5.text)
            val_bend_step[5] = float(self.ids.input_step_bend5.text)
            val_turn_step[5] = float(self.ids.input_step_turn5.text)

            val_feed_step[6] = float(self.ids.input_step_length6.text)
            val_bend_step[6] = float(self.ids.input_step_bend6.text)
            val_turn_step[6] = float(self.ids.input_step_turn6.text)

            val_feed_step[7] = float(self.ids.input_step_length7.text)
            val_bend_step[7] = float(self.ids.input_step_bend7.text)
            val_turn_step[7] = float(self.ids.input_step_turn7.text)

            val_feed_step[8] = float(self.ids.input_step_length8.text)
            val_bend_step[8] = float(self.ids.input_step_bend8.text)
            val_turn_step[8] = float(self.ids.input_step_turn8.text)

            val_feed_step[9] = float(self.ids.input_step_length9.text)
            val_bend_step[9] = float(self.ids.input_step_bend9.text)
            val_turn_step[9] = float(self.ids.input_step_turn9.text)

            for i in range(0,9):
                data_base_process[0,i] = val_feed_step[i]
                data_base_process[1,i] = val_bend_step[i]
                data_base_process[2,i] = val_turn_step[i]

            val_feed_step = data_base_process[0,:]
            val_bend_step = data_base_process[1,:] 
            val_turn_step = data_base_process[2,:] 

            self.ids.pipe_bended_illustration.clear_widgets()

            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            # self.fig.tight_layout()

            offset_length = val_feed_step
            bend_angle = val_bend_step / 180 * np.pi
            turn_angle = val_turn_step / 180 * np.pi
            pipe_radius = val_pipe_diameter / 2

            Uo = np.linspace(0, 2 * np.pi, 30)
            Yo = np.linspace(0, 0, 5)
            Uo, Yo = np.meshgrid(Uo, Yo)
            Xo = pipe_radius * np.cos(Uo) - val_machine_die_radius
            Zo = pipe_radius * np.sin(Uo)
            
            X0, Y0, Z0 = self.simulate(Xo, Yo, Zo, offset_length[0], bend_angle[0], turn_angle[0])
            X1, Y1, Z1 = self.simulate(X0, Y0, Z0, offset_length[1], bend_angle[1], turn_angle[1])
            X2, Y2, Z2 = self.simulate(X1, Y1, Z1, offset_length[2], bend_angle[2], turn_angle[2])
            X3, Y3, Z3 = self.simulate(X2, Y2, Z2, offset_length[3], bend_angle[3], turn_angle[3])
            X4, Y4, Z4 = self.simulate(X3, Y3, Z3, offset_length[4], bend_angle[4], turn_angle[4])
            X5, Y5, Z5 = self.simulate(X4, Y4, Z4, offset_length[5], bend_angle[5], turn_angle[5])
            X6, Y6, Z6 = self.simulate(X5, Y5, Z5, offset_length[6], bend_angle[6], turn_angle[6])
            X7, Y7, Z7 = self.simulate(X6, Y6, Z6, offset_length[7], bend_angle[7], turn_angle[7])
            X8, Y8, Z8 = self.simulate(X7, Y7, Z7, offset_length[8], bend_angle[8], turn_angle[8])
            X9, Y9, Z9 = self.simulate(X8, Y8, Z8, offset_length[9], bend_angle[9], turn_angle[9])

            self.ax.plot_surface(X9, Y9, Z9, color='gray', alpha=1)
            self.ax.set_aspect('equal')
            self.ax.view_init(elev=view_camera[0], azim=view_camera[1], roll=view_camera[2])
            self.ids.pipe_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))   
        except:
            toast("error update pipe bending process illustration")

    def simulate(self, prev_X, prev_Y, prev_Z, offset_length, bend_angle, turn_angle):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        global val_feed_step
        global val_bend_step
        global val_turn_step
        
        global data_base_process
    
        pipe_radius = val_pipe_diameter / 2
        # step 1 : create straight pipe
        # straight pipe
        Ua = np.linspace(0, 2 * np.pi, 30)
        Ya = np.linspace(offset_length, 0, 5)
        Ua, Ya = np.meshgrid(Ua, Ya)
        Xa = pipe_radius * np.cos(Ua) - val_machine_die_radius
        Za = pipe_radius * np.sin(Ua)
        # combine become one object with previous mesh
        Xa = np.append(prev_X, Xa, axis=0)
        Ya = np.append(prev_Y + offset_length, Ya, axis=0)
        Za = np.append(prev_Z, Za, axis=0)

        # step 2 : create bended pipe
        # theta: poloidal angle; phi: toroidal angle 
        theta = np.linspace(0, 2 * np.pi, 30) 
        phi   = np.linspace(0, bend_angle, 30) 
        theta, phi = np.meshgrid(theta, phi) 
        # torus parametrization 
        Xb = (val_machine_die_radius + pipe_radius * np.cos(theta)) * -np.cos(phi)
        Yb = (val_machine_die_radius + pipe_radius * np.cos(theta)) * -np.sin(phi)
        Zb = pipe_radius * np.sin(theta) 

        # step 3 : combine become one object
        Xc = np.append(Xa, Xb, axis=0)
        Yc = np.append(Ya, Yb, axis=0)
        Zc = np.append(Za, Zb, axis=0)

        # step 4 : rotate  object at Z axis (C axis)
        Xd = np.cos(bend_angle) * Xc + np.sin(bend_angle) * Yc
        Yd = -np.sin(bend_angle) * Xc + np.cos(bend_angle) * Yc
        Zd = Zc

        # step 5 : translate to origin, rotate  object at Y axis (B axis), translate back to previous position
        # translate
        Xe = Xd + val_machine_die_radius
        Ze = Zd
        # rotate
        Xf = np.cos(turn_angle) * Xe + -np.sin(turn_angle) * Ze
        Zf = np.sin(turn_angle) * Xe + np.cos(turn_angle) * Ze
        # translate back
        Xf = Xf - val_machine_die_radius
        Yf = Yd

        return Xf, Yf, Zf

    def reset(self):
        global val_pipe_length
        global val_pipe_diameter
        global val_pipe_thickness

        global val_feed_step
        global val_bend_step
        global val_turn_step
        
        global data_base_process

        val_feed_step = np.zeros(10)
        val_bend_step = np.zeros(10)
        val_turn_step = np.zeros(10)

        data_base_process = np.zeros([3, 10])

        self.ids.input_step_length0.text = str(val_feed_step[0])
        self.ids.input_step_bend0.text = str(val_bend_step[0])
        self.ids.input_step_turn0.text = str(val_turn_step[0])

        self.ids.input_step_length1.text = str(val_feed_step[1])
        self.ids.input_step_bend1.text = str(val_bend_step[1])
        self.ids.input_step_turn1.text = str(val_turn_step[1])

        self.ids.input_step_length2.text = str(val_feed_step[2])
        self.ids.input_step_bend2.text = str(val_bend_step[2])
        self.ids.input_step_turn2.text = str(val_turn_step[2])

        self.ids.input_step_length3.text = str(val_feed_step[3])
        self.ids.input_step_bend3.text = str(val_bend_step[3])
        self.ids.input_step_turn3.text = str(val_turn_step[3])

        self.ids.input_step_length4.text = str(val_feed_step[4])
        self.ids.input_step_bend4.text = str(val_bend_step[4])
        self.ids.input_step_turn4.text = str(val_turn_step[4])

        self.ids.input_step_length5.text = str(val_feed_step[5])
        self.ids.input_step_bend5.text = str(val_bend_step[5])
        self.ids.input_step_turn5.text = str(val_turn_step[5])

        self.ids.input_step_length6.text = str(val_feed_step[6])
        self.ids.input_step_bend6.text = str(val_bend_step[6])
        self.ids.input_step_turn6.text = str(val_turn_step[6])

        self.ids.input_step_length7.text = str(val_feed_step[7])
        self.ids.input_step_bend7.text = str(val_bend_step[7])
        self.ids.input_step_turn7.text = str(val_turn_step[7])

        self.ids.input_step_length8.text = str(val_feed_step[8])
        self.ids.input_step_bend8.text = str(val_bend_step[8])
        self.ids.input_step_turn8.text = str(val_turn_step[8])

        self.ids.input_step_length9.text = str(val_feed_step[9])
        self.ids.input_step_bend9.text = str(val_bend_step[9])
        self.ids.input_step_turn9.text = str(val_turn_step[9]) 

        self.update_graph()

    def save(self):
        try:
            name_file = "\data\\" + self.ids.input_file_name.text + ".gcode"
            name_file_now = datetime.now().strftime("\data\%d_%m_%Y_%H_%M_%S.gcode")
            cwd = os.getcwd()
            if self.ids.input_file_name.text == "":
                disk = cwd + name_file_now
            else:
                disk = cwd + name_file
            print(disk)
            with open(disk,"wb") as f:
                np.savetxt(f, data_base_process.T, fmt="%.3f",delimiter="\t",header="Feed [mm] \t Bend [mm] \t Plane [mm]")
            print("sucessfully save data")
            toast("sucessfully save data")
        except:
            print("error saving data")
            toast("error saving data")
                
    def screen_main_menu(self):
        self.screen_manager.current = 'screen_main_menu'

    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate_auto(self):
        self.screen_manager.current = 'screen_operate_auto'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        # os.system("shutdown -h 1")

class PipeBendingCNCApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Gray"
        self.icon = 'asset/logo.png'
        Window.fullscreen = 'auto'
        Window.borderless = False
        # Window.size = 900, 1440
        # Window.size = 450, 720
        # Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')

        return screen


if __name__ == '__main__':
    PipeBendingCNCApp().run()