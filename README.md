pellmonMQTT
===========

An MQTT client for PellMon.

PellmonMQTT connects to the PellMon DBUS interface and publishes all data at pellmon/_item_ and subscribes to all settings at pellmon/settings/_item_. Changed data items are republished and received data is written to the corresponding PellMon _item_. 


####Usage:
<pre>usage: pellmonMQTT [-h] [-H HOST] [-p PORT] [-d {SESSION,SYSTEM}]

optional arguments:
  -h, --help            show this help message and exit
  -H HOST, --host HOST  mqtt host to connect to. Defaults to localhost
  -p PORT, --port PORT  network port to connect to. Defaults to 1883
  -d {SESSION,SYSTEM}, --dbus {SESSION,SYSTEM}
                        which bus to use, SESSION is default/pre>

