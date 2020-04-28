#! /bin/bash
echo `ifconfig eth0 down`
echo `ifconfig eth0 hw ether 04:AA:BB:CC:DD:EE`
echo `ifconfig eth0 192.168.0.8`
echo `ifconfig eth0 up`
echo `chmod 777 ./Test_D`
echo `./Test_D`
