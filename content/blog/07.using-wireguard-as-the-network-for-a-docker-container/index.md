---
title: 'Using WireGuard as the network for a Docker container'
slug: using-wireguard-as-the-network-for-a-docker-container
published: true
publishDate: '2022-09-07T09:00:00+01:00'
image: images/header.jpg
categories:
- networking
tags:
- tutorial
- networking
- linux
- hacking
- 'reverse engineering'
- software
- theory
- docker
- python
- c
---

**Docker** is a container engine for the Linux operating system. It leverages two Linux kernel functionalities, _chroot jails_ (or, nowadays, the `pivot_root` system call, but [the details](https://github.com/opencontainers/runc/blob/214c16fd9a3bd9fe56a2476933e31749a7c0576b/libcontainer/rootfs_linux.go#L125) don't really matter here) and _namespaces_, to create **containers**, or isolated environments where you can run processes separately from your host system.

This has roughly the same advantages of virtualization: isolation ([not](https://github.com/carlospolop/hacktricks/blob/master/linux-unix/privilege-escalation/escaping-from-a-docker-container.md)), portability, separation of concerns, reproducibility. These are all good things for a lot of applications, including CI, orchestration, resilient setups, etc.

Docker offers **several built-in options** for **networking** inside of containers. The simplest ones include sharing the same network interfaces as the host (`host`), having virtual interfaces joined to a standard Linux bridge (`bridge`), overlay networking (Docker's SDN thing, `overlay`) and having no network at all (`none`).

In this article, we're going to go through the endeavour of adding a feature to Docker: **WireGuard networking**. More precisely, we're not going to create a WireGuard tunnel on the host and then redirect the traffic using routing rules and/or \[ip|nf]tables. That's easy and uninteresting (and a kludge :). Instead, we're going to plug actual WireGuard interfaces into Docker containers, by leveraging Docker's actual paradigms and abstractions.

The article is divided into three parts. First, we're going to go over [the theory](#the-theory) (which you can safely skip if you don't care). We're going to talk about what a container actually is, and answer a rather curious question: why do containers don't actually exist? Then, we're going to [manually apply](#making-it-work) what we learned using standard userspace tools. In other words, we're going to meddle with Docker containers and manually set them up to have a WireGuard interface as their only network interface. Last, we're going to go through [implementing a Docker driver](#docker-driver) to make all of that actually happen during container creation.

Albeit we will sometimes (shallowly) dive into kernel code and system calls for added context and nerd points, the article is not very technically advanced, and I reckon it can be an enjoyable read for all of those who like to dig a bit deeper into how things work. We assume reasonable familiarity with Linux userspace tools (the `iproute2` suite in particular) and Docker, as well as a general understanding of how a Unix-like operating system works. Other than that, just sit back and enjoy!

#### The theory

As mentioned, Docker makes use of **Linux namespaces**. What are Linux namespaces, exactly? In this part of the article, we're going to demistify the concept, and compile and run an actual code example to make our own network namespace.

The Linux kernel has many different facilities, including the [Virtual FileSystem](https://www.kernel.org/doc/html/v5.19/filesystems/vfs.html), [process groups and hierarchies](https://www.kernel.org/doc/html/v5.19/admin-guide/cgroup-v2.html), and [networking](https://www.kernel.org/doc/html/v5.19/networking/index.html). These all contain a lot of **state**, which is generally shared between all processes in the system. For example, all processes access the same filesystems. They all see the same process groups and can send signals to all other processes using their PIDs (Process IDs). And they can all bind to the same network interfaces, with the same addresses, sharing the range of available TCP and UDP ports, etc.

This is a quite usual arrangement for an operating system, but, of course, if we want to run isolated containers without a separate kernel, we have to somehow hide this shared state to them. This is where namespaces come in. **Namespaces** are, quite simply, a way to partition kernel state into many separate spaces. And this is exactly what Docker does to create containers: it spawns a new namespace for each of the kernel subsystems, and runs a process inside these new namespaces. This way, containers are effectively a "clean slate" environment, which are (reasonably) isolated and independent of what's happening on the host.

Looking at it from a different point of view, a **Docker container** is quite simply a normal process - spawned from whatever command you indicate in your Dockerfile -, that gets started in such a way that the system calls it performs are served using a fresh set of kernel state and a different root filesystem. This process isn't actually _contained_ in anything, and in this sense containers are only a conceptual abstraction that has no actual runtime equivalent. Demistified enough?

{{< alert severity="info" >}}
As a side node, this is also kind of true for other isolating abstractions, such as hardware-accelerated Virtual Machines on x86 systems. In this case, too, Virtual Machine code is actual x86 code executed normally\* on the processor, which however is configured to refer to different data structure for virtual memory and other facilities when VM code is executing. (\*With the caveat that privileged instructions trap and get emulated by the hypervisor, so in this case it _is_ kind of contained in a way.)
{{< /alert >}}

Let's now briefly discuss how these namespaces are created. It's actually quite simple! Creating a new namespace is achieved with the `unshare` system call, which is Linux-specific. I have written a small sample program, _unshare-example.c_, which lists all interfaces before and after an `unshare` call with the `CLONE_NEWNET` flag, which indicates we want to move the current process to a fresh network namespace. You can find it [here](https://github.com/vmsh0/wireguard-docker), in the article's companion repository. Quite unfortunately, it consists of roughly 90% boilerplate code to list the interfaces and 10% actual program logic. This is due to the use of the Netlink protocol, which is what you use nowadays to speak with the kernel and ask it for information about network interfaces.

In case you don't feel like running it yourself (which I suggest - it's dead easy as it doesn't have any dependencies), the output of the program looks like the following on my system:

```
$ make unshare-example && sudo ./unshare-example
cc     unshare-example.c   -o unshare-example
before unshare:
ifin: 1, ifname: lo
ifin: 2, ifname: enp4s0
ifin: 3, ifname: cam
ifin: 5, ifname: wlan0
ifin: 12, ifname: docker0
ifin: 105, ifname: wg-out
ifin: 113, ifname: nlmon0
after unshare:
ifin: 1, ifname: lo
```

As you can see, I have quite a number of network interfaces in the main network namespace. After the `unshare` call, the process gets moved to a brand new namespace, and as such, it can no longer see the "host" (or, as we now know, the _initial namespace_) network interfaces. Does this look familiar? It is exactly what happens when you start a Docker container using `none` as the network driver: Docker will unshare the network namespace, and then it will leave it untouched.

For the curious, namespace unsharing **in the kernel** happens [here](https://elixir.bootlin.com/linux/v5.19.5/source/kernel/nsproxy.c#L211) in `unshare_nsproxy_namespaces`. This function creates a new namespace proxy (`struct nsproxy`), which is just a structure containing references to what namespaces are used by a given process. The function then populates this new proxy with existing namespaces which are not getting unshared, and the fresh namespaces which are getting unshared. For example, in our example program, we only use the `CLONE_NEWNET` flag in the `unshare` call. As such, in this case, the new namespace proxy will contain the same references as the old one, except for the `net_ns` member, which will be populated with a reference to a brand-new namespace. In more concise terms, `nsproxy` is a copy-on-write structure.

{{< alert severity="warning" >}}
A note on the naming of the `nsproxy` structure. I argue that's not a great name, as the term _proxy_ usually denotes a pluggable layer of indirection, i.e. something that might or might not be there depending on the situation. In this case, however, this layer of indirection is not optional! Every process has a namespace proxy, and it's also the mechanism through which a child inherits a parent's process namespace.
{{< /alert >}}

#### Making it work

Enough theory. Let's get to work! You can find a sample [Dockerfile](https://github.com/vmsh0/wireguard-docker/blob/main/Dockerfile). It simply spins up a container with the latest Arch Linux and `/bin/sh` as the entrypoint. You can use that, or do your containers using your preferred image. Whatever you pick, **spin up a container** using something like:

```
host$ docker build -t useless-arch
host$ docker run -d --name arch --network none -t useless-arch
host$ sudo ip netns attach dockerns `docker inspect -f '{{.State.Pid}}' arch`
```

{{< alert severity="info" >}}
The last command attaches the container's namespace, created by Docker, to the name "dockerns". This is a userspace convention that we use for convenience, and it simply causes a symlink from `/var/run/netns/dockerns` to `/proc/<pid>/ns/net` to be created. That can also be done manually using the `ln` command without any functional difference. This symlink will be consulted by the `ip` command whenever we will use the "dockerns" name to refer to the network namespace.
{{< /alert >}}

At this point our container is up and running, and it has a separate network namespace (along other types of namespaces), which we baptized with the name "dockerns". If you start a shell into the container (`docker exec -i -t arch sh`) and check the list of network interfaces, you will only find the loopback interface, just like it happened with the `unshare` example we examined in the theory section.

We are now going to create an **outer WireGuard interface** to use for testing (`wg-out`). We can quickly spin it up using the `wg-out.conf` configuration file from the repository, which will also assign the IP address _192.168.5.1/30_ to the interface (make sure to change it to something else if it clashes with your existing network):

```
host$ sudo wg-quick up ./wg-out.conf
```

{{< alert severity="error" >}}
The configuration files from the repository contain some example matching private/public keyspairs, which you can use to follow along and experiment without having to generate new ones. **Please take care to never reuse those in any real-life situation!**
{{< /alert >}}

We can now set up our **WireGuard interface inside** the container. To do that, we're going to use the `ip netns exec` command to execute commands inside our Docker network namespace, for all operations except for actually creating the interface. Since our outer interface has address _192.168.5.1/30_, let's give the interface inside the container address _192.168.5.2/30_. The `wg-in.conf` file instructs the WireGuard interface to use _localhost_ as its peer. If this doesn't make sense yet, just hang on for a minute!

```
host$ sudo ip l add name wg-in netns dockerns type wireguard
host$ sudo ip netns exec dockerns wg setconf wg-in ./wg-in.conf
host$ sudo ip netns exec dockerns ip a add 192.168.5.2/30 dev wg-in
host$ sudo ip netns exec dockerns ip l set wg-in up
host$ sudo ip netns exec dockerns ip r add 0.0.0.0/0 dev wg-in
```

Before going in-depth and seeing why this works, let's **try it out**:

```
host$ docker exec -i -t arch sh
container# ping 192.168.5.1
PING 192.168.5.1 (192.168.5.1) 56(84) bytes of data.
64 bytes from 192.168.5.1: icmp_seq=1 ttl=64 time=0.843 ms
64 bytes from 192.168.5.1: icmp_seq=2 ttl=64 time=0.777 ms
^C
--- 192.168.5.1 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1005ms
rtt min/avg/max/mdev = 0.777/0.810/0.843/0.033 ms
```

...Yup. It seems to be working!

{{< alert severity="success" >}}
Exercise for the reader: pinging the container from outside should also work, but only after an initial ping from inside. Why?
{{< /alert >}}

The more attentive readers might be wondering why it works. After all, we clearly created the interface _inside_ the Docker container, in a separate namespace, and as such it's not supposed to be able to connect to its peer (which in this case is _localhost_, i.e. our testing `wg-out` interface, but in principle could be something non-local) and communicate with it.

It might be tempting to think that it works because the loopback interfaces inside containers is the same as the host loopback interface, and as such all processes can communicate via the _localhost_ address. However, this is not only not the case, but it would also be a violation of the containerization principles we so eloquently enumerated at the beginning of the article!

The actual reason is a bit more faceted. However, the good news is that it's the result of intentional (and good) design. As you can see [here](https://elixir.bootlin.com/linux/v5.19.5/source/drivers/net/wireguard/socket.c#L377), the WireGuard kernel implementation takes care to open its **sockets** in the creating network namespace (i.e. whatever network namespace the userspace process which created the interface used), which it remembers from [here](https://elixir.bootlin.com/linux/v5.19.5/source/drivers/net/wireguard/device.c#315) during interface creation. This is also documented in [some of the examples](https://www.wireguard.com/netns/) on the official WireGuard website.

If we look back at the commands we've used to configure `wg-in`, you will notice that all the commands were executed in the container namespace, except for the first one, or the actual creation of the interface. We did specify the network namespace where to create the interface, but if we look closely at the `ip-link(8)` manual page, we read the following about the `netns` parameter:

> move the device to the network namespace associated with name NETNSNAME or process PID.

Let's piece it all together. The interface is created in the host, and as such it will use that network namespace to communicate with other WireGuard peers. But then it's immediately moved to the container namespace, so it doesn't actually pollute the host. At that point, we can configure it however we like and add network routes referring to it directly inside the container. The following illustrations show a schematic to wrap up what's going on in the kernel in our test setup (A), as well as an hypothetical setup where we have a remote WireGuard server in place of `wg-out` (B).

![Illustration A](namespace-illustrations-A.png?classes=caption "Illustration A: the inner and outer WireGuard interfaces connect locally through sockets living in the same network namespace, even though one of the interfaces is in a different namespace.")

![Illustration B](namespace-illustrations-B.png?classes=caption "Illustration B: the container WireGuard interface connects to a remote WireGuard peer through the host namespace.")

{{< alert severity="success" >}}
Exercise for the reader: find out whether, during the `ip link` command, there exists an interval of time when the interface actually *exists* in the host namespace, before getting moved to the container namespace. If you feel like, share your methodology and results by sending me an email.
{{< /alert >}}

#### Docker driver

There is one more piece to the puzzle. And that is, the methodology works, but it doesn't really plug into the Docker architecture in any meaningful way. Luckily, Docker - or rather its component **libnetwork** - offers the possibility of creating **custom network drivers**. There are two possible approaches to that: writing a "native" Go driver, and writing a _remote driver_, which is simply the same API wrapped in HTTP calls. We're going with the latter.

The **driver API** is surprisingly gaunt. Basically, you create a Unix socket in a special directory, and libnetwork sends you HTTP requests asking to provide information or perform actions. I will not go into detail on this part, which I think is mostly uninteresting, but I will provide two key resources: the [API reference](https://github.com/moby/libnetwork/blob/master/docs/remote.md), some [useful documentation](https://docs.docker.com/engine/extend/plugin_api/) on how to set plugins up with systemd on a production system (and more high level information), and a barebones [example implementation](https://github.com/vmsh0/wireguard-docker/tree/main/docker-plugin) that I made.

{{< alert severity="warning" >}}
There's an error in the above API reference page. For the _Join_ call, the following is mentioned: "_If no gateway and no default static route is set by the driver in the Join response, LibNetwork will add an additional interface to the sandbox connecting to a default gateway network (a bridge network named docker\_gwbridge) and program the default gateway into the sandbox accordingly, pointing to the interface address of the bridge docker\_gwbridge._" However, that is incorrect, as even when a default route is provided through the new interface, the gateway network is still added (which we don't want for our application). The way to disable that is to pass `"DisableGatewayService": true` in the JSON response to the _Join_ call.
{{< /alert >}}

We'll quickly go over the basics of my implementation. You can find it in the companion repository, in the `docker-plugin` directory. It is a Python/Flask web application, not nearly ready for production but implementing all of the local network creation and join operations, and even some basic error handling.

**Private keys** for the containers are generated deterministically from a provided seed and assigned IP addresses, and the respective public keys should of course be computed on the other side of the tunnels. Following libnetwork's architecture, our driver simply sets a WireGuard interface up and configures it with peers and keys. libnetwork, then, does the rest - including routes and addresses.

{{< alert severity="warning" >}}
Curiously, libnetwork passes drivers a "SandboxKey" - which is, hear hear, a filesystem path to a bind mount of the [nsfs](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=e149ed2b805fefdccf7ccdfc19eca22fdd4514ac) of the container's network namespace. In plainer words, libnetwork provides us with the means to directly manipulate the container's network namespace, but then it actually expects to create the new interface in the initial namespace and then move it itself. Funky. (Or bad API design?)
{{< /alert >}}

Let's **take it for a spin**, with a single container for simplicity. First of all, we need to update the configuration of `wg-out` to expect the deterministic key for our container. To do that, we need to pick a secret seed and a non-secret additional cryptographic material ("additional" in short). For this example, we're going to pick the strings "testseed" and "testadditional" respectively, which of course are _not_ good choices for a production system. Let's find the base64 for both, and from that, let's compute the private and public keys for our container using the script provided with the example driver (remember to change the IP addresses if you used something different while following along):

```
host$ SEED=`echo "testseed" | base64`
host$ ADDITIONAL=`echo "testadditional" | base64`
host$ ./privkeys.py --add $ADDITIONAL $SEED 192.168.5.2 | wg pubkey
+Pm8wi17cOoQ/QvaBq/WLcslAcgX1cCkrJA5dG57nU8=
```

We can now use the output value to update our `wg-out.conf` WireGuard configuration, changing the PublicKey of the only peer to reflect the output of the script we just ran. If you are using the same seed, additional, and IP addresses as in these examples, you will notice that the public key you get is the exact same, and that it is what `wg-out.conf` already contains. If that's the case, you are all set. Otherwise, if you are using different parameters (and, as such, keys), you will need to refresh the WireGuard interface to use the new keys. A quick way to do that is to just recreate it:

```
host$ sudo wg-quick down ./wg-out.conf
host$ sudo wg-quick up ./wg-out.conf
```

Now, **let's run the driver** and create a Docker network using it. We pass the same cryptographic material we used to generate the container public key to the driver, so that it can generate the respective private key and make everything work together:

```
host$ sudo flask run --host=unix:///run/docker/plugins/wireguard-plugin.sock
host$ docker network create -o "io.bestov.wg.peer"="localhost:10101" -o "io.bestov.wg.peerkey"="ZDT64H99t/mK5RFAxcZRx2KTK4PN8cVP55zWhkFXWgk=" -o "io.bestov.wg.seed"="$SEED" -o "io.bestov.wg.additional"="$ADDITIONAL" --gateway 192.168.5.1 --subnet 192.168.5.0/30 --driver wireguard-plugin wireguard-testnet
```

Now let's clean up the container from the previous examples, and run it from scratch using our new custom network:

```
host$ docker kill arch; docker rm arch
host$ docker container run -d --name arch --network wireguard-testnet -t useless-arch
```

Finally, let's test it:

```
host$ ping 192.168.5.2
PING 192.168.5.2 (192.168.5.2) 56(84) bytes of data.
64 bytes from 192.168.5.2: icmp_seq=1 ttl=64 time=0.185 ms
64 bytes from 192.168.5.2: icmp_seq=2 ttl=64 time=0.668 ms
64 bytes from 192.168.5.2: icmp_seq=3 ttl=64 time=0.496 ms
^C
--- 192.168.5.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2021ms
rtt min/avg/max/mdev = 0.185/0.449/0.668/0.199 ms
```

We can also test it from inside the container:

```
host$ docker exec -it arch sh
container# ping 192.168.5.1
PING 192.168.5.1 (192.168.5.1) 56(84) bytes of data.
64 bytes from 192.168.5.1: icmp_seq=1 ttl=64 time=0.304 ms
64 bytes from 192.168.5.1: icmp_seq=2 ttl=64 time=0.782 ms
64 bytes from 192.168.5.1: icmp_seq=3 ttl=64 time=0.626 ms
^C
--- 192.168.5.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2038ms
rtt min/avg/max/mdev = 0.304/0.570/0.782/0.199 ms
```

It works. Differently from our previous examples, this already works right from the start in the host-to-container direction. This is because (spoiler for one of the exercises incoming) I have included a fixed _PersistentKeepalive_ directive in the custom network driver, and as such, the container interface contacts its peer immediately after it goes up instead of waiting for some actual traffic to pass inside the tunnel.

#### A few more words on the crypto stuff

In the last section I kind of skimmed over the whole **deterministic key generation** thing, which however I think is a reasonably cool idea (and learned me a couple things on cryptography too). Here's a few more words about it.

Let's **state our problem** more clearly. The example driver assumes we have an IP address space that gets assigned to containers. Now, each of the containers connecting to the WireGuard endpoint must have its own key. This is because keys are not merely used for authentication, but also for the routing itself, so it's something we can't change at all. Of course, when starting each of the containers, we could explicitly pick an IP address and a key and pass them to the driver via the `docker start --driver-opt` flag, and that would fix it. However, this goes against the principle that we don't really care which IP addresses are assigned to containers (and if we do, it's still nice not to care about keys, at least).

To solve the issue of IP addresses, Docker automatically assigns them using something called an **IPAM** (IP Address Management) driver. This is built-in and enabled by defualt. It works for all network drivers, including ours. If you take a look at the source code, you will see that when handling a _CreateEndpoint_ request, it indeed expects to get an IP address assignment from Docker. But then, this still leaves us to deal with the worst part of the issue: **WireGuard keys**. There are various approaches that come to mind:

* Having a **fixed database** of keys, one for each IP address, covering the entire subnet we are assigning via Docker's IPAM driver. This has the pro of being trivially simple, but the con of having to handle a database full of keys (ugh, scary) that needs to be transferred to each of the hosts where containers are spawned. This also utterly fails if the subnet size changes or some of the keys get leaked: the database needs to be recomputed from scratch, and worst of all, securely retransmitted.
* Having an **out-of-band** protocol to get keys from the WireGuard endpoint. That is, when the driver is creating a container interface, it simply asks the endpoint what key it should use for the address it has obtained from IPAM. This has the pro of being centralized (easy to understand), and the con of... being centralized (containers can't be deployed when the central host is offline). It's also more complex, because you need one more daemon and one more API.
* Having a master key, and **deriving** keys from it using the IP addresses as cryptographic material. This is kind of a middle ground: you still have to share a secret, but it's one single small secret, so it's easier. And also, significantly, this secret doesn't change if the subnet size changes, and by adding some additional non-secret material to the mix, the secret doesn't have to change even if a part of the container keys (but not the secret) are leaked.

Well, we already know what we picked, so let's see how it works a bit more in-depth.

We have a secret byte string, **s**, and a non-secret byte string **a**. Both the WireGuard endpoint and each of hosts where containers are spawned know both of these. Now let's define a function **H(s, a, addr)**, where **addr** is the 4-byte representation of an IP address we're trying to assign, as follows (**|** denotes byte string concatenation):

> **H(s, a, addr) = keccak256(s | a | addr)**

This is an **hashing function** that has a few interesting properties. It is immune to length-extension attacks becase it's a fixed-length payload, and also because we're using _keccak256_. For each different value of **addr**, even those with a small [Hamming distance](https://en.wikipedia.org/wiki/Hamming_distance) from each other (which is exactly what is going to happen when we assign IP addresses sequentially), we will have [an entirely different hash](https://en.wikipedia.org/wiki/Avalanche_effect). Finally, it contains secret material, and as such an attacker cannot compute the hash from an IP address. In other words, it seems to be suitable to generate our private keys.

One last thing. WireGuard uses the Curve25519 public key cryptography system. To generate Curve25519 private keys, random bit strings are [clamped](https://git.zx2c4.com/wireguard-tools/tree/src/curve25519.h#n18), removing some information from them. The why is very interesting and very effectively explained [here](https://neilmadden.blog/2020/05/28/whats-the-curve25519-clamping-all-about/). As such, we redefine our **H** function to have this bit clamping performed on the result of the keccak256 hash. (I won't write down the details here - you can find them at the links above as well as [in the example driver](https://github.com/vmsh0/wireguard-docker/blob/980b09e3ab89ea8263deb7ae4e1c7686078ceb0c/docker-plugin/privkeys.py#L30) coming with this article). As a side note, it would have been interesting to use a key derivation function that could independently work on private and public keys (like Bitcoin's BIP0032), but I didn't bother with that to keep things a bit simpler.

All of this is implemented in the `privkeys.py` script coming with the driver. The script, as exemplified in the previous section, can be used as a command-line tool to compute keys. When used in a simple shell script, it can be used to generate the configuration for a WireGuard endpoint, covering an entire IP address range. The same keys will of course be generated by the driver when configuring the containers, but vitally, the keys will never be trasmitted over the net.

Let's now go over some **usage scenarios**, which should showcase the strenght of this solution.

##### Scenario 1: setting it up

Imagine that we want to **deploy 100 containers**. We pick a /25 subnet, say 10.0.42.0/25, and we pick out the 10.0.42.126 address for the WireGuard endpoint (so, conveniently, containers will be numbered .1, .2, ..., .100). We pick a `$SEED` and an `$ADDITIONAL`, and we run the `privkeys.py` script in a cycle to generate the WireGuard configuration for the central endpoint, with Peer entries looking like this:

```
[Peer]
PublicKey = `./privkeys.py --add $ADDITIONAL $SEED 10.0.42.x | wg pubkey`
AllowedIPs = 10.0.42.x/32
```

We then securely move the secret `$SEED` value to the containers host, and also the non-secret `$ADDITIONAL` value. When each of the containers is started, it will get an IP address, and the respective private key, computed with the same `$SEED` and `$ADDITIONAL` values. As such, it will be able to communicate with the endpoint.

##### Scenario 2: adding more containers

We want to **add 10 more containers**. This is easy! We just run `privkeys.py` with the same seed and additional values on 10 more IP addresses, from .101 to .110, generating 10 more Peer entries. We restart the WireGuard interface to load the new keys (this will not drop connections across the tunnel!), and start 10 more containers, which will be able to communicate just like the first 100. Note that we did not need to change or retransmit any shared information!

##### Scenario 3: leaked private key

Ouch. One of our internet-facing containers was **hacked** and its private key compromised. What now? Well, the good news is that from that private key, the attackers can't gather any of the other private keys. The bad news is that, especially if we cheaped out on our firewall configuration, the attackers can now pretend to be the container they have compromised.

Luckily, we have a quick fix: run the `privkeys.py` in a cycle again, with a different additional. Then, change the container host configuration to use this new additional. Note that we didn't need to transmit any secret information, but still, we fixed it!

#### Wrap-up

Ooof. This required quite a bit of research, and most of the information was not very readily available. While libnetwork provides a reasonable amount of information to get started, in more than one instance it required some trial-and-error (and a couple of source code dives) to piece everything together and get all of the required details. I hope my example driver and the whole investigative process can serve as documentation for future dwellers.

We have also analyzed a crypto-based solution for the problem of **distributing keys**. The interesting takeaway, to me at least, is that shared secrets are difficult, but key derivation (which can be easy enough, when using a modern hash function such as keccak256) can make them a little less painful.

Of course, while the provided driver works and implements this key derivation scheme, it lacks many of the bells and whistles that would be needed for an **actual deployment**. Those that come to mind immediately are more configurability, and unit tests. The good news, however, is that as far as I can see, it should work correctly when containers are distributed on multiple hosts.

What's more to say? If you make any improvements to my solutions, or if you think the article can be improved in any way, please leave a comment of [write me an email](/about-me). Thank you for reading!

#### Credits
Header image by [**Stewart D. Macfarlane**](https://en.wikipedia.org/wiki/User:Pencefn), released under [CC Attribution-Share Alike 3.0 Unported](https://creativecommons.org/licenses/by-sa/3.0/deed.en).
