#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
    Copyright (C) 2013  Anders Nylund
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from builtins import object
import os
import sys
import argparse
from time import sleep
from gi.repository import Gio, GLib
import paho.mqtt.client as mosquitto
import simplejson

DEBUG = False

class DbusNotConnected(Exception):
    """ This exception is raised when Dbus is not connected. """
    print("DbusNotConnected: " + str(Exception))
    #pass

class Dbus_handler(object):
    """ The Dbus_handler """
    def __init__(self, mq, bus, mqttTopic):
        if DEBUG:
            print(">>>>> dbus_init")
        if bus == 'SYSTEM':
            self.bustype = Gio.BusType.SYSTEM
        else:
            self.bustype = Gio.BusType.SESSION
        self.mq = mq
        self.mqttTopic = mqttTopic

    def start(self):
        """ start """
        if DEBUG:
            print(">>>>> dbus_start")
        self.notify = None
        self.bus = Gio.bus_get_sync(self.bustype, None)
        Gio.bus_watch_name(
            self.bustype,
            'org.pellmon.int',
            Gio.DBusProxyFlags.NONE,
            self.dbus_connect,
            self.dbus_disconnect,
            )

    def dbus_connect(self, connection, name, owner):
        """ dbus_connect """

        if DEBUG:
            print(">>>>> dbus_connect")

        self.notify = Gio.DBusProxy.new_sync(
            self.bus,
            Gio.DBusProxyFlags.NONE,
            None,
            'org.pellmon.int',
            '/org/pellmon/int',
            'org.pellmon.int',
            None)
        Status.dbus_connected = True
        #Publish all data items tagged with 'All' to pellmon/_item_
        self.db = self.notify.GetFullDB('(as)', ['All',])

        for item in self.db:
            try:
                value = self.getItem(item['name'])
                print(f"Publish {str(value)} to {self.mqttTopic}/ {item['name']}")
                self.mq.publish(f"{self.mqttTopic}/{item['name']}", value, qos=2, retain=True)
            except RuntimeError as error:
                print("Exeption caught in Publish - dbus_connect: " + error)
                pass

    def subscribe(self):
        """Listen to the DBUS 'item changed' signal and publish changes at pellmon/_item_ """
        if DEBUG:
            print(">>>>> subscribe")
        def on_signal(proxy, sender_name, signal_name, parameters):
            parameter = parameters[0]
            msg = []
            msg = simplejson.loads(parameter)
            for dbusmsg in msg:
                self.mq.publish(f"{self.mqttTopic}/{dbusmsg['name']}", dbusmsg['value'], qos=2, retain=True)
                print(f"Publish {dbusmsg['value']} to {self.mqttTopic}/{dbusmsg['name']}")
        #Subscribe to all data items tagged with 'Settings' at pellmon/settings/_item
        self.settings = self.notify.GetFullDB('(as)', ['All',])
        for item in self.settings:
            if item['type'] in ('W', 'R/W'):
                #print('Subscribe to %s/settings/%s'%(self.mqttTopic, item['name']))
                print(f"Subscribe to {self.mqttTopic}/settings/{item['name']}")
                self.mq.subscribe(f"{self.mqttTopic}/settings/{item['name']}")

        self.notify.connect("g-signal", on_signal)

    def dbus_disconnect(self, connection, name):
        """ dbus_disconnect """
        if DEBUG:
            print(">>>>> dbus_disconnect")
        Status.dbus_connected = False
        Status.subscribed = False
        if self.notify:
            self.notify = None

    def getItem(self, itm):
        """ getItem """
        if DEBUG:
            print(">>>>> getItem")
        if self.notify:
            try:
                return self.notify.GetItem('(s)', str(itm))
            except RuntimeError:
                return 'error'
        else:
            raise DbusNotConnected("server not running")

    def setItem(self, item, value):
        """ setItem """
        if DEBUG:
            print(">>>>> setItem")
        if self.notify:
            return self.notify.SetItem('(ss)',item, str(value))
        raise DbusNotConnected("server not running")

    def getdb(self):
        """ getdb """
        if DEBUG:
            print(">>>>> getdb")
        if self.notify:
            return self.notify.GetDB()
        raise DbusNotConnected("server not running")

    def getDBwithTags(self, tags):
        """ getDBwithTags """
        if DEBUG:
            print(">>>>> getDBwithTags")
        if self.notify:
            return self.notify.GetDBwithTags('(as)', tags)
        raise DbusNotConnected("server not running")

    def getFullDB(self, tags):
        """ getFullDB """
        if DEBUG:
            print(">>>>> getFullDB")
        if self.notify:
            db = self.notify.GetFullDB('(as)', str(tags))
            return db
        raise DbusNotConnected("server not running")

    def getMenutags(self):
        """ getMenutags """
        if DEBUG:
            print(">>>>> getMenutags")
        if self.notify:
            return self.notify.getMenutags()
        raise DbusNotConnected("server not running")

