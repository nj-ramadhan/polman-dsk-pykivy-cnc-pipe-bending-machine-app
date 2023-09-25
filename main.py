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
        "200": "#EE2222",
        "500": "#EE2222",
        "700": "#EE2222",
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

if(not DEBUG):
    # GPIO control and sensor acquisiton
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import RPi.GPIO as GPIO
    import RPi.GPIO as GPIO
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
#     from ina219c import INA219 as read_c
#     from ina219p import INA219 as read_p

    GPIO.cleanup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_ENABLE, GPIO.OUT)
    GPIO.setup(PIN_POLARITY, GPIO.OUT)

# x_datum = np.zeros(MAX_POINT)
# y_datum = np.zeros(MAX_POINT)
x_electrode = np.zeros((4, MAX_POINT))
n_electrode = np.zeros((ELECTRODES_NUM, STEPS))
c_electrode = np.array(["#196BA5","#FF0000","#FFDD00","#00FF00","#00FFDD"])
l_electrode = np.array(["Datum","C1","C2","P1","P2"])
data_base = np.zeros([5, 1])
data_pos = np.zeros([2, 1])
data_pos = np.zeros([2, 1])

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
    screen_setting = ObjectProperty(None)
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
            self.screen_manager.current = 'screen_setting'
            return False

