mkc64tap.py
===========

This is a simple tool to generate .TAP files for the C64.

The generated tape can be loaded using the kernal loader.

Example:

    mkc64tap.py file.prg -o file.tap


Then you can use that .TAP file in your favourite emulator:

  1. attach the tape
  2. run `LOAD"*",8,1:RUN"`

All PRG files are added as non-relocatable programs. Run the
tool with `-h` flag for help.

Requirements:

  - Python 2.7

References:

  - http://c64tapes.org/dokuwiki/doku.php?id=loaders:rom_loader

