Darul Uloom Library: offline app
================================

Four sections, switched with the tabs at the bottom:
  Search      index.html    the catalogue search
  Shelf Map   shelves.html  which shelf each book is on (a saved copy; books are moved in the Shelf Map in Claude)
  3D Library  3d.html       the library room in 3D
  Dars        dars.html     the darsi kutub (dars books), grouped by year group

Open the site once with signal and add it to the home screen. After that, all four
sections work with no internet. Fonts (fonts/) and the 3D engine (lib/) are part of
the app, so nothing is loaded from outside. Their licences are in those folders.

Darsi kutub
-----------
For any kitab with more than one copy, ONE copy is the madrasah library copy and the
other copies are madrasah (dars) copies used by the year groups:
  library copy = 1, madrasah copies = total copies - 1
unless the catalogue gives its own number of madrasah copies (some dars books keep
their class copies outside the library).

This lives in the master catalogue only (no second list). Three optional fields per book:
  Dars             yes / no
  Years            year groups, e.g. "Year 1, Year 2, Iftā"
  Madrasah copies  a number, only when it is not total copies - 1
Every title with more than one copy is shown as darsi as a SUGGESTION and listed
under "Unassigned" (unconfirmed) until a teacher sets its year groups. Put "no" in
Dars for a multi-copy title that is not a dars book.

The Dars tab lists them by year (a book in several years appears under each), with
the library and madrasah copies and the shelf each stands on, linking to the Shelf Map
and the 3D Library. On Search, a darsi book shows "Library copy: 1 · Madrasah copies: N
· Years: …".

darsi-kutub.csv is the same list as a spreadsheet (Title, Author, Category, Year groups,
Total copies, Library copy, Madrasah copies, Shelf). It is written from the catalogue on
every update, so it always matches the app; download it from the Dars tab. In the book list
a darsi book carries mc (madrasah copies) and y (year groups, once set).

Updates are built and uploaded by Claude: each update stamps a new version in sw.js,
and phones pick it up the next time the app is opened with signal.
