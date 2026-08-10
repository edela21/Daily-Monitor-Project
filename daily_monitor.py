"""
Daily Proof - a small "soft lock" app that asks you to confirm 5 daily
photos (out in the world / tree, breakfast, lunch, dinner, library) before
letting you get on with your day. Writes a markdown note + copies the
photos into your Obsidian vault.

Run this manually to test, or add it to your Windows Startup folder so it
runs automatically when you log in (see README.md).
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import json
import shutil
import smtplib
from email.message import EmailMessage

from datetime import date
from pathlib import Path
import os
from PIL import Image, ImageTk

CONFIG_PATH = Path(__file__).parent / "config.json"
QUOTES_PATH = Path(__file__).parent / "quotes.json"

DEFAULT_CONFIG = {
    # Change this to the path of your Obsidian vault
    "vault_path": "C:/Users/YourName/ObsidianVault",
    # Subfolder inside the vault where daily proof goes
    "subfolder": "DailyProof",
    # Email settings - leave sender_email blank to disable sending entirely
    "sender_email": "e.delaneyfn2187@gmail.com",
    "sender_app_password": "ydhj qecs apkv cyum",
    "supervisor_email": "kathryndelaney5@gmail.com",
}

# (internal_key, display_label) - what photos you need to upload
CATEGORIES = [
    ("out_in_world", "Tree of the day"),
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
    ("library", "Library / Study"),
]

# (internal_key, display_label) - what the time sliders track (independent
# of the photo categories above)
TIME_CATEGORIES = [
    ("outside", "Time outside"),
    ("library", "Time in library"),
    ("reading", "Time reading"),
    ("working", "Time working"),
    ("wasted", "Time wasted"),
]

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic")
MAX_MINUTES = 180  # slider range per task: 0-180 minutes (3 hours)


def load_config():
    """Load config.json, creating a default one on first run."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG


def get_daily_quote():
    """Pick a quote deterministically based on today's date, so it's
    stable all day and cycles through the list before repeating."""
    if not QUOTES_PATH.exists():
        return None
    with open(QUOTES_PATH, "r", encoding="utf-8") as f:
        quotes = json.load(f)
    if not quotes:
        return None
    # day-of-epoch as a stable, ever-increasing index
    day_index = date.today().toordinal()
    return quotes[day_index % len(quotes)]


def today_folder(config):
    """Return (Path, date_string) for today's photo folder, creating it."""
    today = date.today()
    today_str = today.strftime("%d-%m-%Y")
    #today_str = date.today().isoformat()
    folder = Path(config["vault_path"]) / config["subfolder"] / today_str
    folder.mkdir(parents=True, exist_ok=True)
    return folder, today_str


def existing_photo(folder, key):
    """Return the Path to today's photo for this category, or None."""
    for ext in IMAGE_EXTS:
        p = folder / f"{key}{ext}"
        if p.exists():
            return p
    return None


def time_data_path(folder):
    return folder / "_time.json"


def load_time_data(folder):
    """Load today's per-task minutes, defaulting to 0 for each time category."""
    path = time_data_path(folder)
    data = {key: 0 for key, _ in TIME_CATEGORIES}
    if path.exists():
        with open(path, "r") as f:
            saved = json.load(f)
        data.update({k: saved.get(k, 0) for k in data})
    return data


def save_time_data(folder, data):
    with open(time_data_path(folder), "w") as f:
        json.dump(data, f, indent=2)


