---
title: 'All you need to know about KBD keyboard files (and nothing more)'
slug: all-you-need-to-know-about-kbd-keyboard-files
publishDate: '2022-10-31T09:00:00+01:00'
categories:
- linux
tags:
- tutorial
- linux
- 'reverse engineering'
- software
- archaeology
image: images/header.jpg
---

It's been a few years now since I switched to Wayland. I use [Sway](https://github.com/swaywm/sway), a compositor based on [wlroots](https://gitlab.freedesktop.org/wlroots/wlroots), and apart from the sporadic broken Wayland application (easy fix: force XWayland) and Java application (easy fix: set `_JAVA_AWT_WM_NONREPARENTING=1`), it's mostly been great times.

I have also been a long time user of [UK International Keyboard](http://www.chiark.greenend.org.uk/~johns/kbukint.html), and that is the layout I know by heart and use on all physical keyboards. This layout builds upon the standard UK keyboard to enable you to type ṽårìóǘş kïņḑş õf åçĉëñţş äņḑ şẙḿbôĺş not found on the keyboard itself. This is achieved through dead keys: special keyboard sequences which enable a modified state for the next key you type, allowing to make combined characters without pressing a large number of keys all at once. For example, to produce the character ñ, I use _AltGr-~_ - which is the "dead tilde" combination -, and then I type _n_ separately.

Lately, I came across the issue of typing Greek characters, for maths and engineering-related applications. For the first few hours of work, I made do with simply having a character table handy and copy-pasting as needed. But soon enough, I realized this was no long term solution. Soon thereafter, my generalization instinct was so kind as to make me notice that hey, it would be good to have a general way to configure the keyboard to type any symbols I might like... using dead keys!

Starting from UK International Keyboad (from now on _kbukint_), I tried to go through adding some sequences. 

### XKB

X Keyboard Extension, or XKB (right?), is the way X applications have been handling keyboard for a few decades. While I can't find any historic description of how it came to be (and I'm too young to just know), [specification documents](https://www.x.org/releases/current/doc/kbproto/xkbproto.pdf) date as back as 1996, suggesting that similar non-standard ways of doing the same thing must have been around for some time at that point.

What does Wayland have to do with all of this? Well, while Wayland doesn't have any official way to handle keyboards and keymaps, XKB is [what they suggest to use](https://wayland-book.com/seat/xkb.html), and in particular, all of the Wayland implementations I've seen tend to use [xkbcommon](https://xkbcommon.org/doc/current/md_doc_compat.html), a quite modern implementation which is reasonably compatible: it uses the same keyboard data distribution that comes with X11.

The upside of this is obvious: we have the same data format! So almost 30 years of experience with real-world keyboard layouts is still here at our disposal to use with xkbcommon. The downside is a bit more subtle: we have the same data format. Yup. As while it works just fine, it can be rather... peculiar. To see a couple of examples:
* It fiercely promotes include hell. Ok, this one is kind of obvious. Keyboards all look very similar, so it's understandable that efforts were made to reduce duplication. These efforts reached their objective... by paying a steep price.
* The files are not very self-referential. That is, looking at them - both names and contents - you really struggle to get what they are doing. And as, especially nowadays, those files are used by 4 different libraries and compatibility layers to do all kinds of stuff, it can be a bit difficult to find the right documentation.

#### XKB + Wayland (just for fun)

Now that I have scared away the less corageous dwellers, let's take a look at how a keyboard definition works. We're going to take a very simple approach: let's suppose we press the key `A` on our keyboard. How does the focused program know to type the character `a`?

You can find the long version [here](https://wayland-book.com/seat/keyboard.html), but the bottom line is that a Wayland compositor (or server) will communicate with a client over a `wl_keyboard` Wayland object. This will:
* inform the client upon the current keyboard layout (in XKB format) on connection, as well as any changes down the road
* forward the raw keyboard events, so that the client can run them through their preferred keyboard library (such as `xkbcommon`!)

### How does XKB work?

With those premises, then, I argue that writing a custom keyboard layout is akin to finding out how `xkbcommon` and similar libraries (i.e. implementations of XKB) work: since it's their job to turn raw keystrokes into characters according to keyboard layout files, our problem is (in a nutshell) understanding how to correctly instruct them to to their job.

#### XKB abstractions

To achieve that, we have to learn about a few abstractions. Those abstractions correspond to actual files residing in `/usr/share/X11/xkb` (further paths in this article will be relative to this one), in directories called with their lowercase name:
- _Keycodes_ are a simple correspondance between _raw input events_ and _X key events_. In modern Linux, the `evdev` keycodes are the most commonly used, as [evdev is the preferred way](https://docs.kernel.org/input/input.html#evdev) to expose input events to userspace ([curiously](https://wayland-book.com/seat/keyboard.html#input-events), before feeding `evdev` scancodes to XKB, you need to increment their value by 8; that is, the mapping contained in `keycodes/evdev` expects you to do that. I do not know who made that choice or why, and if you do know please leave a comment!)
- _Types_ are kind of abstruse, but in a nutshell, they define how the current XKB state is utilized when a keycode gets translated into a symbol. This will be much clearer later on, but for now keep in mind that each keycode is associated to one or more symbols (example: keycode for `A` → symbols `a` and `A` on most keyboard layouts), and types are ways to determine how to decide which symbol to pick when there is more than one available for a given keycode (example: to pick between `a` and `A`, the `Shift` or `Caps Lock` modifiers are used on most keyboard layouts)
- _Symbols_, also called _keysyms_, are (finally) what gets emitted following a keypress. Symbol files contain big tables describing what the combination of each state (more on this later) and keycode should be translated into a symbol - once again, taking _types_ into consideration. In fact, symbols by themselves are what could be reasonably described as "keymaps". _Groups_ are also a thing here: they simply are alternative sets of symbols available in a keymap (I'm guessing this is a relic from times where changing a keymap on-the-fly was not a thing), and you can have at most 4 of them for each keymap
- _Geometry_. I didn't bother understanding this one in detail, as `xkbcommon` describes it as: "there were very few geometry definitions available, and while xkbcommon was responsible for parsing this insanely complex format, it never actually did anything with it". It contains information such as keyboard size, where the keys are placed, the color of LEDs, and the radius of keycap corners (I know it sounds like a joke, but go check for yourself). This is documented as only being useful for programs that show you a graphical representation of your keyboard layout
- _Compat_ and _rules_. These are incredibly specific, and I will not go in much detail. Compat thingies (how else would I define them?) define various compatibility things of assorted type, such as Caps Lock locking, LEDs, and funky keyboard and platform-dependant stuff. Rules define ways to put all the other abstractions together in various funky ways and with manual overrides called _options_.

#### The translation process

So, the translation process, as I mentioned before, is conceptually pretty simple:

```
(keycode, state) → symbol (→ UTF-8 representation, if must print)
```

Our next step, as you can imagine, is to find out exactly what this _state_ is, and how it plays with keycodes to produce symbols. So far, looking at the abstractions, we have gathered this information:
- Depending on the _type_ of a symbol, the state is interpreted differently
- _Groups_ can outright change the set of symbols we are working with

To paint a full picture, we actually need to introduce one more abstraction. Some keycodes, instead of resulting in a symbol, result in a change of _level_. The level then combines with the _type_ of a keycode mapping to select which symbol is emitted. We can now better describe our `A` key example: the _Level 1_ symbol for the key `A` is `a`, while the _Level 2_ symbol is `A`. You guessed it: in most keyboard layout, you go from Level 1 to Level 2 temporarily with the `Shift` key, or in a latching way (but only for alphabetic characters!) with the `Caps Lock` key. Commonly, the `AltGr` (aka `Right Alt`) key brings you to Level 3, and the combination of `Shift` and `AltGr` to Level 4.

Before diving into this I was not really familiar with the concept of _keyboard levels_, but [it seems](https://en.wikipedia.org/wiki/AltGr_key) that it's actually the common terminology. It makes sense historically: typewriters had letter heads that had literally characters on multiple levels, and you _shifted_ (as in, moved a big chunk of the mechanism) to higher levels to print different characters.

Let's put it together:
- `(keycode, state) → symbol (→ UTF-8 representation, if must print)`
- `state = (active group, active shift level)`
- So, in substance, the emitted symbol depends on the received keycode (i.e. what key was stroked), the active group (sorry, we'll skip this one entirely for this article), and the active shift level (depending on the type, determined e.g. by `Shift`, `Caps Lock`, `Num Lock`, etc.)

#### A full example: printing the letter "A"

Let's take the "gb" symbol map into consideration now, and to go back once again to the same example, let's see how that translates our `A` keypress into the uppercase letter "A". We finally get to take a look at the file format! So first of all, let's find the "gb" keymap in `symbols/gb` and [open it](https://github.com/freedesktop/xkeyboard-config/blob/3c325a4e9a6344e0e8ceb341464553085705e052/symbols/gb).

The first thing we might notice is that in the same file we have multiple `xkb_symbols` directives. These are not different groups, but completely separate symbol maps! It might be useful to know how the different maps inside the same files are addressed. It is rather simple: `file(map)`. So, the first keymap inside the `gb` file, which is called `basic` (line 4), is referred to `gb(basic)`.

The second thing we notice is that the `gb(basic)` keymap is actually pretty short, and doesn't include most of the keys we expect to find on an English keyboard. The most attentive observers, however, will have noticed an `include` directive (line 9), and it does exactly what you think it does: it includes stuff from a different map. In our case, the include reads `latin`, and you might notice that we have no `(map)` part in our `file(map)` map name. This just means "include the default `latin` map".

So let us [open](https://github.com/freedesktop/xkeyboard-config/blob/master/symbols/latin) the `symbols/latin` file now, and let's take a look at the `latin(basic)` map - which is the one marked with `default` (line 3). Finally, we spot our `A` (line 39)! It reads:

```
    key <AC01>	{ [         a,          A,           ae,           AE ]	};
```

Let's dissect it. `key <AC01>` means that we are defining the mapping for keycode `<AC01>`. This keycode corresponds to the physical key immediately to the right of the `Caps Lock` key on ISO and ANSI QWERTY keyboards. Curly braces are then `{` opened, and after that, square braces are `[` opened as well. We then have a comma-separated list of symbols: `a`, `A`, `ae`, `AE`. These correspond to the four different levels allowed by the type (more on it later). So our symbol of interest `A` is a Level 2 letter. Note that this does _not_ correspond to their UTF-8 (or any other encoding) representation: it is merely a coincidence (or rather, in this case, a convenience), that the `a` symbol is normally rendered as "a" - and we don't need to go far to find a counterexample: the symbol `ae` normally renders to "æ", and not "ae". Finally, both brackets are `]}` closed.

So, we pressed `Shift-A`, and our XKB library is good and well-functioning and upon receiving the corresponding scan codes it knows to pick the Level 2 symbol for `<AC01>`. How is this symbol converted to its UTF-8 (or, again, any other encoding) representation, assuming that you are e.g. typing stuff into a text editor? Pretty simple: XKB libraries have [big lists](https://github.com/xkbcommon/libxkbcommon/blob/2530f6444bfad2bf67ee926e57df8987afeebf4a/include/xkbcommon/xkbcommon-keysyms.h) of symbols, and [big look up tables](https://github.com/xkbcommon/libxkbcommon/blob/68dddd4132521dc72133a4f0010d0d07ec30a16e/src/ks_tables.h) to help with parsing a "a" in the keymap file to the [XKB_KEY_A](https://github.com/xkbcommon/libxkbcommon/blob/2530f6444bfad2bf67ee926e57df8987afeebf4a/include/xkbcommon/xkbcommon-keysyms.h#L578) constant value in the big list. And obviously, they have functions such as [`xkb_state_key_get_utf8()`](https://xkbcommon.org/doc/current/group__state.html#ga0774b424063b45c88ec0354c77f9a247) to take advantage of all of the above in a locale-sensitive manner.

One more detail to go through to finish up with this example. We can actually rewrite the above line as:

```
    name[Group1] = "Default group";
    ...
    key <AC01>	{
        type = "FOUR_LEVEL_ALPHABETIC",
        symbols[Group1] = [a, A, ae, AE]
    };
```

What we did in this "long form" version was to make the _type_ and _group_ explicit. Two interesting things on these matters:
- The _type_, if not specified like above, it is automatically determined. [Here](https://github.com/xkbcommon/libxkbcommon/blob/f60bdb1680650a131e8e21ffa4a8a16775a35c9f/src/xkbcomp/symbols.c#L1278) is how xkbcommon does it (archaeology: the copyright note bears the year 1994 and the name Silicon Graphics Computer Systems, Inc.). Basically, it depends upon whether you have 1, 2, or 4 levels defined, and whether level pairs 1-2 and 3-4 (when applicable) define `lowercase-UPPERCASE` pairs of characters. This is make `Caps Lock` work as a permanent shift for letters, but not for numbers. [This document](https://www.charvolant.org/doug/xkb/html/node5.html#SECTION00054000000000000000), which was otherwise quite helpful, only proposes unexhaustive rules which only deal with up to two levels per keycode
- _Groups_ need to be defined beforehand (i.e. inside a keymap `{scope}`, but outside key `{scopes}`) and given a name, if at all used.

To wrap up the example, a quick recap:
- We pressed the `Shift-A` keys on the keyboard
- A Linux driver for the keyboard picked those up, and emitted them to userspace through `evdev` using [their key codes](https://github.com/torvalds/linux/blob/30a0b95b1335e12efef89dd78518ed3e4a71a763/include/uapi/linux/input-event-codes.h#L105) (to be pedantic, the driver emitted a scan code, and it was the converted to a key code through a process that can be tapped into from userspace using `udev`)
- Our XKB library received all that and mapped it to keycode `<AC01>`, inspected its type, decided that `Shift` means Level 2, and picked the Level 2 symbol `A`
- Our userspace application asked the library to convert that to UTF-8, and the library proposed the character "A" for that

#### Types in-depth

Actually, _in-depth_ would mean an insane amount of research and write-up. So let's just stick to a selection of the actually interesting stuff (_ONE\_LEVEL_, _TWO\_LEVEL_, _ALPHABETIC_, and _FOUR\_LEVEL\_SEMIALPHABETIC_) and see how these work.

Starting from the first three, defined in `types/basic`:

```
    type "ONE_LEVEL" {
        modifiers = None;
        map[None] = Level1;
        level_name[Level1]= "Any";
    };

    type "TWO_LEVEL" {
        modifiers = Shift;
        map[Shift] = Level2;
        level_name[Level1] = "Base";
        level_name[Level2] = "Shift";
    };

    type "ALPHABETIC" {
        modifiers = Shift + Lock;
        map[Shift] = Level2;
        map[Lock] = Level2;
        level_name[Level1] = "Base";
        level_name[Level2] = "Caps";
    };
```

I think most of it is very much self-explicative: the types map different modifiers (`Shift`, `Lock`) to different levels. The only interesting note is the difference between _TWO\_LEVEL_ and _ALPHABETIC_: the former ignores `Caps Lock`, which is consistent with the fact that `Caps Lock` doesn't work on numbers.

The last one is defined in `types/extra`:

```
    type "FOUR_LEVEL_SEMIALPHABETIC" {
        modifiers = Shift + Lock + LevelThree;
        map[None] = Level1;
        map[Shift] = Level2;
        map[Lock] = Level2;
        map[LevelThree] = Level3;
        map[Shift+LevelThree] = Level4;
        map[Lock+LevelThree] = Level3;
        map[Shift+Lock+LevelThree] = Level4;
        preserve[Lock+LevelThree] = Lock;
        preserve[Shift+Lock+LevelThree] = Lock;
        level_name[Level1] = "Base";
        level_name[Level2] = "Shift";
        level_name[Level3] = "Alt Base";
        level_name[Level4] = "Shift Alt";
    };
```

This one is a little more involved, but not much when you filter out the noise (such as `level_name` which is just aesthetics for tooling). First of all, we see something called a _virtual modifier_ called `LevelThree`. It's usually `AltGr`, and we will see later how to redefine it for our symbol maps. Then, going to the juice: levels 1 and 2 work exactly the same as in the _ALPHABETIC_ type; `LevelThree` is for level 3 (duh); and `Shift + LevelThree` is for level 4.

Then we see something peculiar: level 3 and four are _also_ defined as `Lock+LevelThree` and `Shift+Lock+LevelThree`. Why? Well, because the mappings define _exact matches_. Since we want `AltGr` to work even when `Caps Lock` is active, we have to explicitly say that's ok. But then this poses a problem: modifiers get consumed when they match with a mapping. Since `Caps Lock` is also used by what [are called](https://www.x.org/releases/X11R7.6/doc/xorg-docs/input/XKB-Enhancing.pdf) "internal capitalization routines" (about which I could not find any information), and presumably by some applications, we want it to go through after a match. Hence the `preserve` directives: we define the same matches we had in the `map` directives, and we say that, for those matches, we want the `Lock` modifier to go through.

Before wrapping up this section, let's go through how automatic type selection is performed. As I [previously linked](https://github.com/xkbcommon/libxkbcommon/blob/f60bdb1680650a131e8e21ffa4a8a16775a35c9f/src/xkbcomp/symbols.c#L1278), xkbcommon provides us with the answer for something that (as far as I can see) lacks explicit documentation. We find out that the selection depends upon three variables: the number of defined levels, the _case_ (as in upper or lower) of the symbols, and whether any the symbols on any on the levels is defined _keymap_ or not. We notice a pretty blatant violation of abstraction here: why would XKB care about character case, when symbols are abstract things that conceptually predate characters in any encoding or locale? I suspect the answer is simply "because it made writing symbol maps a bit nicer". On to it:

| **#lvls** | **case** | **num** | **resulting type** | **meaning** |
|---|---|---|---|---|
| ≤1 | any | any | ONE_LEVEL | Modifiers ignored |
| 2 | xX | any | ALPHABETIC | Caps/Shift = L2 |
| 2 | ?? | yes | KEYPAD | Num = L2 |
| 2 | ?? | no | TWO_LEVEL | Shift = L2, Shift + Num = L1 |
| ≤4 | xXxX | any | FOUR_LEVEL_ALPHABETIC | Caps/Shift = L2, Three = L3, Caps/Shift + Three = L4 |
| ≤4 | xX?? | any | FOUR_LEVEL_SEMIALPHABETIC | Caps/Shift = L2, Three = L3, Shift + Three = L4 |
| ≤4 | ???? | yes | FOUR_LEVEL_KEYPAD | Num/Shift = L2, Shift + Num = L1, Three = L3, Three + Shift + Num = L3, Num/Shift + Three = L4 |
| ≤4 | ??? | no | FOUR_LEVEL | Shift = L2, Three = L3, Shift + Three = L4 |
| any | any | any | no type | ...no idea, sorry |

<br>

This is not all that interesting. I decided to include it because it seems that the only other place where it was documented, apart from here, was the source code of existing XKB implementations.

#### Picking a modifier for LevelThree

We have seen in the types we examined that the level three modifier is... `LevelThree`.  If you have never seen the `LevelThree` key on your keyboard, look more carefully. If you still haven't found it, look eve- I'm just joking. Of course there is no `LevelThree` key on your keyboard.

The idea is that `Shift` is pretty standard, but `LevelThree`, you may want to pick depending on your keyboard type and layout. For that, XKB has a mechanism called "virtual modifiers". They are actually defined in an unnecessarily perverse way, needing two separate (but related) directives in symbol files to be bound to an actual modifier key, and needing to be re-declared in type files where they are used.

Luckily, we don't have to go through any of that: the XKB data distribution pre-declares most of the stuff you will ever need, and conveniently provides the `symbols/level{2,3,5}` files, containing the correct directives to use various keys as Level 3 modifiers. For example, if you include `level3(ralt_switch)` in your symbol map, then `AltGr` will become your `LevelThree`. As an alternative, `level3(alt_switch)` is also available, imitating Macs (both `Alt`s shift to Level 3). And so on.

#### Dead keys

Dead keys are, simply put, symbols which don't have a character representation; instead, they are meant to be combined with other symbols to produce more complex sequences. `man 5 Compose` from libX11 offers some information, and the [xkbcommon documentation](https://xkbcommon.org/doc/current/group__compose.html) some more, but, simply put, we just need to emit them in symbol maps, and then consume them in a `Compose` file.

The syntax for compose files is as follows:

```
<dead_grave> <A> : "À" Agrave
```
The sequence is defined before a `:` colon, and the resulting emitted UTF-8 character and symbol after it. The UTF-8 character can also be omitted, and in this case the implementation will decide how to behave (usually depending on the locale, according to libX11).

An exhaustive list of dead key symbols (`grave_*`) can be found [in the source code of xkbcommon](https://github.com/xkbcommon/libxkbcommon/blob/f60bdb1680650a131e8e21ffa4a8a16775a35c9f/src/ks_tables.h#L747) (as always!), and you can find existing `Compose` files on your local system in `/usr/share/X11/locale`. Here you will find a `compose.dir` file, which matches locales with `Compose` files. For example, using the `localectl`, I find out my locale is `en_GB.UTF-8`. A quick grep through `compose.dir` quickly reveals that my compose file is (like for most other locales) `en_US.UTF-8/Compose`. That's the file that libX11 and xkbcommon and all other compliant XKB implementations will consult for key composition.

### Back to the beginning: Greek letters

Let's remind ourselves why we walked this path, climbed the mountain, endured the snow, and read so much documentation and source code... ah, yes, right, I wanted to type some Greek letters. Well, this is easy with our current knowledge:
- Change a symbol map, adding a way to emit `dead_greek` (or conceptually, and other dead key symbol - it's just a name)
- Add Compose entries for the Greek letters.

Looking at `/usr/share/X11/locale/en_US.UTF-8/Compose` we actually get a surprise: half of the job has already been done for us. All the Greek letters are there, both lowercase and uppercase, in the form `<dead_greek> <some_latin_letter>`. Then it's just a matter to take the symbol map I use, `kbukint`, and adding a way to emit `<dead_greek>`. I pick `AltGr + G` for that, so let's replace the Level 3 symbol `NoSymbol` with `dead_greek`:

```
    key <AC05> { [ g, G, dead_greek, NoSymbol ] };
```

And with this, we wrap up. Αντιο σας!

### Further reading

- All [documentation](https://xkbcommon.org/doc/current/index.html) and [source code](https://github.com/xkbcommon/libxkbcommon) of xkbcommon is a _great_ resource to learn about XKB: its a modern no-nonsense implementation of the parts that actually matter for modern applications
- [An Unreliable Guide to XKB Configuration](https://www.charvolant.org/doug/xkb/html/xkb.html) by Doug Palmer, and in particular the _XKB Configuration Files_ section, provided great starting points for many parts of my research
- The [Arch Wiki article about XKB](https://wiki.archlinux.org/title/X_keyboard_extension) is also a great resource to get started, and the Wiki is an invaluable resource in general for all things Linux
- [How to further enhance
XKB configuration](https://www.x.org/releases/X11R7.6/doc/xorg-docs/input/XKB-Enhancing.pdf), by Kamil Toman and Ivan U. Pascal. This is just basically a tutorial on how to make a custom keymap, and it goes into enough technical detail in a few places to have been useful to my research
- [The XKB Configuration Guide](https://www.x.org/releases/X11R7.5/doc/input/XKB-Config.html), official X.Org stuff

Header image by [Dmitry Nosachev](https://commons.wikimedia.org/wiki/User:Nosachevd), licensed as CC Attribution-Share Alike 4.0 International.