import serial
from datetime import datetime as dt
from datetime import timedelta as td
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from twython import Twython, TwythonError
from tempfile import TemporaryFile
import ConfigParser
from multiprocessing import Process, Lock

def updateTime(time, ser, lock):
    with lock:
        try:
            ser.write("%02d%02d" % (time.hour, time.minute))
        except ValueError:
            print "Could not update. Serial connection might be severed."
    while 1:
        if dt.now().minute != time.minute:
            with lock:
                print "Updating clock time."
            time = dt.now()
            with lock:
                try:
                    ser.write("%02d%02d" % (time.hour, time.minute))
                except ValueError:
                    print "Could not update. Serial connection might be severed."

''' def nextAlarm(ref):
    ind = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    try:
        opt = nextAlarm.config.option('alarm', ind[ref.weekday()])
    except Error:
        pass'''

def sample(ser, lock, alarm):
    start = dt.now()
    time = []
    temp = []
    vol = []
    
    while alarm > dt.now():
        if ser.inWaiting():
            with lock:
                response = ser.readline().split(' ')
                print response
            try:
                tTemp = float(response[0])
                tVol = int(response[2])
                tTime = dt.now()
                # If there's an error, it will not add any elements.
                temp.append(tTemp)
                vol.append(tVol)
                time.append(tTime)
            except ValueError:
                with lock:
                    print "^^^ Corrupted data, ignoring."
    
    try:
        while not ser.inWaiting():
            with lock:
                ser.write("s")
    except ValueError:
        with lock:
            print "Serial connection might be severed."
        
    return (temp, vol, time)

def plot(temp, vol, time, creds):
    hours = mdates.HourLocator()
    minutes = mdates.MinuteLocator()
    hoursFmt = mdates.DateFormatter("%Y-%m-%d %H:%M")
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    
    ax.plot(time, temp, "r-")
    
    ax.set_ylabel("Temperature", color="r")
    for t1 in ax.get_yticklabels():
        t1.set_color("r")
    
    ax.xaxis.set_major_locator(hours)
    ax.xaxis.set_major_formatter(hoursFmt)
    ax.xaxis.set_minor_locator(minutes)
    
    ax.set_xlim(min(time), max(time))
    ax.set_ylim(50, 100)
    ax.format_xdata = mdates.DateFormatter("%Y-%m-%d %H:%M")
    ax.grid(True)
    
    ax2 = ax.twinx()
    ax2.plot(time, vol, "b-")
    
    ax2.set_yscale('log')
    ax2.set_ylabel("Volume", color="b")
    for t1 in ax2.get_yticklabels():
        t1.set_color("b")
    
    fig.autofmt_xdate()
    
    try:
        t = Twython(creds['con_key'], creds['con_secret'], creds['access_token'], creds['access_secret'])
        image = TemporaryFile()
        fig.savefig(image)
        image.seek(0)
        t.update_status_with_media(media=image, status="Sleep plot for %s." % dt.now().strftime("%m-%d-%Y"))
        image.close()
    except IOError as e:
        print e
        fig.savefig('/home/pi/plot-%s.png' % dt.now().strftime("%Y%m%d-%H%M%S"))
    except TwythonError as e:
        print e
        fig.savefig('/home/pi/plot-%s.png' % dt.now().strftime("%Y%m%d-%H%M%S"))

if __name__ == "__main__":
    ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=None)
    ser.open()
    
    lock = Lock()
    p = Process(target=updateTime, args=(dt.now(), ser, lock))
    p.daemon = True
    p.start()

    config = ConfigParser.RawConfigParser()
    config.read('impetus.conf')
    creds = dict(config.items('twitter'))

    try:
        while 1:
            ser.flushInput()
            while not ser.inWaiting():
                pass # set up alarm
            with lock:
                print "In sleep, sampling..."
            temp, vol, time = sample(ser, dt.now() + td(hours=2), lock)
            plot(temp, vol, time, creds)
            with lock:
                print "Out of sleep, graph tweeted."
    except KeyboardInterrupt:
        pass

    with lock:
        ser.close()
