from kivy.clock import Clock
from kivy.lang import Builder
from kivy.config import Config
from kivy.logger import Logger
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.app import MDApp
from kivymd.toast import toast
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from pymodbus.client import ModbusTcpClient
from pymodbus.client import AsyncModbusTcpClient
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
import os
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

modbus_client = ModbusTcpClient('192.168.1.111')

val_feed_pv = 0.
val_bend_pv = 0.
val_turn_pv = 0.
val_feed_sv = 0.
val_bend_sv = 0.
val_turn_sv = 0.
val_feed_step = np.zeros(10)
val_bend_step = np.zeros(10)
val_turn_step = np.zeros(10)
data_base_process = np.zeros([3, 10])

conf_feed_speed_pv = 1
conf_bend_speed_pv = 1
conf_turn_speed_pv = 1
conf_bed_pos_pv = 0
conf_feed_speed_sv = 1
conf_bend_speed_sv = 1
conf_turn_speed_sv = 1
conf_bed_pos_sv = 0
conf_feed_speed_step = np.ones(10)
conf_bend_speed_step = np.ones(10)
conf_turn_speed_step = np.ones(10)
conf_bed_pos_step = np.zeros(10)
data_base_config = np.ones([4, 10])

flag_conn_stat = False
flag_mode = False
flag_run = False
flag_alarm = False
flag_reset = False

flag_cylinder_press = False
flag_cylinder_clamp = False
flag_cylinder_chuck = False
flag_cylinder_mandrell = False
flag_cylinder_table_up = False
flag_cylinder_table_shift = False
flag_cylinder_holder_top = False
flag_cylinder_holder_bottom = False

flag_jog_enable = False
flag_jog_req_feed = False
flag_jog_req_bend = False
flag_jog_req_turn = False
flag_operate_req_feed = False
flag_operate_req_bend = False
flag_operate_req_turn = False

flag_origin_req = False

sens_clamp_close = False
sens_bend_reducer = False
sens_bend_origin = False
sens_press_open = False
sens_table_up = False
sens_table_down = False
sens_feed_origin = False
sens_feed_reducer = False
sens_chuck_close = False

flag_seqs_arr = np.zeros(11)
flag_steps_arr = np.zeros(11)

view_camera = np.array([45, 0, 0])

