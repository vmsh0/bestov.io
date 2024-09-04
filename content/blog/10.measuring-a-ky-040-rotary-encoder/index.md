---
title: 'Measuring a KY-040 rotary encoder'
slug: measuring-a-ky-040-rotary-encoder
publishDate: '2023-01-06T09:00:00+01:00'
categories:
- hardware
tags:
- microcontroller
- hacking
- tinkering
- hardware
- arduino
- software
image: images/header.jpg
---

I'm doing a project, a very simple one: it's a **sous vide cooker**. The details don't matter, as in this article we are going to focus on a single component: the KY-040 rotary encoder.

If you are here, you have most likely just bought a KY-040 clone from China, and are looking into how to hook it up to your Arduino. This is a bit of a deviation from the usual highly technical and specific content of this blog, but there's a good reason for it: I spent 15 minutes googling about this, and all I got was some generic copy-pasted (often clearly stolen) code that mostly - albeit very inefficiently - worked.

As that was not good enough for me, I approached the problem from scratch. So let's go through it!

### Incremental rotary encoders

Incremental rotary encoders are pieces of hardware where a rotating shaft is fixed to a pair of contacts. These contacts, while rotating, brush against a fixed ferrule, which, along its angular lenght, alternates between being conected to GND, and being unconnected. So, while the encoder is being rotated, the two contacts get repeatedly connected and disconnected from ground.

Now, one important detail: these contacts are not aligned along the rotating axis. As such, they will get connected and disconnected from ground with a time offset between one another. Of course, depending on whether the shaft is rotated clockwise or counter-clockwise, one or the other contact will lead the other one in changing state. And this property can indeed be used to measure the direction of rotation.

