# Daily-Monitor-Project

Daily Proof

A small "soft lock" app that pops up full-screen when you log in to Windows
and asks you to attach 5 photos for the day:


Out in the world / Tree of the day
Breakfast
Lunch
Dinner
Library / Study


Once all 5 are attached, the photos are copied into your Obsidian vault and
a markdown note is generated with them embedded. The "Unlock" button then
closes the window. There's also a "Not now (Esc)" button if you genuinely
need to bypass it — this is a nudge, not a real lock.

1. Requirements


Python 3.9+ (Windows installer from python.org — tick "Add to PATH" during install)
Tkinter comes bundled with the standard Windows Python install, no extra
packages needed.


2. Configure your vault path

Open config.json and set vault_path to your actual Obsidian vault folder, e.g.:

json{
  "vault_path": "C:/Users/Alex/Documents/ObsidianVault",
  "subfolder": "DailyProof"
}

The app will create a DailyProof folder inside your vault, with:

ObsidianVault/
  DailyProof/
    2026-06-16/
      out_in_world.jpg
      breakfast.jpg
      lunch.jpg
      dinner.jpg
      library.jpg
    2026-06-16.md

Each daily note embeds the 5 photos using Obsidian's ![[...]] image syntax,
so they'll render directly when you open the note.

3. Test it manually

In a terminal, from this folder:

python daily_proof.py

A fullscreen window should appear. Click "Choose Photo" for each category,
pick an image file, and watch the status turn green. Once all 5 are green,
"Unlock" becomes clickable.

4. Run it automatically at login

Easiest option — Startup folder:


Press Win + R, type shell:startup, press Enter. This opens your
Startup folder.
In that folder, create a shortcut to pythonw.exe (this runs Python
without a console window). It's usually at:
C:\Users\<you>\AppData\Local\Programs\Python\Python3x\pythonw.exe
Edit the shortcut's properties and set "Target" to:
"C:\...\pythonw.exe" "C:\path\to\daily_proof\daily_proof.py"
Set "Start in" to the daily_proof folder (so it can find config.json).


Now the app will pop up every time you log in to Windows.

5. Notes / next steps


This is a soft lock: it doesn't change Windows login or block other
apps, it's just a fullscreen reminder that's mildly annoying to skip.
That's intentional — it avoids any risk of locking yourself out of your
own machine.
If you take photos on your phone, set up a synced folder (OneDrive,
Google Photos sync, Syncthing, etc.) so they show up on your PC, then use
"Choose Photo" to pick them from that folder.
To re-run the check more than once a day (e.g. you want it to reappear if
you log out and back in), it already works that way automatically — it's
keyed off today's date.
Future idea: once this is working, you can call a vision model on each
photo to sanity-check it (e.g. "does this look like a meal / a tree /
a library?") before counting it as done. Happy to help wire that up once
the basic flow feels right.
