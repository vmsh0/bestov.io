---
title: 'Don''t try to outsmart the universe'
slug: dont-try-to-outsmart-the-universe
publishDate: '2020-04-29T09:00:00+01:00'
categories:
- networking
- mantra
tags:
- ipsec
- pfsense
- debian
- networking
- ouch
image: 'images/header.jpg'
---

Today I migrated an **IPsec** (with IKEv1) site-to-site setup from a pfSense machine to a Debian machine.

Since the **pfSense** machine was still the Internet gateway for the network, IKE and ESP packets still had to go through it. Now, I recalled _something_ about **firewalls not playing too nice with IPsec**, so I researched a bit, and I concluded I needed some very specific SNAT rules. (I also realized that IPsec was _not really_ meant for what we're using it for, but over the course of many years enough ~~functionality was kludged together~~ RFCs were written to make it work and industry has adopted it quite widely.)

Well, I created the **rules** and it didn't work. I spent hours trying to **debug** the key exchange process, tweaking the strongSwan configuration, capturing packets using the terrible pfSense facilities. At some point I got exhausted, so I deleted all the rules I had added and I began closing everything, including two ssh sessions I had opened to work on the Debian machine. While I was closing the second one, which was running **tcpdump**, I noticed some unusual (read: different than before) activity. So I reopened a second ssh session and I typed:

`ipsec status`

...sure enough, deleting all the firewall rules I had created **fixed** the setup. After some investigation, it turned out they were good enough to make IPsec think it didn't need to use NAT-traversal, but not good enough to make it work without it. I quickly enabled IP forwarding on the Debian machine, created a static route on pfSense, and just like that the site was connected to the other site.

Don't try to outsmart the universe.