def send_proof_email(config, folder, today_str):
    """Email the day's 5 photos to the supervisor. Returns (success, message)."""
    sender = config.get("sender_email", "")
    password = config.get("sender_app_password", "")
    recipient = config.get("supervisor_email", "")
 
    if not sender or not password or not recipient:
        return False, "Email not configured (sender/password/recipient missing in config.json)"
 
    photos = []
    for key, _ in CATEGORIES:
        photo = existing_photo(folder, key)
        if photo:
            photos.append(photo)
 
    if not photos:
        return False, "No photos found to send"
 
    msg = EmailMessage()
    msg["Subject"] = f"Daily Proof - {today_str}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Hi Mum,\n\nDaily proof photos for {today_str}, attached ({len(photos)} photos).\n \nLove,\nEthan \n(Automated email from Daily Proof app)"
    )
 
    for photo in photos:
        with open(photo, "rb") as f:
            data = f.read()
        ext = photo.suffix.lstrip(".").lower()
        maintype = "image"
        subtype = "jpeg" if ext in ("jpg", "jpeg") else ext
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype, filename=photo.name
        )
 
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True, f"Sent {len(photos)} photos to {recipient}"
    except Exception as e:
        return False, f"Failed to send email: {e}"


def write_markdown(config, folder, today_str, time_data=None):
    """Write/update the Obsidian note for today, embedding any photos found
    and writing per-task time data into YAML frontmatter for charting."""
    notes_root = Path(config["vault_path"]) / config["subfolder"]
    md_path = notes_root / "DailyMonitor" /f"{today_str}.md"

    if time_data is None:
        time_data = load_time_data(folder)

    frontmatter = ["---", f"date: {today_str}"]
    for key, _ in TIME_CATEGORIES:
        frontmatter.append(f"time_{key}: {time_data.get(key, 0)}")
    frontmatter.append("---")

    lines = [f"# Daily Proof", ""]

    quote = get_daily_quote()
    if quote:
        lines.append(f">[!tip] #### {quote['quote']}")
        lines.append(f"> — {quote['author']}")
        lines.append("")

    done_count = 0

    for key, label in CATEGORIES:
        photo = existing_photo(folder, key)
        lines.append(f"## {label}")
        if photo:
            rel_path = f"{today_str}/{photo.name}"
            lines.append(f"![[{rel_path}]]")
            done_count += 1
        else:
            lines.append("_missing_")
        lines.append("")

    lines.append("## Time tracking")
    for key, label in TIME_CATEGORIES:
        minutes = time_data.get(key, 0)
        lines.append(f"- {label}: {minutes} min")
    lines.append("")

    count = f"## **Progress: {done_count}/{len(CATEGORIES)}**"

    md_path.write_text(
        "\n".join(frontmatter + [""] + [count] + lines), encoding="utf-8"
    )


