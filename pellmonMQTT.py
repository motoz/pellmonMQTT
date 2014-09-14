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
import readline, os
import sys
import argparse
from gi.repository import Gio, GLib, GObject
import mosquitto

class DbusNotConnected(Exception):
    pass

class Dbus_handler:
    def __init__(self, bus='SESSION'):
        if bus=='SYSTEM':
            self.bustype=Gio.BusType.SYSTEM
        else:
            self.bustype=Gio.BusType.SESSION

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
        print 's'

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
        self.db = self.notify.GetDB()
        print self.db
        for item in self.db:
            print item
            mqttc.publish("pellmon/%s"%item, self.getItem(item))
        
        def on_signal(proxy, sender_name, signal_name, parameters):
            p = parameters[0]
            msg = []
            l = p.split(';')
            for ds in l:
                d= ds.split(':')
                mqttc.publish("pellmon/%s"%d[0], d[1])
                print d[0],d[1]

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

       
if __name__ == "__main__":
    
    def on_connect(*args):
        print "Connected";
       
    def on_publish(*args):
        print 'published'
    
    #GObject.threads_init()
    
    #create a broker
    mqttc = mosquitto.Mosquitto("python_sub")
    #mqttc.on_connect = on_connect
    mqttc.on_publish = on_publish
    mqttc.connect("192.168.1.4", 1883, 60, True)

    # A main loop is needed for dbus "name watching" to work
    main_loop = GLib.MainLoop()
    
    def publish():
        print dbus.getdb()
 
    #GLib.timeout_add(100, publish)



    dbus = Dbus_handler('SYSTEM')
    dbus.start()
    print 'started'
    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass
