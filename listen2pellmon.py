#! /usr/bin/python
# -*- coding: utf-8 -*-

import mosquitto

#define what happens after connection
def on_connect(rc):
    print "Connected";

#On recipt of a message create a pynotification and show it
def on_message(msg):
    print msg.topic, msg.payload

#create a broker
mqttc = mosquitto.Mosquitto("python_sub2")

#define the callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect

#connect
mqttc.connect("192.168.1.4", 1883, 60, True)

#subscribe to topic test
mqttc.subscribe("pellmon/+")

#keep connected to broker
while True:
    mqttc.loop()
    pass

