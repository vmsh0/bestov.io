---
title: 'Hacking a tap water purifier'
slug: hacking-a-tap-water-purifier
publishDate: '2021-01-17T09:00:00+01:00'
categories:
- hardware
tags:
- microcontroller
- hacking
- tinkering
- 'reverse engineering'
- hardware
- arduino
- software
image: images/header.jpg
---

A few months ago, my father bought himself a **water purifier**. It's a quite convenient and eco-friendly device which filters tap water, and optionally cools it and carbonates it, eliminating the need of buying bottled water entirely.

The company that sold it to him also sold him a stand-alone **faucet**, as a replacement for his old one. This new piece of hardware is actually **two devices in one**: it has pipes for cold and hot water, like a standard mixer faucet, and also an additional pipe with no valve, directly connected to the water purifier. Additionally, it has three buttons on the spout, with little icons representing ambient temperature water, cooled sparkling water, and cooled water.

{{< alert severity="info" >}}
The purifier gives options for ambient temperature water and cooled still water, but sparkling water is only available cooled. Exercise for the reader: why?
{{< /alert >}}

You might be wondering **why** one would want to hack a water purifier. The reason is quite simple: while the device works quite well as it is, it _is_ very slow, and whoever designed it had the short-sightedness to require the user to keep the button pressed the entire time. Filling a tea kettle (or anything more than a small glass) feels like a cumbersome and boring task! Luckily, it was quite easy and cheap to devise a solution.

### Reverse-engineering the system

Between the faucet buttons and the water purifier, the company installed a small board with an IDC socket, which connects to the faucet buttons, and an RJ11 socket, which connects to the purifier itself. This board serves two purposes: it mounts an RGB led, which is the only user-facing output of the purifier, and it connects the faucet buttons to the purifier itself.

It is a very simple board, but it came with a black adhesive foam pad on the back side, so I had to get that out of the way. Initially, I tried to peel it off and scrape off the remains using a razor blade. Due to the legs of the thru-hole components, this didn't really work. I tried with an acetone solution next, but had no luck with that either. Finally, I tried to use heat, and that worked really well: I used an hair drier initially, and then I simply submerged the entire board in boiling water, which heated the glue enough to allow it to be easily removed it in just a few passes.

The circuit is very simple. The RGB LED is powered from four lines, and the three faucet buttons are multiplexed to just two lines simply by forming a different voltage divider depending on which button is pressed (the output of which probably goes to an ADC pin on the purifier microprocessor).

### The plan
Barring the idea of a logic gates circuit (I'm a software guy!), and being quite time-constrained (I'm a software guy finishing his undergrad!), I decided I was just going to _Arduino_ my way out of this one. I always keep a few cheap Arduino Pro Mini clones around for this kind of occasions :).

The **idea** is simple: using the real button presses as an input, **feed "virtual" button presses** to the purifier. This way,  multiple modes of operation can be implemented easily:
* A **short press** could start the water, until a second short press, or some maximum time elapses (wasting water is bad!)
* A **long press** could keep the water running until the button is released, just like it was originally
* **Multiple short presses** could encode the amount of time needed to fill a particular container (e.g. two presses to fill a water jug, three presses to fill the tea kettle) - the single short press is now a particular case of this one!

### The hardware
The first solution I devised was to just spin up a **replacement board**. But then I realized that the board doesn't receive a ground line through the RJ11 port at all: there are two 0-potential lines coming from the RJ11 port, which are for the common terminal of the three buttons, and for the cathode of the LED, but as far as I could measure those are both current-limited! There's no chance I could power an Arduino out of that, so I discarded the idea and decided to make an **add-on board** instead. This is very unfortunate, because it means that I will have to add a power supply under the sink.

Since the new board is now going to have its own ground, a **coupling device** is needed. I picked relays, because I had a bunch of Omron G5LE-1's around (total overkill!). Since these beasts absorb as much as 80 mA @ 5V, I had to power them through transistors, as the ATmega328P on the Arduino cannot provide that much current by itself. I found some 2N3904 in a drawer, and a few 1N4006 to use as flyback diodes. I quickly made a prototype, which worked like a charm (the diodes are on the opposite side):

![](board.jpg)
(you can find the schematic in the code repository - see below)

### The software
The **architecture** is quite simple: there is a timer-driven interrupt function which polls the buttons, does some very simple debouncing, and adds an event of "button up", "button down", or "sequence" (meaning that the short-press detection time has elapsed) to a **sequence**. After each event is added, the sequence is read, and if it makes sense, it results in a **state change**, i.e. activating or deactivating one of the relays.

For example, the sequence <_button down (1)_, _button up (1)_, _sequence_> semantically represents "one press, short, button 1" (which might represent the state change "activate relay 1 for 10 seconds"), while the sequence <_button down (2)_, _button up (2)_, _button down (2)_, _sequence_> represents "two presses, begin long, button 2" (which might represent the state change "activate relay 2").

These sequences various constraints: button presses of different buttons cannot be intersected (e.g. <_button down (1)_, _button down (2)_, _button up (2)_, _button up (1)_>), a sequence may only start with a _button down_, and may be only terminated with a _sequence_.

{{< alert severity="info" >}}
You may have noticed at this point that the sequences can be formalized as a formal language, and the semanticization can be represented as attributes in an attribute grammar! It's very easy to write a context-free grammar which correctly handles (i.e. without generating invalid sequences) a finite number of buttons, but it is impossible to write one for infinitely many buttons. Excercises for the reader: why? what are the practical consequences? Also, my faucet runs a parser™, so one more excercise: what kind of parser is that?
{{< /alert >}}

I sometimes like to have fun writing assembly, but being quite time constrained for this project, I simply implemented everything in Wiring using the Arduino IDE. You can find the code (and the add-on board schematic) [here](https://github.com/vmsh0/hacking-a-tap-water-purifier/blob/main/arduino.ino).

### Conclusion
It's total overkill! I used a over-sized MCU, with over-sized relays, and an over-sized firmware to reach the objective. But it was a very interesting project nontheless, as I had to work around the ground issue, and I only used components I already had around (constraints are fun!).