class ScreenSetting(BoxLayout):
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScreenSetting, self).__init__(**kwargs)
        Clock.schedule_once(self.delayed_init)
        Clock.schedule_interval(self.regular_check, 2)

    def regular_check(self, dt):
        global flag_run
        if(flag_run):
            self.ids.bt_measure.text = "STOP MEASUREMENT"
            self.ids.bt_measure.md_bg_color = "#A50000"
        else:
            self.ids.bt_measure.text = "RUN MEASUREMENT"
            self.ids.bt_measure.md_bg_color = "#196BA5"

    def delayed_init(self, dt):
        self.ids.mode_ves.active = True

        self.fig, self.ax = plt.subplots()
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()
        l, b, w, h = self.ax.get_position().bounds
        self.ax.set_position(pos=[l, b + 0.3*h, w, h*0.7])
        
        self.ax.set_xlabel("distance [m]", fontsize=10)
        self.ax.set_ylabel("n", fontsize=10)

        self.ids.layout_illustration.add_widget(FigureCanvasKivyAgg(self.fig))

    def illustrate(self):
        global dt_mode
        global dt_config
        global dt_distance
        global dt_constant
        global dt_time
        global dt_cycle
        global x_datum
        global y_datum
        global data_pos

        dt_distance = self.ids.slider_distance.value
        dt_constant = self.ids.slider_constant.value
        dt_time = self.ids.slider_time.value
        dt_cycle = int(self.ids.slider_cycle.value)

        self.fig, self.ax = plt.subplots()
        self.ids.layout_illustration.remove_widget(FigureCanvasKivyAgg(self.fig))
        x_datum = np.zeros(MAX_POINT)
        y_datum = np.zeros(MAX_POINT)
        # x_datum = np.zeros(MAX_POINT)
        # y_datum = np.zeros(MAX_POINT)

        if("WENNER (ALPHA)" in dt_config):
            num_step = 0
            num_trial = 1
            for multiplier in range(dt_constant):
                for pos_el in range(ELECTRODES_NUM - 3 * num_trial):
                    x_electrode[0, num_step] = pos_el
                    x_electrode[1, num_step] = num_trial + x_electrode[0, num_step]
                    x_electrode[2, num_step] = num_trial + x_electrode[1, num_step]
                    x_electrode[3, num_step] = num_trial + x_electrode[2, num_step]
                    x_datum[num_step] = (x_electrode[1, num_step] + (x_electrode[2, num_step] - x_electrode[1, num_step])/2) * dt_distance
                    y_datum[num_step] = (multiplier + 1) * dt_distance
                    
                    num_step += 1

                num_trial += 1

        elif("WENNER (BETA)" in dt_config):
            num_step = 0
            num_trial = 1
            for multiplier in range(dt_constant):
                for pos_el in range(ELECTRODES_NUM - 3 * num_trial):
                    x_electrode[0, num_step] = pos_el
                    x_electrode[1, num_step] = num_trial + x_electrode[0, num_step]
                    x_electrode[2, num_step] = num_trial + x_electrode[1, num_step]
                    x_electrode[3, num_step] = num_trial + x_electrode[2, num_step]
                    x_datum[num_step] = (x_electrode[1, num_step] + (x_electrode[2, num_step] - x_electrode[1, num_step])/2) * dt_distance
                    y_datum[num_step] = (multiplier + 1) * dt_distance
                    
                    num_step += 1

                num_trial += 1

        if("WENNER (GAMMA)" in dt_config):
            num_step = 0
            num_trial = 1
            for multiplier in range(dt_constant):
                for pos_el in range(ELECTRODES_NUM - 3 * num_trial):
                    x_electrode[0, num_step] = pos_el
                    x_electrode[1, num_step] = num_trial + x_electrode[0, num_step]
                    x_electrode[2, num_step] = num_trial + x_electrode[1, num_step]
                    x_electrode[3, num_step] = num_trial + x_electrode[2, num_step]
                    x_datum[num_step] = (x_electrode[1, num_step] + (x_electrode[2, num_step] - x_electrode[1, num_step])/2) * dt_distance
                    y_datum[num_step] = (multiplier + 1) * dt_distance
                    
                    num_step += 1

                num_trial += 1

        elif("SCHLUMBERGER" in dt_config):
            num_step = 0
            num_trial = 1
            for multiplier in range(dt_constant):
                for pos_el in range(ELECTRODES_NUM - 3 * num_trial):
                    x_electrode[0, num_step] = pos_el
                    x_electrode[1, num_step] = num_trial + x_electrode[0, num_step]
                    x_electrode[2, num_step] = num_trial + x_electrode[1, num_step]
                    x_electrode[3, num_step] = num_trial + x_electrode[2, num_step]
                    x_datum[num_step] = (x_electrode[1, num_step] + (x_electrode[2, num_step] - x_electrode[1, num_step])/2) * dt_distance
                    y_datum[num_step] = (multiplier + 1) * dt_distance
                    
                    num_step += 1

                num_trial += 1

        elif("DIPOLE-DIPOLE" in dt_config):
            nmax_available = 0
            if(ELECTRODES_NUM % 2) != 0:
                if(dt_constant > (ELECTRODES_NUM - 3) / 2):
                    nmax_available = (ELECTRODES_NUM - 3) / 2
                else:
                    nmax_available = dt_constant
            else:
                if(dt_constant > (ELECTRODES_NUM - 3) / 2):
                    nmax_available = round((ELECTRODES_NUM - 3) / 2)
                else:
                    nmax_available = dt_constant

            num_datum = 0
            count_datum = 0      
            for i in range(nmax_available):
                for j in range(ELECTRODES_NUM - 1 - i * 2):
                    num_datum = num_datum + j
                count_datum = count_datum + num_datum
                num_datum = 0     

            num_step = 1
            num_trial = 1
            for i in range(nmax_available):
                for j in range(ELECTRODES_NUM - 1 - i * 2):
                    for k in range(ELECTRODES_NUM - i * 2 - j):
                        x_electrode[1, num_step] = j
                        x_electrode[0, num_step] = j + 1 + (i - 1)
                        x_electrode[2, num_step] = num_trial + x_electrode[0, num_step]
                        x_electrode[3, num_step] = i + x_electrode[2, num_step]
                        x_datum[num_step] = (x_electrode[0, num_step] + (x_electrode[2, num_step] - x_electrode[0, num_step])/2) * dt_distance
                        y_datum[num_step] = (i + 1) * dt_distance
                        
                        num_step += 1
                        num_trial += 1

                    num_trial = 0
        else:
            pass

        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()
        l, b, w, h = self.ax.get_position().bounds
        self.ax.set_position(pos=[l, b + 0.3*h, w*0.9, h*0.7])
        self.ax.set_xlabel("distance [m]", fontsize=10)
        self.ax.set_ylabel("n", fontsize=10)
       
        self.ax.set_facecolor("#eeeeee")
        
        x_data = np.trim_zeros(x_datum)
        y_data = np.trim_zeros(y_datum)
        # x_data = x_datum[np.array([x.size>0 for x in x_datum])]
        # y_data = y_datum[np.array([y.size>0 for y in y_datum])]
        data_pos = np.array([x_data, y_data])

        #datum location
        self.ax.scatter(x_data, y_data, c=c_electrode[0], label=l_electrode[0], marker='.')

        #electrode location
        self.ax.scatter(x_electrode[0,0]*dt_distance , 0, c=c_electrode[1], label=l_electrode[1], marker=7)
        self.ax.scatter(x_electrode[1,0]*dt_distance , 0, c=c_electrode[2], label=l_electrode[2], marker=7)
        self.ax.scatter(x_electrode[2,0]*dt_distance , 0, c=c_electrode[3], label=l_electrode[3], marker=7)
        self.ax.scatter(x_electrode[3,0]*dt_distance , 0, c=c_electrode[4], label=l_electrode[4], marker=7)

        self.ax.invert_yaxis()
        self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), title="Electrode")         
        self.ids.layout_illustration.clear_widgets()
        self.ids.layout_illustration.add_widget(FigureCanvasKivyAgg(self.fig))

    def measure(self):
        global flag_run

        if(flag_run):
            flag_run = False
        else:
            flag_run = True

    def checkbox_mode_click(self, instance, value, waves):
        global checks_mode
        global dt_mode
        
        if value == True:
            checks_mode.append(waves)
            modes = ''
            for x in checks_mode:
                modes = f'{modes} {x}'
            self.ids.output_mode_label.text = f'{modes} MODE CHOSEN'
        else:
            checks_mode.remove(waves)
            modes = ''
            for x in checks_mode:
                modes = f'{modes} {x}'
            self.ids.output_mode_label.text = ''
        
        dt_mode = modes

    def checkbox_config_click(self, instance, value, waves):
        global checks_config
        global dt_config

        if value == True:
            checks_config.append(waves)
            configs = ''
            for x in checks_config:
                configs = f'{configs} {x}'
            self.ids.output_config_label.text = f'{configs} CONFIGURATION CHOSEN'
        else:
            checks_config.remove(waves)
            configs = ''
            for x in checks_config:
                configs = f'{configs} {x}'
            self.ids.output_config_label.text = ''
        
        dt_config = configs

    def screen_setting(self):
        self.screen_manager.current = 'screen_setting'

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

        if(flag_run):
            self.ids.bt_measure.text = "STOP MEASUREMENT"
            self.ids.bt_measure.md_bg_color = "#A50000"
            # Clock.schedule_interval(self.inject_current, dt_time / 1000)
            # Clock.schedule_interval(self.measurement_sampling, dt_time / 10000)
            flag_autosave_data = True

            if("(VES) VERTICAL ELECTRICAL SOUNDING" in dt_mode):
                if(flag_measure == False):
                    Clock.schedule_interval(self.measurement_check, ((4 * dt_cycle * dt_time) / 1000))
                    Clock.schedule_interval(self.inject_current, ((dt_cycle * dt_time)  / 1000))
                
                flag_measure = True
        
            elif("(SP) SELF POTENTIAL" in dt_mode):
                if(flag_measure == False):
                    Clock.schedule_interval(self.measurement_check, ((4 * dt_cycle * dt_time) / 1000))
                
                flag_measure = True
                
            elif("(R) RESISTIVITY" in dt_mode):
                if(flag_measure == False):
                    Clock.schedule_interval(self.measurement_check, ((4 * dt_cycle * dt_time) / 1000))
                    Clock.schedule_interval(self.inject_current, ((dt_cycle * dt_time)  / 1000))
                
                flag_measure = True
                
            elif("(R+IP) INDUCED POLARIZATION" in dt_mode):
                if(flag_measure == False):
                    Clock.schedule_interval(self.measurement_check, ((4 * dt_cycle * dt_time) / 1000))
                    Clock.schedule_interval(self.inject_current, ((dt_cycle * dt_time)  / 1000))
                
                flag_measure = True                        
            else:
                pass
            

        else:
            self.ids.bt_measure.text = "RUN MEASUREMENT"
            self.ids.bt_measure.md_bg_color = "#196BA5"
            Clock.unschedule(self.measurement_check)
            Clock.unschedule(self.inject_current)
            inject_state = 0
            flag_measure = False
            if(not DEBUG):
                # GPIO.output(PIN_FWD, GPIO.LOW)
                # GPIO.output(PIN_REV, GPIO.LOW)
                GPIO.output(PIN_ENABLE, GPIO.HIGH)
                GPIO.output(PIN_POLARITY, GPIO.HIGH)
            if(flag_autosave_data):
                self.autosave_data()
                flag_autosave_data = False

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

    def screen_setting(self):
        self.screen_manager.current = 'screen_setting'

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
        Clock.schedule_interval(self.regular_check, 2)

    def regular_check(self, dt):
        global flag_run
        global flag_dongle
        global count_mounting
        global dt_time
        global data_base
        global flag_autosave_graph

        if(flag_run):
            self.ids.bt_measure.text = "STOP MEASUREMENT"
            self.ids.bt_measure.md_bg_color = "#A50000"
            Clock.schedule_interval(self.measurement_check, dt_time / 100)
            flag_autosave_graph = True
        else:
            self.ids.bt_measure.text = "RUN MEASUREMENT"
            self.ids.bt_measure.md_bg_color = "#196BA5"
            Clock.unschedule(self.measurement_check)
            if(flag_autosave_graph):
                self.autosave_graph()
                flag_autosave_graph = False  
        
        if not DISK_ADDRESS.exists() and flag_dongle:
            try:
                print("try mounting")
                serial_file = str(DISK_ADDRESS) + "/serial.key"
                print(serial_file)
                with open(serial_file,"r") as f:
                    serial_number = f.readline()
                    if serial_number == SERIAL_NUMBER:
                        print("success, serial number is valid")
                        self.ids.bt_save_graph.disabled = False
                    else:
                        print("fail, serial number is invalid")
                        self.ids.bt_save_graph.disabled = True                    
            except:
                print(f"Could not mount {DISK_ADDRESS}")
                self.ids.bt_save_graph.disabled = True
                count_mounting += 1
                if(count_mounting > 10):
                    flag_dongle = False 

    def measurement_check(self, dt):
        global flag_run
        global x_datum
        global y_datum
        global data_base
        global data_pos

        data_limit = len(data_base[2,:])
        visualized_data_pos = data_pos

        try:
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()
            
            self.ax.set_xlabel("distance [m]", fontsize=10)
            self.ax.set_ylabel("n", fontsize=10)
            self.ax.set_facecolor("#eeeeee")

            # datum location
            max_data = np.max(data_base[2,:data_limit])
            cmap, norm = mcolors.from_levels_and_colors([0.0, max_data, max_data * 2],['green','red'])
            self.ax.scatter(visualized_data_pos[0,:data_limit], -visualized_data_pos[1,:data_limit], c=data_base[2,:data_limit], cmap=cmap, norm=norm, label=l_electrode[0], marker='o')
            # electrode location
            self.ids.layout_graph.clear_widgets()
            self.ids.layout_graph.add_widget(FigureCanvasKivyAgg(self.fig))

            print("successfully show graphic")
        
        except:
            print("error show graphic")

        if(data_limit >= len(data_pos[0,:])):
            self.measure()

    def delayed_init(self, dt):
        self.fig, self.ax = plt.subplots()
        self.fig.set_facecolor("#eeeeee")
        self.fig.tight_layout()
        l, b, w, h = self.ax.get_position().bounds
        self.ax.set_position(pos=[l, b + 0.3*h, w, h*0.7])
        
        self.ax.set_xlabel("distance [m]", fontsize=10)
        self.ax.set_ylabel("n", fontsize=10)

        self.ids.layout_graph.add_widget(FigureCanvasKivyAgg(self.fig))        

    def measure(self):
        global flag_run
        if(flag_run):
            flag_run = False
        else:
            flag_run = True

    def reset_graph(self):
        global data_base
        global data_pos

        data_base = np.zeros([5, 1])
        data_pos = np.zeros([2, 1])

        try:
            self.ids.layout_graph.clear_widgets()
            self.fig, self.ax = plt.subplots()
            self.fig.set_facecolor("#eeeeee")
            self.fig.tight_layout()
            l, b, w, h = self.ax.get_position().bounds
            self.ax.set_position(pos=[l, b + 0.3*h, w, h*0.7])
            
            self.ax.set_xlabel("distance [m]", fontsize=10)
            self.ax.set_ylabel("n", fontsize=10)

            self.ids.layout_graph.add_widget(FigureCanvasKivyAgg(self.fig))        
            print("successfully reset graphic")
        
        except:
            print("error reset graphic")


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
                
    def screen_setting(self):
        self.screen_manager.current = 'screen_setting'

    def screen_data(self):
        self.screen_manager.current = 'screen_data'

    def screen_graph(self):
        self.screen_manager.current = 'screen_graph'

    def exec_shutdown(self):
        # os.system("shutdown /s /t 1") #for windows os
        toast("shutting down system")
        os.system("shutdown -h 1")

class ResistivityMeterApp(MDApp):
    def build(self):
        self.theme_cls.colors = colors
        self.theme_cls.primary_palette = "Blue"
        self.icon = 'asset/logo_labtek_p.ico'
        # Window.fullscreen = 'auto'
        Window.borderless = True
        Window.size = 1024, 600
        Window.allow_screensaver = True

        screen = Builder.load_file('main.kv')

        return screen


if __name__ == '__main__':
    ResistivityMeterApp().run()