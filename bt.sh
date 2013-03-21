#!/bin/sh

#How often to query BT device
SLEEP_TIME=10

if [ $# -lt 1 ] ; then
  echo "Need BT address"
  exit 1
fi

#bluetooth address to connect to
PC_BT_ADDR=$1

#####################################
# Some functions we need
#####################################

#This function tries upto 10 times to establish connection
# To your PC via bluetooth
rfcomm_loop () {
  cc=0
  while ! rfcomm connect 0 ${PC_BT_ADDR} 1 > /dev/null 2>&1 ; do
    cc=$(( $cc + 1 ))
    if [[ $cc -gt 10 ]]; then
       echo "Too many failed attempts, aborting"
       return 1
    fi
    echo "retrying in 3 seconds"
    sleep 3
  done

  return $?
}

######################################
#  Script starts here
######################################

#Wait for user to enable bluetooth
cc=0
while ! hciconfig hci0 > /dev/null 2>&1 ; do
  cc=$(( $cc + 1 ))
  if [[ $cc -gt 60 ]] ; then
    echo "User didn't enable bluetooth, giving up"
    exit 1
  fi
  echo "waiting for bluetooth..."
  sleep $SLEEP_TIME
done

echo "Have hci0"
hciconfig -a hci0

#Launch rfcomm
sleep 2
echo "Attempting to connect to:" ${PC_BT_ADDR}
rfcomm_loop > /dev/null 2>&1 &

sleep 5
cc=0
#Wait for rfcomm to come up
while ! rfcomm show rfcomm0 > /dev/null 2>&1 ; do 
  cc=$(( $cc + 1 ))
  if [[ $cc -gt 20 ]] ; then
    echo "Failed to get rfcomm0 connection"
    exit 1
  fi
  echo "Waiting for rfcomm0 connection"
  sleep 5
done

echo "Have rfcomm0"
rfcomm show rfcomm0

