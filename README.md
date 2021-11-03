# domoticz.plugin.remote1wireThermo
Domoticz plugin  for read 1wire thermometers on remote Raspberry


INSTALL:
Clone the repository to ~/domoticz/plugins and restart domoticz.

SETUP:
Go to the Hardware menu and create new hardware of type "Remote 1 wire thermometers on Raspberry". Set user@host and either password or file with keys to access to remote raspberry. Using the password is not recomended and requires sshpass. Install it with "sudo apt install sshpass". It's better to access using key. Create key with ssh-keygen and add public key to ~/.ssh/authorized_keys.

Devices will be created automatically. When you connedt new 1wire thermometer to remote raspberry, new device will be created automatically within a minute.

