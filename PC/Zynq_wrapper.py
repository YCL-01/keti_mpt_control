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
from time import sleep

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

		for i in range(0, self.working_board):
			self.zynq_sock_list[i].setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 6000)
			self.zynq_sock_list[i].connect(self.zynq_addr_list[i])

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
		self.label_list = []
		for i in range(0, self.working_board*16):
			self.I_val_uncal.append([])
			self.I_val_cal.append([])
			label = "ANT %d" % (i+1)
			self.label_list.append(label)

		self.cal_check = 1
		self.color_list = ["maroon","firebrick","red","orangered","coral","orange","gold","darkolivegreen","olive","olivedrab",
		"limegreen","lawngreen","springgreen","cyan","steelblue","blueviolet"]
		self.graph_status = ["I val before","I val after"]
		self.title_list = ["BOARD A ","BOARD B ","BOARD C ","BOARD D "]
		
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
	
	## FFT calculation
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

		for j in range(0, self.working_board):
			plt.subplot(2,self.working_board,j+1)
			plt.title(self.title_list[j] + self.graph_status[0])
			for i in range(j*16,(j+1)*16):
				plt.plot(self.time, self.I_val_uncal[i], color = self.color_list[i%16], linewidth=2.0, linestyle="-", label = self.label_list[i])
			plt.legend(loc = 4)

		for j in range(0, self.working_board):
			plt.subplot(2,self.working_board,self.working_board + j + 1)
			plt.title(self.title_list[j] + self.graph_status[1])
			for i in range(j*16,(j+1)*16):
				plt.plot(self.time, self.I_val_cal[i], color = self.color_list[i%16], linewidth=2.0, linestyle="-", label = self.label_list[i])
			plt.legend(loc = 4)

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

				output = output + "ANT " + str(j*16 + i-1) + "	"
				output = output + "degree:	" + str(self.get_angle_data((j*16) + (i-1))) + "  " + str(self.get_angle_data((j*16) + (i-1)) - self.get_angle_data(0)) + " \n"
				
				sin_val = ""
				cos_val = ""

				if(i%4 == 0):
					send_buff_2 = send_buff_2 + send_buff_cos + send_buff_sin
					send_buff_cos = ""
					send_buff_sin = ""
					output = output + "\n"

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

				if((i+1)%4 == 0):
					output2 = output2 + "\n"

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
