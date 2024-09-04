---
title: 'A security post-mortem & the (shamefully) flimsy security of Meta, Inc.'
slug: the-shamefully-flimsy-security-of-meta
publishDate: '2023-02-09T09:00:00+01:00'
categories:
- security
tags:
- ouch
- fail
- 'social networks'
- security
- phishing
image: images/header.jpg
---

Andrea has a small content creation business. They're what the youngsters call an _influencer_, and as such, among their equity, they possess very valuable social accounts with a valuable follower count. A few days ago, one of those accounts was hacked, using a classic vector: a stolen password, either leaked or phished, combined with 2FA phishing.

This article is a post-mortem (and in a way a post-vitae), showing what we did to recover access to the account, and to secure it. Brace yourselves: there is a juicy plot twist.

### Act 1: hands up! this is a robbery!
_your money or your (digital) life_

Let's analyze the following set of information from Day 1:

- I get a message from Andrea, saying "hey, please, ignore any messages from my Instagram account: it has been hacked!"
- Andrea recovers their account using Instagram's "selfie identification" - a form of account recovery where you send a video selfie, and someone (or something) compares it with your Instagram pictures to assess whether it's really you
- Andrea changes their Instagram and Facebook passwords, and happily notifies me that the crisis is over

The post-mortem is over, right? ...Of course not. Because Andrea, the following day, writes me a new message, saying "hey again. please, just block my Instagram account... it's lost forever. they're still in." And I don't think much of it. But then my mind circles back to it a few hours later, and I think - wow, how did that happen? They managed to recover their account. They changed their passwords. They have 2FA and email notifications set up. What makes them say that?

If you're emphatizing with the story and playing along in your head, maybe a couple of ideas have popped up in your mind: Andrea's email account has been compromised as well, and/or Andrea's got their whole computer compromised (think of a keylogger, or a trojan).

So I get back to Andrea, in fact I call them - I need to get to the bottom of this _fast_ -, and I ask some questions, for example:

- hi Andrea! so, what happened?
- but you did change all of your passwords to something you have never used before, right?
- and you did _not_ change your email password, tho, correct?
- have you downloaded any attachments or new programs lately?

After that conversation, the set of additional information, from Day 2, looks like this:

- the account was recovered, the passwords changed to safe and uncompromised new ones...
- ...but then they soon notice that their contancts are still getting phishy messages
- Andrea has only downloaded two files in the last few days: both were document attachments from people they trust, and the content was very specific and private and reflected their expectations - it could not have been made up by a third party
- they had not changed their email password

### Act 2: saving the world
_and feeling like heroes in the process_

Ouch. Not knowing very well the security hygene of Andrea, my bat-senses activated. I told Andrea - hear, it's not that I don't trust you, but let's change all of the passwords again. This time exhaustively and in the correct order: email first, and then accounts connected to it. Not only that, let's also reset and/or enable 2FA on all accounts, enable all available forms of login notifications, and completely wipe any trusted devices and existing logins from the accounts.

