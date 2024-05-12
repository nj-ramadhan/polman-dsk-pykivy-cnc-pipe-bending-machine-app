import numpy as np
import os

val_pipe_length = 6000.0
val_pipe_diameter = 50.3
val_pipe_thickness = 1.0
data_base_pipe_setting = np.array([val_pipe_length,
                                   val_pipe_diameter,
                                   val_pipe_thickness])

val_machine_eff_length = 200.
val_machine_supp_pos = 200.
val_machine_clamp_front_delay = 5.
val_machine_clamp_rear_delay = 5.
val_machine_press_front_delay = 5.
val_machine_press_rear_delay = 5.
val_machine_collet_clamp_delay = 5.
val_machine_collet_open_delay = 5.
val_machine_die_radius = 100.0
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

name_file = "settings.cfg"

data_base_save = np.hstack((data_base_pipe_setting, data_base_machine_setting, data_base_advanced_setting))
print(data_base_save)
with open(name_file,"wb") as f:
    np.savetxt(f, data_base_save.T, fmt="%.3f",delimiter="\t")
print("sucessfully save data")


data_set = np.loadtxt(name_file, delimiter="\t", encoding=None)
data_base_load = data_set.T
data_base_pipe_setting = data_base_load[:3]
data_base_machine_setting = data_base_load[3:12]
data_base_advanced_setting = data_base_load[12:]

print(data_base_pipe_setting)
print(data_base_machine_setting)
print(data_base_advanced_setting)