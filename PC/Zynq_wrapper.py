"""
//------------------------------------//
// AUTHOR   : Youngchan Lim
//------------------------------------//
"""

import pyqtgraph as pg
import time
import numpy as np
import ast
import math
import matplotlib.pyplot as plt
import sys
import socket

class Zynq:
	def __init__(self, bd_num):
		### Each ARTIX SFR starting address
		self.flag = " "
		self.working_board = bd_num
		### Network 
		self.zynq_ip = ["192.168.0.5", "192.168.0.6", "192.168.0.7", "192.168.0.8"]
		self.zynq_port = [5030, 5032, 5033, 5034]
		self.zynq_addr_list = []
		self.zynq_sock_list = []
		
		for i in range(0, self.working_board):
			self.zynq_addr_list.append((self.zynq_ip[i], self.zynq_port[i]))
			self.zynq_sock_list.append(socket.socket(socket.AF_INET,socket.SOCK_DGRAM))
			self.zynq_sock_list[i].setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 6000)

		### Socket [NI_client -> PC_server]
		self.pc_ip = "192.168.0.2"
		self.ni_ip = "192.168.0.12"
		self.ni_port = 5031
		self.pc_addr = (self.pc_ip, self.ni_port)
		self.ni_addr = (self.ni_ip, self.ni_port)
		self.ni_set_data = "run"
		self.ni_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.ni_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1000)
		self.ni_sock.bind(self.pc_addr)

		### Rx cal 
		self.Rx_Queue = []
		 # make list with the board

		self.fmax = 100000      # sampling frequency 5Mhz/100000 Hz
		self.loop_max_cnt = 500
		self.freq_data = np.arange(-self.loop_max_cnt/2, self.loop_max_cnt/2) / self.loop_max_cnt * self.fmax
		self.time = np.arange(200)
		self.abs_data = []
		self.phase_data = []
		self.angle_data = []
		self.line_I = []
		self.line_Q = []

		### Chart
		self.I_val_uncal = []
		self.I_val_cal = []
		for i in range(0, self.working_board*16):
			self.I_val_uncal.append([])
			self.I_val_cal.append([])
		self.cal_check = 1

	## Receiving ADC memory data from ARTIX
	def Recv_mem_data(self, socket_number):
		for i in range(0, self.working_board):
			self.Rx_Queue.append([])
		tmp = []
		for j in range(0, socket_number):
			for i in range(0, 32):
				data, addr = self.zynq_sock_list[j].recvfrom(2000)
				self.Rx_Queue[j].append(data.decode())
				print("memory recv: ",i+1,"/ board: ",j+1,"\n")

		#Read From Rx Queue
		for i in range(0, socket_number):
			for j in range(0, 32):
				tmp = self.Rx_Queue[i].pop(0).split(' ')
			#Append I & Q Data
				if( j%2 == 0 ):
					self.line_I.append( tmp[1:] )
				else:
					self.line_Q.append( tmp[1:] )	## FFT calibration for Rx cal

	def FFT_cal(self):
		for j in range(0,16*self.working_board): #ANT CH 32
			#Init Variables 
			iqch=[]
			fft_abs = []
			iqch_shift = []
			I_value = []
			Q_value = []

			for i in range(0,self.loop_max_cnt):

				I_value = int(self.line_I[j][i],16)
				if I_value >= 2048:
					I_value = I_value - 4096
				I_value = I_value/2048

				Q_value = int(self.line_Q[j][i],16)
				if Q_value >= 2048:
					Q_value = Q_value - 4096
				Q_value = Q_value/2048
				
				iqch.append(complex(I_value, Q_value))

				if(i<200):
					if(self.cal_check %2 == 1):
						self.I_val_uncal[j].append(I_value)

					if(self.cal_check %2 == 0):
						self.I_val_cal[j].append(I_value)		

			iqch = np.fft.fft(iqch)
			iqch_shift = np.fft.fftshift(iqch)
			fft_abs=abs(iqch_shift)
			self.abs_data.append(fft_abs)
			self.phase_data.append(np.angle(iqch_shift,deg=False))
			self.angle_data.append(np.angle(iqch_shift,deg=True))

	## Plot for IQ signal received for the board                                                                  
	def show_IQ_chart(self):
		plt.subplot(2,4,1)
		plt.title("BOARD A I val before")
		plt.plot(self.time, self.I_val_uncal[0], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 1")
		plt.plot(self.time, self.I_val_uncal[1], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 2")
		plt.plot(self.time, self.I_val_uncal[2], color="red", linewidth=2.0, linestyle="-", label = "ANT 3")
		plt.plot(self.time, self.I_val_uncal[3], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 4")
		plt.plot(self.time, self.I_val_uncal[4], color="coral", linewidth=2.0, linestyle="-", label = "ANT 5")
		plt.plot(self.time, self.I_val_uncal[5], color="orange", linewidth=2.0, linestyle="-", label = "ANT 6")
		plt.plot(self.time, self.I_val_uncal[6], color="gold", linewidth=2.0, linestyle="-", label = "ANT 7")
		plt.plot(self.time, self.I_val_uncal[7], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 8")
		plt.plot(self.time, self.I_val_uncal[8], color="olive", linewidth=2.0, linestyle="-", label = "ANT 9")
		plt.plot(self.time, self.I_val_uncal[9], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 10")
		plt.plot(self.time, self.I_val_uncal[10], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 11")
		plt.plot(self.time, self.I_val_uncal[11], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 12")
		plt.plot(self.time, self.I_val_uncal[12], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 13")
		plt.plot(self.time, self.I_val_uncal[13], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 14")
		plt.plot(self.time, self.I_val_uncal[14], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 15")
		plt.plot(self.time, self.I_val_uncal[15], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 16")
		plt.legend(loc = 4)
		
		plt.subplot(2,4,2)
		plt.title("BOARD B I val before")
		plt.plot(self.time, self.I_val_uncal[16], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 17")
		plt.plot(self.time, self.I_val_uncal[17], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 18")
		plt.plot(self.time, self.I_val_uncal[18], color="red", linewidth=2.0, linestyle="-", label = "ANT 19")
		plt.plot(self.time, self.I_val_uncal[19], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 20")
		plt.plot(self.time, self.I_val_uncal[20], color="coral", linewidth=2.0, linestyle="-", label = "ANT 21")
		plt.plot(self.time, self.I_val_uncal[21], color="orange", linewidth=2.0, linestyle="-", label = "ANT 22")
		plt.plot(self.time, self.I_val_uncal[22], color="gold", linewidth=2.0, linestyle="-", label = "ANT 23")
		plt.plot(self.time, self.I_val_uncal[23], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 24")
		plt.plot(self.time, self.I_val_uncal[24], color="olive", linewidth=2.0, linestyle="-", label = "ANT 25")
		plt.plot(self.time, self.I_val_uncal[25], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 26")
		plt.plot(self.time, self.I_val_uncal[26], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 27")
		plt.plot(self.time, self.I_val_uncal[27], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 28")
		plt.plot(self.time, self.I_val_uncal[28], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 29")
		plt.plot(self.time, self.I_val_uncal[29], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 30")
		plt.plot(self.time, self.I_val_uncal[30], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 31")
		plt.plot(self.time, self.I_val_uncal[31], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 32")
		plt.legend(loc = 4)
"""		
		plt.subplot(2,4,3)
		plt.title("BOARD C I val before")
		plt.plot(self.time, self.I_val_uncal[32], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 33")
		plt.plot(self.time, self.I_val_uncal[33], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 34")
		plt.plot(self.time, self.I_val_uncal[34], color="red", linewidth=2.0, linestyle="-", label = "ANT 35")
		plt.plot(self.time, self.I_val_uncal[35], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 36")
		plt.plot(self.time, self.I_val_uncal[36], color="coral", linewidth=2.0, linestyle="-", label = "ANT 37")
		plt.plot(self.time, self.I_val_uncal[37], color="orange", linewidth=2.0, linestyle="-", label = "ANT 38")
		plt.plot(self.time, self.I_val_uncal[38], color="gold", linewidth=2.0, linestyle="-", label = "ANT 39")
		plt.plot(self.time, self.I_val_uncal[39], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 40")
		plt.plot(self.time, self.I_val_uncal[40], color="olive", linewidth=2.0, linestyle="-", label = "ANT 41")
		plt.plot(self.time, self.I_val_uncal[41], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 42")
		plt.plot(self.time, self.I_val_uncal[42], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 43")
		plt.plot(self.time, self.I_val_uncal[43], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 44")
		plt.plot(self.time, self.I_val_uncal[44], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 45")
		plt.plot(self.time, self.I_val_uncal[45], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 46")
		plt.plot(self.time, self.I_val_uncal[46], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 47")
		plt.plot(self.time, self.I_val_uncal[47], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 48")
		plt.legend(loc = 4)

		plt.subplot(2,4,4)
		plt.title("BOARD D I val before")
		plt.plot(self.time, self.I_val_uncal[48], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 49")
		plt.plot(self.time, self.I_val_uncal[49], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 50")
		plt.plot(self.time, self.I_val_uncal[50], color="red", linewidth=2.0, linestyle="-", label = "ANT 51")
		plt.plot(self.time, self.I_val_uncal[51], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 52")
		plt.plot(self.time, self.I_val_uncal[52], color="coral", linewidth=2.0, linestyle="-", label = "ANT 53")
		plt.plot(self.time, self.I_val_uncal[53], color="orange", linewidth=2.0, linestyle="-", label = "ANT 54")
		plt.plot(self.time, self.I_val_uncal[54], color="gold", linewidth=2.0, linestyle="-", label = "ANT 55")
		plt.plot(self.time, self.I_val_uncal[55], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 56")
		plt.plot(self.time, self.I_val_uncal[56], color="olive", linewidth=2.0, linestyle="-", label = "ANT 57")
		plt.plot(self.time, self.I_val_uncal[57], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 58")
		plt.plot(self.time, self.I_val_uncal[58], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 59")
		plt.plot(self.time, self.I_val_uncal[59], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 60")
		plt.plot(self.time, self.I_val_uncal[60], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 61")
		plt.plot(self.time, self.I_val_uncal[61], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 62")
		plt.plot(self.time, self.I_val_uncal[62], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 63")
		plt.plot(self.time, self.I_val_uncal[63], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 64")
		plt.legend(loc = 4)
"""
		plt.subplot(2,4,5)
		plt.title("BOARD A I val after")
		plt.plot(self.time, self.I_val_cal[0], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 1")
		plt.plot(self.time, self.I_val_cal[1], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 2")
		plt.plot(self.time, self.I_val_cal[2], color="red", linewidth=2.0, linestyle="-", label = "ANT 3")
		plt.plot(self.time, self.I_val_cal[3], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 4")
		plt.plot(self.time, self.I_val_cal[4], color="coral", linewidth=2.0, linestyle="-", label = "ANT 5")
		plt.plot(self.time, self.I_val_cal[5], color="orange", linewidth=2.0, linestyle="-", label = "ANT 6")
		plt.plot(self.time, self.I_val_cal[6], color="gold", linewidth=2.0, linestyle="-", label = "ANT 7")
		plt.plot(self.time, self.I_val_cal[7], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 8")
		plt.plot(self.time, self.I_val_cal[8], color="olive", linewidth=2.0, linestyle="-", label = "ANT 9")
		plt.plot(self.time, self.I_val_cal[9], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 10")
		plt.plot(self.time, self.I_val_cal[10], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 11")
		plt.plot(self.time, self.I_val_cal[11], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 12")
		plt.plot(self.time, self.I_val_cal[12], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 13")
		plt.plot(self.time, self.I_val_cal[13], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 14")
		plt.plot(self.time, self.I_val_cal[14], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 15")
		plt.plot(self.time, self.I_val_cal[15], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 16")
		plt.legend(loc = 4)
		
		plt.subplot(2,4,6)
		plt.title("BOARD B I val after")
		plt.plot(self.time, self.I_val_cal[16], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 17")
		plt.plot(self.time, self.I_val_cal[17], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 18")
		plt.plot(self.time, self.I_val_cal[18], color="red", linewidth=2.0, linestyle="-", label = "ANT 19")
		plt.plot(self.time, self.I_val_cal[19], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 20")
		plt.plot(self.time, self.I_val_cal[20], color="coral", linewidth=2.0, linestyle="-", label = "ANT 21")
		plt.plot(self.time, self.I_val_cal[21], color="orange", linewidth=2.0, linestyle="-", label = "ANT 22")
		plt.plot(self.time, self.I_val_cal[22], color="gold", linewidth=2.0, linestyle="-", label = "ANT 23")
		plt.plot(self.time, self.I_val_cal[23], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 24")
		plt.plot(self.time, self.I_val_cal[24], color="olive", linewidth=2.0, linestyle="-", label = "ANT 25")
		plt.plot(self.time, self.I_val_cal[25], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 26")
		plt.plot(self.time, self.I_val_cal[26], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 27")
		plt.plot(self.time, self.I_val_cal[27], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 28")
		plt.plot(self.time, self.I_val_cal[28], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 29")
		plt.plot(self.time, self.I_val_cal[29], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 30")
		plt.plot(self.time, self.I_val_cal[30], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 31")
		plt.plot(self.time, self.I_val_cal[31], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 32")
		plt.legend(loc = 4)
"""	
		plt.subplot(2,4,7)
		plt.title("BOARD C I val after")
		plt.plot(self.time, self.I_val_cal[32], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 33")
		plt.plot(self.time, self.I_val_cal[33], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 34")
		plt.plot(self.time, self.I_val_cal[34], color="red", linewidth=2.0, linestyle="-", label = "ANT 35")
		plt.plot(self.time, self.I_val_cal[35], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 36")
		plt.plot(self.time, self.I_val_cal[36], color="coral", linewidth=2.0, linestyle="-", label = "ANT 37")
		plt.plot(self.time, self.I_val_cal[37], color="orange", linewidth=2.0, linestyle="-", label = "ANT 38")
		plt.plot(self.time, self.I_val_cal[38], color="gold", linewidth=2.0, linestyle="-", label = "ANT 39")
		plt.plot(self.time, self.I_val_cal[39], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 40")
		plt.plot(self.time, self.I_val_cal[40], color="olive", linewidth=2.0, linestyle="-", label = "ANT 41")
		plt.plot(self.time, self.I_val_cal[41], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 42")
		plt.plot(self.time, self.I_val_cal[42], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 43")
		plt.plot(self.time, self.I_val_cal[43], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 44")
		plt.plot(self.time, self.I_val_cal[44], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 45")
		plt.plot(self.time, self.I_val_cal[45], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 46")
		plt.plot(self.time, self.I_val_cal[46], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 47")
		plt.plot(self.time, self.I_val_cal[47], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 48")
		plt.legend(loc = 4)

		plt.subplot(2,4,8)
		plt.title("BOARD D I val after")
		plt.plot(self.time, self.I_val_cal[48], color="maroon", linewidth=2.0, linestyle="-", label = "ANT 49")
		plt.plot(self.time, self.I_val_cal[49], color="firebrick", linewidth=2.0, linestyle="-", label = "ANT 50")
		plt.plot(self.time, self.I_val_cal[50], color="red", linewidth=2.0, linestyle="-", label = "ANT 51")
		plt.plot(self.time, self.I_val_cal[51], color="orangered", linewidth=2.0, linestyle="-", label = "ANT 52")
		plt.plot(self.time, self.I_val_cal[52], color="coral", linewidth=2.0, linestyle="-", label = "ANT 53")
		plt.plot(self.time, self.I_val_cal[53], color="orange", linewidth=2.0, linestyle="-", label = "ANT 54")
		plt.plot(self.time, self.I_val_cal[54], color="gold", linewidth=2.0, linestyle="-", label = "ANT 55")
		plt.plot(self.time, self.I_val_cal[55], color="darkolivegreen", linewidth=2.0, linestyle="-", label = "ANT 56")
		plt.plot(self.time, self.I_val_cal[56], color="olive", linewidth=2.0, linestyle="-", label = "ANT 57")
		plt.plot(self.time, self.I_val_cal[57], color="olivedrab", linewidth=2.0, linestyle="-", label = "ANT 58")
		plt.plot(self.time, self.I_val_cal[58], color="limegreen", linewidth=2.0, linestyle="-", label = "ANT 59")
		plt.plot(self.time, self.I_val_cal[59], color="lawngreen", linewidth=2.0, linestyle="-", label = "ANT 60")
		plt.plot(self.time, self.I_val_cal[60], color="springgreen", linewidth=2.0, linestyle="-", label = "ANT 61")
		plt.plot(self.time, self.I_val_cal[61], color="cyan", linewidth=2.0, linestyle="-", label = "ANT 62")
		plt.plot(self.time, self.I_val_cal[62], color="steelblue", linewidth=2.0, linestyle="-", label = "ANT 63")
		plt.plot(self.time, self.I_val_cal[63], color="blueviolet", linewidth=2.0, linestyle="-", label = "ANT 64")
		plt.legend(loc = 4)
"""
		plt.show()

	## RX calibraiton function
	def Rx_calibration(self, command, address, value):
		send_buff = command + address + self.flag + value
		for i in range(0, self.working_board):
			self.zynq_sock_list[i].sendto(send_buff.encode(),self.zynq_addr_list[i])

		self.Recv_mem_data(self.working_board)
		self.FFT_cal()
		output = ""
		output2 = ""

		for j in range(0, self.working_board):
			send_buff_cos = ""
			send_buff_sin = ""
			send_buff_2 = "check"
			for i in range(1, 17):
				max_phase = self.get_max_phase_val((j*16) + (i - 1))
				# I value
				X = np.cos(max_phase) * 0.7
				if(X < 0):
					cos_val = int(4096 - abs(X*(2048)))
				else:
					cos_val = int(X*(2048))
				send_buff_cos = send_buff_cos + " " + hex(cos_val)
				
				
				# Q value
				Y =  np.sin(max_phase) * 0.7
				if(Y < 0):
					sin_val = int(4096 - abs(Y*(2048)))
				else:
					sin_val = int(Y*(2048))
				send_buff_sin = send_buff_sin + " " + hex(sin_val)

				output = output + "ANT " + str(j*16 + i) + "	"
				output = output + "degree:	" + str(self.get_angle_data((j*16) + (i-1))) + "  " + str(self.get_angle_data((j*16) + (i-1)) - self.get_angle_data(0)) + " \n"
				#output = output + " \n phase 		: " + str(max_phase)
				#output = output + " \n index		: " + str(self.get_max_abs_idx(0)) + "\n===========\n"
				
				sin_val = ""
				cos_val = ""

				if(i%4 == 0):
					send_buff_2 = send_buff_2 + send_buff_cos + send_buff_sin
					send_buff_cos = ""
					send_buff_sin = ""

			print(send_buff_2)
			self.zynq_sock_list[j].sendto(send_buff_2.encode(),self.zynq_addr_list[j])
		
		self.cal_check = self.cal_check + 1
		# clear
		self.abs_data = []
		self.phase_data = []
		self.angle_data = []
		self.line_I = []
		self.line_Q = []
		self.Rx_Queue = []

		# re_recv
		self.Recv_mem_data(self.working_board)
		self.FFT_cal()

		for j in range(0, self.working_board):
			for i in range(0, 16):
				output2 = output2 + "ANT " + str(j*16 + i) + "	"
				output2 = output2 + "degree:	" + str(self.get_angle_data((j*16) + i)) + "  " + str(self.get_angle_data((j*16) + i) - self.get_angle_data(0)) +" \n"
				#output2 = output2 + " \n phase 		: " + str(self.get_max_phase_val((j*16) + i))
				#output2 = output2 + " \n index		: " + str(self.get_max_abs_idx(0)) + "\n===========\n"

		self.show_IQ_chart()

		#clear
		self.abs_data = []
		self.phase_data = []
		self.angle_data = []
		self.line_I = []
		self.line_Q = []
		self.cal_check = self.cal_check + 1
		self.I_val_uncal = []
		self.I_val_cal = []
		for i in range(0, self.working_board*16):
			self.I_val_uncal.append([])
			self.I_val_cal.append([])

		return output, output2

	## Return max index for called Antenna
	def get_max_abs_idx(self, ANT_NUM):
		max_idx = np.where(self.abs_data[0] == max(self.abs_data[0]))
		return max_idx
	
	## Return angle data for called Antenna
	def get_angle_data(self, ANT_NUM):
		if(ANT_NUM == 31):
			ANT_NUM = ANT_NUM - 3
		value = self.angle_data[ANT_NUM][self.get_max_abs_idx(0)]
		value = value - 6.98126421
		if(value < 0):
			value = value + 360
		return value.astype(int)

	## Return max phase for called Antenna
	def get_max_phase_val(self, ANT_NUM):
		value = self.phase_data[ANT_NUM][self.get_max_abs_idx(0)]
		value = value - 0.12184605
		if(value < 0):
		#	print("ANT under zero: ", ANT_NUM, "\n")
			value = value + 2*np.pi		
		return value
	
	## Tx reset sweep init to 0x0
	def Tx_reset(self, command, address, value):
		send_buff_1 = command + address + self.flag + value
		for i in range(0, self.working_board):
			self.zynq_sock_list[i].sendto(send_buff_1.encode(),self.zynq_addr_list[i])

	## TX calibration
	def Tx_cal(self, command, address, value):
		degree_list = []
		send_buff_1 = command + address + self.flag + value
		for i in range(0 , self.working_board):
			self.zynq_sock_list[i].sendto(send_buff_1.encode(),self.zynq_addr_list[i])

		self.ni_sock.sendto(self.ni_set_data.encode(), self.ni_addr)
		print("wating...\n")
		recv_data, recv_addr = self.ni_sock.recvfrom(1000)
		recv_data = recv_data.decode()

		data = "check 0x0"
		degree_data_var = 0

		for i in range(0, self.working_board):
			if(i == 0):
				for j in range(0, 15):
					degree_data_var = 360 - float(recv_data.split(' ').pop(j))
					print("ANT_", (i*16) +  j+1, ": ", degree_data_var, "\n")
					degree_data_var = int(degree_data_var/6.1111)
					degree_data_var = hex(degree_data_var)
					data = data + " " + degree_data_var
					degree_data_var = 0
			else:
				for j in range(15, 31):
					degree_data_var = 360 - float(recv_data.split(' ').pop(j))
					print("ANT_", j+1, ": ", degree_data_var, "\n")
					degree_data_var = int(degree_data_var/6.1111)
					degree_data_var = hex(degree_data_var)
					data = data + " " + degree_data_var
					degree_data_var = 0

			self.zynq_sock_list[i].sendto(data.encode(),self.zynq_addr_list[i])
			data = "check"

		self.ni_sock.sendto(self.ni_set_data.encode(), self.ni_addr)
		recv_data, recv_addr = self.ni_sock.recvfrom(1000)
		print(recv_data.decode())

	##TX OR RX ENABLE / DISABLE 
	def EnDis_write(self, command, address, value, bd):
		buff = command + address + self.flag + value
		self.zynq_sock_list[bd].sendto(buff.encode(),self.zynq_addr_list[bd])

	##READ DESIGNATED SFR AREA
	def SFR_read(self, command, address, value, bd):
		buff = command + address + self.flag + value
		self.zynq_sock_list[bd].sendto(buff.encode(),self.zynq_addr_list[bd])
		data, addr= self.zynq_sock_list[bd].recvfrom(300)
		return data.decode()

	##WRITE DESIGNATED SFR AREA
	def SFR_write(self, command, address, value, bd):
		buff = command + address + self.flag + value
		self.zynq_sock_list[bd].sendto(buff.encode(),self.zynq_addr_list[bd])