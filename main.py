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

USERNAME = 'labtek'
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

    def screen_operate(self):
        self.screen_manager.current = 'screen_operate'

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

    def screen_operate(self):
        self.screen_manager.current = 'screen_operate'

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

    def screen_operate(self):
        self.screen_manager.current = 'screen_operate'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenOperate(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        global dt_time
        global dt_cycle
        
        super(ScreenOperate, self).__init__(**kwargs)
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

        step_length[0] = 100.
        step_bend[0] = 90.
        step_turn[0] = 0.

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()

        # straight pipe
        Uc = np.linspace(0, 2 * np.pi, 32)
        Xc = np.linspace(0, step_length[0], 4)
        Uc, Xc = np.meshgrid(Uc, Xc)
        pipe_radius = pipe_diameter / 2
        Yc = pipe_radius * np.cos(Uc)
        Zc = pipe_radius * np.sin(Uc)

        # theta: poloidal angle; phi: toroidal angle 
        bend_angle = step_bend[0] / 180 * np.pi
        theta = np.linspace(0, 2*np.pi, 100) 
        phi   = np.linspace(0, bend_angle, 100) 
        theta, phi = np.meshgrid(theta, phi) 

        # R0: major radius; a: minor radius 
        R0, a = machine_die_radius, pipe_radius 

        # torus parametrization 
        y = (R0 + a*np.cos(theta)) * np.cos(phi) - machine_die_radius
        x = (R0 + a*np.cos(theta)) * np.sin(phi) + step_length[0]
        z = a * np.sin(theta) 

        self.ax.plot_surface(Xc, Yc, Zc, color='gray')
        self.ax.plot_surface(x, y, z, color='gray')
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

    def screen_operate(self):
        self.screen_manager.current = 'screen_operate'

    def screen_compile(self):
        self.screen_manager.current = 'screen_compile'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenCompile(BoxLayout):
    screen_manager = ObjectProperty(None)
    global flag_run

    def __init__(self, **kwargs):
        super(ScreenCompile, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global pipe_diameter
        global machine_die_radius

        global step_length
        global step_bend
        global step_turn

        # step_length[0] = 100.
        # step_bend[0] = 90.
        # step_turn[0] = 0.

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

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()

        offset_length = step_length
        bend_angle = step_bend / 180 * np.pi
        turn_angle = step_turn / 180 * np.pi
        
        X0, Y0, Z0 = self.simulate(offset_length[0], bend_angle[0], turn_angle[0])

        self.ax.plot_surface(X0, Y0, Z0, color='red', alpha=0.5)
        # self.ax.set_box_aspect(aspect=(1, 1, 1))
        self.ax.set_aspect('equal')
        # self.ax.set_xlim([0, 6000])
        # self.ax.set_ylim([-100, 100])
        # self.ax.set_zlim([-100, 100])
        # self.ax.axis('off')
        self.ids.pipe_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    

    def update(self):
        global step_length
        global step_bend
        global step_turn
        
        try:
            self.ids.pipe_bended_illustration.clear_widgets()
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

            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()

            offset_length = step_length
            bend_angle = step_bend / 180 * np.pi
            turn_angle = step_turn / 180 * np.pi
            
            X0, Y0, Z0 = self.simulate(offset_length[0], bend_angle[0], turn_angle[0])
            X1, Y1, Z1 = self.simulate(offset_length[1], bend_angle[1], turn_angle[1])
            X2, Y2, Z2 = self.simulate(offset_length[2], bend_angle[2], turn_angle[2])
            X3, Y3, Z3 = self.simulate(offset_length[3], bend_angle[3], turn_angle[3])

            self.ax.plot_surface(X0, Y0, Z0, color='red', alpha=0.5)
            self.ax.plot_surface(X1, Y1, Z1, color='green', alpha=0.5)
            self.ax.plot_surface(X2, Y2, Z2, color='blue', alpha=0.5)
            self.ax.plot_surface(X3, Y3, Z3, color='gray', alpha=0.5)
            # self.ax.set_box_aspect(aspect=(1, 1, 1))
            self.ax.set_aspect('equal')
            # self.ax.set_xlim([0, 6000])
            # self.ax.set_ylim([-100, 100])
            # self.ax.set_zlim([-100, 100])
            # self.ax.axis('off')
            self.ids.pipe_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    
        except:
            toast("error update pipe illustration")

    def simulate(self, offset_length, bend_angle, turn_angle):
        global pipe_diameter
        global machine_die_radius

        pipe_radius = pipe_diameter / 2
        # step 1 : create straight pipe
        # straight pipe
        Ua = np.linspace(0, 2 * np.pi, 30)
        Ya = np.linspace(0, offset_length, 5)
        Ua, Ya = np.meshgrid(Ua, Ya)
        
        Xa = pipe_radius * np.cos(Ua) - machine_die_radius
        Ya = -Ya + offset_length
        Za = pipe_radius * np.sin(Ua)

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

    def save_graph(self):
        try:
            now = datetime.now().strftime("/%d_%m_%Y_%H_%M_%S.jpg")
            disk = str(DISK_ADDRESS) + now
            self.fig.savefig(disk)
            print("sucessfully save graph")
            toast("sucessfully save graph")
        except:
            print("error saving graph")
            toast("error saving graph")
                
    def autosave_graph(self):
        try:
            now = datetime.now().strftime("/%d_%m_%Y_%H_%M_%S.jpg")
            cwd = os.getcwd()
            disk = cwd + now
            self.fig.savefig(disk)
            print("sucessfully auto save graph")
            # toast("sucessfully save graph")
        except:
            print("error auto saving graph")
            # toast("error saving graph")
                
    def screen_pipe_setting(self):
        self.screen_manager.current = 'screen_pipe_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_operate(self):
        self.screen_manager.current = 'screen_operate'

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