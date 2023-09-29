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

tube_length = 6000.0
tube_diameter = 60.3
tube_thickness = 3.0

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
    screen_tube_setting = ObjectProperty(None)
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
            self.screen_manager.current = 'screen_tube_setting'
            return False

class ScreenTubeSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenTubeSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global tube_length
        global tube_diameter
        global tube_thickness

        self.ids.input_tube_length.text = str(tube_length)
        self.ids.input_tube_diameter.text = str(tube_diameter)
        self.ids.input_tube_thickness.text = str(tube_thickness)

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()

        Uc = np.linspace(0, 2 * np.pi, 32)
        Xc = np.linspace(0, tube_length, 4)

        Uc_inner = np.linspace(0, 2 * np.pi, 32)
        Xc_inner = np.linspace(0, tube_length, 4)

        Uc, Xc = np.meshgrid(Uc, Xc)
        Uc_inner, Xc_inner = np.meshgrid(Uc_inner, Xc_inner)
        
        tube_radius = tube_diameter / 2
        tube_radius_inner = (tube_diameter / 2) - tube_thickness

        Yc = tube_radius * np.cos(Uc)
        Zc = tube_radius * np.sin(Uc)

        Yc_inner = tube_radius_inner * np.cos(Uc_inner)
        Zc_inner = tube_radius_inner * np.sin(Uc_inner)

        self.ax.plot_surface(Xc, Yc, Zc, color='gray', alpha=0.8)
        self.ax.plot_surface(Xc_inner, Yc_inner, Zc_inner, color='gray')
        self.ax.set_box_aspect(aspect=(1, 1, 1))
        # self.ax.set_xlim([0, 6000])
        # self.ax.set_ylim([-100, 100])
        # self.ax.set_zlim([-100, 100])
        # self.ax.axis('off')

        self.ids.tube_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    

    def update(self):
        global tube_length
        global tube_diameter
        global tube_thickness

        try:
            self.ids.tube_illustration.clear_widgets()
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()

            tube_length = float(self.ids.input_tube_length.text)
            tube_diameter = float(self.ids.input_tube_diameter.text)
            tube_thickness = float(self.ids.input_tube_thickness.text)

            Uc = np.linspace(0, 2 * np.pi, 32)
            Xc = np.linspace(0, tube_length, 4)

            Uc_inner = np.linspace(0, 2 * np.pi, 32)
            Xc_inner = np.linspace(0, tube_length, 4)

            Uc, Xc = np.meshgrid(Uc, Xc)
            Uc_inner, Xc_inner = np.meshgrid(Uc_inner, Xc_inner)
            
            tube_radius = tube_diameter / 2
            tube_radius_inner = (tube_diameter / 2) - tube_thickness

            Yc = tube_radius * np.cos(Uc)
            Zc = tube_radius * np.sin(Uc)

            Yc_inner = tube_radius_inner * np.cos(Uc_inner)
            Zc_inner = tube_radius_inner * np.sin(Uc_inner)

            self.ax.plot_surface(Xc, Yc, Zc, color='gray', alpha=0.8)
            self.ax.plot_surface(Xc_inner, Yc_inner, Zc_inner, color='gray')
            self.ax.set_box_aspect(aspect=(1, 1, 1))
            # self.ax.set_xlim([0, 6000])
            # self.ax.set_ylim([-100, 100])
            # self.ax.set_zlim([-100, 100])
            # self.ax.axis('off')

            self.ids.tube_illustration.add_widget(FigureCanvasKivyAgg(self.fig))
        except:
            toast("error update tube illustration")

    def screen_tube_setting(self):
        self.screen_manager.current = 'screen_tube_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_data(self):
        self.screen_manager.current = 'screen_data'

    def screen_graph(self):
        self.screen_manager.current = 'screen_graph'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenMachineSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenMachineSetting, self).__init__(**kwargs)

    def screen_tube_setting(self):
        self.screen_manager.current = 'screen_tube_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_data(self):
        self.screen_manager.current = 'screen_data'

    def screen_graph(self):
        self.screen_manager.current = 'screen_graph'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenAdvancedSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenAdvancedSetting, self).__init__(**kwargs)

    def screen_tube_setting(self):
        self.screen_manager.current = 'screen_tube_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_data(self):
        self.screen_manager.current = 'screen_data'

    def screen_graph(self):
        self.screen_manager.current = 'screen_graph'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenData(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        global dt_time
        global dt_cycle
        
        super(ScreenData, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)
        Clock.schedule_interval(self.regular_check, 1)

    def regular_check(self, dt):
        global flag_run
        global flag_measure
        global flag_dongle
        global count_mounting
        global dt_time
        global dt_cycle
        global data_base
        global inject_state
        global flag_autosave_data

        global flag_run
        if(flag_run):
            pass
        else:
            pass

#         self.ids.bt_save_data.disabled = False
            
        if not DISK_ADDRESS.exists() and flag_dongle:
            try:
                print("try mounting")
                serial_file = str(DISK_ADDRESS) + "/serial.key"
                print(serial_file)
                with open(serial_file,"r") as f:
                    serial_number = f.readline()
                    if serial_number == SERIAL_NUMBER:
                        print("success, serial number is valid")
                        self.ids.bt_save_data.disabled = False
                    else:
                        print("fail, serial number is invalid")
                        self.ids.bt_save_data.disabled = True                    
            except:
                print(f"Could not mount {DISK_ADDRESS}")
                self.ids.bt_save_data.disabled = True
                count_mounting += 1
                if(count_mounting > 10):
                    flag_dongle = False 
 

    def measurement_check(self, dt):
        global dt_time
        global data_base
        global dt_current
        global dt_voltage

        voltage = np.max(np.fabs(dt_voltage))
        current = np.max(np.fabs(dt_current))
        if(current > 0.0):
            resistivity = voltage / current
        else:
            resistivity = 0
            
        std_resistivity = np.std(data_base[2, :])
        ip_decay = (np.sum(dt_voltage) / voltage ) * ((dt_cycle * dt_time)/10000)

        data_acquisition = np.array([voltage, current, resistivity, std_resistivity, ip_decay])
        data_acquisition.resize([5, 1])
        data_base = np.concatenate([data_base, data_acquisition], axis=1)

        self.ids.realtime_voltage.text = f"{voltage:.3f}"
        self.ids.realtime_current.text = f"{current:.3f}"
        self.ids.realtime_resistivity.text = f"{resistivity:.3f}"

        self.data_tables.row_data=[(f"{i + 1}", f"{data_base[0,i]:.3f}", f"{data_base[1,i]:.3f}", f"{data_base[2,i]:.3f}", f"{data_base[3,i]:.3f}", f"{data_base[4,i]:.3f}") for i in range(len(data_base[1]))]

    def inject_current(self, dt):
        global inject_state

        if(inject_state > 3):
            Clock.unschedule(self.measurement_sampling)
            inject_state = 0
            
        if(inject_state == 0):
            Clock.unschedule(self.measurement_sampling)
            if(not DEBUG):
                # GPIO.output(PIN_FWD, GPIO.LOW)
                # GPIO.output(PIN_REV, GPIO.LOW)
                GPIO.output(PIN_ENABLE, GPIO.HIGH)
                GPIO.output(PIN_POLARITY, GPIO.HIGH)
                print("not injecting current")
            
        elif(inject_state == 1):
            Clock.schedule_interval(self.measurement_sampling, (dt_cycle * dt_time) / 10000)
            if(not DEBUG):
                GPIO.output(PIN_ENABLE, GPIO.LOW)
                GPIO.output(PIN_POLARITY, GPIO.HIGH)
                print("inject positive current")
            
        elif(inject_state == 2):
            Clock.unschedule(self.measurement_sampling)
            if(not DEBUG):
                # GPIO.output(PIN_FWD, GPIO.LOW)
                # GPIO.output(PIN_REV, GPIO.LOW)
                GPIO.output(PIN_ENABLE, GPIO.HIGH)
                GPIO.output(PIN_POLARITY, GPIO.HIGH)
                print("not injecting current")
            
        elif(inject_state == 3):
            Clock.schedule_interval(self.measurement_sampling, (dt_cycle * dt_time) / 10000)
            if(not DEBUG):
                GPIO.output(PIN_ENABLE, GPIO.LOW)
                GPIO.output(PIN_POLARITY, GPIO.LOW)
                print("inject negative current")
            
        print("inject: ", inject_state)
        inject_state += 1
        
    def measurement_sampling(self, dt):
        global dt_current
        global dt_voltage
        global ads

        # Data acquisition
        dt_voltage_temp = np.zeros_like(dt_voltage)
        dt_current_temp = np.zeros_like(dt_current)

        if(not DEBUG):
            try:
                chan_c = AnalogIn(ads, ADS.P0)
                realtime_current = (chan_c.voltage - C_OFFSET) * C_GAIN
#                 ina_c = read_c(SHUNT_OHMS, MAX_EXPECTED_AMPS)
#                 ina_c.configure(ina_c.RANGE_16V, ina_c.GAIN_AUTO)
#                 dt_current_temp[:1] = ina_c.current()
                dt_current_temp[:1] = realtime_current
            except:
                toast("error read current")
                dt_current_temp[:1] = 0.0

            try:
                chan_p = AnalogIn(ads, ADS.P1)
                realtime_voltage = (chan_p.voltage - P_OFFSET) * P_GAIN
#                 ina_p = read_p(SHUNT_OHMS, MAX_EXPECTED_AMPS)
#                 ina_p.configure(ina_p.RANGE_16V, ina_p.GAIN_AUTO)
#                 dt_voltage_temp[:1] = ina_p.voltage()
                dt_voltage_temp[:1] = realtime_voltage                

            except:
                toast("error read voltage")
                dt_voltage_temp[:1] = 0.0

        dt_voltage_temp[1:] = dt_voltage[:-1]
        dt_voltage = dt_voltage_temp
        
        dt_current_temp[1:] = dt_current[:-1]
        dt_current = dt_current_temp       

    def delayed_init(self, dt):
        layout = self.ids.layout_tables
        
        self.data_tables = MDDataTable(
            use_pagination=True,
            pagination_menu_pos="auto",
            rows_num=4,
            column_data=[
                ("No.", dp(10)),
                ("Volt [V]", dp(27)),
                ("Curr [mA]", dp(27)),
                ("Resi [kOhm]", dp(27)),
                ("Std Dev Res", dp(27)),
                ("IP (R decay)", dp(27)),
            ],
        )
        layout.add_widget(self.data_tables)

    def reset_data(self):
        global data_base
        global dt_measure
        global dt_current
        global dt_voltage
        
        data_base = np.zeros([5, 1])
        dt_measure = np.zeros(6)
        dt_current = np.zeros(10)
        dt_voltage = np.zeros(10)
        
        layout = self.ids.layout_tables
        
        self.data_tables = MDDataTable(
            use_pagination=True,
            pagination_menu_pos="auto",
            rows_num=4,
            column_data=[
                ("No.", dp(10)),
                ("Volt [V]", dp(27)),
                ("Curr [mA]", dp(27)),
                ("Resi [kOhm]", dp(27)),
                ("Std Dev Res", dp(27)),
                ("IP (R decay)", dp(27)),
            ],
        )
        layout.add_widget(self.data_tables)

    def save_data(self):
        global data_base
        global dt_distance
        global dt_config
        global data_pos

        x_loc = data_pos[0, :]
        print(x_loc)

        data = data_base[2, :len(x_loc)]
        print(data)

        spaces = np.ones_like(x_loc) * dt_distance
        print(spaces)

        data_write = np.vstack((x_loc, spaces, data))
        print(data_write)

        if("WENNER (ALPHA)" in dt_config):
            mode = 1
        elif("WENNER (BETA)" in dt_config):
            mode = 1
        elif("WENNER (GAMMA)" in dt_config):
            mode = 1
        elif("POLE-POLE" in dt_config):
            mode = 2
        elif("DIPOLE-DIPOLE" in dt_config):
            mode = 3
        elif("SCHLUMBERGER" in dt_config):
            mode = 7

        try:

            now = datetime.now().strftime("/%d_%m_%Y_%H_%M_%S.dat")
            # disk = str(DISK_ADDRESS) + now
            disk = os.getcwd() + now
            head="%s \n%.2f \n%s \n%s \n0 \n1" % (now, dt_distance, mode, len(data_base.T[2]))
            foot="0 \n0 \n0 \n0 \n0"
            with open(disk,"wb") as f:
                np.savetxt(f, data_write.T, fmt="%.3f", delimiter="\t", header=head, footer=foot, comments="")
            print("sucessfully save data")
            toast("sucessfully save data")
        except:
            print("error saving data")
            toast("error saving data")

    def autosave_data(self):
        global data_base
        try:
            now = datetime.now().strftime("/%d_%m_%Y_%H_%M_%S.raw")
            cwd = os.getcwd()
            disk = cwd + now
            with open(disk,"wb") as f:
                np.savetxt(f, data_base.T, fmt="%.3f",delimiter="\t",header="Volt [V] \t Curr [mA] \t Res [kOhm] \t StdDev \t IP [R decay]")
            print("sucessfully auto save data")
            # toast("sucessfully save data")
        except:
            print("error auto saving data")
            # toast("error saving data")

    def measure(self):
        global flag_run
        if(flag_run):
            flag_run = False
        else:
            flag_run = True

    def screen_tube_setting(self):
        self.screen_manager.current = 'screen_tube_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_data(self):
        self.screen_manager.current = 'screen_data'

    def screen_graph(self):
        self.screen_manager.current = 'screen_graph'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h now")

class ScreenGraph(BoxLayout):
    screen_manager = ObjectProperty(None)
    global flag_run

    def __init__(self, **kwargs):
        super(ScreenGraph, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)

    def delayed_init(self, dt):
        global tube_length
        global tube_diameter
        global tube_thickness

        self.ids.input_tube_length.text = str(tube_length)
        self.ids.input_tube_diameter.text = str(tube_diameter)
        self.ids.input_tube_thickness.text = str(tube_thickness)

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()

        # theta: poloidal angle; phi: toroidal angle 
        theta = np.linspace(0, 2*np.pi, 100) 
        phi   = np.linspace(0, 2*np.pi, 100) 
        theta, phi = np.meshgrid(theta, phi) 

        # R0: major radius; a: minor radius 
        R0, a = 2., 1. 

        # torus parametrization 
        x = (R0 + a*np.cos(theta)) * np.cos(phi) 
        y = (R0 + a*np.cos(theta)) * np.sin(phi) 
        z = a * np.sin(theta) 

        # "cut-off" half of the torus using transparent colors 
        c = np.full(x.shape + (4,), [0, 0, 0.85, 1])  # shape (nx, ny, 4)
        c[x>0, -1] = 0 # set these to transparent 

        self.ax.plot_surface(x, y, z, facecolors=c, rstride=5, cstride=5)
        # self.ax.set_box_aspect(aspect=(1, 1, 1))
        self.ax.set_aspect('equal')
        # self.ax.set_xlim([0, 6000])
        # self.ax.set_ylim([-100, 100])
        # self.ax.set_zlim([-100, 100])
        # self.ax.axis('off')

        self.ids.tube_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))    

    def update(self):
        global tube_length
        global tube_diameter
        global tube_thickness

        try:
            self.ids.tube_bended_illustration.clear_widgets()
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()

            tube_length = float(self.ids.input_tube_length.text)
            tube_diameter = float(self.ids.input_tube_diameter.text)
            tube_thickness = float(self.ids.input_tube_thickness.text)

            Uc = np.linspace(0, 2 * np.pi, 32)
            Xc = np.linspace(0, tube_length, 4)

            Uc_inner = np.linspace(0, 2 * np.pi, 32)
            Xc_inner = np.linspace(0, tube_length, 4)

            Uc, Xc = np.meshgrid(Uc, Xc)
            Uc_inner, Xc_inner = np.meshgrid(Uc_inner, Xc_inner)
            
            tube_radius = tube_diameter / 2
            tube_radius_inner = (tube_diameter / 2) - tube_thickness

            Yc = tube_radius * np.cos(Uc)
            Zc = tube_radius * np.sin(Uc)

            Yc_inner = tube_radius_inner * np.cos(Uc_inner)
            Zc_inner = tube_radius_inner * np.sin(Uc_inner)

            self.ax.plot_surface(Xc, Yc, Zc, color='gray', alpha=0.8)
            self.ax.plot_surface(Xc_inner, Yc_inner, Zc_inner, color='gray')
            # self.ax.set_box_aspect(aspect=(1, 1, 1))
            self.ax.set_aspect('equal')
            # self.ax.set_xlim([0, 6000])
            # self.ax.set_ylim([-100, 100])
            # self.ax.set_zlim([-100, 100])
            # self.ax.axis('off')

            self.ids.tube_bended_illustration.add_widget(FigureCanvasKivyAgg(self.fig))
        except:
            toast("error update tube illustration")

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
                
    def screen_tube_setting(self):
        self.screen_manager.current = 'screen_tube_setting'

    def screen_machine_setting(self):
        self.screen_manager.current = 'screen_machine_setting'

    def screen_advanced_setting(self):
        self.screen_manager.current = 'screen_advanced_setting'

    def screen_data(self):
        self.screen_manager.current = 'screen_data'

    def screen_graph(self):
        self.screen_manager.current = 'screen_graph'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h 1")

class PipeBendingCNCApp(MDApp):
    def build(self):
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Blue"
        self.icon = 'asset/logo.ico'
        Window.fullscreen = 'auto'
        Window.borderless = True
        # Window.size = 1024, 600
        Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')

        return screen


if __name__ == '__main__':
    PipeBendingCNCApp().run()