class ScreenSplash(MDScreen):    
    def __init__(self, **kwargs):
        super(ScreenSplash, self).__init__(**kwargs)
        Clock.schedule_interval(self.update_progress_bar, .01)
        Clock.schedule_once(self.delayed_init, 5)
        
    def delayed_init(self, dt):
        Clock.schedule_interval(self.regular_update_connection, 5)
        Clock.schedule_interval(self.regular_display, 1)
        Clock.schedule_interval(self.regular_highspeed_display, 0.5)
        Clock.schedule_interval(self.regular_get_data, 0.5)

    def regular_update_connection(self, dt):
        global flag_conn_stat
        try:
            modbus_client.connect()
            flag_conn_stat = modbus_client.connected
            modbus_client.close()
        except Exception as e:
            toast(e)         

    def regular_get_data(self, dt):
        global flag_conn_stat, flag_mode, flag_run, flag_alarm, flag_reset, flag_jog_enable
        global val_feed_pv, val_bend_pv, val_turn_pv
        global val_feed_sv, val_bend_sv, val_turn_sv
        global conf_feed_speed_pv, conf_turn_speed_pv, conf_bend_speed_pv
        global conf_feed_speed_sv, conf_turn_speed_sv, conf_bend_speed_sv
        global conf_bed_pos_pv, conf_bed_pos_sv
        global sens_clamp_close, sens_bend_reducer, sens_bend_origin
        global sens_press_open, sens_table_up, sens_table_down
        global sens_feed_origin, sens_feed_reducer, sens_chuck_close
        global flag_seqs_arr, flag_steps_arr

        try:
            if flag_conn_stat:
                modbus_client.connect()
                operate_flags = modbus_client.read_coils(3072, 4, slave=1) #M0 - M3
                # flag_mode, flag_run, flag_alarm, flag_reset = flags
                jog_flags = modbus_client.read_coils(3092, 1, slave=1) #M20

                feed_registers = modbus_client.read_holding_registers(3512, 2, slave=1) #V3000 - V3001
                bend_registers = modbus_client.read_holding_registers(3542, 2, slave=1) #V3030 - V3031
                turn_registers = modbus_client.read_holding_registers(3572, 2, slave=1) #V3060 - V3061
                feed_speed_registers = modbus_client.read_holding_registers(3712, 2, slave=1) #V3200 - V3201
                bend_speed_registers = modbus_client.read_holding_registers(3742, 2, slave=1) #V3230 - V3231
                turn_speed_registers = modbus_client.read_holding_registers(3772, 2, slave=1) #V3260 - V3261
                bed_pos_registers = modbus_client.read_coils(3372, 2, slave=1) #M300 - M301

                sens_flags = modbus_client.read_coils(3183, 9, slave=1) #M111 - M119

                seq_init_flags = modbus_client.read_coils(3133, 2, slave=1) #M61 - M62
                seq_flags = modbus_client.read_coils(3143, 9, slave=1) #M71 - M79
                step_flags = modbus_client.read_coils(3272, 11, slave=1) #M200 - M210

                modbus_client.close()

                flag_mode = operate_flags.bits[0]
                flag_run = operate_flags.bits[1]
                flag_alarm = operate_flags.bits[2]
                flag_reset = operate_flags.bits[3]

                flag_jog_enable = jog_flags.bits[0]

                val_feed_pv = int(feed_registers.registers[0]) if (int(feed_registers.registers[0]) <= 32768) else (int(feed_registers.registers[0]) - 65536) 
                val_feed_sv = int(feed_registers.registers[1]) if (int(feed_registers.registers[1]) <= 32768) else (int(feed_registers.registers[1]) - 65536)
                val_bend_pv = int(bend_registers.registers[0]) if (int(bend_registers.registers[0]) <= 32768) else (int(bend_registers.registers[0]) - 65536)
                val_bend_sv = int(bend_registers.registers[1]) if (int(bend_registers.registers[1]) <= 32768) else (int(bend_registers.registers[1]) - 65536)
                val_turn_pv = int(turn_registers.registers[0]) if (int(turn_registers.registers[0]) <= 32768) else (int(turn_registers.registers[0]) - 65536)
                val_turn_sv = int(turn_registers.registers[1]) if (int(turn_registers.registers[1]) <= 32768) else (int(turn_registers.registers[1]) - 65536)

                conf_feed_speed_pv = int(feed_speed_registers.registers[0]) if (int(feed_speed_registers.registers[0]) <= 32768) else (int(feed_speed_registers.registers[0]) - 65536)
                conf_feed_speed_sv = int(feed_speed_registers.registers[1]) if (int(feed_speed_registers.registers[1]) <= 32768) else (int(feed_speed_registers.registers[1]) - 65536)
                conf_bend_speed_pv = int(bend_speed_registers.registers[0]) if (int(bend_speed_registers.registers[0]) <= 32768) else (int(feed_speed_registers.registers[0]) - 65536)
                conf_bend_speed_sv = int(bend_speed_registers.registers[1]) if (int(bend_speed_registers.registers[1]) <= 32768) else (int(feed_speed_registers.registers[1]) - 65536)
                conf_turn_speed_pv = int(turn_speed_registers.registers[0]) if (int(turn_speed_registers.registers[0]) <= 32768) else (int(feed_speed_registers.registers[0]) - 65536)
                conf_turn_speed_sv = int(turn_speed_registers.registers[1]) if (int(turn_speed_registers.registers[1]) <= 32768) else (int(feed_speed_registers.registers[1]) - 65536)
                conf_bed_pos_pv = bed_pos_registers.bits[0]
                conf_bed_pos_sv = bed_pos_registers.bits[1]

                sens_clamp_close = sens_flags.bits[0]
                sens_bend_reducer = sens_flags.bits[1]
                sens_bend_origin = sens_flags.bits[2]
                sens_press_open = sens_flags.bits[3]
                sens_table_up = sens_flags.bits[4]
                sens_table_down = sens_flags.bits[5]
                sens_feed_origin = sens_flags.bits[6]
                sens_feed_reducer = sens_flags.bits[7]
                sens_chuck_close = sens_flags.bits[8]

                flag_seqs_arr[0] = seq_init_flags.bits[0]
                flag_seqs_arr[1] = seq_init_flags.bits[1]

                flag_seqs_arr[2] = seq_flags.bits[0]
                flag_seqs_arr[3] = seq_flags.bits[1]
                flag_seqs_arr[4] = seq_flags.bits[2]
                flag_seqs_arr[5] = seq_flags.bits[3]
                flag_seqs_arr[6] = seq_flags.bits[4]
                flag_seqs_arr[7] = seq_flags.bits[5]
                flag_seqs_arr[8] = seq_flags.bits[6]
                flag_seqs_arr[9] = seq_flags.bits[7]
                flag_seqs_arr[10] = seq_flags.bits[8]

                flag_steps_arr[0] = step_flags.bits[0]
                flag_steps_arr[1] = step_flags.bits[1]
                flag_steps_arr[2] = step_flags.bits[2]
                flag_steps_arr[3] = step_flags.bits[3]
                flag_steps_arr[4] = step_flags.bits[4]
                flag_steps_arr[5] = step_flags.bits[5]
                flag_steps_arr[6] = step_flags.bits[6]
                flag_steps_arr[7] = step_flags.bits[7]
                flag_steps_arr[8] = step_flags.bits[8]
                flag_steps_arr[9] = step_flags.bits[9]
                flag_steps_arr[10] = step_flags.bits[10]
                
        except Exception as e:
            msg = f'{e}'
            toast(msg)  

    def regular_display(self, dt):
        global flag_conn_stat        
        global conf_bed_pos_step

        try:
            screenMainMenu = self.screen_manager.get_screen('screen_main_menu')
            screenPipeSetting = self.screen_manager.get_screen('screen_pipe_setting')
            screenMachineSetting = self.screen_manager.get_screen('screen_machine_setting')
            screenAdvancedSetting = self.screen_manager.get_screen('screen_advanced_setting')
            screenOperateManual = self.screen_manager.get_screen('screen_operate_manual')
            screenOperateAuto = self.screen_manager.get_screen('screen_operate_auto')
            screenCompile = self.screen_manager.get_screen('screen_compile')

            if flag_conn_stat:
                screenMainMenu.ids.comm_status.text = "Status: Connected"
                screenMainMenu.ids.comm_status.color = "#196BA5"
                screenPipeSetting.ids.comm_status.text = "Status: Connected"
                screenPipeSetting.ids.comm_status.color = "#196BA5"
                screenMachineSetting.ids.comm_status.text = "Status: Connected"
                screenMachineSetting.ids.comm_status.color = "#196BA5"                        
                screenAdvancedSetting.ids.comm_status.text = "Status: Connected"
                screenAdvancedSetting.ids.comm_status.color = "#196BA5"  
                screenOperateManual.ids.comm_status.text = "Status: Connected"
                screenOperateManual.ids.comm_status.color = "#196BA5"  
                screenOperateAuto.ids.comm_status.text = "Status: Connected"
                screenOperateAuto.ids.comm_status.color = "#196BA5"  
                screenCompile.ids.comm_status.text = "Status: Connected"
                screenCompile.ids.comm_status.color = "#196BA5"  

            else:
                screenMainMenu.ids.comm_status.text = "Status: Disconnected"
                screenMainMenu.ids.comm_status.color = "#ee2222"
                screenPipeSetting.ids.comm_status.text = "Status: Disconnected"
                screenPipeSetting.ids.comm_status.color = "#ee2222"
                screenMachineSetting.ids.comm_status.text = "Status: Disconnected"
                screenMachineSetting.ids.comm_status.color = "#ee2222"
                screenAdvancedSetting.ids.comm_status.text = "Status: Disconnected"
                screenAdvancedSetting.ids.comm_status.color = "#ee2222"
                screenOperateManual.ids.comm_status.text = "Status: Disconnected"
                screenOperateManual.ids.comm_status.color = "#ee2222"
                screenOperateAuto.ids.comm_status.text = "Status: Disconnected"
                screenOperateAuto.ids.comm_status.color = "#ee2222"
                screenCompile.ids.comm_status.text = "Status: Disconnected"
                screenCompile.ids.comm_status.color = "#ee2222"
                                  
            if conf_bed_pos_step[0] != 1:
                screenCompile.ids.bt_bed_pos0.text = "DN"
                screenCompile.ids.bt_bed_pos0.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos0.text = "UP"
                screenCompile.ids.bt_bed_pos0.md_bg_color = "#ee2222"

            if conf_bed_pos_step[1] != 1:
                screenCompile.ids.bt_bed_pos1.text = "DN"
                screenCompile.ids.bt_bed_pos1.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos1.text = "UP"
                screenCompile.ids.bt_bed_pos1.md_bg_color = "#ee2222"

            if conf_bed_pos_step[2] != 1:
                screenCompile.ids.bt_bed_pos2.text = "DN"
                screenCompile.ids.bt_bed_pos2.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos2.text = "UP"
                screenCompile.ids.bt_bed_pos2.md_bg_color = "#ee2222"

            if conf_bed_pos_step[3] != 1:
                screenCompile.ids.bt_bed_pos3.text = "DN"
                screenCompile.ids.bt_bed_pos3.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos3.text = "UP"
                screenCompile.ids.bt_bed_pos3.md_bg_color = "#ee2222"

            if conf_bed_pos_step[4] != 1:
                screenCompile.ids.bt_bed_pos4.text = "DN"
                screenCompile.ids.bt_bed_pos4.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos4.text = "UP"
                screenCompile.ids.bt_bed_pos4.md_bg_color = "#ee2222"

            if conf_bed_pos_step[5] != 1:
                screenCompile.ids.bt_bed_pos5.text = "DN"
                screenCompile.ids.bt_bed_pos5.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos5.text = "UP"
                screenCompile.ids.bt_bed_pos5.md_bg_color = "#ee2222"

            if conf_bed_pos_step[6] != 1:
                screenCompile.ids.bt_bed_pos6.text = "DN"
                screenCompile.ids.bt_bed_pos6.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos6.text = "UP"
                screenCompile.ids.bt_bed_pos6.md_bg_color = "#ee2222"

            if conf_bed_pos_step[7] != 1:
                screenCompile.ids.bt_bed_pos7.text = "DN"
                screenCompile.ids.bt_bed_pos7.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos7.text = "UP"
                screenCompile.ids.bt_bed_pos7.md_bg_color = "#ee2222"

            if conf_bed_pos_step[8] != 1:
                screenCompile.ids.bt_bed_pos8.text = "DN"
                screenCompile.ids.bt_bed_pos8.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos8.text = "UP"
                screenCompile.ids.bt_bed_pos8.md_bg_color = "#ee2222"

            if conf_bed_pos_step[9] != 1:
                screenCompile.ids.bt_bed_pos9.text = "DN"
                screenCompile.ids.bt_bed_pos9.md_bg_color = "#196BA5"
            else:
                screenCompile.ids.bt_bed_pos9.text = "UP"
                screenCompile.ids.bt_bed_pos9.md_bg_color = "#ee2222"

        except Exception as e:
            Logger.error(e)

    def regular_highspeed_display(self, dt):
        global flag_mode, flag_run, flag_alarm
        global val_feed_pv, val_bend_pv, val_turn_pv
        global val_feed_sv, val_bend_sv, val_turn_sv
        global conf_feed_speed_pv, conf_turn_speed_pv, conf_bend_speed_pv
        global conf_feed_speed_sv, conf_turn_speed_sv, conf_bend_speed_sv
        global conf_bed_pos_pv, conf_bed_pos_sv
        global sens_clamp_close, sens_bend_reducer, sens_bend_origin
        global sens_press_open, sens_table_up, sens_table_down
        global sens_feed_origin, sens_feed_reducer, sens_chuck_close
        global flag_seqs_arr, flag_steps_arr

        screenOperateManual = self.screen_manager.get_screen('screen_operate_manual')
        screenOperateAuto = self.screen_manager.get_screen('screen_operate_auto')

        try:
            screenOperateAuto.ids.lb_set_feed.text = str(val_feed_sv)
            screenOperateAuto.ids.lb_set_bend.text = str(val_bend_sv)
            screenOperateAuto.ids.lb_set_turn.text = str(val_turn_sv)

            screenOperateAuto.ids.lb_real_feed.text = str(val_feed_pv)
            screenOperateAuto.ids.lb_real_bend.text = str(val_bend_pv)
            screenOperateAuto.ids.lb_real_turn.text = str(val_turn_pv)

            screenOperateAuto.ids.lb_feed_speed.text = str(conf_feed_speed_pv)
            screenOperateAuto.ids.lb_bend_speed.text = str(conf_bend_speed_pv)
            screenOperateAuto.ids.lb_turn_speed.text = str(conf_turn_speed_pv)
            screenOperateAuto.ids.lb_bed_pos.text = "UP" if conf_bed_pos_pv == 1 else "DN"

            screenOperateManual.ids.bt_feed_speed.text = str(conf_feed_speed_pv)
            screenOperateManual.ids.bt_bend_speed.text = str(conf_bend_speed_pv)
            screenOperateManual.ids.bt_turn_speed.text = str(conf_turn_speed_pv)

            if not flag_mode:
                screenOperateManual.ids.bt_mode.md_bg_color = "#196BA5"
                screenOperateManual.ids.bt_mode.text = "MANUAL MODE"
                screenOperateAuto.ids.bt_mode.md_bg_color = "#196BA5"
                screenOperateAuto.ids.bt_mode.text = "MANUAL MODE"
            else:
                screenOperateManual.ids.bt_mode.md_bg_color = "#ee2222"
                screenOperateManual.ids.bt_mode.text = "AUTO MODE"
                screenOperateAuto.ids.bt_mode.md_bg_color = "#ee2222"
                screenOperateAuto.ids.bt_mode.text = "AUTO MODE"

            if flag_run:
                screenOperateAuto.ids.lp_run.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_run.md_bg_color = "#223322"

            if flag_alarm:
                screenOperateAuto.ids.lp_alarm.md_bg_color = "#ee2222"
            else:
                screenOperateAuto.ids.lp_alarm.md_bg_color = "#332222"

            if sens_clamp_close:
                screenOperateManual.ids.lp_clamp_close.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_clamp_close.md_bg_color = "#223322"

            if sens_bend_reducer:
                screenOperateManual.ids.lp_bend_reducer.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_bend_reducer.md_bg_color = "#223322"

            if sens_bend_origin:
                screenOperateManual.ids.lp_bend_origin.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_bend_origin.md_bg_color = "#223322"

            if sens_press_open:
                screenOperateManual.ids.lp_press_open.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_press_open.md_bg_color = "#223322"

            if sens_table_up:
                screenOperateManual.ids.lp_table_up.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_table_up.md_bg_color = "#223322"

            if sens_table_down:
                screenOperateManual.ids.lp_table_down.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_table_down.md_bg_color = "#223322"

            if sens_feed_origin:
                screenOperateManual.ids.lp_feed_origin.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_feed_origin.md_bg_color = "#223322"

            if sens_feed_reducer:
                screenOperateManual.ids.lp_feed_reducer.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_feed_reducer.md_bg_color = "#223322"

            if sens_chuck_close:
                screenOperateManual.ids.lp_chuck_close.md_bg_color = "#22ee22"
            else:
                screenOperateManual.ids.lp_chuck_close.md_bg_color = "#223322"

            if flag_seqs_arr[0]:
                screenOperateAuto.ids.lp_seq_init1.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq_init1.md_bg_color = "#223322"

            if flag_seqs_arr[1]:
                screenOperateAuto.ids.lp_seq_init2.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq_init2.md_bg_color = "#223322"

            if flag_seqs_arr[2]:
                screenOperateAuto.ids.lp_seq1.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq1.md_bg_color = "#223322"

            if flag_seqs_arr[3]:
                screenOperateAuto.ids.lp_seq2.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq2.md_bg_color = "#223322"

            if flag_seqs_arr[4]:
                screenOperateAuto.ids.lp_seq3.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq3.md_bg_color = "#223322"

            if flag_seqs_arr[5]:
                screenOperateAuto.ids.lp_seq4.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq4.md_bg_color = "#223322"

            if flag_seqs_arr[6]:
                screenOperateAuto.ids.lp_seq5.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq5.md_bg_color = "#223322"

            if flag_seqs_arr[7]:
                screenOperateAuto.ids.lp_seq6.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq6.md_bg_color = "#223322"

            if flag_seqs_arr[8]:
                screenOperateAuto.ids.lp_seq7.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq7.md_bg_color = "#223322"

            if flag_seqs_arr[9]:
                screenOperateAuto.ids.lp_seq8.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq8.md_bg_color = "#223322"

            if flag_seqs_arr[10]:
                screenOperateAuto.ids.lp_seq9.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_seq9.md_bg_color = "#223322"

            if flag_steps_arr[0]:
                screenOperateAuto.ids.lp_step0.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step0.md_bg_color = "#223322"

            if flag_steps_arr[1]:
                screenOperateAuto.ids.lp_step1.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step1.md_bg_color = "#223322"

            if flag_steps_arr[2]:
                screenOperateAuto.ids.lp_step2.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step2.md_bg_color = "#223322"

            if flag_steps_arr[3]:
                screenOperateAuto.ids.lp_step3.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step3.md_bg_color = "#223322"

            if flag_steps_arr[4]:
                screenOperateAuto.ids.lp_step4.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step4.md_bg_color = "#223322"

            if flag_steps_arr[5]:
                screenOperateAuto.ids.lp_step5.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step5.md_bg_color = "#223322"

            if flag_steps_arr[6]:
                screenOperateAuto.ids.lp_step6.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step6.md_bg_color = "#223322"

            if flag_steps_arr[7]:
                screenOperateAuto.ids.lp_step7.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step7.md_bg_color = "#223322"

            if flag_steps_arr[8]:
                screenOperateAuto.ids.lp_step8.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step8.md_bg_color = "#223322"

            if flag_steps_arr[9]:
                screenOperateAuto.ids.lp_step9.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step9.md_bg_color = "#223322"

            if flag_steps_arr[10]:
                screenOperateAuto.ids.lp_step10.md_bg_color = "#22ee22"
            else:
                screenOperateAuto.ids.lp_step10.md_bg_color = "#223322"

        except Exception as e:
            Logger.error(e)

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
        
