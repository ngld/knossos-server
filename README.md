# Knossos server tools

Various scripts / tools which are related to Knossos but belong on a server, not on the client.

## Dependencies

To run these scripts you'll need the following:
* [Python][py] 3
* [Six][six]
* [7zip][7z] (IMPORTANT: This script needs the full implementation, i.e. ```p7zip-full``` _and_ ```p7zip-rar``` on Ubuntu)
* [semantic_version][sv]
* [Redis][redis]

The following commands should install everything you need:
* Ubuntu: ```apt-get install python3 python3-six p7zip-full p7zip-rar```
* Arch Linux: ```pacman -S python python-six p7zip```

## Installation

1. Install the dependencies listed in ```requirements.txt``` (```pip install -r requirements.txt```).
2. Copy ```conf/settings.py.dist``` to ```conf/settings.py``` and change it to fit your environment.

## Usage

If you're developing or want to get the server running quickly, you can run the ```launch.sh``` script.

The server consists of three components:

* ```server.py```: This is a normal WSGI application which can run on a WSGI server (mod_wsgi, uwsgi, gunicorn, etc.)
  it servers all regular HTTP requests and is implemented using [Flask][fsk]. You can also run the script directly to
  launch it without a WSGI server.

* ```websocket_server.py```: This part is implemented using [Tornado][torn] and handles all WebSocket requests.
  *IMPORTANT:* At any point in time there should only be *one* process running this script.

* ```worker.py```: This part does most of the actual work. You can run as many instances of this as you want.
  It doesn't listen as a server but connects to Redis.


All three components communicate over Redis. ```server.py``` and ```websocket_server.py``` should be reachable over the same domain and port.
One possible setup is to run [uwsgi][uwsgi] with the provided config in ```conf/app.ini``` which will properly distribute the requests.

You should run the ```cron.py``` script about once per day, it removes old / unused data from the Redis store.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
The third party code contained in third_party and static is licensed under the MIT License. The relevant files are marked accordingly.

[py]: http://www.python.org/
[six]: https://pypi.python.org/pypi/six/
[7z]: http://www.7-zip.org/
[sv]: https://pypi.python.org/pypi/semantic_version
[redis]: http://redis.io/
[fsk]: http://flask.pocoo.org/
[torn]: http://www.tornadoweb.org/en/stable/
[uwsgi]: https://uwsgi-docs.readthedocs.io/en/latest/
