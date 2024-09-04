---
title: 'Streaming video with commodity links, part 2: let''s (try to) do it (and fail)'
slug: linux-redundant-ip-link-2
publishDate: '2020-06-20T09:00:00+01:00'
categories:
- networking
tags:
- debian
- networking
- linux
- bonding
- redundancy
- failover
- fail
image: images/header1.jpg
---

In the [previous installment](/blog/linux-redundant-ip-link) of the series, we analyzed the problem of near-istantaneous Internet connection failover without breaking existing connections for live video streaming. The **solution** we devised consists in setting up L2 GRE tunnels to a fixed gateway with a very reliable internet connection (think a dedicated machine in a datacenter), and using the Linux Bonding Driver's link monitoring functionality to manage the failover for us.

Now we are going to **try and make it work**. For my experiments, I'm using Debian 10 "buster" with the latest available kernel:

`Linux fo-gw 4.19.0-9-amd64 #1 SMP Debian 4.19.118-2+deb10u1 (2020-06-07) x86_64 GNU/Linux`

Pretty much all modern distributions should ship the required network functionality as kernel modules (`ip_gre` and `bonding`), but in case you want to be sure you can use the following command:

```bash
find /lib/modules/$(uname -r)/kernel -name bonding.ko -or -name ip_gre.ko
```

The **environment** I'm using for testing is two virtual machines:
* `fo-gw`: the gateway for the video streaming
* `fo-exit`: the datacenter machine (we called it "fixed gateway" in the previous installment)

The first virtual machine has got three network cards: one for ssh management from my PC, and two connected to the second virtual machine. The second virtual machine, in addition to this, also has a fourth network card connected to the Internet. Using `systemd-networkd`, I reneamed them all. I called the management card `mgmt0`, the two interconnected cards `intra15` and `intra16`, and the internet card `inet0`:

```none
root@fo-exit:/home/user# ip l
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: intra15: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
    link/ether 00:0c:29:56:b9:15 brd ff:ff:ff:ff:ff:ff
3: intra16: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
    link/ether 00:50:56:39:2b:16 brd ff:ff:ff:ff:ff:ff
4: inet0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
    link/ether 00:0c:29:56:b9:5b brd ff:ff:ff:ff:ff:ff
5: mgmt0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
    link/ether 00:0c:29:56:b9:65 brd ff:ff:ff:ff:ff:ff
```

I assigned IP addresses as follows:
```none
+---------+--------------+--------------+
|         | fo-gw        | fo-exit      |
+---------+--------------+--------------+
| intra15 | 10.88.15.100 | 10.88.15.200 |
| intra16 | 10.88.16.100 | 10.88.16.200 |
| inet0   |              | dhcp         |
| mgmt0   | don't care   | don't care   |
+---------+--------------+--------------+
```

This setup is a bit different from what we had hypothesized, but the slight changes made setting it up much quicker. It shouldn't make much difference, but I will make sure update the article as soon as we test this in production with the final topology.

