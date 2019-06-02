# Evohome Schedule Restore v0.3
# Copyright (c) 2019 Evsdd 
# Python 3.7
# Requires pyserial module which can be installed using 'python -m pip install pyserial'
# Prototype program to restore schedules to the Evotouch controller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# import required modules
from __future__ import print_function
import serial                     
import time
import datetime
import struct
import textwrap
import zlib

from array import array

##### Start of user configuration setup
##### Note: file and serial port settings below are all for Windows OS

##### Set restore filename
input_restore_file = "e:\\Python\\Evohome_Restore_Test.txt"

##### Configure serial port
ComPort = serial.Serial('COM4')   # open port 
ComPort.baudrate = 115200         # set baud rate (HGI80=115200)
ComPort.bytesize = 8              # Number of data bits = 8
ComPort.parity   = 'N'            # No parity
ComPort.stopbits = 1              # Number of Stop bits = 1
ComPort.timeout = 2               # Read timeout = 1sec

##### Evohome controller ID
ControllerID =  0x51d74

##### End of user configuration setup

##### Additional configuration setup (you don't need to alter these)
GatewayID =  0x4802DA 
Max_zones = 12                    # Maximum number of zones        
Com_SCHD = 0x0404                 # Evohome Command SCHEDULE                       

# Create device values required for message structure
ControllerTXT = '{:02d}:{:06d}'.format((ControllerID & 0xFC0000) >> 18, ControllerID & 0x03FFFF)
GatewayTXT = '{:02d}:{:06d}'.format((GatewayID & 0xFC0000) >> 18, GatewayID & 0x03FFFF)
print('ControllerID=0x%06X (%s)' % (ControllerID, ControllerTXT))
             
# message send and response confirmation
def msg_send_rest(msg_type,msg_comm,msg_pay,msg_addr1='--:------',msg_addr2='--:------',msg_addr3='--:------',msg_delay=1,msg_resp=0):
  send_data = bytearray('{0:s} --- {1:s} {2:s} {3:s} {4:04X} {5:03d} {6:s}'.format(msg_type, msg_addr1, msg_addr2, msg_addr3, msg_comm, int(len(msg_pay)/2), msg_pay), 'utf-8') + b'\r\n'
  print('Send:[{:s}]'.format(send_data.decode().strip()))
  time.sleep(msg_delay) ## wait before sending message to avoid overloading serial port
  No = ComPort.write(send_data)
  
  if msg_resp:   # wait for response command from addr2 device
    send_time = time.time()
    resp = False
    j = 0  # retry counter
    RQ_zone = int(msg_pay[1:2], 16)
    RQ_packet = msg_pay[10:12]
    RQ_packet_tot = msg_pay[12:14]
    while (resp == False):      
       data = ComPort.readline().decode().replace("\x11","").rstrip() # Wait and read data      
       if data:                         # Only proceed if line read before timeout
         print(data)
         msg_type = data[4:6]           # Extract message type
         dev1 = data[11:20]             # Extract deviceID 1
         dev2 = data[21:30]             # Extract deviceID 2
         dev3 = data[31:40]             # Extract deviceID 3
         cmnd = data[41:45]             # Extract command
         RP_zone = int(data[51:52], 16) # Extract first 2 bytes of payload and convert to int
         RP_packet = data[60:62]
         RP_packet_tot = data[62:64]
         if (cmnd == '%04X' % msg_comm and dev1 == msg_addr2 and RQ_zone == RP_zone and RQ_packet == RP_packet):  #perform basic response check (TODO fully verify acknowledgement)
            response = RP_packet_tot             
            resp = True
         else:
           if (j == 5): # retry 5 times
             resp = True
             print("Send failure!")
             response = ''
           else:
             if ((time.time() - send_time) > 1): # Wait 1sec before each re-send
               j += 1
               print('Re-send[{0:d}][{1:s}]'.format(j, send_data.decode().strip()))
               No = ComPort.write(send_data) # re-send message
               send_time = time.time()
  return response

