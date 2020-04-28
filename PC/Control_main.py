"""
//------------------------------------//
// AUTHOR   : Youngchan Lim
//------------------------------------//
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, pyqtSignal,  QThread, QTimer
from PyQt5 import uic
from Zynq_wrapper import Zynq
from NI_udp import NI
import sys
import socket

#GUI
form_class = uic.loadUiType("bf_controlbox.ui")[0]

class MyWindow(QMainWindow, form_class):
	def __init__(self):
		super().__init__()
		self.setupUi(self)

		self.working_board = 3

		### Each ARTIX SFR starting address
		self.ARTIX_Address_list = [0x40400000, 0x40c00000, 0x41400000, 0x41c00000]
		self.ARTIX_Address = 0x40400000
		self.ARTIX_number = 1
		self.Board_number = 1
		self.flag = " "
		self.Zynq_obj = Zynq(self.working_board) 

		### button reaction on UI
		self.btn_Stop.clicked.connect(lambda:self.Stop())
		self.btn_BOARD_select.clicked.connect(lambda:self.BOARD_select(int(self.BOARD_comboBox.currentText())))
		self.btn_ARTIX_select.clicked.connect(lambda:self.ARTIX_select(int(self.ARTIX_comboBox.currentText())))

		 ## Rx calibration
		self.btn_Rx_cal_board.clicked.connect(lambda:self.Rx_cal("l ", self.ARTIX_Address, "0x0"))
		self.btn_rx_cal_comp_bp.clicked.connect(lambda:self.EnDis_write("b ", self.ARTIX_Address, "0x2C9", self.Board_number - 1))
		
		 ## Tx calibration
		self.btn_Tx_cal.clicked.connect(lambda:self.Tx_cal("t ", self.ARTIX_Address, "0x0"))
		self.btn_Tx_reset.clicked.connect(lambda:self.Tx_reset("p ", self.ARTIX_Address, "0x0"))
		
		self.btn_Tx_en.clicked.connect(lambda:self.EnDis_write("w ", self.ARTIX_Address, "0x20", self.Board_number - 1)) #global 0x20
		self.btn_Tx_dis.clicked.connect(lambda:self.EnDis_write("w ", self.ARTIX_Address, "0x0", self.Board_number - 1))
		self.btn_Rx_en.clicked.connect(lambda:self.EnDis_write("w ", self.ARTIX_Address, "0x10", self.Board_number - 1))
		self.btn_Rx_dis.clicked.connect(lambda:self.EnDis_write("x ", self.ARTIX_Address, "0x0", self.Board_number - 1))
		
		self.btn_SFR_write.clicked.connect(lambda:self.SFR_write("w ", self.SFR_address.text(), self.SFR_input.text(), self.Board_number - 1))
		self.btn_SFR_read.clicked.connect(lambda:self.SFR_read("r ", self.SFR_address.text(), "0", self.Board_number - 1))

		self.btn_Retro.clicked.connect(lambda:self.SFR_write("c ", "0x0", "0x0", 0))
		self.btn_Retro_2.clicked.connect(lambda:self.SFR_write("s ", "0x0", "0x0", 0))

	##BOARD_SELECT
	def BOARD_select(self, value):
		self.Board_number = value
		print("BOARD: ",self.Board_number,"ARTIX: ", self.ARTIX_number)
	
	##ARTIX_SELECT
	def ARTIX_select(self, value):
		self.ARTIX_Address = self.ARTIX_Address_list[value-1]
		self.ARTIX_number = value
		print("BOARD: ",self.Board_number,"ARTIX: ", self.ARTIX_number)

	##PRINT DESIGNATED SFR VALUE 
	def Text_view(self, output):
		self.SFR_output.clear()
		self.SFR_output.setPlainText(output)

	def Text_view_2(self, output):
		self.value_output1.clear()
		self.value_output1.setPlainText(output)

	def Text_view_3(self, output):
		self.value_output2.clear()
		self.value_output2.setPlainText(output)

	##Tx calibration
	def Tx_cal(self, command, address, value):
		address = str(address)
		self.Zynq_obj.Tx_cal(command, address, value)

	##Tx sweep init reset
	def Tx_reset(self, command, address, value):
		address = str(address)
		self.Zynq_obj.Tx_reset(command, address, value)

	##READ DESIGNATED SFR AREA
	def SFR_read(self, command, address, value, bd):
		address = hex(int(address, 16) + self.ARTIX_Address)
		result = self.Zynq_obj.SFR_read(command, address, value, bd)
		self.Text_view(result)

	##WRITE DESIGNATED SFR AREA
	def SFR_write(self, command, address, value, bd):
		address = hex(int(address, 16) + self.ARTIX_Address)
		self.Zynq_obj.SFR_write(command, address, value, bd)
		if(command == "c " or command == "s "):
			for i in range(1, self.working_board):
				self.Zynq_obj.SFR_write(command, address, value, i)
	
	##TX OR RX ENABLE / DISABLE 
	def EnDis_write(self, command, address, value, bd):
		address = hex(address)
		self.Zynq_obj.EnDis_write(command, address, value, 0)
		if(command == "x " or command == 'b '):
			for i in range(1, self.working_board):
				self.Zynq_obj.EnDis_write(command, address, value, i)

	## RX calibraiton function
	def Rx_cal(self, command, address, value):
		address = hex(address)
		output1, output2 = self.Zynq_obj.Rx_calibration(command, address, value)
		self.Text_view_2(output1)
		self.Text_view_3(output2)

	##SHUTDOWN
	def Stop(self):
		sys.exit(0)

if __name__ == "__main__":
	app = QApplication(sys.argv)
	myWindow = MyWindow()
	myWindow.show()
	app.exec_()