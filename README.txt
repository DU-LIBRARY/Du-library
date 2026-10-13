Darul Uloom Library: offline app
================================

Three sections, switched with the tabs at the bottom:
  Search      index.html    the catalogue search
  Shelf Map   shelves.html  which shelf each book is on (a saved copy; books are moved in the Shelf Map in Claude)
  3D Library  3d.html       the library room in 3D

Open the site once with signal and add it to the home screen. After that, all three
sections work with no internet. Fonts (fonts/) and the 3D engine (lib/) are part of
the app, so nothing is loaded from outside. Their licences are in those folders.

Updates are built and uploaded by Claude: each update stamps a new version in sw.js,
and phones pick it up the next time the app is opened with signal.