# decode zlib compressed payload
def decode_schedule(message):
#def decode_schedule(message,zone):
  i = 0
  try:
    data = zlib.decompress(bytearray.fromhex(message))
    Status = True
  except zlib.error:
    Status = False
  if Status:    
    for record in [data[i:i+20] for i in range(0, len(data), 20)]:
      (zone, day, time, temp, unk) = struct.unpack("<xxxxBxxxBxxxHxxHH", record)
      print('ZONE={0:d} DAY={1:d} TIME={2:02d}:{3:02d} TEMP={4:.2f}'.format(zone+1, day+1, *divmod(time, 60), temp/100), file=output_backup)
  return Status

##### Controller startup commands
time.sleep(2) ## wait for serial port to stabilise

line_chunks = []
Last_zone = 1
cobj = zlib.compressobj(level=9, wbits=14)
compressed_data = b''

# Restore all zone schedules from file to controller and verify 
with open(input_restore_file, "r") as input_restore:
   for line in input_restore:
      line_chunks = line.split()
      Zone = int(line_chunks[0].split('=')[1])
      Day = int(line_chunks[1].split('=')[1]) - 1
      Time = line_chunks[2].split('=')[1].split(':')
      Time_mins = int(Time[0])*60 + int(Time[1])

      Temperature = int(float(line_chunks[3].split('=')[1]) * 100)

      record = struct.pack('<xxxxBxxxBxxxHxxHxx', Zone-1, Day, Time_mins, Temperature)
      
      if (Zone == Last_zone + 1):  # Ready to send zone schedule
        compressed_data += cobj.flush()        
          
        schedule = compressed_data.hex()
        compressed_data = b''
          
        #Restore complete zone schedule to controller (TODO add verification)
        Pack_Total = 1 + int(len(schedule) / 82)
        Packet = 1
        while (Packet <= Pack_Total):
          pay_start = int((Packet - 1) * 82)
          
          if (Packet != Pack_Total):
            pay_end = int(pay_start + 82)
          else:
            pay_end = int((len(schedule) % 82) + pay_start)
          payload = '{0:02X}200008{1:02X}{2:02d}{3:02d}{4:s}'.format(Zone-2, int((pay_end - pay_start) / 2), Packet, Pack_Total, schedule[pay_start: pay_end])       
          Packet += 1
          response = msg_send_rest(msg_type='W', msg_addr1=GatewayTXT, msg_addr2=ControllerTXT, msg_comm=Com_SCHD, msg_pay=payload,msg_delay=1,msg_resp=1)
          if (response == '00'):
            print('Restore Complete: Zone=%d!' % (Zone-1))
          
        cobj = zlib.compressobj(level=9, wbits=14)
      compressed_data += cobj.compress(record)
      Last_zone = Zone

# Send schedule for last zone
compressed_data += cobj.flush()
                  
schedule = compressed_data.hex()
          
# Restore complete zone schedule to controller (TODO add verification)
Pack_Total = 1 + int(len(schedule) / 82)
Packet = 1
while (Packet <= Pack_Total):
  pay_start = int((Packet - 1) * 82)
  if (Packet != Pack_Total):
    pay_end = int(pay_start + 82)
  else:
    pay_end = int((len(schedule) % 82) + pay_start)
  payload = '{0:02X}200008{1:02X}{2:02d}{3:02d}{4:s}'.format(Zone-1, int((pay_end - pay_start) / 2), Packet, Pack_Total, schedule[pay_start: pay_end])
  Packet += 1
  response = msg_send_rest(msg_type='W', msg_addr1=GatewayTXT, msg_addr2=ControllerTXT, msg_comm=Com_SCHD, msg_pay=payload,msg_delay=1,msg_resp=1)
  if (response == '00'):
    print('Restore Complete: Zone=%d!' % Zone)
