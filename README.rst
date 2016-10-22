This project provides a unified and configurable interface to various user notification methods.
Currently android and ios push notification services have been implemented.


Install
=======
Install these debian packages:

  - build-essential
  - rsync
  - python-dev
  - virtualenv
  - python-pip
  - redis-server
  - supervisor
  - tcpdump

Create and activate the virtualenv:

  ``virtualenv venv``
  
  ``source venv/bin/activate``

Install required python packages inside the virtualenv

  ``pip install -r requirements.txt``


Interface
=========


GCM
---
Sample http call
::

  POST https://gcm-http.googleapis.com/gcm/send
  Content-Type:application/json
  Authorization:key={{ auth-key }}
  {
    "to": "/topics/foo-bar",
    "data": {
      "message": "This is a GCM Topic Message!",
     }
  }


FCM
---
Firebase is similar to GCM

http and https proxies for connection are supported.


APNS
----
To convert the cert and key from p12 file to pem format:

  ``openssl pkcs12 -nokeys -clcerts -passin pass: -in filename.p12 -out cert.pem``
  
  ``openssl pkcs12 -nocerts -nodes -passin pass: -in filename.p12 -out key.pem``

http, socks4 and socks5 proxies for connection are supported.


Usage
=====

pontiac-server
--------------
To install and run the service:

  ``sudo make install && make run``

You can also use the provided supervisor configuration.

To send a notification request:

  ``echo '[{"type": "fcm", "tokens":[""], "title": "tt", "body": "bb", "badge": 1, "silent": false, "expiry_time": "2017-01-01 11:22:33", "custom_data": {}}]' | http -v --json post http://localhost:1234/notif``
  ``echo '[{"type": "apns", "tokens":[""], "title": "tt", "body": "bb", "badge": 1, "silent": false, "expiry_time": "2017-01-01 11:22:33", "custom_data": {}}]' | http -v --json post http://localhost:1234/notif``

pontiac-cli
-----------
Sample usage for FCM:

  ``./pontiac-cli.py -v fcm --proxy "http://localhost:8080" --api-key "" --reg-id "" -- '{"message_title": "tiTle", "message_body": "bODy"}'``

Sample usage for APNS

  ``./pontiac-cli.py -v apns --cert cert.pem --key key.pem --token "" -- '{"alert": "aLErt", "badge": 1, "sound": "default", "category": "mycat", "content-available": false, "custom-data": {"key1": "value1"}}'``
  ``./pontiac-cli.py -v apns --proxy "http://localhost:8080" --cert cert.pem --key key.pem --release --token "" -- '{"sound": null, "category": "mycat", "content-available": true, "custom-data": {"key1": "value1"}}'``


Abstract Notification Syntax
----------------------------
Application API key (in case of FCM) and application certificate and key files
(in case of APNS), should have already been set in application settings.

notifications should be sent in the following json formatted document:
::

  [
    {
      "type": ["fcm" | "apns"] // push notification service name
      "tokens": ["", ...] // list of client identifiers which we want to send notification to
      "title": "" // notification title. only supported on android
      "body": "" // notification message body. APNS calls this "alert".
      "badge": num // an integer which will stick besides an application icon on iOS
      "sound": "name" // a pre-defined sound name to be played on notification arrival
      "category": "" // an application defined identifier to make it possible to differentiate between different message types. iOS 8+.
      "silent": bool // whether notification is silent for the user and only for waking up the application on client device
      "expiry_time": datetime+tz // the time after which notification is considered expired and does not need further processing and can be dropped
      "custom_data": object // application-specified message payload meaningful solely to client app
    }
  ]


Proxy
-----
If you want to use a proxy, try to use a http proxy server (CONNECT tunnel) for
connecting to push notification servers. SOCKS proxies are not well supported and
might not work. If you only have a SOCKS proxy, you can use software like polipo
use it as a HTTP proxy.


polipo
~~~~~~
If you see a "403 Forbidden Port" error message from polipo when attempting to browse to a host:port,
you need to configure polipo to accept traffic to more ports for either HTTP or HTTPS.
To set them wide open, add the following to /etc/polipo/config:
::

  allowedPorts = 1-65535
  tunnelAllowedPorts = 1-65535

Unlike other proxies, Polipo needs to be restarted after alterations.


tinyproxy
~~~~~~~~~
If you get "403 Access violation" error message, you should allow all ports when CONNECT proxy
is requested. To do this uncomment all ``ConnectPort`` lines in /etc/tinyproxy.conf and restart
tinyproxy.


Profile
=======
To profile API performance:

  ``httperf -v --server hostname --port 80 --uri /notif --method GET --http-version 1.0 --hog --num-conns 10000 --rate 1000 --timeout 10``
  ``ab -v 1 -n 1000 -c 100 -s 10 http://hostname:port/notif``

To debug the API on the wire:

  ``ssh -p 8522 user@host "sudo tcpdump -i any -U -s 0 -w - 'host 192.168.104.1 and tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'" | wireshark -k -i -``