class ScreenMainMenu(MDScreen):    
    def __init__(self, **kwargs):
        super(ScreenMainMenu, self).__init__(**kwargs)

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


class ScreenPipeSetting(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenPipeSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        self.load()

        self.update_graph()

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

    def load(self):
        global data_base_pipe_setting
        global val_pipe_length, val_pipe_diameter, val_pipe_thickness

        try:
            data_settings = np.loadtxt("conf\\settings.cfg", encoding=None)
            data_base_load = data_settings.T
            data_base_pipe_setting = data_base_load[:3]

            val_pipe_length = data_base_pipe_setting[0]
            val_pipe_diameter = data_base_pipe_setting[1]
            val_pipe_thickness = data_base_pipe_setting[2]

            self.ids.input_pipe_length.text = str(val_pipe_length)
            self.ids.input_pipe_diameter.text = str(val_pipe_diameter)
            self.ids.input_pipe_thickness.text = str(val_pipe_thickness)
            toast("sucessfully load pipe setting")
        except:
            toast("error load pipe setting")

    def save(self):
        global data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting
        global val_pipe_length, val_pipe_diameter, val_pipe_thickness

        try:
            self.update()

            data_base_pipe_setting = np.array([val_pipe_length,
                                   val_pipe_diameter,
                                   val_pipe_thickness])

            data_base_save = np.hstack((data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting))
            with open("conf\\settings.cfg","wb") as f:
                np.savetxt(f, data_base_save.T, fmt="%.3f")
            toast("sucessfully save pipe setting")
        except:
            toast("error save pipe setting")

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

class ScreenMachineSetting(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenMachineSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        self.load()

    def update(self):
        global flag_conn_stat

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
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_register(2512, int(val_machine_eff_length), slave=1) #V2000
                modbus_client.write_register(2513, int(val_machine_supp_pos), slave=1) #V2001
                modbus_client.write_register(2514, int(val_machine_clamp_front_delay), slave=1) #V2002
                modbus_client.write_register(2515, int(val_machine_clamp_rear_delay), slave=1) #V2003
                modbus_client.write_register(2516, int(val_machine_press_front_delay), slave=1) #V2004
                modbus_client.write_register(2517, int(val_machine_press_rear_delay), slave=1) #V2005
                modbus_client.write_register(2518, int(val_machine_collet_clamp_delay), slave=1) #V2006
                modbus_client.write_register(2519, int(val_machine_collet_open_delay), slave=1) #V2007
                modbus_client.write_register(2520, int(val_machine_die_radius), slave=1) #V2008
                modbus_client.close()
            else:
                toast("PLC Slave is not connected")  

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

    def load(self):
        global data_base_machine_setting
        global val_machine_eff_length, val_machine_supp_pos, val_machine_clamp_front_delay, val_machine_clamp_rear_delay
        global val_machine_press_front_delay, val_machine_press_rear_delay, val_machine_collet_clamp_delay
        global val_machine_collet_open_delay, val_machine_die_radius

        try:
            data_settings = np.loadtxt("conf\\settings.cfg", encoding=None)
            data_base_load = data_settings.T
            data_base_machine_setting = data_base_load[3:12]

            val_machine_eff_length = data_base_machine_setting[0]
            val_machine_supp_pos = data_base_machine_setting[1]
            val_machine_clamp_front_delay = data_base_machine_setting[2]
            val_machine_clamp_rear_delay = data_base_machine_setting[3]
            val_machine_press_front_delay = data_base_machine_setting[4]
            val_machine_press_rear_delay = data_base_machine_setting[5]
            val_machine_collet_clamp_delay = data_base_machine_setting[6]
            val_machine_collet_open_delay = data_base_machine_setting[7]
            val_machine_die_radius = data_base_machine_setting[8]

            self.ids.input_machine_eff_length.text = str(val_machine_eff_length)
            self.ids.input_machine_supp_pos.text = str(val_machine_supp_pos)
            self.ids.input_machine_clamp_front_delay.text = str(val_machine_clamp_front_delay)
            self.ids.input_machine_clamp_rear_delay.text = str(val_machine_clamp_rear_delay)
            self.ids.input_machine_press_front_delay.text = str(val_machine_press_front_delay)
            self.ids.input_machine_press_rear_delay.text = str(val_machine_press_rear_delay)
            self.ids.input_machine_collet_clamp_delay.text = str(val_machine_collet_clamp_delay)
            self.ids.input_machine_collet_open_delay.text = str(val_machine_collet_open_delay)
            self.ids.input_machine_die_radius.text = str(val_machine_die_radius)
            toast("sucessfully load machine setting")
        except:
            toast("error load machine setting")

    def save(self):
        global data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting
        global val_machine_eff_length, val_machine_supp_pos, val_machine_clamp_front_delay, val_machine_clamp_rear_delay
        global val_machine_press_front_delay, val_machine_press_rear_delay, val_machine_collet_clamp_delay
        global val_machine_collet_open_delay, val_machine_die_radius

        try:
            self.update()
            
            data_base_machine_setting = np.array([val_machine_eff_length,
                                   val_machine_supp_pos,
                                   val_machine_clamp_front_delay,
                                   val_machine_clamp_rear_delay,
                                   val_machine_press_front_delay,
                                   val_machine_press_rear_delay,
                                   val_machine_collet_clamp_delay,
                                   val_machine_collet_open_delay,
                                   val_machine_die_radius,
                                   ])
            
            data_base_save = np.hstack((data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting))
            with open("conf\\settings.cfg","wb") as f:
                np.savetxt(f, data_base_save.T, fmt="%.3f")
            toast("sucessfully save machine setting")
        except:
            toast("error save machine setting")

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

class ScreenAdvancedSetting(MDScreen):
    def __init__(self, **kwargs):
        super(ScreenAdvancedSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        self.load()
           
    def update(self):
        global modbus_client

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
        val_advanced_start_mode = float(self.ids.input_advanced_start_mode.text)
        val_advanced_first_line = float(self.ids.input_advanced_first_line.text)
        val_advanced_finish_job = float(self.ids.input_advanced_finish_job.text)
        val_advanced_receive_pos_x = float(self.ids.input_advanced_receive_pos_x.text)
        val_advanced_receive_pos_b = float(self.ids.input_advanced_receive_pos_b.text)
        val_advanced_prod_qty = float(self.ids.input_advanced_prod_qty.text)
        val_advanced_press_semiclamp_time = float(self.ids.input_advanced_press_semiclamp_time.text)
        val_advanced_press_semiopen_time = float(self.ids.input_advanced_press_semiopen_time.text)
        val_advanced_clamp_semiclamp_time = float(self.ids.input_advanced_clamp_semiclamp_time.text)
        val_advanced_springback_20 = float(self.ids.input_advanced_springback_20.text)
        val_advanced_springback_120 = float(self.ids.input_advanced_springback_120.text)
        val_advanced_max_bend = float(self.ids.input_advanced_max_bend.text)
        val_advanced_press_start_angle = float(self.ids.input_advanced_press_start_angle.text)
        val_advanced_press_stop_angle = float(self.ids.input_advanced_press_stop_angle.text)

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_register(2522, int(val_advanced_pipe_head), slave=1) #V2010
                modbus_client.write_register(2523, int(val_advanced_start_mode), slave=1) #V2011
                modbus_client.write_register(2524, int(val_advanced_first_line), slave=1) #V2012
                modbus_client.write_register(2525, int(val_advanced_finish_job), slave=1) #V2013
                modbus_client.write_register(2526, int(val_advanced_receive_pos_x), slave=1) #V2014
                modbus_client.write_register(2527, int(val_advanced_receive_pos_b), slave=1) #V2015
                modbus_client.write_register(2528, int(val_advanced_prod_qty), slave=1) #V2016
                modbus_client.write_register(2529, int(val_advanced_press_semiclamp_time), slave=1) #V2017
                modbus_client.write_register(2530, int(val_advanced_press_semiopen_time), slave=1) #V2018
                modbus_client.write_register(2531, int(val_advanced_clamp_semiclamp_time), slave=1) #V2019
                modbus_client.write_register(2532, int(val_advanced_springback_20), slave=1) #V2020
                modbus_client.write_register(2533, int(val_advanced_springback_120), slave=1) #V2021
                modbus_client.write_register(2534, int(val_advanced_max_bend), slave=1) #V2022
                modbus_client.write_register(2535, int(val_advanced_press_start_angle), slave=1) #V2023
                modbus_client.write_register(2536, int(val_advanced_press_stop_angle), slave=1) #V2024
                modbus_client.close()
            else:
                toast("PLC Slave is not connected")  
        except:
            toast("error send machine_setting data to PLC Slave") 

    def load(self):
        global data_base_advanced_setting
        global val_advanced_pipe_head, val_advanced_start_mode, val_advanced_first_line, val_advanced_finish_job
        global val_advanced_receive_pos_x, val_advanced_receive_pos_b, val_advanced_prod_qty, val_advanced_press_semiclamp_time
        global val_advanced_press_semiopen_time, val_advanced_clamp_semiclamp_time, val_advanced_springback_20, val_advanced_springback_120
        global val_advanced_max_bend, val_advanced_press_start_angle, val_advanced_press_stop_angle

        try:
            data_settings = np.loadtxt("conf\\settings.cfg", encoding=None)
            data_base_load = data_settings.T
            data_base_advanced_setting = data_base_load[12:]

            val_advanced_pipe_head = data_base_advanced_setting[0]
            val_advanced_start_mode = data_base_advanced_setting[1]
            val_advanced_first_line = data_base_advanced_setting[2]
            val_advanced_finish_job = data_base_advanced_setting[3]
            val_advanced_receive_pos_x = data_base_advanced_setting[4]
            val_advanced_receive_pos_b = data_base_advanced_setting[5]
            val_advanced_prod_qty = data_base_advanced_setting[6]
            val_advanced_press_semiclamp_time = data_base_advanced_setting[7]
            val_advanced_press_semiopen_time = data_base_advanced_setting[8]
            val_advanced_clamp_semiclamp_time = data_base_advanced_setting[9]
            val_advanced_springback_20 = data_base_advanced_setting[10]
            val_advanced_springback_120 = data_base_advanced_setting[11]
            val_advanced_max_bend = data_base_advanced_setting[12]
            val_advanced_press_start_angle = data_base_advanced_setting[13]
            val_advanced_press_stop_angle = data_base_advanced_setting[14]

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
            toast("sucessfully load advanced setting")
        except:
            toast("error load advanced setting")

    def save(self):
        global data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting
        global val_machine_eff_length, val_machine_supp_pos, val_machine_clamp_front_delay, val_machine_clamp_rear_delay
        global val_machine_press_front_delay, val_machine_press_rear_delay, val_machine_collet_clamp_delay
        global val_machine_collet_open_delay, val_machine_die_radius

        try:
            self.update()
            
            data_base_advanced_setting = np.array([val_advanced_pipe_head,
                                   val_advanced_start_mode,
                                   val_advanced_first_line,
                                   val_advanced_finish_job,
                                   val_advanced_receive_pos_x,
                                   val_advanced_receive_pos_b,
                                   val_advanced_prod_qty,
                                   val_advanced_press_semiclamp_time,
                                   val_advanced_press_semiopen_time,
                                   val_advanced_clamp_semiclamp_time,
                                   val_advanced_springback_20,
                                   val_advanced_springback_120,
                                   val_advanced_max_bend,
                                   val_advanced_press_start_angle,
                                   val_advanced_press_stop_angle,
                                   ])
            
            data_base_save = np.hstack((data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting))
            with open("conf\\settings.cfg","wb") as f:
                np.savetxt(f, data_base_save.T, fmt="%.3f")
            toast("sucessfully save advanced setting")
        except:
            toast("error save advanced setting")

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

class ScreenOperateManual(MDScreen):
    def __init__(self, **kwargs):      
        super(ScreenOperateManual, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global val_feed_sv, val_bend_sv, val_turn_sv

        self.ids.input_operate_feed.text = str(val_feed_sv)
        self.ids.input_operate_bend.text = str(val_bend_sv)
        self.ids.input_operate_turn.text = str(val_turn_sv)

    def exec_mode(self):
        global flag_conn_stat, flag_mode

        if flag_mode:
            flag_mode = False
        else:
            flag_mode = True

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3072, flag_mode, slave=1) #M0
                modbus_client.close()
        except Exception as e:
            toast(e) 

    def exec_press(self):
        global flag_conn_stat, flag_cylinder_press

        if flag_cylinder_press:
            flag_cylinder_press = False
            self.ids.bt_press.md_bg_color = "#196BA5"
        else:
            flag_cylinder_press = True
            self.ids.bt_press.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3082, flag_cylinder_press, slave=1) #M10
                modbus_client.close()
        except:
            toast("error send flag_cylinder_press data to PLC Slave") 

    def exec_clamp(self):
        global flag_conn_stat, flag_cylinder_clamp

        if flag_cylinder_clamp:
            flag_cylinder_clamp = False
            self.ids.bt_clamp.md_bg_color = "#196BA5"
        else:
            flag_cylinder_clamp = True
            self.ids.bt_clamp.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3083, flag_cylinder_clamp, slave=1) #M11
                modbus_client.close()
        except:
            toast("error send flag_cylinder_clamp data to PLC Slave") 

    def exec_chuck(self):
        global flag_conn_stat, flag_cylinder_chuck

        if flag_cylinder_chuck:
            flag_cylinder_chuck = False
            self.ids.bt_chuck.md_bg_color = "#196BA5"
        else:
            flag_cylinder_chuck = True
            self.ids.bt_chuck.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3084, flag_cylinder_chuck, slave=1) #M12
                modbus_client.close()
        except:
            toast("error send flag_cylinder_chuck data to PLC Slave") 

    def exec_mandrell(self):
        global flag_conn_stat, flag_cylinder_mandrell

        if flag_cylinder_mandrell:
            flag_cylinder_mandrell = False
            self.ids.bt_mandrell.md_bg_color = "#196BA5"
        else:
            flag_cylinder_mandrell = True
            self.ids.bt_mandrell.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3085, flag_cylinder_mandrell, slave=1) #M13
                modbus_client.close()
        except:
            toast("error send flag_cylinder_mandrell data to PLC Slave") 

    def exec_table_up(self):
        global flag_conn_stat, flag_cylinder_table_up

        if flag_cylinder_table_up:
            flag_cylinder_table_up = False
            self.ids.bt_table_up.md_bg_color = "#196BA5"
        else:
            flag_cylinder_table_up = True
            self.ids.bt_table_up.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3086, flag_cylinder_table_up, slave=1) #M14
                modbus_client.close()
        except:
            toast("error send flag_cylinder_table_up data to PLC Slave") 

    def exec_table_shift(self):
        global flag_conn_stat, flag_cylinder_table_shift

        if flag_cylinder_table_shift:
            flag_cylinder_table_shift = False
            self.ids.bt_table_shift.md_bg_color = "#196BA5"
        else:
            flag_cylinder_table_shift = True
            self.ids.bt_table_shift.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3087, flag_cylinder_table_shift, slave=1) #M15
                modbus_client.close()
        except:
            toast("error send flag_cylinder_table_shift data to PLC Slave") 

    def exec_holder_top(self):
        global flag_conn_stat, flag_cylinder_holder_top

        if flag_cylinder_holder_top:
            flag_cylinder_holder_top = False
            self.ids.bt_holder_top.md_bg_color = "#196BA5"
        else:
            flag_cylinder_holder_top = True
            self.ids.bt_holder_top.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3088, flag_cylinder_holder_top, slave=1) #M16
                modbus_client.close()
        except:
            toast("error send flag_cylinder_holder_top data to PLC Slave") 

    def exec_holder_bottom(self):
        global flag_conn_stat, flag_cylinder_holder_bottom

        if flag_cylinder_holder_bottom:
            flag_cylinder_holder_bottom = False
            self.ids.bt_holder_bottom.md_bg_color = "#196BA5"
        else:
            flag_cylinder_holder_bottom = True
            self.ids.bt_holder_bottom.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3089, flag_cylinder_holder_bottom, slave=1) #M17
                modbus_client.close()
        except:
            toast("error send flag_cylinder_holder_bottom data to PLC Slave") 

    def exec_jog_enable(self):
        global flag_conn_stat, flag_jog_enable
        if flag_jog_enable:
            flag_jog_enable = False
            self.ids.bt_jog_enable.md_bg_color = "#196BA5"
        else:
            flag_jog_enable = True
            self.ids.bt_jog_enable.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3092, flag_jog_enable, slave=1) #M20
                modbus_client.close()
        except:
            toast("error send flag_jog_enable data to PLC Slave")  

    def end_jog(self):
        global flag_conn_stat
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coils(3093, [False, False, False, False, False, False], slave=1) #M21 - M26
                modbus_client.close()
        except:
            toast("error send end_jog data to PLC Slave")  

    def exec_jog_feed_p(self):
        global flag_conn_stat, flag_jog_req_feed
        flag_jog_req_feed = True
        self.ids.bt_jog_feed_p.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3093, True, slave=1) #M21
                modbus_client.close()
        except:
            toast("error send exec_jog_feed_p data to PLC Slave")  

    def exec_jog_feed_n(self):
        global flag_conn_stat, flag_jog_req_feed
        flag_jog_req_feed = True
        self.ids.bt_jog_feed_n.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3094, True, slave=1) #M22
                modbus_client.close()
        except:
            toast("error send exec_jog_feed_n data to PLC Slave")     

    def end_jog_feed(self):
        global flag_jog_req_feed
        flag_jog_req_feed = False
        self.ids.bt_jog_feed_p.md_bg_color = "#196BA5"
        self.ids.bt_jog_feed_n.md_bg_color = "#196BA5"
        self.end_jog()

    def exec_jog_bend_p(self):
        global flag_conn_stat, flag_jog_req_bend
        flag_jog_req_bend = True
        self.ids.bt_jog_bend_p.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3095, True, slave=1) #M23
                modbus_client.close()
        except:
            toast("error send exec_jog_bend_p data to PLC Slave")  

    def exec_jog_bend_n(self):
        global flag_conn_stat, flag_jog_req_bend
        flag_jog_req_bend = True
        self.ids.bt_jog_bend_n.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3096, True, slave=1) #M24
                modbus_client.close()
        except:
            toast("error send exec_jog_bend_n data to PLC Slave")  

    def end_jog_bend(self):
        global flag_jog_req_bend
        flag_jog_req_bend = False
        self.ids.bt_jog_bend_p.md_bg_color = "#196BA5"
        self.ids.bt_jog_bend_n.md_bg_color = "#196BA5"
        self.end_jog()

    def exec_jog_turn_p(self):
        global flag_conn_stat, flag_jog_req_turn
        flag_jog_req_turn = True
        self.ids.bt_jog_turn_p.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3097, True, slave=1) #M25
                modbus_client.close()
        except:
            toast("error send exec_jog_turn_p data to PLC Slave")  

    def exec_jog_turn_n(self):
        global flag_conn_stat, flag_jog_req_turn
        flag_jog_req_turn = True
        self.ids.bt_jog_turn_n.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3098, True, slave=1) #M26
                modbus_client.close()
        except:
            toast("error send exec_jog_turn_n data to PLC Slave")  

    def end_jog_turn(self):
        global flag_jog_req_turn
        flag_jog_req_turn = False
        self.ids.bt_jog_turn_p.md_bg_color = "#196BA5"
        self.ids.bt_jog_turn_n.md_bg_color = "#196BA5"
        self.end_jog()

    def choice_speed(self, movement):
        global flag_conn_stat
        global conf_feed_speed_sv, conf_bend_speed_sv, conf_turn_speed_sv
        global data_base_config

        if(movement=="feed"):
            if conf_feed_speed_sv < 5:
                conf_feed_speed_sv += 1
            else:
                conf_feed_speed_sv = 1

        if(movement=="bend"):
            if conf_bend_speed_sv < 5:
                conf_bend_speed_sv += 1
            else:
                conf_bend_speed_sv = 1

        if(movement=="turn"):
            if conf_turn_speed_sv < 5:
                conf_turn_speed_sv += 1
            else:
                conf_turn_speed_sv = 1

        try:
            if flag_conn_stat:
                modbus_client.connect()
                # modbus_client.write_register(3712, conf_feed_speed_sv, slave=1) #V3200
                modbus_client.write_register(3713, conf_feed_speed_sv, slave=1) #V3201
                # modbus_client.write_register(3742, conf_bend_speed_sv, slave=1) #V3230
                modbus_client.write_register(3743, conf_bend_speed_sv, slave=1) #V3231
                # modbus_client.write_register(3772, conf_turn_speed_sv, slave=1) #V3260
                modbus_client.write_register(3773, conf_turn_speed_sv, slave=1) #V3261
                modbus_client.close()
        except:
            toast("error send configuration speed data to PLC Slave")

    def exec_operate_feed(self):
        global flag_conn_stat, flag_operate_req_feed
        global val_feed_sv

        flag_operate_req_feed = True
        self.ids.bt_operate_feed.md_bg_color = "#ee2222"
        val_feed_sv = float(self.ids.input_operate_feed.text)

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3099, flag_operate_req_feed, slave=1) #M27
                modbus_client.write_register(3513, int(val_feed_sv), slave=1) #V3001
                modbus_client.close()
        except:
            toast("error send exec_operate_feed and val_operate_feed data to PLC Slave") 

    def end_operate_feed(self):
        global flag_conn_stat, flag_operate_req_feed
        flag_operate_req_feed = False
        self.ids.bt_operate_feed.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3099, flag_operate_req_feed, slave=1) #M27
                modbus_client.close()
        except:
            toast("error send end_operate_feed data to PLC Slave") 

    def exec_operate_bend(self):
        global flag_conn_stat, flag_operate_req_bend
        global val_bend_sv

        flag_operate_req_bend = True
        self.ids.bt_operate_bend.md_bg_color = "#ee2222"
        val_bend_sv = float(self.ids.input_operate_bend.text)

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3100, flag_operate_req_bend, slave=1) #M28
                modbus_client.write_register(3543, int(val_bend_sv), slave=1) #V3031
                modbus_client.close()
        except:
            toast("error send exec_operate_bend and val_operate_bend data to PLC Slave") 

    def end_operate_bend(self):
        global flag_conn_stat, flag_operate_req_bend
        flag_operate_req_bend = False
        self.ids.bt_operate_bend.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3100, flag_operate_req_bend, slave=1) #M28
                modbus_client.close()
        except:
            toast("error send end_operate_bend data to PLC Slave") 

    def exec_operate_turn(self):
        global flag_conn_stat, flag_operate_req_turn
        global val_turn_sv

        flag_operate_req_turn = True
        self.ids.bt_operate_turn.md_bg_color = "#ee2222"
        val_turn_sv = float(self.ids.input_operate_turn.text)

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3101, flag_operate_req_turn, slave=1) #M29
                modbus_client.write_register(3573, int(val_turn_sv), slave=1) #V3061
                modbus_client.close()
        except:
            toast("error send exec_operate_turn and val_operate_turn data to PLC Slave")

    def end_operate_turn(self):
        global flag_conn_stat, flag_operate_req_turn
        flag_operate_req_turn = False
        self.ids.bt_operate_turn.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3101, flag_operate_req_turn, slave=1) #M29
                modbus_client.close()
        except:
            toast("error send end_operate_turn data to PLC Slave")

    def exec_origin(self):
        global flag_conn_stat, flag_origin_req
        flag_origin_req = True
        self.ids.bt_origin.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3102, flag_origin_req, slave=1) #M30
                modbus_client.close()
        except:
            toast("error send flag_origin_req data to PLC Slave")

    def end_origin(self):
        global flag_conn_stat, flag_origin_req
        flag_origin_req = False
        self.ids.bt_origin.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3102, flag_origin_req, slave=1) #M30
                modbus_client.close()
        except:
            toast("error send flag_origin_req data to PLC Slave")

    def exec_reset(self):
        global flag_conn_stat, flag_reset
        flag_reset = True
        self.ids.bt_reset.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3075, flag_reset, slave=1) #M3
                modbus_client.close()
        except:
            toast("error send flag_reset data to PLC Slave")

    def end_reset(self):
        global flag_conn_stat, flag_reset
        flag_reset = False
        self.ids.bt_reset.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3075, flag_reset, slave=1) #M3
                modbus_client.close()
        except:
            toast("error send flag_reset data to PLC Slave")

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