{{< alert severity="info" >}}
This is a form of [Gray coding](https://en.wikipedia.org/wiki/Gray_code), which is a fancy term to talk about a binary number system in which no two bits ever change state together from one number to the next.) This property is actually more important for absolute encoders, which can simultaneously measure direction of rotation and absolute position.
{{< /alert >}}

### Measuring the direction of rotation

Incremental rotary encoders are usually of the _snappy_ kind - that is, they have a fixed number of angular positions they will "snap to". While there is no strict technical reason why this is done, it does make measuring them a bit easier. Why? Because the steps between these angular positions effectively define one unit of change. This means that we can look for a specific signal shape (or rather two - one for each direction), corresponding to this unit of change, and call it a day.

Let's look to the KY-040 specifically. Its two contacts are connected to pins called "CK" and "DT" - clock and data. Both are pulled up to VCC by default, and get connected to ground during rotation as described before. Those, I think, are quite misleading names, as they are just two perfectly identical contacts placed at two different positions along the rotation axis. But they should give one vital clue, which is exactly what most existing tutorials and articles miss: one should be used as a clock, and the other one should be used as a data signal.

To see why, let's take a look at a signal capture I performed a few hours ago. The two following signals are generated when turning the encoder clockwise and counterclockwise by one unit.

![Signal capture of the encoder. On the left, a capture of the "clockwise" signal can be seen. The CK signal goes from high to low; after a few milliseconds, the DT signal also goes from high to low; after a few more milliseconds, the CK signal goes back to high; and finally, after a few more milliseconds, the DT signal also goes back to high. On the left, instead, a capture of the "counterclockwise" signal can be seen. This looks like the left signal, with one vital difference: the CK and DT signals are basically reversed, in that the DT signal switches before the CK signalfrom high to low, and then from low to high.](images/cap-signals.png)

For the clockwise direction, we see the CK signal leading the DT signal in its state changes; while for the counterclockwise direction we see the DT signal leading instead. So far, so good: this is exactly what we have discussed above.

Now, it might be tempting - and most _first Google page_ articles I found do give in to this temptation -, to this that detecting the relative phase of these two signals is the straightforward approach. That is, polling both signals and when one changes, checking whether we had observed the other one change before it. And some go as far as checking that indeed, after going high-to-low, the signals once again change from low-to-high in the expected order, i.e. the one that was last observed.

As it turns out, this is a complete waste of processor cycles! There is one completely crystal clear property of the signals that one can use to detect the direction of rotation instead, and it doesn't require to keep any state beyond what's needed for edge detection. And that is, when CK goes high, DT can be polled. Its current state single-handedly tells us which direction we are turning. In other words, we simply use a rising-edge on CK as signal that one unit of rotation has happened, and the state of DT at that instant (actually, we get as much as a few ms - or tens of thousands of clock cycles, to measure it!) to determine the direction. So it is in this sense that one pin is the clock, and the other one is data.

{{< alert severity="info" >}}
Clearly, it is perfectly fine to invert everything and use DT as the "clock" and CK as the "data" instead
{{< /alert >}}

### Arduino

With this in mind, let's wire it all up to an Arduino and test it. There are no surprises in the circuit I'm using - of which I'm not including a drawing because unfortunately the latest releases of both KiCad and Fritzing are broken beyond usability and I'm currently on a time budget.

Anyway - I have connected VCC and GND as expected, and then pins CK and DT of the encoder respectively to pins 3 and 4 of my Arduino Mega. Between both CK and GND, and DT and GND, I have connected 50nF ceramic capacitors. This, along with the KY-040 pull up resistors, make a low-pass filter to implement very basic debouncing.

The capacitors are not mandatory. Instead, the software-based filter you can see just below should be enough. I included them because I was seeing a lot of bouncing in my logic measurements and that was bothering me.

This is my code:

```
#include <digitalWriteFast.h>

const int ROT_CK_PIN = 3;  /* must be an interruptable pin */
const int ROT_DT_PIN = 4;

volatile unsigned char rot_rot;
#ifdef ROT_SOFT_FILTER
volatile unsigned long last = 0;
#endif
void rot_ck_int() {
#ifdef ROT_SOFT_FILTER
  /* very basic debouncing */
  unsigned long now = millis(); /* this call takes a few us */
  if (now - last < 2)
    return;
  last = now;
#endif
  rot_rot = 1 + (!!digitalReadFast(ROT_DT_PIN));  /* cw = 1, ccw = 2 */
}

void setup() {
  Serial.begin(9600);
  pinMode(ROT_CK_PIN, INPUT_PULLUP);
  pinMode(ROT_DT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ROT_CK_PIN), rot_ck_int, RISING);
}

void loop() {
  static int value = 0;
  unsigned char rot = rot_rot;
  rot_rot = 0;  /* reset message-passing primitive as soon as possible */

  switch (rot) {
    case 1:
      value += 1;
      Serial.print(" cw ");
      Serial.println(value);
      break;
    case 2:
      value -= 1;
      Serial.print("ccw ");
      Serial.println(value);
      break;
  }
}
```

As you can see, it uses an interruptable pin to capture the rising edge on CK. Then, it optionally performs some very dirt-stupid debouncing (which however I've observed to work more than well enough), and finally, it passes the detected direction of rotation to the non-interrupt environment using the very simple IPC primitive of setting the `rot_rot` variable to one of two magic values.

{{< alert severity="info" >}}
The magic values 1 and 2 were picked because they can be generated by just taking the result of reading DT and adding 1 - an operation which takes just a few clock cycles and doesn't branch. (Not that it would change anything in the average Arduino sketch, but this was used in an application which had a few time-sensitive things going on.)
{{< /alert >}}

{{< alert severity="success" >}}
Exercises for the reader. A) why am I going through the trouble of using an `unsigned char` variable, instead of just _any random int_? B) is `volatile` really needed for the variable `last`?
{{< /alert >}}

### A note of disappointment

For the scarcity of rigorous and clear _hobby level_ Internet resources; and the latest versions of KiCad and Fritzing, which to my amazement proved to both be useless to draw a circuit so simple I could describe it using text.