class Status(object):
    """ Class Status """
    if DEBUG:
        print(">>>>> Status")
    mqtt_connected = False
    dbus_connected = False
    subscribed = False

###################
#     Main entry  #
###################
if __name__ == "__main__":

    """ Functions to be used by mqtt """
    def on_connect(*args):
        """ on_connect """
        print("broker connected")
        Status.subscribed = False
        Status.mqtt_connected = True

    def on_publish(*args):
        """ What do when calling on_publish """
        pass #print 'published'
        #print('Publishing')

    def on_subscribe(*args):
        """ on_subscribe """
        pass #print 'subscribed'
        #print('Subscribing')

    def on_disconnect(*args):
        """ on_disconnect """
        print("Disconnecting from MQTT: ")
        mqtt_connected = False

    def on_message(*args):
        """Call the DBUS setItem method with item name and payload
        from topic subscription at pellmon/settings/_item_"""
        print('subscribed item changed')
        msg = args[-1]
        item = msg.topic.split('/')[-1]
        try:
            dbus.setItem(item, msg.payload)
            #print('Set %s=%s, %s'%(item, msg.payload, dbus.setItem(item, msg.payload.decode("utf-8"))))
            print(f"Set {item}={msg.payload}, {dbus.setItem(item, msg.payload.decode('utf-8'))}" )
        except RuntimeError as error:
            print("Exception caught: " + error)
            pass

    def manager():
        """ Manager binding dbus and mqtt together """
        if not Status.subscribed:
            print('Manager: Not subscribed')
            if Status.dbus_connected and Status.mqtt_connected:
                print('Manager: subscribing...')
                dbus.subscribe()
                Status.subscribed = True
        return True

    parser = argparse.ArgumentParser(prog='pellmonMQTT')
    parser.add_argument('-H', '--host',
                        default='localhost',
                        help='mqtt host to connect to. Defaults to localhost')
    parser.add_argument('-p', '--port',
                        default='1883',
                        help='network port to connect to. Defaults to 1883')
    parser.add_argument('-d', '--dbus',
                        default='SESSION',
                        choices=['SESSION', 'SYSTEM'],
                        help='which bus to use, SESSION is default')
    parser.add_argument('-t', '--topic',
                        default='pellmon',
                        help='Defines the topic to publish/listen to, default is pellmon')
    parser.add_argument('-u', '--username',
                        default='', help='Define a username which will be used to connect to the mqtt broker')
    parser.add_argument('-P', '--password',
                        default='',
                        help='Define a password which will be used to connect to the mqtt broker')
    arguments = parser.parse_args()

    #GObject.threads_init()

    # A main loop is needed for dbus "name watching" to work
    main_loop = GLib.MainLoop()

    GLib.timeout_add_seconds(1, manager)

    #create a broker
    mqttc = mosquitto.Client(protocol=mosquitto.MQTTv311)
    mqttc.on_connect = on_connect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_message = on_message

    print("topic: " + arguments.topic + " connecting on " + arguments.dbus)
    dbus = Dbus_handler(mqttc, arguments.dbus, arguments.topic)
    dbus.start()

    connect = False
    print("MQTT broker not connected yet..")
    while not connect:
        try:
            mqttc.username_pw_set(username=arguments.username, password=arguments.password)
            mqttc.connect(arguments.host, int(arguments.port), 60)
            #mqttc.reconnect_delay_set(120, 300, True)
            #mqttc.reconnect_delay_set(120, 300, True)
            mqttc.reconnect_delay_set(min_delay=1, max_delay=120)
            connect = True
        except KeyboardInterrupt:
            print("Error caught on connect")
            raise
        except Exception as error:
            print(error)
            sleep(5)

    print("MQTT broker Connected..")
    print("Python version: " + str(sys.version))
    mqttc.loop_start()

    print("Connected to broker ", arguments.host)
    try:
        main_loop.run()
    except KeyboardInterrupt:
        print("Caught keyboard interrupt - MQTT broker leaving")
        mqttc.loop_stop()
        mqttc.disconnect()
        #pass
    finally:
        print("End of Job")