I offered my help in doing that, and I proceeded to do it - helping Andrea to pick the new passwords, this time around using [safe practices](https://xkcd.com/936/) (Andrea had revealed their old passwords to me - like most people, they're not very good at creating good passwords.)

This time - I say to myself - we did everything right. So now, finally, it's over. Or...

### Act 3: we have a mole in our organization
_and we need to dig it out asap, because people are losing money_

Day 3. I have just changed the last password, regenerated the backup codes, reset 2FA, cleaned existing logins, even wrote to some of the recently contacted people that a scam was going on and not to comply with any instructions with links and codes involved coming from this account. At this point Instagram's _Login activity_ page looks like this:

![](andrea-login-activity.png "Andrea's Login activity, according to Instagram. Only one logged in device is shown - my own device. No hackers in sight.")

Then I noticed a notification pop up on the Messages menu item on the same Instagram page. Ok, it must be someone that has just read my warning message, thanking me. Let's go _heart_ their message and feel good about myself. But then, with shock and horror, I noticed that not only my warning message was gone (the audacity of that bitch...), but that the phishing act was proceeding, with some degree of success.

I hurried back to the _Login activity_ page, to find in more shock and more horror that, still, no login activity whatsoever was recorded apart from my own. Andrea, on the phone, confirmed that not only they didn't log in back into their accounts just yet, but that their computer had been off since the beginning of Act 2. Additionally, no email notification of new log-ins into Instagram had arrived. So, putting this all together, is was now clear that:

- it's not a virus in Andrea's computer
- Andrea's mailbox is not compromised - we got no notifications from Microsoft, except the one of my own login
- no one logged in the Instagram after completely overhauling the account's security settings

There is only one logical conclusion to this: _I_ am the scammer. Except, of course, since I know I'm not the scammer, there must be another explanation.

### Act 4: panic!
_sir, we dug out the mole. the mole is still inside_

Yes, panic. Because there must be another explanation, but now, since Instagram seems to think that I'm the only person logged in, only the very scary explanations remain. Some of them are:

- _I_ got compromised. But what are the chances? I had never seen Andrea's credentials before Act 1, so this means that they compromised me _in addition_ to Andrea, _after_ I started helping them. Now, Andrea is an influencer, not a government official or a secret agent. Also, my workstation is a pretty hardened (and non-standard to quite a degree) Linux machine. And finally, I have not made contact with no one new since the whole situation began. Thus, it is almost impossible that this is the case. Almost, so let's keep this aside.
- _Instagram_ got compromised. Again... what are the chances? But I have no way to verify this, either positively or negatively, so let's also keep this aside.
- Damn, I'm once again out of ideas.

So I did what any investigator in any decent invastigator movie does: I started annoying random people, and ran them through my information. And sure enough, just like in movies... it happened.

### Act 5: elementary, my dear Watson!
_it was just classic misdirection all along_

A dear friend - the same behind [this failed article series](https://www.bestov.io/blog/linux-redundant-ip-link) -, came up with an abstute observation: some of these _pesky modern social networks_ have provisions to give control of the account to third parties, for things like moderation, ad management, etc. A quick online search resulted in [a useful hit](https://help.instagram.com/218638451837962) right from Meta. It was useful, because it quickly allowed me to rule out my friend's idea.

But like in the movies, the answer never cames outright. The smart investigator still needs to connect the last few dots. Otherwise, where would be the fun? Now, I'm not a smart investigator, but luckly I still got to connect those last few dots. So it's time for the plot twist.

Your Instagram contains a backdoor, created by Meta, called the "Meta Accounts Center." There is some evidence disseminated throughout your Instagram settings interface that this is the case, but let's see why these do not sufficiently communicate that your account is indeed backdoor-enabled:

![](andrea-meta-account.png "The two pieces of evidence to the existence of the Meta Account Center")

Piece of evidence A. _Account Center_ is a thing. Nice. And some account settings are moving? Sounds cool. If you scroll down the page, you also find piece of evidence B. Control shared experiences. Mh, cool. Post sharing. Who cares, I'm trying to fix bad things herWAIT WHAT? Logging in??

So, let's put this in a different way: assuming you scroll down to the right place in the page, you are now blessed to have 0.04% of your screen (I'm not joking - it's a thousand pixels out of about 2 million) telling you that hey - you see all these security and log-in settings here? Well, turns our we have a different website that _also_ allows you to decide more ways to log in to this very same account.

### Act 6: meet the assassin: Blessed Elvis
_everyone is finally relieved but also kinda still sad that someone died and it could have just as well been avoided_

An image speaks more than a thousand words:

![](andrea-blessed-elvis.png "Meta's backdoor finally informs us that a shady pal with a made up name can access Andrea's account")

But let's still put it in words: if you are willing to try out Meta's new ~~backdoor~~ place for important security information, you find out that there is Elvis: a shady pal with a made up name and a sports car as a profile picture who, after the whole account recovery shenanigan, is still free to access Andrea's account - with their own personal set of credentials.

Now - apparently Andrea, using their Instagram account, can access Elvis' Facebook account too. Time for a vendetta. But you see, Meta's new ~~backdoor~~ place for important security information sure gives you a lot of log-in related information, but some of it is not exactly correct: you _can't_, in fact, access a Facebook account with an Instagram account, even if the permissions to do so are (apparently) set up in the backdoor settings website. So false alarm: Elvis is not sloppy, they just know all there is to know about Meta's new ~~backdoor~~ place for important security information.

So... time for a quick clean up. First, I tried to block Elvis' Facebook account from being able to be used to access Andrea's Instagram account. But as it turns out, to stop a criminal you need their password. Luckily, whoever designed this thing, in a moment of pure enlightment, decided not to also require the password to _completely remove_ an account from the backdoor. And so, just like that, Elvis was behind bars. Just kidding, they're probably enjoying their new swimming pool, thanks to people's charitable contributions.

But you know, at least Andrea can get back to their non-criminal job. So that's finally achieved.

### Lessons
_a couple for me, but most of them for Meta, Inc._

What can we learn from this? Apart from the usual yada yada about security hygiene and stuff - because let's say it, if you assume your users have the slightest awareness about computer security you should consider getting a different job.

#### Sometimes, the answer is just difficult to find

It's not to make myself feel better, because there's no need to: I am thoroughly convinced I did an ok job managing this mess. But it's useful to remind myself that sometimes the answer is very difficult to find.

I had a set of information, and I connected it with a set of logical assumptions. Of course, it's been thousands of years since we first realized that empirical measurements of reality can easily fool us, but nonetheless, it took me a while to realize that if all of the plausible stuff is exhausted, then I should continue on to the implausible stuff.

I also learned that I should have more faith in what I see in television and drama: all of this quite literally happened like a Sherlock Holmes episode. All of it. Matteo, if you're reading me, you're my Watson. In retrospective, it was quite fun.

#### In a crime investigation, never trust the victim

Yup. Andrea got phished. I verified this very simply: I looked at the scammer's method, right from when they were trying to scam Andrea's contacts.

Here's the gist: they ask you to vote for them in a contest of some kind, then they tell you that to do that you need to open a link. That link is a page that steals your Instagram credentials, and then redirects you to Instagram's own page to add your mobile phone as a second factor. Nothing suspicious so far to your average user: it's Instagram, right? You logged in, and now it's asking you to increase the security of your account. Happened a thousand times to any of us. It's annoying, but this time a friend is counting on us.

So the user goes along with it. They get a code, they confirm their phone number to Instagram. But then here's the trick. The scammer immediately logs into your account, and you get a second code. They then ask you (remember - you don't know they're a scammer, you think it's a friend asking for a favour!) to send them that code, to confirm your vote for the contest.

And boom, they're inside. Time for the backdoor: they go to your Meta backdoor settings page, and they enable it with a random account they are using just as a way to log into yours.

But Andrea didn't tell me any of this. In fact, while I'm writing this article, they have no idea yet they've been scammed. I'm going to break the news to them by phone in a few hours. But I'm already sure: Andrea's mailbox contains a trail of the scam: phone verification added, and immediately a new access from an unknown location. And a few hours later, the first message from Andrea to me.

#### And about Meta...

So let me get this straight: Meta could have stopped this at so many different levels it's outright embarassing. Let's see the most blatant ones:

- Better spam control. Damn, Habbo Hotel was on top of this 15 years ago better than Meta, one of the biggest companies in the world, is today.
- Better notifications for new log-ins. In-app is essential, SMS would also be great (btw, Facebook has it and they're looking to remove it. So it's a habit, apparently.)
- ...any kind of notifications for new log-ins, really. Because after everything was over, I went and checked more thoroughly: if you log in through the backdoor, you don't get _any_ notification _anywhere_. And it doesn't appear as a login session in Login activity, either. Calling it a _backdoor_ doesn't sound like a joke anymore, does it?
- Put all the security and login-related settings in one place. Instead, they're _so_ scattered that evidently someone forgot to make this _new and improved_ login method _not_ behave like a backdoor. I.e. the simplest corollary of _reduce your attack surface_. I can't believe there are still Internet-first Fortune 100 companies that don't get this right.
- If you really need to have your security settings scattered around different websites, consider mentioning that using a tad more than 0.04% of the screen's area. A big red message in the center of all the security-related setting tabs would do, for example.
- When a user sets up your backdoor to use a (1) brand new Facebook account with (2) a different name, (3) email, (4) phone number, (5) date of birth, (6) that was registered in a foreign country, (7) with no content whatsoever, or any single of these 7 red flags, or maybe even without any red flag (since you're not too good a security anyway)... maybe send an email to the other accounts. Or something.
- When a user recovers their Instagram account after it was stolen, do not only restore the account contents, but also the backdoor, to its previous state.
- [WebAuthn](https://webauthn.guide/), please.

Really, _any_ of these 8 would have strongly mitigated the _security colander_ that is Meta. And most of them are so dead simple and obvious, that a very clear picture starts to get painted right before our eyes: Meta doesn't give a shit about protecting your personal data and your money. Their effort is so shallow and sub-standard that it's difficult to believe. It's so sloppy that it's probably illegal under GDPR's clear-cut resposibility to make a reasonable effort to protect your users' data.

Till next time.