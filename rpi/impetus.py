#! /usr/bin/env python
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
from multiprocessing import Process, Lock, Pipe
import signal
from time import sleep

def updateTime(time, ser, lock):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
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
            sleep(50)

def updateSched(pipe):
    # KeyboardInterrupt is not a good thing to catch in here.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    config = ConfigParser.RawConfigParser()
    config.read('impetus.conf')
    creds = dict(config.items('twitter'))
    pipe.send(creds)

    t = Twython(creds['con_key'], creds['con_secret'], creds['access_token'], creds['access_secret'])
    
    lastUpdate = safeConfGet(config, 'alarm', 'last_time')
    if lastUpdate:
        lastUpdate = dt.strptime(lastUpdate, "%Y-%m-%d %H:%M:%S.%f")
    else:
        lastUpdate = dt.min

    lastId = safeConfGet(config, 'alarm', 'last_id')

    while 1:
        if pipe.poll():
            obj = pipe.recv()
            if isinstance(obj, dt):
                pipe.send(nextAlarm(obj, config))
            elif obj == "teardown":
                break
        if dt.now() > lastUpdate + td(minutes=3):
            try:
                dms = t.get_direct_messages(since_id=lastId)
                if dms:
                    dms.reverse()
                    for dm in dms: 
                        processed = processDm(config, dm)
                        if processed:
                            lastId = processed
                            t.send_direct_message(screen_name=dm['sender_screen_name'], text="Command sent on %s has been processed." % dm['created_at'])
            except TwythonError:
                pass # Hrm.
            lastUpdate = dt.now()
        sleep(1)

    config.set('alarm', 'last_id', lastId)
    config.set('alarm', 'last_time', lastUpdate)

    cfg = open("impetus.conf", "w")
    config.write(cfg)
    cfg.close()
    pipe.close()
    
def processDm(config, dm):
    if dm['sender_screen_name'] == "seandw":
        text = dm['text'].lower().split(' ')
        if text[0] == "set":
            if len(text) == 2: # Impromptu!
                config.set('alarm', 'impromptu', text[1])
            elif len(text) == 3:
                config.set('alarm', text[1], text[2])
        elif text[0] == "stop":
            if len(text) == 1:
                config.remove_option('alarm', 'impromptu')
            elif len(text) == 2:
                config.remove_option('alarm', text[1])
        return dm['id']
    else:
        return 0

def safeConfGet(config, section, option):
    if config.has_option(section, option):
        return config.get(section, option)
    else:
        return None

def strToDt(tStr, ref):
    t = tStr.split(":")
    return ref.replace(hour=int(t[0]), minute=int(t[1]), second=0)

def nextAlarm(ref, config):
    ind = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    
    imp = safeConfGet(config, "alarm", "impromptu")
    if imp:
        newTime = strToDt(imp, ref)
        if newTime > ref:
            config.remove_option("alarm", "impromptu")
            return newTime

    today = safeConfGet(config, "alarm", ind[ref.weekday()])    
    if today:
        newTime = strToDt(today, ref)
        if newTime > ref:
            return newTime
    
    if imp:
        config.remove_option("alarm", "impromptu")
        return strToDt(imp, ref+td(days=1))

    tomorrow = safeConfGet(config, "alarm", ind[(ref.weekday()+1)%7])
    if tomorrow:
        return strToDt(tomorrow, ref+td(days=1))
        
    return None

def sample(ser, lock, alarm):
    time = []
    temp = []
    vol = []
    start = dt.now()

    with lock:
        print "Alarm set for: %s" % alarm.strftime("%Y-%m-%d %H:%M")

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
    
    with lock:
        try:
            ser.write("s")
        except ValueError:
            print "Serial connection might be severed."
        
    return (temp, vol, time, start, dt.now())

def plot(temp, vol, time, start, end, creds):
    hours = mdates.DayLocator()
    minutes = mdates.HourLocator()
    hoursFmt = mdates.DateFormatter("%Y-%m-%d %H:%M")
    
    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.plot(time, temp, "r-")
    
    ax.set_title("Sleep from %s to %s" % (start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M")))
    ax.set_ylabel("Temperature (F)", color="r")
    for t1 in ax.get_yticklabels():
        t1.set_color("r")
    
    ax.xaxis.set_major_locator(hours)
    ax.xaxis.set_major_formatter(hoursFmt)
    ax.xaxis.set_minor_locator(minutes)
    
    ax.format_xdata = mdates.DateFormatter("%Y-%m-%d %H:%M")
    ax.grid(True)
    
    ax2 = fig.add_subplot(212)
    ax2.xaxis.set_major_locator(hours)
    ax2.xaxis.set_major_formatter(hoursFmt)
    ax2.xaxis.set_minor_locator(minutes)
    ax2.plot(time, vol, "b-")
    
    ax2.set_ylabel("Volume", color="b")
    for t1 in ax2.get_yticklabels():
        t1.set_color("b")

    ax2.format_xdata = mdates.DateFormatter("%Y-%m-%d %H:%M")
    ax2.grid(True)
    
    fig.autofmt_xdate()
    
    try:
        t = Twython(creds['con_key'], creds['con_secret'], creds['access_token'], creds['access_secret'])
        image = TemporaryFile()
        fig.savefig(image)
        image.seek(0)
        t.update_status_with_media(media=image, status="Sleep plot for %s to %s." % (start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M")))
        image.close()
    except IOError as e:
        print e
        fig.savefig('/home/pi/plot-%s.png' % dt.now().strftime("%Y%m%d-%H%M%S"))
    except TwythonError as e:
        print e
        fig.savefig('/home/pi/plot-%s.png' % dt.now().strftime("%Y%m%d-%H%M%S"))

    plt.close()

def main():
    ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=None)
    ser.open()

    ''' Process for maintaining the display's time. '''
    lock = Lock()
    tDaemon = Process(target=updateTime, args=(dt.now(), ser, lock))
    tDaemon.daemon = True
    tDaemon.start()

    ''' Process for maintaining alarm schedule, configuration. '''
    pipe, proc_pipe = Pipe()
    aProc = Process(target=updateSched, args=(proc_pipe,))
    aProc.start()

    creds = pipe.recv()

    try:
        while 1:
            ser.flushInput()
            while not ser.inWaiting():
                pass # set up alarm
            ser.flushInput()
            with lock:
                print "In sleep, sampling..."
            pipe.send(dt.now())
            temp, vol, time, start, end = sample(ser, lock, pipe.recv())
            plot(temp, vol, time, start, end, creds)
            with lock:
                print "Out of sleep, graph tweeted."
    except KeyboardInterrupt:
        pass

    with lock:
        ser.write("R")
        ser.close()

    pipe.send("teardown")
    pipe.close()
    aProc.join()

if __name__ == "__main__":
    main()
