This repository contains scripts for dumping debug symbols from OS X
system libraries contained in Apple system updates.

It uses [reposado](https://github.com/wdas/reposado) to mirror updates from
Apple's update servers locally, and then several scripts to unpack the updates
and dump symbols into [Breakpad](code.google.com/p/google-breakpad/)'s
textual symbol format.

A [Dockerfile](Dockerfile) is provided to ease usage given the number of
prerequisites. You can pull a prebuilt image from
`luser/breakpad-mac-update-symbols` on Docker Hub.

This software is provided under the MIT license. See [LICENSE](LICENSE).
