import numpy as np
import kivy
import sys
import os
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.datatables import MDDataTable
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.filemanager import MDFileManager
from kivy.clock import Clock
from kivy.config import Config
from kivy.metrics import dp
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from matplotlib.ticker import AutoMinorLocator
from datetime import datetime
from pathlib import Path
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
import time

plt.style.use('bmh')

colors = {
    "Red": {
        "A200": "#EE2222",
        "A500": "#EE2222",
        "A700": "#EE2222",
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

DEBUG = True
    
STEPS = 51
# MAX_POINT_WENNER = 500
MAX_POINT = 10000
ELECTRODES_NUM = 48

PIN_ENABLE = 23 #16
PIN_POLARITY = 24 #18

C_OFFSET = 2.52
C_GAIN = 5.0

P_OFFSET = 0.00
P_GAIN = 1.0
# SHUNT_OHMS = 0.1
# MAX_EXPECTED_AMPS = 0.1
# 
# PIN_FWD = 16
# PIN_REV = 18

USERNAME = 'pipe_bending_cnc'
# DISK_ADDRESS = Path("/media/pi/RESDONGLE/")
DISK_ADDRESS = Path("/media/" + USERNAME + "/RESDONGLE/")
SERIAL_NUMBER = "2301212112233412"

pipe_length = 6000.
pipe_diameter = 60.3
pipe_thickness = 3.

machine_die_radius = 100.

step_length = np.zeros(10)
step_bend = np.zeros(10)
step_turn = np.zeros(10)

checks_mode = []
checks_config = []
dt_mode = ""
dt_config = ""
dt_distance = 1
dt_constant = 1
dt_time = 500
dt_cycle = 1

dt_measure = np.zeros(6)
dt_current = np.zeros(10)
dt_voltage = np.zeros(10)
flag_run = False
flag_measure = False
flag_dongle = True
flag_autosave_data = False
flag_autosave_graph = False

count_mounting = 0
inject_state = 0

class ScreenSplash(BoxLayout):
    screen_manager = ObjectProperty(None)
    screen_pipe_setting = ObjectProperty(None)
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
            self.screen_manager.current = 'screen_pipe_setting'
            return False

class ScreenPipeSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenPipeSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global pipe_length
        global pipe_diameter
        global pipe_thickness

        self.ids.input_pipe_length.text = str(pipe_length)
        self.ids.input_pipe_diameter.text = str(pipe_diameter)
        self.ids.input_pipe_thickness.text = str(pipe_thickness)

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()

        Xr, Yr, Zr = self.simulate(pipe_length, pipe_diameter, pipe_thickness)

        self.ax.plot_surface(Xr, Yr, Zr, color='gray')
        self.ax.set_box_aspect(aspect=(1, 1, 1))
        # self.ax.set_xlim([0, 6000])
        # self.ax.set_ylim([-100, 100])
        # self.ax.set_zlim([-100, 100])
        # self.ax.axis('off')

        self.ids.pipe_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    

    def update(self):
        global pipe_length
        global pipe_diameter
        global pipe_thickness

        try:
            self.ids.pipe_illustration.clear_widgets()
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()

            pipe_length = float(self.ids.input_pipe_length.text)
            pipe_diameter = float(self.ids.input_pipe_diameter.text)
            pipe_thickness = float(self.ids.input_pipe_thickness.text)

            Xr, Yr, Zr = self.simulate(pipe_length, pipe_diameter, pipe_thickness)

            self.ax.plot_surface(Xr, Yr, Zr, color='gray')
            self.ax.set_box_aspect(aspect=(1, 1, 1))
            # self.ax.set_xlim([0, 6000])
            # self.ax.set_ylim([-100, 100])
            # self.ax.set_zlim([-100, 100])
            # self.ax.axis('off')

            self.ids.pipe_illustration.add_widget(FigureCanvasKivyAgg(self.fig))
        except:
            toast("error update pipe illustration")

    def simulate(self, pipe_length, pipe_diameter, pipe_thickness):
        Uc = np.linspace(0, 2 * np.pi, 50)
        Xc = np.linspace(0, pipe_length, 2)

        Uc_inner = np.linspace(0, 2 * np.pi, 50)
        Xc_inner = np.linspace(0, pipe_length, 2)

        Uc, Xc = np.meshgrid(Uc, Xc)
        Uc_inner, Xc_inner = np.meshgrid(Uc_inner, Xc_inner)
        
        pipe_radius = pipe_diameter / 2
        pipe_radius_inner = (pipe_diameter / 2) - pipe_thickness

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
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenMachineSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenMachineSetting, self).__init__(**kwargs)

    def update(self):
        global machine_die_radius

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
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenAdvancedSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenAdvancedSetting, self).__init__(**kwargs)

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
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenOperateManual(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):      
        super(ScreenOperateManual, self).__init__(**kwargs)

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
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenOperateAuto(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        global dt_time
        global dt_cycle
        
        super(ScreenOperateAuto, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager, select_path=self.select_path
        )

    def file_manager_open(self):
        self.file_manager.show(os.path.expanduser("~"))  # output manager to the screen
        self.manager_open = True

    def select_path(self, path: str):
        '''
        It will be called when you click on the file name
        or the catalog selection button.

        :param path: path to the selected directory or file;
        '''

        self.ids.input_file_dir.text = path
        self.exit_manager()
        toast(path)

    def exit_manager(self, *args):
        '''Called when the user reaches the root of the directory tree.'''

        self.manager_open = False
        self.file_manager.close()

    def events(self, instance, keyboard, keycode, text, modifiers):
        '''Called when buttons are pressed on the mobile device.'''

        if keyboard in (1001, 27):
            if self.manager_open:
                self.file_manager.back()
        return True
    
    def delayed_init(self, dt):
        global pipe_diameter
        global machine_die_radius

        global step_length
        global step_bend
        global step_turn

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()

        offset_length = step_length
        bend_angle = step_bend / 180 * np.pi
        turn_angle = step_turn / 180 * np.pi
        pipe_radius = pipe_diameter / 2

        Uo = np.linspace(0, 2 * np.pi, 30)
        Yo = np.linspace(0, 0, 5)
        Uo, Yo = np.meshgrid(Uo, Yo)
        Xo = pipe_radius * np.cos(Uo) - machine_die_radius
        Zo = pipe_radius * np.sin(Uo)

        screen_compile = ScreenCompile()
        
        X0, Y0, Z0 = screen_compile.simulate(Xo, Yo, Zo, offset_length[0], bend_angle[0], turn_angle[0])

        self.ax.plot_surface(X0, Y0, Z0, color='gray', alpha=1)
        # self.ax.set_box_aspect(aspect=(1, 1, 1))
        self.ax.set_aspect('equal')
        # self.ax.set_xlim([0, 6000])
        # self.ax.set_ylim([-100, 100])
        # self.ax.set_zlim([-100, 100])
        # self.ax.axis('off')
        self.ids.pipe_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    
   

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
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenCompile(BoxLayout):
    screen_manager = ObjectProperty(None)
    global flag_run
    global step_length
    global step_bend
    global step_turn

    global pipe_diameter
    global machine_die_radius

    def __init__(self, **kwargs):
        super(ScreenCompile, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        self.reset()

    def update(self):
        try:
            step_length[0] = float(self.ids.input_step_length0.text)
            step_bend[0] = float(self.ids.input_step_bend0.text)
            step_turn[0] = float(self.ids.input_step_turn0.text)

            step_length[1] = float(self.ids.input_step_length1.text)
            step_bend[1] = float(self.ids.input_step_bend1.text)
            step_turn[1] = float(self.ids.input_step_turn1.text)

            step_length[2] = float(self.ids.input_step_length2.text)
            step_bend[2] = float(self.ids.input_step_bend2.text)
            step_turn[2] = float(self.ids.input_step_turn2.text)

            step_length[3] = float(self.ids.input_step_length3.text)
            step_bend[3] = float(self.ids.input_step_bend3.text)
            step_turn[3] = float(self.ids.input_step_turn3.text)

            step_length[4] = float(self.ids.input_step_length4.text)
            step_bend[4] = float(self.ids.input_step_bend4.text)
            step_turn[4] = float(self.ids.input_step_turn4.text)

            step_length[5] = float(self.ids.input_step_length5.text)
            step_bend[5] = float(self.ids.input_step_bend5.text)
            step_turn[5] = float(self.ids.input_step_turn5.text)

            step_length[6] = float(self.ids.input_step_length6.text)
            step_bend[6] = float(self.ids.input_step_bend6.text)
            step_turn[6] = float(self.ids.input_step_turn6.text)

            step_length[7] = float(self.ids.input_step_length7.text)
            step_bend[7] = float(self.ids.input_step_bend7.text)
            step_turn[7] = float(self.ids.input_step_turn7.text)

            step_length[8] = float(self.ids.input_step_length8.text)
            step_bend[8] = float(self.ids.input_step_bend8.text)
            step_turn[8] = float(self.ids.input_step_turn8.text)

            step_length[9] = float(self.ids.input_step_length9.text)
            step_bend[9] = float(self.ids.input_step_bend9.text)
            step_turn[9] = float(self.ids.input_step_turn9.text)

            self.ids.pipe_bended_illustration.clear_widgets()

            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()

            offset_length = step_length
            bend_angle = step_bend / 180 * np.pi
            turn_angle = step_turn / 180 * np.pi
            pipe_radius = pipe_diameter / 2

            Uo = np.linspace(0, 2 * np.pi, 30)
            Yo = np.linspace(0, 0, 5)
            Uo, Yo = np.meshgrid(Uo, Yo)
            Xo = pipe_radius * np.cos(Uo) - machine_die_radius
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
            self.ids.pipe_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    
        except:
            toast("error update pipe illustration")

    def simulate(self, prev_X, prev_Y, prev_Z, offset_length, bend_angle, turn_angle):
        pipe_radius = pipe_diameter / 2
        # step 1 : create straight pipe
        # straight pipe
        Ua = np.linspace(0, 2 * np.pi, 30)
        Ya = np.linspace(offset_length, 0, 5)
        Ua, Ya = np.meshgrid(Ua, Ya)
        Xa = pipe_radius * np.cos(Ua) - machine_die_radius
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
        Xb = (machine_die_radius + pipe_radius * np.cos(theta)) * -np.cos(phi)
        Yb = (machine_die_radius + pipe_radius * np.cos(theta)) * -np.sin(phi)
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
        Xe = Xd + machine_die_radius
        Ze = Zd
        # rotate
        Xf = np.cos(turn_angle) * Xe + -np.sin(turn_angle) * Ze
        Zf = np.sin(turn_angle) * Xe + np.cos(turn_angle) * Ze
        # translate back
        Xf = Xf - machine_die_radius
        Yf = Yd

        return Xf, Yf, Zf

    def reset(self):
        step_length = np.zeros(10)
        step_bend = np.zeros(10)
        step_turn = np.zeros(10)

        self.ids.input_step_length0.text = str(step_length[0])
        self.ids.input_step_bend0.text = str(step_bend[0])
        self.ids.input_step_turn0.text = str(step_turn[0])

        self.ids.input_step_length1.text = str(step_length[1])
        self.ids.input_step_bend1.text = str(step_bend[1])
        self.ids.input_step_turn1.text = str(step_turn[1])

        self.ids.input_step_length2.text = str(step_length[2])
        self.ids.input_step_bend2.text = str(step_bend[2])
        self.ids.input_step_turn2.text = str(step_turn[2])

        self.ids.input_step_length3.text = str(step_length[3])
        self.ids.input_step_bend3.text = str(step_bend[3])
        self.ids.input_step_turn3.text = str(step_turn[3])

        self.ids.input_step_length4.text = str(step_length[4])
        self.ids.input_step_bend4.text = str(step_bend[4])
        self.ids.input_step_turn4.text = str(step_turn[4])

        self.ids.input_step_length5.text = str(step_length[5])
        self.ids.input_step_bend5.text = str(step_bend[5])
        self.ids.input_step_turn5.text = str(step_turn[5])

        self.ids.input_step_length6.text = str(step_length[6])
        self.ids.input_step_bend6.text = str(step_bend[6])
        self.ids.input_step_turn6.text = str(step_turn[6])

        self.ids.input_step_length7.text = str(step_length[7])
        self.ids.input_step_bend7.text = str(step_bend[7])
        self.ids.input_step_turn7.text = str(step_turn[7])

        self.ids.input_step_length8.text = str(step_length[8])
        self.ids.input_step_bend8.text = str(step_bend[8])
        self.ids.input_step_turn8.text = str(step_turn[8])

        self.ids.input_step_length9.text = str(step_length[9])
        self.ids.input_step_bend9.text = str(step_bend[9])
        self.ids.input_step_turn9.text = str(step_turn[9]) 

        self.update()

    def save(self):
        try:
            now = datetime.now().strftime("/%d_%m_%Y_%H_%M_%S.jpg")
            disk = str(DISK_ADDRESS) + now
            self.fig.savefig(disk)
            print("sucessfully save graph")
            toast("sucessfully save graph")
        except:
            print("error saving graph")
            toast("error saving graph")
                
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
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h 1")

class PipeBendingCNCApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Blue"
        self.icon = 'asset/logo.ico'
        Window.fullscreen = 'auto'
        Window.borderless = True
        # Window.size = 1366, 768
        Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')

        return screen


if __name__ == '__main__':
    PipeBendingCNCApp().run()