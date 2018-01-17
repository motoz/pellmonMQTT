#! /usr/bin/python
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
import os
import sys
import argparse
from gi.repository import Gio, GLib, GObject
from time import sleep
import paho.mqtt.client as mosquitto
import simplejson

class DbusNotConnected(Exception):
    pass

class Dbus_handler:
    def __init__(self, mq, bus='SESSION'):
        if bus=='SYSTEM':
            self.bustype=Gio.BusType.SYSTEM
        else:
            self.bustype=Gio.BusType.SESSION
        self.mq = mq

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
        print "connected"
        self.notify = Gio.DBusProxy.new_sync(
            self.bus,
            Gio.DBusProxyFlags.NONE,
            None,
            'org.pellmon.int',
            '/org/pellmon/int',
            'org.pellmon.int',
            None)
        #Publish all data items tagged with 'All' to pellmon/_item_
        self.db = self.notify.GetFullDB('(as)',['All',])
        for item in self.db:
            try:
                value = self.getItem(item['name'])
                print 'Publish %s to pellmon/%s'%(value, item['name'])
                self.mq.publish("pellmon/%s"%item['name'], value, qos=2, retain=True)
            except:
                pass

        #Subscribe to all data items tagged with 'Settings' at pellmon/settings/_item
        self.settings = self.notify.GetFullDB('(as)',['Settings',])
        for item in self.settings:
            print 'Subscribe to pellmon/settings/%s'%item['name']
            self.mq.subscribe("pellmon/settings/%s"%item['name'])

        #Listen to the DBUS 'item changed' signal and publish changes at pellmon/_item_
        def on_signal(proxy, sender_name, signal_name, parameters):
            p = parameters[0]
            msg = []
            msg = simplejson.loads(p)
            print msg	
            for d in msg:
                self.mq.publish("pellmon/%s"%d['name'], d['value'], qos=2, retain=True)
                print 'Publish %s to pellmon/%s'%(d['value'], d['name'])

        self.notify.connect("g-signal", on_signal)

    def dbus_disconnect(self, connection, name):
        if self.notify:
            self.notify = None

    def getItem(self, itm):
        if self.notify:
            try:
                return self.notify.GetItem('(s)',itm)
            except:
                return 'error'
        else:
            raise DbusNotConnected("server not running")

    def setItem(self, item, value):
        if self.notify:
            return self.notify.SetItem('(ss)',item, value)
        else:
            raise DbusNotConnected("server not running")

    def getdb(self):
        if self.notify:
            return self.notify.GetDB()
        else:
            raise DbusNotConnected("server not running")

    def getDBwithTags(self, tags):
        if self.notify:
            return self.notify.GetDBwithTags('(as)',tags)
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

class config:
    pass

if __name__ == "__main__":
    
    def on_connect(*args):
        print "Connected";
       
    def on_publish(*args):
        pass #print 'published'

    def on_subscribe(*args):
        pass #print 'subscribed'

    def on_message(*args):
        """Call the DBUS setItem method with item name and payload from topic subscription at pellmon/settings/_item_"""
        msg = args[-1]
        item = msg.topic.split('/')[-1]
        try:
            print 'Set %s=%s, %s'%(item, msg.payload, dbus.setItem(item, msg.payload))
        except:
            pass


    parser = argparse.ArgumentParser(prog='pellmonMQTT')
    parser.add_argument('-H', '--host', default='localhost', help='mqtt host to connect to. Defaults to localhost')
    parser.add_argument('-p', '--port', default='1883', help='network port to connect to. Defaults to 1883')
    parser.add_argument('-d', '--dbus', default='SESSION', choices=['SESSION', 'SYSTEM'], help='which bus to use, SESSION is default')

    args = parser.parse_args()

    GObject.threads_init()

    # A main loop is needed for dbus "name watching" to work
    main_loop = GLib.MainLoop()
    
    #create a broker
    mqttc = mosquitto.Client(protocol=mosquitto.MQTTv311)
    mqttc.on_connect = on_connect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_message = on_message
    connect = False
    while not connect:
        try:
            mqttc.connect(args.host, args.port, 60)
            #mqttc.reconnect_delay_set(120, 300, True)
            #mqttc.reconnect_delay_set(120, 300, True)    
            connect = True
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print e
            sleep(5)
    
    mqttc.loop_start()

    dbus = Dbus_handler(mqttc, args.dbus)
    dbus.start()

    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass
