import numpy as np

val_machine_die_radius = 50
val_feed_step = np.array([200,300,100,200,300,400,200,400,50,100])
val_bend_step = np.array([90,60,90,30,45,90,90,60,30,30])
val_feed_absolute = np.zeros(10)

val_bend_offset = (val_machine_die_radius * 2 * np.pi * val_bend_step / 360)

val_feed_absolute[0] = val_feed_step[0]
for i in range(1,10):
    # feed absolute = feed offset + last feed absolute + 2 pi * r * die radius / 360
    val_feed_absolute[i] = int(val_feed_step[i] + val_feed_absolute[i-1] + (val_machine_die_radius * 2 * np.pi * val_bend_step[i] / 360))
print(val_feed_absolute)
print(val_feed_absolute.astype(int))

# for i in range(1,9):
#     # feed absolute = feed offset + last feed absolute + 2 pi * r * die radius / 360
#     val_feed_absolute[i] = int(val_feed_step[i] + val_feed_absolute[i-1] + val_bend_offset[i])
# print(val_feed_absolute)
list_val_feed_step = list(val_feed_absolute)

print(list_val_feed_step, type(list_val_feed_step))