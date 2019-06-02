Evohome Schedule Restore v0.3
Copyright (c) 2019 Evsdd 
Python 3.7
Requires pyserial module which can be installed using 'python -m pip install pyserial'
Prototype program to restore schedules to the Evotouch controller
 
INSTRUCTIONS FOR USE:
To begin using the script, first edit user configuration setup section.  Choose your restore file name and location which contains the schedule information (see Evohome_Schedule_Backup output for file structure information), configure your serial port which is connected to the HGI80 (or equivalent) and finally enter your controller ID. 
You are now ready to run the script!
Note: the Evohome controller allows a maximum of 42 setpoints per zone.  If this limit is exceeded the controller will reject the schedule for the particular zone, leaving the existing schedule effective.
