#
# Read remote 1 wire thermometers
#
# Author: Josef Pavlik, 2021-2022, based on Multi-threaded example of Dnpwwo
#
# https://github.com/josefpavlik/domoticz.plugin.remote1wireThermo
# requires sshpass (sudo apt install sshpass
"""
<plugin key="Remote1wire" name="Remote 1 wire thermometers on Raspberry" author="Josef Pavlik" version="1.1.0" >
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
        self.devUuids={}
        self.ssh=None
        self.nextbeat=time.time()

    def onStart(self):
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()
        Domoticz.Heartbeat(15)
        self.nextbeat=time.time()
        self.startSsh()

    def onHeartbeat(self):
        if self.ssh!=None:
          if self.ssh.poll()==None:
            Domoticz.Debug("ssh no result")
            return
          if self.ssh.poll()!=0:
            Domoticz.Debug("ssh error %d" % self.ssh.poll())
            for line in self.ssh.stderr:
              Domoticz.Error(line.strip())
          else:
            Domoticz.Debug("ssh has result")
            self.gotResult()
        self.ssh=None
        if time.time()>=self.nextbeat:
          self.startSsh()  

    def startSsh(self):
        self.nextbeat+=int(Parameters["Mode5"])
        self.devUuids={}
# rescan the devices
        for i in Devices:
          d=Devices[i]
          self.devUuids[d.DeviceID]=d.Unit
#                  Domoticz.Debug("FIND device "+d.DeviceID)

        # ssh pi@10.0.0.51 'for i in /sys/bus/w1/devices/*-* ; do echo -ne $(basename $i | sed s/.*-//)\\t; cat $i/temperature; done '

        script="for i in /sys/bus/w1/devices/*-* ; do sleep 0.5; echo -ne $(basename $i | sed s/.*-//)\\\\t; cat $i/temperature; done"
        if Parameters["Mode2"] != "":
          cmd=["timeout", "60", "sshpass", "-p", Parameters["Mode2"], "ssh", Parameters["Mode1"], script ]
        else:
          cmd=["timeout", "60", "ssh", "-o", "StrictHostKeyChecking=no", Parameters["Mode1"], "-i", Parameters["Mode3"], script ]
        self.ssh = subprocess.Popen( cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                bufsize=0)
        Domoticz.Debug("ssh started")

        
    def gotResult(self):
        for line in self.ssh.stdout:
          Domoticz.Debug(line.strip())
          p=line.replace("\n","").split("\t")
          if len(p)==2: self.update_device(p[0], p[1])
  
    
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
    
    def onStop(self):
        if self.ssh!=None and self.ssh.poll()!=None:
          self.ssh.terminate()

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
