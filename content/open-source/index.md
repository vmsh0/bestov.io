---
title: "Open Source"
image: 'images/heading.png'
menus: main
---

# Open Source

Open Source is beautiful. I have made several contributions to Open Source software, in the form of patches, bug reports, translations, and donations. I have also released my own software. This page exists to keep track of what I consider to be my most relevant contributions to the world of Open Source.

## My software

I have released some software. It is mostly small and specific, but you never know who might share your use cases!

### accio

[accio](https://github.com/vmsh0/accio) is a set of a script and some configuration files that allows you to easily configure your Linux distribution to use LUKS2 Full Disk Encryption, and unlocking your computer on boot using a YubiKey. Please note that these days I discourage people from using Accio, as the same functionality has been integrated in systemd and is thus actively supported by some of the best minds in Open Source.

### wedge

[wedge](https://github.com/vmsh0/wedge) is a very small and simple C program with no dependencies. Its
only job is to translate a stream of serial data to Linux keyboard events. I wrote it as a result of a company's request
to port some of their Windows systems to Linux, and this "wedge" software they were using for their optical bar code
readers was the only blocking dependency. It includes configuration instructions, a systemd unit, and udev rules for
complete plug-and-play functionality.

wedge is a beautiful example of the Unix philosophy: it is a small single-purpose software that has been continuously
running in production since 2020 without a single incident.

## My contributions

There are some of the contributions I've made to Open Source projects.

### Linux Kernel
The [Linux Kernel](https://www.kernel.org/) is a modern Open Source operating system kernel used in many real-world applications such as servers, desktop computers, and smartphones.

I [contributed](https://patchwork.kernel.org/project/netdevbpf/patch/20211117090010.125393-1-pbl@bestov.io/) a fix to enable raw sockets to be bound to a nonlocal address. I also contributed a fix and regression tests coverage[[1]](https://patchwork.kernel.org/project/netdevbpf/patch/20220617085435.193319-1-pbl@bestov.io/)[[2]](https://patchwork.kernel.org/project/netdevbpf/patch/20220619162734.113340-1-pbl@bestov.io/) for a change of behaviour that was introduced as a result of my first patch.

### Duplicati
[Duplicati](https://duplicati.com/) is an incremental backup solution supporting many different cloud backends, including consumer and non-consumer ones, out of the box.

I [contributed](https://github.com/duplicati/duplicati/pull/4661) a patch implementing exponential backoff for failed storage-backend operations. Since most storage operations Duplicati performs are network-based, exponential backoff is a good idea to avoid generating useless traffic and getting banned from APIs for being too insistent, and it is also a better retries-limited retry strategy.

Please note that I currently can't endorse using Duplicati as a good solution for backing up anything important. Unfortunately, I've had it fail on me multiple times due to its [less-than-ideal](https://forum.duplicati.com/t/database-rebuild/13884) local database system.

### python-snap7
[python-snap7](https://github.com/gijzelaerr/python-snap7) is a Python library implementing bindings and utility objects for the [Snap7 library](https://snap7.sourceforge.net/), to communicate with Siemens S7 series PLCs.

I contributed multiple improvements, including:
* a [small fix](https://github.com/gijzelaerr/python-snap7/pull/377) for a broken feature
* a [new datatype](https://github.com/gijzelaerr/python-snap7/pull/378), not contained in the Siemens specs but very common in real-world systems
* a [partial refactor](https://github.com/gijzelaerr/python-snap7/pull/385) of one of the classes, to give it better-defined semantics and better documentation
* a [refactor](https://github.com/gijzelaerr/python-snap7/pull/386) of the library to only use relative imports

### OpenWRT

OpenWRT is a project developing an open firmware for routers and network appliances, and providing instructions and
information about running custom software on commercial network devices.

I contributed the [serial access pictures and information](https://openwrt.org/inbox/toh/technicolor/tg789vac_v2#serial)
for the Technicolor TG789vac v2, which is a device based on OpenWRT. I use this as an example about how non-programmers
can give very useful contributions to Open Source projects.  

### Laravel Sail

Laravel Sail is a small Laravel sub-project maintaining a set of Docker containers to easily deploy a dev environment for Laravel.

I contributed [a PR](https://github.com/laravel/sail/pull/677) containing proof-of-concept support for running the main Sail container as a rootless container (making it compatible with Docker Desktop and rootless Podman).