#### That looks GRE...at
We are now going to set up the **GRE tunnels**. The `ip_gre` module exposes a device type called _gretap_, which is a GRE tunnel encapsulating Ethernet. We want one GRE tunnel for each link between the virtual machines (eventually, one for each Internet connection of the streaming machine). Creating them is very simple:
```none
fo-gw# ip link add name gretap15 type gretap local 10.88.15.100 remote 10.88.15.200
fo-gw# ip link add name gretap16 type gretap local 10.88.16.100 remote 10.88.16.200
fo-exit# ip link add name gretap15 type gretap local 10.88.15.200 remote 10.88.15.100
fo-exit# ip link add name gretap16 type gretap local 10.88.16.100 remote 10.88.16.100
both# ip link set gretap15 up
both# ip link set gretap16 up
````

If you query the available links with `ip l`, you will notice that in addition to the tunnels we just created, we also have three devices called `gre0`, `gretap0` and `erspan0`. This happens because the module, which gets loaded by `iproute2` automatically upon tunnel creation, creates those devices by default upon initialization. These are fallback tunnel, to which packets not matching any specific tunnel get delivered. You cannot disable this feature (well, there's [a patch](https://patchwork.ozlabs.org/project/netdev/patch/20180308205141.77868-1-edumazet@google.com/) if you really want), and deleting them doesn't work. However, they should be completely harmless.

Let's temporarily assign some IP addresses to our tunnel interfaces to run some tests (you would normally assign /30's to tunnels, but I'm assigning /24's to be coherent with the numbering I used previously):
```none
fo-gw# ip addr add dev gretap15 10.188.15.100/24
fo-gw# ip addr add dev gretap16 10.188.16.100/24
fo-exit# ip addr add dev gretap15 10.188.15.200/24
fo-exit# ip addr add dev gretap16 10.188.16.200/24
```

Let's start `tcpdump` on `intra15` on one of the machines (let's say `fo-exit`), and then let's ping the GRE tunnel's address from the other machine:
```none
fo-exit# tcpdump -i intra15
fo-gw# ping -c 5 10.188.15.200
```

We see something like this:
```none
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on intra15, link-type EN10MB (Ethernet), capture size 262144 bytes
00:08:56.747151 IP 10.88.15.100 > 10.88.15.200: GREv0, length 102: IP 10.188.15.100 > 10.188.15.200: ICMP echo request, id 3560, seq 1, length 64
00:08:56.747708 IP 10.88.15.200 > 10.88.15.100: GREv0, length 102: IP 10.188.15.200 > 10.188.15.100: ICMP echo reply, id 3560, seq 1, length 64
00:08:57.748620 IP 10.88.15.100 > 10.88.15.200: GREv0, length 102: IP 10.188.15.100 > 10.188.15.200: ICMP echo request, id 3560, seq 2, length 64
00:08:57.748754 IP 10.88.15.200 > 10.88.15.100: GREv0, length 102: IP 10.188.15.200 > 10.188.15.100: ICMP echo reply, id 3560, seq 2, length 64
00:08:58.753121 IP 10.88.15.100 > 10.88.15.200: GREv0, length 102: IP 10.188.15.100 > 10.188.15.200: ICMP echo request, id 3560, seq 3, length 64
00:08:58.753190 IP 10.88.15.200 > 10.88.15.100: GREv0, length 102: IP 10.188.15.200 > 10.188.15.100: ICMP echo reply, id 3560, seq 3, length 64
00:09:00.783705 IP 10.88.15.100 > 10.88.15.200: GREv0, length 102: IP 10.188.15.100 > 10.188.15.200: ICMP echo request, id 3560, seq 5, length 64
00:09:00.783786 IP 10.88.15.200 > 10.88.15.100: GREv0, length 102: IP 10.188.15.200 > 10.188.15.100: ICMP echo reply, id 3560, seq 5, length 64
00:09:01.925612 ARP, Request who-has 10.88.15.100 tell 10.88.15.200, length 28
00:09:01.925696 IP 10.88.15.200 > 10.88.15.100: GREv0, length 46: ARP, Request who-has 10.188.15.100 tell 10.188.15.200, length 28
00:09:01.968912 ARP, Request who-has 10.88.15.200 tell 10.88.15.100, length 46
00:09:01.968936 ARP, Reply 10.88.15.200 is-at 00:0c:29:56:b9:15 (oui Unknown), length 28
00:09:01.968970 IP 10.88.15.100 > 10.88.15.200: GREv0, length 46: ARP, Request who-has 10.188.15.200 tell 10.188.15.100, length 28
00:09:01.968981 ARP, Reply 10.88.15.100 is-at 00:0c:29:5b:99:15 (oui Unknown), length 46
00:09:01.969016 IP 10.88.15.200 > 10.88.15.100: GREv0, length 46: ARP, Reply 10.188.15.200 is-at da:9d:34:64:cb:8d (oui Unknown), length 28
00:09:01.971670 IP 10.88.15.100 > 10.88.15.200: GREv0, length 46: ARP, Reply 10.188.15.100 is-at d6:49:e5:19:52:16 (oui Unknown), length 28
^C
16 packets captured
16 packets received by filter
0 packets dropped by kernel
```

We can see the GRE packets flowing, and inside them the IP headers and ICMP packets! As you can see, `tcpdump` doesn't print anything about the Ethernet headers, but we can indeed confirm these are L2 tunnels because the network stack of `fo-exit` decides to send an ARP probe out of both `intra15` and `gretap15` just after it stops receiving the ICMP Echo requests, and `fo-gw` also does the same a fraction of a second later.

Now, `ip l` will say our tunnels have an **MTU** of 1462 bytes, when we really had expected 1458 bytes. However, this MTU value can be confirmed to be working ok with the same `tcpdump` setup as before: if we send a ping with size 1434 bytes, which will result in a IP packet of size 1463 bytes, it will get fragmented as per MTU, and sending a packet of size 1434 bytes works fine. This is because I hadn't accounted for a detail in the previous installment: a virtual L2 layer will not transmit the 4 byte checksum at the end of a frame, since it would be quite useless (as the data integrity is already protected in the "real" L2). This coincidentally means that we have an even lower overhead than we thought.

#### Let's do some bonding!
Now that we have our L2 tunnels, let's create and configure a bonding interface on each machine, and add the GRE tunnels as slaves. This is very simple to do with `iproute2`.
```none
both# ip link set bond-15-16 type bond mode active-backup
both# ip link set gretap15 down
both# ip link set gretap16 down
both# ip link set gretap15 master bond-15-16
both# ip link set gretap16 master bond-15-16
both# ip link set bond-15-16 up
```

Now, as we can verify with `ip a`, the bonding driver isn't smart enough to compute the correct MTU. Also, the `gretap` interfaces still have their addresses, which we don't need anymore. Let's fix all that manually:
```none
fo-gw# ip addr del 10.188.15.100/24 dev gretap15
fo-gw# ip addr del 10.188.16.100/24 dev gretap16
fo-exit# ip addr del 10.188.15.200/24 dev gretap15
fo-exit# ip addr del 10.188.16.200/24 dev gretap16
both# ip link set bond-15-16 mtu 1462
```

As you can verify, this also changes the MTU of the slave interfaces.

Let's now assingn some IP addresses to the bonding interfaces.
```none
fo-gw# ip addr add 10.42.42.100/24 dev bond-15-16
fo-exit# ip addr add 10.42.42.200/24 dev bond-15-16
```

At this point, you should find that you are able to **ping** one machine from the other and vice versa. If you experiment with `tcpdump`, you should observe GRE packets passing through `intra15`, and the same exact traffic passing through `gretap15` and `bond-15-16`. This is exactly what we would expect: while `gretap15` is functional, `bond-15-16` is functionally an _alias_ to it.

Now let's do something more interesting: let's cut `intra15` while running a `ping` command, and let's see what happens. To make the result more evident, I configured my VM manager to have a ~40ms round-trip latency on `intra15`, and ~50ms on `intra16`.

```none
fo-gw# ping 10.42.42.200
PING 10.42.42.200 (10.42.42.200) 56(84) bytes of data.
64 bytes from 10.42.42.200: icmp_seq=1 ttl=64 time=43.4 ms
64 bytes from 10.42.42.200: icmp_seq=2 ttl=64 time=46.3 ms
64 bytes from 10.42.42.200: icmp_seq=3 ttl=64 time=44.0 ms
<intra15 disconnected>
```

And... it doesn't work! The reason is quite simple: by default, the driver is set up not to do any **monitoring**. In other words, it would only work if we'd manually changed the slave device. For the sake of experimenting, let's try to do that and see if it works:
```none
both# ip link set bond-15-16 type bond active_slave gretap16
fo-gw# ping 10.42.42.200
PING 10.42.42.200 (10.42.42.200) 56(84) bytes of data.
64 bytes from 10.42.42.200: icmp_seq=1 ttl=64 time=52.5 ms
64 bytes from 10.42.42.200: icmp_seq=2 ttl=64 time=52.3 ms
64 bytes from 10.42.42.200: icmp_seq=3 ttl=64 time=54.1 ms
```

Yay! It works. Now, let's set up monitoring. In the last installment, we had found that the driver supports both MII and ARP monitoring. MII monitoring, however, wouldn't work for us. Finding out why is left as an excercise for the reader. (Hint: there are many kinds of L2.)

To enable **ARP monitoring**, we have to set the `arp_interval` and `arp_ip_target` parameters of the interface.
```none
fo-gw# ip link set bond-15-16 type bond arp_interval 100 arp_ip_target 10.42.42.200
fo-exit# ip link set bond-15-16 type bond arp_interval 100 arp_ip_target 10.42.42.100
```

Let's also bring `intra15` back online. Now, querying the active slave gives an interesting answer:
```none
both# cat /sys/class/net/bond-15-16/bonding/active_slave
gretap16
```

Ouch. This is not the correct behaviour! as by default the `primary_reselect` option is set to `always` (meaning that the primary interface should be automatically reselected as soon as it is back up). After observing this, I tried disabling `intra16`, with the expected result of the driver switching to `intra15`. After re-enabling `intra16`, however, I observed that the driver was ping-ponging between the two GRE interfaces. I don't know why this is the case, and any suggestion on the matter is appreciated.

As a temporary fix, I tried to set `primary_reselect` to `failure` (i.e. a new slave is only selected upon failure of a different slave.)
```none
both# ip link set bond-15-16 type bond primary_reselect failure
```

However, this did not fix the issue.

I inquired on the `linux-netdev` mailing list about the issue, and someone from Canonical confirmed that it should work, and thus it seems like a bug in one of the involved network drivers.

I asked my friend to stay on hold for a few days; however, he eventually settled on using [OpenMPTCProuter](https://www.openmptcprouter.com/?_target=blank). This has way higher overhead... but it works!

What have we learned today? I'd say a whole lot about Linux networking internals. (Including that, some of it, doesn't work :). I will eventually try the whole thing again using OpenVPN's L2 support. However, not today.

Thank you for reading, and feel free to comment if you happen to try again before me!