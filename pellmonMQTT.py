#! /usr/bin/python3
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
from __future__ import print_function
from builtins import object
import os
import sys
import argparse
from time import sleep
from gi.repository import Gio, GLib, GObject
import paho.mqtt.client as mosquitto
import simplejson

class DbusNotConnected(Exception):
    pass

class Dbus_handler(object):
    def __init__(self, mq, bus, mqttTopic):
        if bus == 'SYSTEM':
            self.bustype = Gio.BusType.SYSTEM
        else:
            self.bustype = Gio.BusType.SESSION
        self.mq = mq
        self.mqttTopic = mqttTopic

    def start(self):
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
        print("dbus connected")
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
                print('Publish %s to %s/%s'%(self.mqttTopic, value, item['name']))
                self.mq.publish("%s/%s"%(self.mqttTopic, item['name']), value, qos=2, retain=True)
            except:
                pass

    def subscribe(self):
        #Listen to the DBUS 'item changed' signal and publish changes at pellmon/_item_
        def on_signal(proxy, sender_name, signal_name, parameters):
            p = parameters[0]
            msg = []
            msg = simplejson.loads(p)
            print(msg)
            for d in msg:
                self.mq.publish("%s/%s"%(self.mqttTopic, d['name']), d['value'], qos=2, retain=True)
                print('Publish %s to %s/%s'%(d['value'], self.mqttTopic, d['name']))
        #Subscribe to all data items tagged with 'Settings' at pellmon/settings/_item
        self.settings = self.notify.GetFullDB('(as)', ['All',])
        for item in self.settings:
            if item['type'] in ('W', 'R/W'):
                print('Subscribe to %s/settings/%s'%(self.mqttTopic, item['name']))
                self.mq.subscribe("%s/settings/%s"%(self.mqttTopic, item['name']))

        self.notify.connect("g-signal", on_signal)

    def dbus_disconnect(self, connection, name):
        Status.dbus_connected = False
        Status.subscribed = False
        if self.notify:
            self.notify = None

    def getItem(self, itm):
        if self.notify:
            try:
                return self.notify.GetItem('(s)', itm)
            except:
                return 'error'
        else:
            raise DbusNotConnected("server not running")

    def setItem(self, item, value):
        if self.notify:
            return self.notify.SetItem('(ss)', item, value)
        else:
            raise DbusNotConnected("server not running")

    def getdb(self):
        if self.notify:
            return self.notify.GetDB()
        else:
            raise DbusNotConnected("server not running")

    def getDBwithTags(self, tags):
        if self.notify:
            return self.notify.GetDBwithTags('(as)', tags)
        else:
            raise DbusNotConnected("server not running")

    def getFullDB(self, tags):
        if self.notify:
            db = self.notify.GetFullDB('(as)', tags)
            return db
        else:
            raise DbusNotConnected("server not running")

    def getMenutags(self):
        if self.notify:
            return self.notify.getMenutags()
        else:
            raise DbusNotConnected("server not running")

class Status(object):
    mqtt_connected = False
    dbus_connected = False
    subscribed = False

if __name__ == "__main__":

    def on_connect(*args):
        print("broker connected")
        Status.subscribed = False
        Status.mqtt_connected = True

    def on_publish(*args):
        pass #print 'published'
        print('published')

    def on_subscribe(*args):
        pass #print 'subscribed'
        print('subscribed')

    def on_disconnect(*args):
        print("disconnected from MQTT: ")
        mqtt_connected = False

    def on_message(*args):
        """Call the DBUS setItem method with item name and payload from topic subscription at pellmon/settings/_item_"""
        print('subscribed item changed')
        msg = args[-1]
        item = msg.topic.split('/')[-1]
        try:
            print('Set %s=%s, %s'%(item, msg.payload, dbus.setItem(item, msg.payload)))
        except:
            pass

    def manager():
        if not Status.subscribed:
            print('Not subscribed')
            if Status.dbus_connected and Status.mqtt_connected:
                print('subscribing...')
                dbus.subscribe()
                Status.subscribed = True
        return True

    parser = argparse.ArgumentParser(prog='pellmonMQTT')
    parser.add_argument('-H', '--host', default='localhost', help='mqtt host to connect to. Defaults to localhost')
    parser.add_argument('-p', '--port', default='1883', help='network port to connect to. Defaults to 1883')
    parser.add_argument('-d', '--dbus', default='SESSION', choices=['SESSION', 'SYSTEM'], help='which bus to use, SESSION is default')
    parser.add_argument('-t', '--topic', default='pellmon', help='Defines the topic to publish/listen to, default is pellmon')
    parser.add_argument('-u', '--username', default='', help='Define a username which will be used to connect to the mqtt broker')
    parser.add_argument('-P', '--password', default='', help='Define a password which will be used to connect to the mqtt broker')
    args = parser.parse_args()

    GObject.threads_init()

    # A main loop is needed for dbus "name watching" to work
    main_loop = GLib.MainLoop()

    GLib.timeout_add_seconds(1, manager)

    #create a broker
    mqttc = mosquitto.Client(protocol=mosquitto.MQTTv311)
    mqttc.on_connect = on_connect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_message = on_message

    dbus = Dbus_handler(mqttc, args.dbus, args.topic)
    dbus.start()

    connect = False
    while not connect:
        try:
            mqttc.username_pw_set(username=args.username, password=args.password)
            mqttc.connect(args.host, int(args.port), 60)
            #mqttc.reconnect_delay_set(120, 300, True)
            #mqttc.reconnect_delay_set(120, 300, True)
            mqttc.reconnect_delay_set(min_delay=1, max_delay=120)
            connect = True
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(e)
            sleep(5)

    mqttc.loop_start()

    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass
