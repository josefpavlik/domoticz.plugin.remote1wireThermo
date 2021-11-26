#
# Read remote 1 wire thermometers
#
# Author: Josef Pavlik, 2021, based on Multi-threaded example of Dnpwwo
#
# requires sshpass (sudo apt install sshpass
"""
<plugin key="Remote1wire" name="Remote 1 wire thermometers on Raspberry" author="Josef Pavlik" version="1.0.0" >
    <description>
        <h2>Remote 1 wire thermometers on Raspberry</h2><br/>
        Read remote 1 wire thermometers<br/>
        You can access the remote host with password or identity file. If you want to use the password, please install  <b> sshpass</b>.
    </description>
    <params>
        <param field="Mode1" label="user@host" width="200px" default=""/>
        <param field="Mode2" label="password" width="200px" default=""/>
        <param field="Mode3" label="identity file" width="200px" default=""/>
        <param field="Mode5" label="Polling period [s]" width="75px" default="60"/>

        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
#from Domoticz import Devices, Parameters
import os
import queue
import sys
import time
import threading
import subprocess


class BasePlugin:
    
    def __init__(self):
        self.messageQueue = queue.Queue()
        self.messageThread = threading.Thread(name="QueueThread", target=BasePlugin.handleMessage, args=(self,))
        self.devUuids={}

    def handleMessage(self):
        try:
            Domoticz.Debug("Entering message handler")
            while True:
                Message = self.messageQueue.get(block=True)
                Domoticz.Debug("got message")
                if Message is None:
                    Domoticz.Debug("Exiting message handler")
                    self.messageQueue.task_done()
                    break

# rescan the devices
                self.devUuids={}
                for i in Devices:
                  d=Devices[i]
                  self.devUuids[d.DeviceID]=d.Unit
#                  Domoticz.Debug("FIND device "+d.DeviceID)

                # ssh pi@10.0.0.51 'for i in /sys/bus/w1/devices/*-* ; do echo -ne $(basename $i | sed s/.*-//)\\t; cat $i/temperature; done '

                script="for i in /sys/bus/w1/devices/*-* ; do echo -ne $(basename $i | sed s/.*-//)\\\\t; cat $i/temperature; done"
                if Parameters["Mode2"] != "":
                  cmd=["sshpass", "-p", Parameters["Mode2"], "ssh", Parameters["Mode1"], script ]
                else:
                  cmd=["ssh", "-o", "StrictHostKeyChecking=no", Parameters["Mode1"], "-i", Parameters["Mode3"], script ]
                ssh = subprocess.Popen( cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True,
                                        bufsize=0)
                

                # Fetch output
                for line in ssh.stderr:
                    Domoticz.Error(line.strip())
                for line in ssh.stdout:
                    #Domoticz.Debug(line.strip())
                    p=line.replace("\n","").split("\t")
                    if len(p)==2: self.update_device(p[0], p[1])
  
                self.messageQueue.task_done()
        except Exception as err:
            Domoticz.Error("handleMessage: "+str(err))
    
    def update_device(self, uuid, value):
        if uuid not in self.devUuids: 
            for nr in range(1,len(Devices)+1):
                if nr not in Devices:
                  unit=nr
                  break
            Domoticz.Debug("CREATING DEVICE "+str(uuid)+" unit="+str(unit))
            Domoticz.Device(Name=uuid,Unit=unit, DeviceID=uuid, Type=80, Used=1).Create()       
            self.devUuids[uuid]=unit
        else:
            unit=self.devUuids[uuid]
        Domoticz.Debug("going to update "+str(unit)+" -> "+str(uuid)+" to "+value)
#        temp=value[:2]+"."+value[2:] # raw - three decimal. I want only 1 decimal
#        temp=print("%.2f" % (float(value)/1000.0)) # this does not work!!!!
#        temp=print("{:.2f}".format(float(value)/1000.0)) # this does not work!!!!
#        temp=print( "{:.{}f}".format(float("123456")/1000.0, 2 ) ) # this does not work!!!!
        x=str((int(value)+50)//100)
        temp=x[:2]+"."+x[2:]
        Domoticz.Debug("updating "+str(uuid)+" to "+temp)
#        Devices[unit].Update(0,temp+";0;0")
        Devices[unit].Update(0,temp)
    
    def onStart(self):
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()
        self.messageThread.start()
        Domoticz.Heartbeat(int(Parameters["Mode5"]))

    def onHeartbeat(self):
        self.messageQueue.put({"Type":"Log", "Text":"Heartbeat test message"})

    def onStop(self):
        # Not needed in an actual plugin
        for thread in threading.enumerate():
            if (thread.name != threading.current_thread().name):
                Domoticz.Log("'"+thread.name+"' is running, it must be shutdown otherwise Domoticz will abort on plugin exit.")

        # signal queue thread to exit
        self.messageQueue.put(None)
        Domoticz.Log("Clearing message queue...")
        self.messageQueue.join()

        # Wait until queue thread has exited
        Domoticz.Log("Threads still active: "+str(threading.active_count())+", should be 1.")
        while (threading.active_count() > 1):
            for thread in threading.enumerate():
                if (thread.name != threading.current_thread().name):
                    Domoticz.Log("'"+thread.name+"' is still running, waiting otherwise Domoticz will abort on plugin exit.")
            time.sleep(1.0)

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def stringOrBlank(input):
    if (input == None): return ""
    else: return str(input)

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
