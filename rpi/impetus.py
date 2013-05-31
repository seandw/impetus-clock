import serial
from datetime import datetime as dt
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
ser.open()

time = []
temp = []
vol = []

try:
    while 1:
        response = ser.readline().split(' ')
        print response
        time.append(dt.now())
        temp.append(float(reponse[0]))
        vol.append(int(response[1]))
except KeyboardInterrupt:
    ser.close()

hours = mdates.HourLocator()
minutes = mdates.MinuteLocator()
hoursFmt = mdates.DateFormatter("%Y-%m-%d %H:%M")

fig = plt.figure()
ax = fig.add_subplot(111)

ax.plot(time, temp, "r.")

ax.set_ylabel("Temperature", color="r")
for t1 in ax.get_yticklabels():
    t1.set_color("r")

ax.xaxis.set_major_locator(hours)
ax.xaxis.set_major_formatter(hoursFmt)
ax.xaxis.set_minor_locator(minutes)

ax.set_xlim(min(time), max(time))
ax.format_xdata = mdates.DateFormatter("%Y-%m-%d %H:%M")
ax.grid(True)

ax2 = ax.twinx()
ax2.plot(time, vol, "b-")

ax2.set_ylabel("Volume", color="b")
for t1 in ax2.get_yticklabels():
    t1.set_color("b")

fig.autofmt_xdate()

plt.show()
#fig.savefig('/home/pi/testplot.png')

