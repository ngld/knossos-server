# Knossos server tools

Various scripts / tools which are related to Knossos but belong on a server, not on the client.

## Dependencies

To run these scripts you'll need the following:
* [Python][py] 3
* [Six][six]
* [7zip][7z] (IMPORTANT: This script needs the full implementation, i.e. ```p7zip-full``` _and_ ```p7zip-rar``` on Ubuntu)
* [semantic_version][sv]

The following commands should install everything you need:
* Ubuntu: ```apt-get install python3 python3-six p7zip-full p7zip-rar```
* Arch Linux: ```pacman -S python python-six p7zip```

## Usage

Take a look at the scripts in the root directory.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
The third party code contained in third_party and static is licensed under the MIT License. The relevant files are marked accordingly.

[py]: http://www.python.org/
[six]: https://pypi.python.org/pypi/six/
[7z]: http://www.7-zip.org/
[sv]: https://pypi.python.org/pypi/semantic_version