class ScreenOperateAuto(MDScreen):
    def __init__(self, **kwargs):       
        super(ScreenOperateAuto, self).__init__(**kwargs)
        self.file_manager = MDFileManager(exit_manager=self.exit_manager, select_path=self.select_path)
        Clock.schedule_once(self.delayed_init, 5)

    def delayed_init(self, dt):
        self.reload()

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
        
        self.update_graph()
        self.send_data()

    def file_manager_open(self):
        self.file_manager.show(os.path.expanduser(os.getcwd() + "\data"))  # output manager to the screen
        self.manager_open = True

    def select_path(self, path: str):
        try:
            self.exit_manager(path)
        except:
            toast("error select file path")

    def exit_manager(self, *args):
        global data_base_process, data_base_config
        try:
            data_set = np.loadtxt(*args, delimiter="\t", encoding=None, skiprows=1)
            data_base_load = data_set.T
            data_base_process = data_base_load[:3,:]
            data_base_config = data_base_load[3:,:]
            self.reload()

            self.manager_open = False
            self.file_manager.close()
        except:
            toast("error open file")
            self.file_manager.close()
    
    def send_data(self):
        global val_feed_step, val_bend_step, val_turn_step

        global data_base_process
        global data_base_config
        global val_machine_die_radius

        global conf_feed_speed_step, conf_bend_speed_step, conf_turn_speed_step
        global conf_bed_pos_step 

        val_feed_step = data_base_process[0,:]
        val_bend_step = data_base_process[1,:] 
        val_turn_step = data_base_process[2,:] 

        conf_feed_speed_step = data_base_config[0,:]
        conf_bend_speed_step = data_base_config[1,:]
        conf_turn_speed_step = data_base_config[2,:]
        conf_bed_pos_step = data_base_config[3,:]
        print(data_base_config)

        val_feed_absolute_step = np.zeros(10)
        val_bend_linear_absolute_step = np.zeros(10)
        # bend linear offset = 2 pi * r * die radius / 360 
        # (conversion from bending movement to feed offset linear movement)
        val_bend_linear_offset_step = val_machine_die_radius * 2 * np.pi * val_bend_step / 360
        # val_bend_linear_offset_step = val_machine_die_radius * val_bend_step / 360

        # setting val_advanced_receive_pos_x as first cycle position set value feed
        val_feed_absolute_step[0] = int(val_feed_step[0] + val_advanced_receive_pos_x)
        val_bend_linear_absolute_step[0] = int(val_feed_absolute_step[0] + val_bend_linear_offset_step[0])        

        for i in range(1,10):
            # feed absolute = feed offset + last feed absolute + bend linear offset
            val_feed_absolute_step[i] = int(val_feed_absolute_step[i-1] + val_feed_step[i])
            
            if val_feed_absolute_step[i] > val_machine_eff_length:
                val_feed_absolute_step[i] = int(val_feed_step[i] + val_advanced_receive_pos_x)

        for i in range(1,9):
            val_bend_linear_absolute_step[i] = int(val_feed_absolute_step[i] + val_bend_linear_offset_step[i])

        val_turn_absolute_step = np.zeros(10)
        val_turn_absolute_step[0] = val_turn_step[0]
        for i in range(1,10):
            # turn absolute = turn offset + last turn absolute
            val_turn_absolute_step[i] = int(val_turn_step[i] + val_turn_absolute_step[i-1])

        list_val_feed_absolute_step = val_feed_absolute_step.astype(int).tolist()
        list_val_bend_step = val_bend_step.astype(int).tolist()
        list_val_turn_absolute_step = val_turn_absolute_step.astype(int).tolist()
        # list_val_turn_step = val_turn_step.astype(int).tolist()
        list_val_bend_linear_absolute_step = val_bend_linear_absolute_step.astype(int).tolist()

        list_conf_feed_speed_step = conf_feed_speed_step.astype(int).tolist()
        list_conf_bend_speed_step = conf_bend_speed_step.astype(int).tolist()
        list_conf_turn_speed_step = conf_turn_speed_step.astype(int).tolist()
        list_conf_bed_pos_step = conf_bed_pos_step.astype(bool).tolist()

        print("list_val_feed_absolute_step", list_val_feed_absolute_step)
        print("list_val_bend_step", list_val_bend_step)
        print("list_val_turn_absolute_step", list_val_turn_absolute_step)
        print("list_val_bend_linear_absolute_step", list_val_bend_linear_absolute_step)



        try:
            if flag_conn_stat:
                modbus_client.connect()
                # modbus_client.write_register(3523, int(val_feed_step[0]), slave=1) #V3011
                # modbus_client.write_register(3553, int(val_bend_step[0]), slave=1) #V3011
                # modbus_client.write_register(3583, int(val_turn_step[0]), slave=1) #V3011

                # modbus_client.write_register(3524, int(val_feed_step[1]), slave=1) #V3011
                # modbus_client.write_register(3554, int(val_bend_step[1]), slave=1) #V3011
                # modbus_client.write_register(3584, int(val_turn_step[1]), slave=1) #V3011

                modbus_client.write_registers(3523, list_val_feed_absolute_step, slave=1) #V3011
                modbus_client.write_registers(3553, list_val_bend_step, slave=1) #V3041
                modbus_client.write_registers(3583, list_val_turn_absolute_step, slave=1) #V3071
                # modbus_client.write_registers(3583, list_val_turn_step, slave=1) #V3071
                modbus_client.write_registers(3623, list_val_bend_linear_absolute_step, slave=1) #V3111

                modbus_client.write_registers(3723, list_conf_feed_speed_step, slave=1) #V3211
                modbus_client.write_registers(3753, list_conf_bend_speed_step, slave=1) #V3241
                modbus_client.write_registers(3783, list_conf_turn_speed_step, slave=1) #V3271
                modbus_client.write_coils(3383, list_conf_bed_pos_step, slave=1) #M311
                # modbus_client.write_coils(3093, [False, False, False, False, False, False], slave=1) #M21 - M26
                modbus_client.close()
        except Exception as e:
            toast(e) 
            
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
    
    def exec_mode(self):
        global flag_conn_stat, flag_mode

        if flag_mode:
            flag_mode = False
        else:
            flag_mode = True

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3072, flag_mode, slave=1) #M0
                modbus_client.close()
        except Exception as e:
            toast(e) 

    def exec_start(self):
        global flag_conn_stat, flag_run
        flag_run = True
        self.ids.bt_start.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3073, flag_run, slave=1) #M1
                modbus_client.close()
        except:
            toast("error send flag_run data to PLC Slave") 

    def end_start(self):
        self.ids.bt_start.md_bg_color = "#196BA5"


    def exec_stop(self):
        global flag_conn_stat, flag_run
        flag_run = False
        self.ids.bt_stop.md_bg_color = "#ee2222"
        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3073, flag_run, slave=1) #M1
                modbus_client.close()
        except:
            toast("error send flag_run data to PLC Slave") 

    def end_stop(self):
        self.ids.bt_stop.md_bg_color = "#196BA5"

    def exec_origin(self):
        global flag_conn_stat, flag_origin_req
        flag_origin_req = True
        self.ids.bt_origin.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3102, flag_origin_req, slave=1) #M30
                modbus_client.close()
        except:
            toast("error send flag_origin_req data to PLC Slave")

    def end_origin(self):
        global flag_conn_stat, flag_origin_req
        flag_origin_req = False
        self.ids.bt_origin.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3102, flag_origin_req, slave=1) #M30
                modbus_client.close()
        except:
            toast("error send flag_origin_req data to PLC Slave")

    def exec_reset(self):
        global flag_conn_stat, flag_reset
        flag_reset = True
        self.ids.bt_reset.md_bg_color = "#ee2222"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3075, flag_reset, slave=1) #M3
                modbus_client.close()
        except:
            toast("error send flag_reset data to PLC Slave")

    def end_reset(self):
        global flag_conn_stat, flag_reset
        flag_reset = False
        self.ids.bt_reset.md_bg_color = "#196BA5"

        try:
            if flag_conn_stat:
                modbus_client.connect()
                modbus_client.write_coil(3075, flag_reset, slave=1) #M3
                modbus_client.close()
        except:
            toast("error send flag_reset data to PLC Slave")
    
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