class App:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.folder, self.today_str = today_folder(config)
        self.status_labels = {}

        root.title("Daily Proof")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.configure(bg="#1e1e1e")

        # --- 1. DYNAMIC SCREEN SIZING FOR FULLSCREEN ---
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # --- 2. HEADER BANNER SETUP ---
        banner_height = 250  # Set this to whatever height you want!
        
        # We wrap the image inside a concrete Frame so Tkinter enforces the exact height
        self.header_container = tk.Frame(root, width=screen_width, height=banner_height, bg="#1e1e1e")
        self.header_container.pack(side="top", fill="x")
        # This line stops the frame from shrinking down to fit the text inside it
        self.header_container.pack_propagate(False) 

        try:
            banner_img_raw = Image.open("bannerimage.webp")
            # Pillow resizes the raw file smoothly to fill the exact dimensions
            banner_resized = banner_img_raw.resize((screen_width, banner_height), Image.Resampling.LANCZOS)
            self.banner_img = ImageTk.PhotoImage(banner_resized)
            
            # The banner label now expands to fill the container perfectly
            self.header_banner = tk.Label(self.header_container, image=self.banner_img, bd=0, highlightthickness=0)
            self.header_banner.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Error loading banner image: {e}")
            # If image fails, the background container frame color acts as the fallback
            self.header_container.configure(bg="#2d2d2d")

        # --- 3. BACKGROUND IMAGE SETUP ---
        try:
            bg_img_raw = Image.open("bgimage.jpg")
            bg_height = screen_height - banner_height
            bg_resized = bg_img_raw.resize((screen_width, bg_height), Image.Resampling.LANCZOS)
            self.bg_img = ImageTk.PhotoImage(bg_resized)
            
            # This label acts as our master background workspace for all central UI widgets
            self.bg_label = tk.Label(root, image=self.bg_img, bd=0, highlightthickness=0)
            self.bg_label.pack(side="bottom", fill="both", expand=True)
        except Exception as e:
            print(f"Error loading background image: {e}")
            self.bg_label = tk.Frame(root, bg="#1e1e1e")
            self.bg_label.pack(side="bottom", fill="both", expand=True)

        # --- 4. TITLE & SUBTITLE (Layered over Header Banner) ---
        title = tk.Label(
            self.header_container,
            text=f"Daily Proof - {self.today_str}",
            font=("Segoe UI", 28, "bold"),
            fg="white",
            bg="#0da7a7",  # Matches fallback, or transparent depending on design
        )
        #title.pack(pady=(25, 5))
        title.place(relx=0.5, y=40, anchor="center")

        subtitle = tk.Label(
            self.header_container,
            text="Add today's 5 photos to continue",
            font=("Segoe UI", 14),
            fg="#130303",
            bg="#1365c2",
        )
        #subtitle.pack(pady=(0, 15))
        subtitle.place(relx=0.5, y=100, anchor="center")

        # --- 5. APPLICATION CONTENT CONTAINER (Layered over Background) ---
        # A main scroll/layout frame to cleanly bundle and center your inputs vertically
    
        
        # Base container to hold both boxes side-by-side
        # We make its background match your theme color so it blends cleanly

        quote = get_daily_quote()
        if quote:
            quote_frame = tk.Frame(self.bg_label, bg="#1e1e1e")
            quote_frame.pack(pady=(10, 15), padx=40)
            quote_lbl = tk.Label(
                quote_frame,
                text=f"\u201c{quote['quote']}\u201d",
                font=("Segoe UI", 13, "italic"),
                fg="#dddddd",
                bg="#1e1e1e",
                wraplength=700,
                justify="center",
            )
            quote_lbl.pack()
            author_lbl = tk.Label(
                quote_frame,
                text=f"\u2014 {quote['author']}",
                font=("Segoe UI", 11),
                fg="#888888",
                bg="#1e1e1e",
            )
            author_lbl.pack(pady=(4, 0))

        # ==========================================
        # BOX 1: PHOTO UPLOAD CONTAINER (LEFT SIDE)
        # ==========================================
        self.photo_box = tk.Frame(self.bg_label, bg="#1e1e1e", bd=2, relief="groove", padx=20, pady=20)
        # side="left" snaps it to the left wall of the background
        # padx=(120, 0) pushes it 120 pixels away from the left screen edge
        self.photo_box.pack(side="left", anchor="nw", padx=(120, 0), pady=40, expand=False)

        # Add a title header inside the Photo Box
        photo_header = tk.Label(
            self.photo_box, text="Daily Photo Proofs", font=("Segoe UI", 16, "bold"), fg="white", bg="#1e1e1e"
        )
        photo_header.pack(pady=(0, 15))

        for key, label in CATEGORIES:
            frame = tk.Frame(self.photo_box, bg="#1e1e1e")
            frame.pack(pady=8, fill="x")

            lbl = tk.Label(
                frame, 
                text=label, 
                font=("Segoe UI", 14), 
                fg="white", 
                bg="#1e1e1e", 
                width=18, 
                anchor="w"
            )
            lbl.pack(side="left")

            status = tk.Label(frame, text="", font=("Segoe UI", 14), bg="#1e1e1e", width=8)
            status.pack(side="left")
            self.status_labels[key] = status

            btn = tk.Button(
                frame, 
                text="Choose Photo", 
                font=("Segoe UI", 11), 
                command=lambda k=key: self.choose_photo(k)
            )
            btn.pack(side="left", padx=5)


        # ==========================================
        # BOX 2: TIME TRACKING CONTAINER (RIGHT SIDE)
        # ==========================================
        self.time_box = tk.Frame(self.bg_label, bg="#1e1e1e", bd=2, relief="groove", padx=20, pady=20)
        # side="right" snaps it to the right wall of the background
        # padx=(0, 120) pushes it 120 pixels away from the right screen edge
        self.time_box.pack(side="right", anchor="ne", padx=(0, 120), pady=40, expand=False)

        # Add a title header inside the Time Box
        time_header = tk.Label(
            self.time_box, text="Time Tracking", font=("Segoe UI", 16, "bold"), fg="white", bg="#1e1e1e"
        )
        time_header.pack(pady=(0, 15))

        self.time_data = load_time_data(self.folder)
        self.time_vars = {}
        self.minute_labels = {}

        for key, label in TIME_CATEGORIES:
            frame = tk.Frame(self.time_box, bg="#1e1e1e")
            frame.pack(pady=6, fill="x")

            lbl = tk.Label(
                frame, text=label, font=("Segoe UI", 14), fg="white", bg="#1e1e1e", width=18, anchor="w"
            )
            lbl.pack(side="left")

            time_var = tk.IntVar(value=self.time_data.get(key, 0))
            self.time_vars[key] = time_var

            minute_lbl = tk.Label(
                frame, text=f"{time_var.get()} min", font=("Segoe UI", 12), fg="#aaaaaa", bg="#1e1e1e", width=8
            )
            minute_lbl.pack(side="right")
            self.minute_labels[key] = minute_lbl

            slider = tk.Scale(
                frame,
                from_=0,
                to=MAX_MINUTES,
                orient="horizontal",
                variable=time_var,
                showvalue=False,
                length=150,
                bg="#1e1e1e",
                fg="white",
                troughcolor="#444444",
                highlightthickness=0,
                command=lambda val, k=key: self.on_slider_change(k, val),
            )
            slider.pack(side="right", padx=5)


        # ==========================================
        # BOTTOM ACTION BUTTONS (Outside the Boxes)
        # ==========================================
        self.unlock_btn = tk.Button(
            self.bg_label, text="Unlock", font=("Segoe UI", 18, "bold"), state="disabled", command=self.unlock
        )
        self.unlock_btn.pack(pady=(10, 5))

        skip_btn = tk.Button(
            self.bg_label, text="Not now (Esc)", font=("Segoe UI", 10), command=self.root.destroy
        )
        skip_btn.pack(pady=5)

    # --- KEEP REFRESH/SLIDER METHODS UNCHANGED ---
    def on_slider_change(self, key, val):
        minutes = int(float(val))
        self.time_data[key] = minutes
        self.minute_labels[key].config(text=f"{minutes} min")
        save_time_data(self.folder, self.time_data)
        write_markdown(self.config, self.folder, self.today_str, self.time_data)

    def choose_photo(self, key):
        path = filedialog.askopenfilename(
            title=f"Select photo for {key}",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.heic")],
        )
        if path:
            ext = Path(path).suffix.lower()
            dest = self.folder / f"{key}{ext}"
            shutil.copy(path, dest)
            self.refresh_status()

    def refresh_status(self):
        all_done = True
        for key, _ in CATEGORIES:
            photo = existing_photo(self.folder, key)
            if photo:
                self.status_labels[key].config(text="\u2713 done", fg="#4caf50")
            else:
                self.status_labels[key].config(text="missing", fg="#f44336")
                all_done = False

        write_markdown(self.config, self.folder, self.today_str, self.time_data)

        if all_done:
            self.unlock_btn.config(state="normal", bg="#4caf50", fg="white")
        else:
            self.unlock_btn.config(state="disabled", bg="#cccccc", fg="#666666")

    def unlock(self):
        write_markdown(self.config, self.folder, self.today_str, self.time_data)
        success, message = send_proof_email(self.config, self.folder, self.today_str)
        if not success:
            messagebox.showwarning(
                "Email not sent",
                f"{message}\n\nUnlocking anyway - check config.json if this keeps happening.",
            )
        self.root.destroy()

def main():
    config = load_config()
    root = tk.Tk()
    App(root, config)
    root.mainloop()


if __name__ == "__main__":
    main()
