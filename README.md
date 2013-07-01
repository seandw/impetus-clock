Impetus
=======

Impetus is a human-detecting alarm clock that is programmable via
Twitter.

## Project Hierarchy

This repository is split up between the two programmable components
and a technical manual.

The manual is in `doc/`, which includes the compiled manual
(`doc/manual.pdf`) and the LaTeX/images that make up the manual.

`arduino/` contains the Arduino project and libraries necessary for
the Arduino Pro Mini portion of this project, which communicates with
all of the sensors and actuators involved in the project.

`rpi/` contains the Python script that is run on a Raspberry Pi to
communicate with Twitter and the Arduino Pro Mini. It was run on
Python 2.7 and required the installation of the `matplotlib`,
`pySerial`, and `Twython` libraries. The folder also includes a
configuration file skeleton used for both Twitter credentials and
alarm times.

## Notes

The programming portion of this project was done in roughly 4 days,
and I believe that it shows. There are plenty of improvements that
could be made as it stands, but at this point, I gain very little from
actually making those improvements aside from getting a tiny little
monkey off my back, as this code is no longer being run on any piece
of hardware.

That being said, be very, very wary of running this code, if you're
crazy enough to think about doing so.