class ScreenCompile(MDScreen):
    def __init__(self, **kwargs):
        global data_base_config
        global conf_feed_speed_step, conf_bend_speed_step, conf_turn_speed_step, conf_bed_pos_step

        super(ScreenCompile, self).__init__(**kwargs)
        self.file_manager = MDFileManager(exit_manager=self.exit_manager, select_path=self.select_path)
        for i in range(0,9):
            data_base_config[0,i] = conf_feed_speed_step[i]
            data_base_config[1,i] = conf_bend_speed_step[i]
            data_base_config[2,i] = conf_turn_speed_step[i]
            data_base_config[3,i] = conf_bed_pos_step[i]

    def file_manager_open(self):
        self.file_manager.show(os.path.expanduser(os.getcwd() + "\data"))  # output manager to the screen
        self.manager_open = True

    def select_path(self, path: str):
        try:
            path_name = os.path.expanduser(os.getcwd() + "\data\\")
            filename = path.replace(path_name, "")
            filename = filename.replace(".gcode", "")
            self.ids.input_file_name.text = filename
            self.exit_manager(path)
        except:
            toast("error select file path")

    def exit_manager(self, *args):
        global data_base_process, data_base_config
        '''Called when the user reaches the root of the directory tree.'''
        try:
            data_set = np.loadtxt(*args, delimiter="\t", encoding=None, skiprows=1)
            data_base_load = data_set.T
            data_base_process = data_base_load[:3,:]
            data_base_config = data_base_load[3:,:]

            self.update_text_data()
            self.update_text_config()
            self.update_graph()

            self.manager_open = False
            self.file_manager.close()
        except Exception as e:
            toast("error open file")
            print(e)
            self.file_manager.close()

    def update_text_data(self):
        global flag_conn_stat
        global val_pipe_length, val_pipe_diameter, val_pipe_thickness
        global val_feed_step, val_bend_step, val_turn_step
        global data_base_process

        val_feed_step = data_base_process[0,:]
        val_bend_step = data_base_process[1,:] 
        val_turn_step = data_base_process[2,:] 
    
        self.ids.input_feed_step0.text = str(val_feed_step[0])
        self.ids.input_bend_step0.text = str(val_bend_step[0])
        self.ids.input_turn_step0.text = str(val_turn_step[0])

        self.ids.input_feed_step1.text = str(val_feed_step[1])
        self.ids.input_bend_step1.text = str(val_bend_step[1])
        self.ids.input_turn_step1.text = str(val_turn_step[1])

        self.ids.input_feed_step2.text = str(val_feed_step[2])
        self.ids.input_bend_step2.text = str(val_bend_step[2])
        self.ids.input_turn_step2.text = str(val_turn_step[2])

        self.ids.input_feed_step3.text = str(val_feed_step[3])
        self.ids.input_bend_step3.text = str(val_bend_step[3])
        self.ids.input_turn_step3.text = str(val_turn_step[3])

        self.ids.input_feed_step4.text = str(val_feed_step[4])
        self.ids.input_bend_step4.text = str(val_bend_step[4])
        self.ids.input_turn_step4.text = str(val_turn_step[4])

        self.ids.input_feed_step5.text = str(val_feed_step[5])
        self.ids.input_bend_step5.text = str(val_bend_step[5])
        self.ids.input_turn_step5.text = str(val_turn_step[5])

        self.ids.input_feed_step6.text = str(val_feed_step[6])
        self.ids.input_bend_step6.text = str(val_bend_step[6])
        self.ids.input_turn_step6.text = str(val_turn_step[6])

        self.ids.input_feed_step7.text = str(val_feed_step[7])
        self.ids.input_bend_step7.text = str(val_bend_step[7])
        self.ids.input_turn_step7.text = str(val_turn_step[7])

        self.ids.input_feed_step8.text = str(val_feed_step[8])
        self.ids.input_bend_step8.text = str(val_bend_step[8])
        self.ids.input_turn_step8.text = str(val_turn_step[8])

        self.ids.input_feed_step9.text = str(val_feed_step[9])
        self.ids.input_bend_step9.text = str(val_bend_step[9])
        self.ids.input_turn_step9.text = str(val_turn_step[9]) 

    def update_text_config(self):
        global flag_conn_stat
        global conf_feed_speed_step, conf_bend_speed_step, conf_turn_speed_step, conf_bed_pos_step
        global data_base_config

        conf_feed_speed_step = data_base_config[0,:]
        conf_bend_speed_step = data_base_config[1,:] 
        conf_turn_speed_step = data_base_config[2,:] 
        conf_bed_pos_step = data_base_config[3,:] 
    
        self.ids.bt_feed_speed_step0.text = str(int(conf_feed_speed_step[0]))
        self.ids.bt_bend_speed_step0.text = str(int(conf_bend_speed_step[0]))
        self.ids.bt_turn_speed_step0.text = str(int(conf_turn_speed_step[0]))
        self.ids.bt_bed_pos0.text = "UP" if conf_bed_pos_step[0] == 1 else "DN"

        self.ids.bt_feed_speed_step1.text = str(int(conf_feed_speed_step[1]))
        self.ids.bt_bend_speed_step1.text = str(int(conf_bend_speed_step[1]))
        self.ids.bt_turn_speed_step1.text = str(int(conf_turn_speed_step[1]))
        self.ids.bt_bed_pos1.text = "UP" if conf_bed_pos_step[1] == 1 else "DN"

        self.ids.bt_feed_speed_step2.text = str(int(conf_feed_speed_step[2]))
        self.ids.bt_bend_speed_step2.text = str(int(conf_bend_speed_step[2]))
        self.ids.bt_turn_speed_step2.text = str(int(conf_turn_speed_step[2]))
        self.ids.bt_bed_pos2.text = "UP" if conf_bed_pos_step[2] == 1 else "DN"

        self.ids.bt_feed_speed_step3.text = str(int(conf_feed_speed_step[3]))
        self.ids.bt_bend_speed_step3.text = str(int(conf_bend_speed_step[3]))
        self.ids.bt_turn_speed_step3.text = str(int(conf_turn_speed_step[3]))
        self.ids.bt_bed_pos3.text = "UP" if conf_bed_pos_step[3] == 1 else "DN"

        self.ids.bt_feed_speed_step4.text = str(int(conf_feed_speed_step[4]))
        self.ids.bt_bend_speed_step4.text = str(int(conf_bend_speed_step[4]))
        self.ids.bt_turn_speed_step4.text = str(int(conf_turn_speed_step[4]))
        self.ids.bt_bed_pos4.text = "UP" if conf_bed_pos_step[4] == 1 else "DN"

        self.ids.bt_feed_speed_step5.text = str(int(conf_feed_speed_step[5]))
        self.ids.bt_bend_speed_step5.text = str(int(conf_bend_speed_step[5]))
        self.ids.bt_turn_speed_step5.text = str(int(conf_turn_speed_step[5]))
        self.ids.bt_bed_pos5.text = "UP" if conf_bed_pos_step[5] == 1 else "DN"

        self.ids.bt_feed_speed_step6.text = str(int(conf_feed_speed_step[6]))
        self.ids.bt_bend_speed_step6.text = str(int(conf_bend_speed_step[6]))
        self.ids.bt_turn_speed_step6.text = str(int(conf_turn_speed_step[6]))
        self.ids.bt_bed_pos6.text = "UP" if conf_bed_pos_step[6] == 1 else "DN"

        self.ids.bt_feed_speed_step7.text = str(int(conf_feed_speed_step[7]))
        self.ids.bt_bend_speed_step7.text = str(int(conf_bend_speed_step[7]))
        self.ids.bt_turn_speed_step7.text = str(int(conf_turn_speed_step[7]))
        self.ids.bt_bed_pos7.text = "UP" if conf_bed_pos_step[7] == 1 else "DN"

        self.ids.bt_feed_speed_step8.text = str(int(conf_feed_speed_step[8]))
        self.ids.bt_bend_speed_step8.text = str(int(conf_bend_speed_step[8]))
        self.ids.bt_turn_speed_step8.text = str(int(conf_turn_speed_step[8]))
        self.ids.bt_bed_pos8.text = "UP" if conf_bed_pos_step[8] == 1 else "DN"

        self.ids.bt_feed_speed_step9.text = str(int(conf_feed_speed_step[9]))
        self.ids.bt_bend_speed_step9.text = str(int(conf_bend_speed_step[9]))
        self.ids.bt_turn_speed_step9.text = str(int(conf_turn_speed_step[9]))
        self.ids.bt_bed_pos9.text = "UP" if conf_bed_pos_step[9] == 1 else "DN"

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
    
    def update(self):
        val_feed_step[0] = float(self.ids.input_feed_step0.text)
        val_bend_step[0] = float(self.ids.input_bend_step0.text)
        val_turn_step[0] = float(self.ids.input_turn_step0.text)

        val_feed_step[1] = float(self.ids.input_feed_step1.text)
        val_bend_step[1] = float(self.ids.input_bend_step1.text)
        val_turn_step[1] = float(self.ids.input_turn_step1.text)

        val_feed_step[2] = float(self.ids.input_feed_step2.text)
        val_bend_step[2] = float(self.ids.input_bend_step2.text)
        val_turn_step[2] = float(self.ids.input_turn_step2.text)

        val_feed_step[3] = float(self.ids.input_feed_step3.text)
        val_bend_step[3] = float(self.ids.input_bend_step3.text)
        val_turn_step[3] = float(self.ids.input_turn_step3.text)

        val_feed_step[4] = float(self.ids.input_feed_step4.text)
        val_bend_step[4] = float(self.ids.input_bend_step4.text)
        val_turn_step[4] = float(self.ids.input_turn_step4.text)

        val_feed_step[5] = float(self.ids.input_feed_step5.text)
        val_bend_step[5] = float(self.ids.input_bend_step5.text)
        val_turn_step[5] = float(self.ids.input_turn_step5.text)

        val_feed_step[6] = float(self.ids.input_feed_step6.text)
        val_bend_step[6] = float(self.ids.input_bend_step6.text)
        val_turn_step[6] = float(self.ids.input_turn_step6.text)

        val_feed_step[7] = float(self.ids.input_feed_step7.text)
        val_bend_step[7] = float(self.ids.input_bend_step7.text)
        val_turn_step[7] = float(self.ids.input_turn_step7.text)

        val_feed_step[8] = float(self.ids.input_feed_step8.text)
        val_bend_step[8] = float(self.ids.input_bend_step8.text)
        val_turn_step[8] = float(self.ids.input_turn_step8.text)

        val_feed_step[9] = float(self.ids.input_feed_step9.text)
        val_bend_step[9] = float(self.ids.input_bend_step9.text)
        val_turn_step[9] = float(self.ids.input_turn_step9.text)
   
    def update_config(self):
        conf_feed_speed_step[0] = int(self.ids.input_feed_speed_step0.text)
        conf_bend_speed_step[0] = int(self.ids.input_bend_speed_step0.text)
        conf_turn_speed_step[0] = int(self.ids.input_turn_speed_step0.text)
        conf_bed_pos_step[0] = 1 if self.ids.bt_bed_pos0.text == "UP" else 0

        conf_feed_speed_step[1] = int(self.ids.input_feed_speed_step1.text)
        conf_bend_speed_step[1] = int(self.ids.input_bend_speed_step1.text)
        conf_turn_speed_step[1] = int(self.ids.input_turn_speed_step1.text)
        conf_bed_pos_step[1] = 1 if self.ids.bt_bed_pos1.text == "UP" else 0

        conf_feed_speed_step[2] = int(self.ids.input_feed_speed_step2.text)
        conf_bend_speed_step[2] = int(self.ids.input_bend_speed_step2.text)
        conf_turn_speed_step[2] = int(self.ids.input_turn_speed_step2.text)
        conf_bed_pos_step[2] = 1 if self.ids.bt_bed_pos2.text == "UP" else 0

        conf_feed_speed_step[3] = int(self.ids.input_feed_speed_step3.text)
        conf_bend_speed_step[3] = int(self.ids.input_bend_speed_step3.text)
        conf_turn_speed_step[3] = int(self.ids.input_turn_speed_step3.text)
        conf_bed_pos_step[3] = 1 if self.ids.bt_bed_pos3.text == "UP" else 0

        conf_feed_speed_step[4] = int(self.ids.input_feed_speed_step4.text)
        conf_bend_speed_step[4] = int(self.ids.input_bend_speed_step4.text)
        conf_turn_speed_step[4] = int(self.ids.input_turn_speed_step4.text)
        conf_bed_pos_step[4] = 1 if self.ids.bt_bed_pos4.text == "UP" else 0

        conf_feed_speed_step[5] = int(self.ids.input_feed_speed_step5.text)
        conf_bend_speed_step[5] = int(self.ids.input_bend_speed_step5.text)
        conf_turn_speed_step[5] = int(self.ids.input_turn_speed_step5.text)
        conf_bed_pos_step[5] = 1 if self.ids.bt_bed_pos5.text == "UP" else 0

        conf_feed_speed_step[6] = int(self.ids.input_feed_speed_step6.text)
        conf_bend_speed_step[6] = int(self.ids.input_bend_speed_step6.text)
        conf_turn_speed_step[6] = int(self.ids.input_turn_speed_step6.text)
        conf_bed_pos_step[6] = 1 if self.ids.bt_bed_pos6.text == "UP" else 0

        conf_feed_speed_step[7] = int(self.ids.input_feed_speed_step7.text)
        conf_bend_speed_step[7] = int(self.ids.input_bend_speed_step7.text)
        conf_turn_speed_step[7] = int(self.ids.input_turn_speed_step7.text)
        conf_bed_pos_step[7] = 1 if self.ids.bt_bed_pos7.text == "UP" else 0

        conf_feed_speed_step[8] = int(self.ids.input_feed_speed_step8.text)
        conf_bend_speed_step[8] = int(self.ids.input_bend_speed_step8.text)
        conf_turn_speed_step[8] = int(self.ids.input_turn_speed_step8.text)
        conf_bed_pos_step[8] = 1 if self.ids.bt_bed_pos8.text == "UP" else 0

        conf_feed_speed_step[9] = int(self.ids.input_feed_speed_step9.text)
        conf_bend_speed_step[9] = int(self.ids.input_bend_speed_step9.text)
        conf_turn_speed_step[9] = int(self.ids.input_turn_speed_step9.text)
        conf_bed_pos_step[9] = 1 if self.ids.bt_bed_pos9.text == "UP" else 0

    def choice_speed(self, movement, number):
        global flag_conn_stat
        global conf_feed_speed_step, conf_bend_speed_step, conf_turn_speed_step
        global data_base_config

        if(movement=="feed"):
            for i in range(0,10):
                if(number==i):
                    if conf_feed_speed_step[i] <= 5:
                        conf_feed_speed_step[i] += 1

        if(movement=="bend"):
            for i in range(0,10):
                if(number==i):
                    if conf_bend_speed_step[i] <= 5:
                        conf_bend_speed_step[i] += 1

        if(movement=="turn"):
            for i in range(0,10):
                if(number==i):
                    if conf_turn_speed_step[i] <= 5:
                        conf_turn_speed_step[i] += 1

        conf_feed_speed_step[conf_feed_speed_step > 5] = 1
        conf_bend_speed_step[conf_bend_speed_step > 5] = 1
        conf_turn_speed_step[conf_turn_speed_step > 5] = 1

        self.update_text_config()

    def choice_bed(self, number):
        global flag_conn_stat
        global conf_bed_pos_step
        global data_base_config 
        for i in range (0,10):       
            if(number==i):
                if conf_bed_pos_step[i] == 1:
                    conf_bed_pos_step[i] = 0
                else:
                    conf_bed_pos_step[i] = 1

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
            self.update()
            
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

        self.ids.input_feed_step0.text = str(val_feed_step[0])
        self.ids.input_bend_step0.text = str(val_bend_step[0])
        self.ids.input_turn_step0.text = str(val_turn_step[0])

        self.ids.input_feed_step1.text = str(val_feed_step[1])
        self.ids.input_bend_step1.text = str(val_bend_step[1])
        self.ids.input_turn_step1.text = str(val_turn_step[1])

        self.ids.input_feed_step2.text = str(val_feed_step[2])
        self.ids.input_bend_step2.text = str(val_bend_step[2])
        self.ids.input_turn_step2.text = str(val_turn_step[2])

        self.ids.input_feed_step3.text = str(val_feed_step[3])
        self.ids.input_bend_step3.text = str(val_bend_step[3])
        self.ids.input_turn_step3.text = str(val_turn_step[3])

        self.ids.input_feed_step4.text = str(val_feed_step[4])
        self.ids.input_bend_step4.text = str(val_bend_step[4])
        self.ids.input_turn_step4.text = str(val_turn_step[4])

        self.ids.input_feed_step5.text = str(val_feed_step[5])
        self.ids.input_bend_step5.text = str(val_bend_step[5])
        self.ids.input_turn_step5.text = str(val_turn_step[5])

        self.ids.input_feed_step6.text = str(val_feed_step[6])
        self.ids.input_bend_step6.text = str(val_bend_step[6])
        self.ids.input_turn_step6.text = str(val_turn_step[6])

        self.ids.input_feed_step7.text = str(val_feed_step[7])
        self.ids.input_bend_step7.text = str(val_bend_step[7])
        self.ids.input_turn_step7.text = str(val_turn_step[7])

        self.ids.input_feed_step8.text = str(val_feed_step[8])
        self.ids.input_bend_step8.text = str(val_bend_step[8])
        self.ids.input_turn_step8.text = str(val_turn_step[8])

        self.ids.input_feed_step9.text = str(val_feed_step[9])
        self.ids.input_bend_step9.text = str(val_bend_step[9])
        self.ids.input_turn_step9.text = str(val_turn_step[9]) 

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
            data_base_save = np.vstack((data_base_process, data_base_config))
            print(data_base_save)
            with open(disk,"wb") as f:
                np.savetxt(f, data_base_save.T, fmt="%.3f",delimiter="\t",header="Feed [mm] \t Bend [mm] \t Plane [mm] \t Feed Speed \t Bend Speed \t Plane Speed \t Bed Pos")
            print("sucessfully save data")
            toast("sucessfully save data")
        except Exception as e:
            print(e)
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

class RootScreen(ScreenManager):
    pass

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

        Builder.load_file('main.kv')
        return RootScreen()

if __name__ == '__main__':
    PipeBendingCNCApp().run()