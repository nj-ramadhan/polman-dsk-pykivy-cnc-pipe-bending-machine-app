import numpy as np

val_machine_die_radius = 40.
val_advanced_receive_pos_x = 160.
val_pipe_length = 6000.
val_machine_eff_length = 1800.
val_feed_step = np.array([400,500,400,150,290,350,250,240,100,200])
val_bend_step = np.array([30,90,30,60,90,50,0,0,0,0])
val_turn_step = np.array([30,30,90,-60,0,-30,0,0,0,0])

val_feed_absolute_step = np.zeros(10)
val_bend_linear_absolute_step = np.zeros(10)
# bend linear offset = 2 pi * r * die radius / 360 
# (conversion from bending movement to feed offset linear movement)
val_bend_linear_offset_step = val_machine_die_radius * 2 * np.pi * val_bend_step / 360
print(val_bend_linear_offset_step)

# setting val_advanced_receive_pos_x as first cycle position set value feed
val_feed_absolute_step[0] = int(val_feed_step[0] + val_advanced_receive_pos_x)
val_bend_linear_absolute_step[0] = int(val_bend_linear_offset_step[0] + val_feed_step[0] + val_advanced_receive_pos_x)

for i in range(1,10):
    # feed absolute = feed offset + last feed absolute + bend linear offset
    val_feed_absolute_step[i] = int(val_feed_absolute_step[i-1] + val_feed_step[i])
    val_bend_linear_absolute_step[i] = int(val_feed_absolute_step[i] + val_bend_linear_offset_step[i])

    if val_feed_absolute_step[i] > val_machine_eff_length:
        val_feed_absolute_step[i] = int(val_feed_step[i] + val_advanced_receive_pos_x)

val_turn_absolute_step = np.zeros(10)
val_turn_absolute_step[0] = val_turn_step[0]
for i in range(1,10):
    # turn absolute = turn offset + last turn absolute
    val_turn_absolute_step[i] = int(val_turn_step[i] + val_turn_absolute_step[i-1])

list_val_feed_absolute_step = val_feed_absolute_step.astype(int).tolist()
list_val_bend_step = val_bend_step.astype(int).tolist()
list_val_turn_absolute_step = val_turn_absolute_step.astype(int).tolist()
# list_val_turn_step = val_turn_step.astype(int).tolist()
list_val_bend_linear_offset_step = val_bend_linear_offset_step.astype(int).tolist()
list_val_bend_linear_absolute_step = val_bend_linear_absolute_step.astype(int).tolist()

print('absolute feed:',val_feed_absolute_step)
print('absolute linear bend:',val_bend_linear_absolute_step)
print('offset linear bend:',val_bend_linear_offset_step)
print('absolute turn:',val_turn_absolute_step)


print(np.pi)