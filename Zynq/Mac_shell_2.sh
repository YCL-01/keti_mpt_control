#! /bin/bash
echo `ifconfig eth0 down`
echo `ifconfig eth0 hw ether 02:AA:BB:CC:DD:EE`
echo `ifconfig eth0 192.168.0.6`
echo `ifconfig eth0 up`
echo `chmod 777 ./Test_B`
