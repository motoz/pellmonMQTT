#! /usr/bin/python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mosquitto

#define what happens after connection
def on_connect(*args):
    print(Connected);

#On recipt of a message
def on_message(*args):
    msg = args[-1]
    print(msg.topic, msg.payload)

#create a broker
mqttc = mosquitto.Mosquitto()

#define the callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect

#connect
mqttc.connect("192.168.1.4", 1883, 60, True)

#subscribe to all pellmon data
mqttc.subscribe("pellmon/+")

#keep connected to broker
while True:
    mqttc.loop()
    pass

