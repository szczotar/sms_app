import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image, ImageTk

import employees_store
import reminder_logic
import report_parser
import templates_store
import theme
import zestawienie
from sms_sender import send_with_retry

theme.setup()

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "psyche_logo.png"

REMINDER_MODES = [
    ("5-day", "5 dni przed", "template_5day"),
    ("reschedule", "Przypomnienie o przelozeniu", "template_reschedule"),
]
_MODE_LABELS = [label for _, label, _ in REMINDER_MODES]
_MODE_BY_LABEL = {label: (key, template_key) for key, label, template_key in REMINDER_MODES}


def _load_logo_image(height: int) -> ctk.CTkImage:
    img = Image.open(LOGO_PATH)
    w, h = img.size
    width = int(w * (height / h))
    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))


def _style_treeview():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Psyche.Treeview",
        background=theme.CARD,
        fieldbackground=theme.CARD,
        foreground=theme.TEXT,
        rowheight=28,
        borderwidth=0,
        font=(theme.FONT_FAMILY, 10),
    )
    style.configure(
        "Psyche.Treeview.Heading",
        background=theme.PURPLE,
        foreground=theme.WHITE,
        font=(theme.FONT_FAMILY, 10, "bold"),
        relief="flat",
    )
    style.map(
        "Psyche.Treeview",
        background=[("selected", theme.MAGENTA)],
        foreground=[("selected", theme.WHITE)],
    )
    style.map("Psyche.Treeview.Heading", background=[("active", theme.PURPLE_DARK)])


class NavCard(ctk.CTkFrame):
    def __init__(self, parent, icon, title, subtitle, accent, accent_hover, command):
        super().__init__(
            parent,
            fg_color=theme.CARD,
            corner_radius=18,
            width=260,
            height=230,
            border_width=1,
            border_color=theme.BORDER,
        )
        self.pack_propagate(False)
        self._accent = accent

        icon_label = ctk.CTkLabel(self, text=icon, font=theme.font(40))
        icon_label.pack(pady=(32, 10))

        title_label = ctk.CTkLabel(self, text=title, font=theme.font(15, "bold"), text_color=theme.TEXT)
        title_label.pack(pady=(0, 6))

        subtitle_label = ctk.CTkLabel(
            self, text=subtitle, font=theme.font(11), text_color=theme.MUTED, justify="center"
        )
        subtitle_label.pack(pady=(0, 14))

        button = ctk.CTkButton(
            self,
            text="Otworz",
            width=120,
            height=34,
            corner_radius=10,
            fg_color=accent,
            hover_color=accent_hover,
            font=theme.font(12, "bold"),
            command=command,
        )
        button.pack()

        for widget in (self, icon_label, title_label, subtitle_label):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event):
        self.configure(border_color=self._accent)

    def _on_leave(self, _event):
        self.configure(border_color=theme.BORDER)


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Ustawienia")
        self.configure(fg_color=theme.BG)
        self.transient(master)

        width, height = 660, 640
        screen_h = self.winfo_screenheight()
        height = min(height, screen_h - 100)
        screen_w = self.winfo_screenwidth()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(560, 420)

        self.templates = templates_store.load()
        self.employees = [dict(e) for e in employees_store.load()]

        # Pack the save button first, anchored to the bottom, so it always
        # reserves its own space before the tabview claims the rest of the
        # cavity (packing an expand widget first would let it squeeze out
        # whatever is packed after it).
        ctk.CTkButton(
            self,
            text="Zapisz",
            command=self.save,
            fg_color=theme.MAGENTA,
            hover_color=theme.MAGENTA_DARK,
            font=theme.font(13, "bold"),
            height=38,
            corner_radius=10,
            width=140,
        ).pack(side="bottom", pady=(0, 16))

        tabview = ctk.CTkTabview(
            self,
            fg_color=theme.CARD,
            segmented_button_fg_color=theme.PURPLE,
            segmented_button_selected_color=theme.MAGENTA,
            segmented_button_selected_hover_color=theme.MAGENTA_DARK,
            segmented_button_unselected_color=theme.PURPLE,
            text_color=theme.WHITE,
        )
        tabview.pack(fill="both", expand=True, padx=16, pady=16)
        tabview.add("Szablony")
        tabview.add("Pracownicy")

        self._build_templates_tab(tabview.tab("Szablony"))
        self._build_employees_tab(tabview.tab("Pracownicy"))

    def _hint(self, parent, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=theme.font(10),
            text_color=theme.MUTED,
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(2, 12))

    def _build_templates_tab(self, outer):
        parent = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        parent.pack(fill="both", expand=True)

        ctk.CTkLabel(
            parent, text="Szablon przypomnienia (5 dni przed wizyta):",
            font=theme.font(12, "bold"), text_color=theme.TEXT,
        ).pack(anchor="w", padx=12, pady=(12, 4))
        self.template_5day = ctk.CTkTextbox(
            parent, height=90, wrap="word", fg_color=theme.BG,
            border_width=1, border_color=theme.BORDER, corner_radius=8,
        )
        self.template_5day.pack(fill="x", padx=12)
        self.template_5day.insert("1.0", self.templates["template_5day"])

        self._hint(
            parent,
            "Dostepne pola: {imie_nazwisko} {data} {godzina} {lekarz} {rodzaj_wizyty} "
            "{koszt_info} {clinic_name} {clinic_phone} {clinic_address}",
        )

        ctk.CTkLabel(
            parent, text="Szablon przypomnienia o mozliwosci przelozenia wizyty:",
            font=theme.font(12, "bold"), text_color=theme.TEXT,
        ).pack(anchor="w", padx=12, pady=(4, 4))
        self.template_reschedule = ctk.CTkTextbox(
            parent, height=70, wrap="word", fg_color=theme.BG,
            border_width=1, border_color=theme.BORDER, corner_radius=8,
        )
        self.template_reschedule.pack(fill="x", padx=12)
        self.template_reschedule.insert("1.0", self.templates["template_reschedule"])

        self._hint(
            parent,
            "Ta wiadomosc jest zawsze taka sama - brak pol z danymi pacjenta/wizyty "
            "(dostepne tylko {clinic_name} {clinic_phone} {clinic_address}).",
        )

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(form, text="Nazwa przychodni:", font=theme.font(11), text_color=theme.TEXT).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.clinic_name = ctk.CTkEntry(form, width=320, fg_color=theme.BG, border_color=theme.BORDER)
        self.clinic_name.grid(row=0, column=1, sticky="we", pady=4, padx=(8, 0))
        self.clinic_name.insert(0, self.templates["clinic_name"])

        ctk.CTkLabel(form, text="Telefon do odwolan:", font=theme.font(11), text_color=theme.TEXT).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.clinic_phone = ctk.CTkEntry(form, width=320, fg_color=theme.BG, border_color=theme.BORDER)
        self.clinic_phone.grid(row=1, column=1, sticky="we", pady=4, padx=(8, 0))
        self.clinic_phone.insert(0, self.templates["clinic_phone"])

        ctk.CTkLabel(form, text="Adres przychodni:", font=theme.font(11), text_color=theme.TEXT).grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.clinic_address = ctk.CTkEntry(form, width=320, fg_color=theme.BG, border_color=theme.BORDER)
        self.clinic_address.grid(row=2, column=1, sticky="we", pady=4, padx=(8, 0))
        self.clinic_address.insert(0, self.templates["clinic_address"])

        form.columnconfigure(1, weight=1)

    def _build_employees_tab(self, parent):
        _style_treeview()

        # Pack the bottom-anchored widgets (add-form, remove button) first so
        # they always keep their space; the treeview (fill+expand) is packed
        # last and only takes whatever cavity remains above them.
        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(side="bottom", fill="x", padx=12, pady=12)

        ctk.CTkButton(
            parent, text="Usun zaznaczonego", command=self._remove_employee,
            fg_color="transparent", hover_color=theme.CARD_HOVER, text_color=theme.MAGENTA_DARK,
            border_width=1, border_color=theme.MAGENTA, font=theme.font(11),
        ).pack(side="bottom", anchor="w", padx=12, pady=(0, 12))

        columns = ("specialization", "name")
        self.employees_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=14, style="Psyche.Treeview"
        )
        self.employees_tree.heading("specialization", text="Specjalizacja")
        self.employees_tree.heading("name", text="Nazwisko i imie")
        self.employees_tree.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        for emp in self.employees:
            self.employees_tree.insert("", "end", values=(emp["specialization"], emp["name"]))

        ctk.CTkLabel(form, text="Specjalizacja:", font=theme.font(11), text_color=theme.TEXT).grid(
            row=0, column=0, sticky="w"
        )
        self.new_specialization = ctk.CTkEntry(form, width=160, fg_color=theme.CARD, border_color=theme.BORDER)
        self.new_specialization.grid(row=0, column=1, padx=(6, 16))

        ctk.CTkLabel(form, text="Nazwisko i imie:", font=theme.font(11), text_color=theme.TEXT).grid(
            row=0, column=2, sticky="w"
        )
        self.new_name = ctk.CTkEntry(form, width=200, fg_color=theme.CARD, border_color=theme.BORDER)
        self.new_name.grid(row=0, column=3, padx=(6, 16))

        ctk.CTkButton(
            form, text="Dodaj", command=self._add_employee, width=90,
            fg_color=theme.PURPLE, hover_color=theme.PURPLE_DARK, font=theme.font(11, "bold"),
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))

    def _add_employee(self):
        name = self.new_name.get().strip()
        specialization = self.new_specialization.get().strip()
        if not name:
            return
        self.employees_tree.insert("", "end", values=(specialization, name))
        self.new_name.delete(0, "end")
        self.new_specialization.delete(0, "end")

    def _remove_employee(self):
        for item in self.employees_tree.selection():
            self.employees_tree.delete(item)

    def save(self):
        templates_store.save(
            {
                "template_5day": self.template_5day.get("1.0", "end").strip(),
                "template_reschedule": self.template_reschedule.get("1.0", "end").strip(),
                "clinic_name": self.clinic_name.get().strip(),
                "clinic_phone": self.clinic_phone.get().strip(),
                "clinic_address": self.clinic_address.get().strip(),
            }
        )
        employees = [
            {"specialization": vals[0], "name": vals[1]}
            for vals in (self.employees_tree.item(item, "values") for item in self.employees_tree.get_children())
        ]
        employees_store.save(employees)
        messagebox.showinfo("Ustawienia", "Zapisano ustawienia.")
        self.destroy()


class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=theme.BG)

        ctk.CTkLabel(
            self, text="Co chcesz dzisiaj zrobic?", font=theme.font(20, "bold"), text_color=theme.TEXT
        ).pack(pady=(60, 6))
        ctk.CTkLabel(
            self, text="Wybierz jedna z opcji ponizej", font=theme.font(12), text_color=theme.MUTED
        ).pack(pady=(0, 40))

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(expand=True)

        NavCard(
            cards,
            icon="\U0001F4AC",
            title="Generuj powiadomienia",
            subtitle="Wyslij SMS-owe przypomnienia\no wizytach na podstawie raportu",
            accent=theme.MAGENTA,
            accent_hover=theme.MAGENTA_DARK,
            command=lambda: app.show_frame("RemindersFrame", "Generuj powiadomienia"),
        ).pack(side="left", padx=20, pady=10)

        NavCard(
            cards,
            icon="\U0001F4CA",
            title="Generuj zestawienia",
            subtitle="Przygotuj zestawienie wizyt z wybranego okresu",
            accent=theme.PURPLE,
            accent_hover=theme.PURPLE_DARK,
            command=lambda: app.show_frame("ZestawienieFrame", "Generuj zestawienia"),
        ).pack(side="left", padx=20, pady=10)


class RemindersFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=theme.BG)
        self.app = app
        self.report_path: str | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkButton(
            top, text="Wybierz plik raportu...", command=self.choose_file,
            fg_color=theme.PURPLE, hover_color=theme.PURPLE_DARK,
            font=theme.font(12, "bold"), height=36, corner_radius=10,
        ).pack(side="left")

        self.file_label = ctk.CTkLabel(
            top, text="Nie wybrano pliku", text_color=theme.MUTED, font=theme.font(11)
        )
        self.file_label.pack(side="left", padx=14)

        ctk.CTkButton(
            top, text="Ustawienia...", command=self.open_settings,
            fg_color="transparent", hover_color=theme.CARD_HOVER, text_color=theme.PURPLE,
            border_width=1, border_color=theme.PURPLE, font=theme.font(12), height=36, corner_radius=10,
        ).pack(side="right")

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=(4, 0))
        ctk.CTkLabel(
            mode_frame, text="Rodzaj wiadomosci:", font=theme.font(12), text_color=theme.TEXT
        ).pack(side="left")
        self.reminder_mode = ctk.CTkOptionMenu(
            mode_frame,
            values=_MODE_LABELS,
            width=260,
            font=theme.font(11),
            fg_color=theme.CARD,
            text_color=theme.TEXT,
            button_color=theme.PURPLE,
            button_hover_color=theme.PURPLE_DARK,
            dropdown_fg_color=theme.CARD,
            dropdown_text_color=theme.TEXT,
            dropdown_hover_color=theme.BORDER,
        )
        self.reminder_mode.set(_MODE_LABELS[0])
        self.reminder_mode.pack(side="left", padx=(10, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(14, 10))

        self.send_button = ctk.CTkButton(
            actions, text="Wyslij SMS", command=self.start_pipeline, state="disabled",
            fg_color=theme.MAGENTA, hover_color=theme.MAGENTA_DARK,
            font=theme.font(13, "bold"), height=40, corner_radius=10, width=160,
        )
        self.send_button.pack(side="left")

        ctk.CTkButton(
            actions, text="Zapisz raport...", command=self.save_report,
            fg_color="transparent", hover_color=theme.CARD_HOVER, text_color=theme.PURPLE,
            border_width=1, border_color=theme.PURPLE, font=theme.font(12), height=40, corner_radius=10,
        ).pack(side="left", padx=(10, 0))

        self.console = ctk.CTkTextbox(
            self, state="disabled", wrap="word", fg_color=theme.CARD, text_color=theme.TEXT,
            font=("Consolas", 10), corner_radius=12, border_width=1, border_color=theme.BORDER,
        )
        self.console.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.summary_label = ctk.CTkLabel(self, text="", font=theme.font(12, "bold"), text_color=theme.PURPLE)
        self.summary_label.pack(padx=20, pady=(0, 16), anchor="w")

        self.after(100, self._drain_log_queue)

    def choose_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Raporty", "*.xlsx *.xls *.csv"), ("Wszystkie pliki", "*.*")]
        )
        if path:
            self.report_path = path
            self.file_label.configure(text=path)
            self.send_button.configure(state="normal")

    def open_settings(self):
        SettingsWindow(self.app)

    def save_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Plik tekstowy", "*.txt"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        content = self.console.get("1.0", "end-1c")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Zapisz raport", "Raport zapisany.")

    def log(self, message: str):
        self._log_queue.put(message)

    def _drain_log_queue(self):
        try:
            while True:
                message = self._log_queue.get_nowait()
                self.console.configure(state="normal")
                self.console.insert("end", message + "\n")
                self.console.see("end")
                self.console.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def start_pipeline(self):
        if not self.report_path:
            return
        self.send_button.configure(state="disabled")
        self.summary_label.configure(text="")
        rtype, template_key = _MODE_BY_LABEL[self.reminder_mode.get()]
        thread = threading.Thread(
            target=self._run_pipeline, args=(self.report_path, rtype, template_key), daemon=True
        )
        thread.start()

    def _run_pipeline(self, path: str, rtype: str, template_key: str):
        templates = templates_store.load()
        employees = employees_store.load()
        try:
            visits = report_parser.load_report(path)
        except Exception as exc:
            self.log(f"BLAD: nie udalo sie odczytac pliku: {exc}")
            self.after(0, lambda: self.send_button.configure(state="normal"))
            return

        sent_count = failed_count = skipped_count = 0

        for visit in visits:
            if not visit.phones:
                self.log(f"POMINIETO: {visit.patient_name} - brak numeru telefonu")
                skipped_count += 1
                continue

            if self.app.sent_log.already_sent(visit.pesel, visit.appointment_date, rtype):
                self.log(f"POMINIETO: {visit.patient_name} - przypomnienie juz wyslane")
                skipped_count += 1
                continue

            rodzaj_wizyty = employees_store.resolve_rodzaj_wizyty(visit.doctor, employees)
            title = employees_store.resolve_title(visit.doctor, employees)
            lekarz_label = f"{title} {visit.doctor}".strip() if title else visit.doctor
            message = reminder_logic.build_message(
                visit, templates[template_key], templates, rodzaj_wizyty, lekarz_label
            )

            any_success = False
            for phone in visit.phones:
                result = send_with_retry(self.app.sender, phone, message)
                if result.success:
                    any_success = True
                    self.log(f"OK: {visit.patient_name} ({phone}) - wyslano przypomnienie {rtype}")
                else:
                    self.log(f"BLAD: {visit.patient_name} ({phone}) - {result.error}")

            if any_success:
                self.app.sent_log.mark_sent(visit.pesel, visit.appointment_date, rtype)
                sent_count += 1
            else:
                failed_count += 1

        summary = f"Wyslano: {sent_count}, bledow: {failed_count}, pominietych: {skipped_count}"
        self.log(f"Podsumowanie: {summary}")
        self.after(0, lambda: self.summary_label.configure(text=summary))
        self.after(0, lambda: self.send_button.configure(state="normal"))


class ZestawienieFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=theme.BG)
        self.app = app
        self.input_path: str | None = None

        ctk.CTkLabel(
            self, text="Zestawienie wizyt",
            font=theme.font(16, "bold"), text_color=theme.TEXT,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        ctk.CTkLabel(
            self,
            text="Wybierz raport zrodlowy (np. za tydzien lub miesiac) - zestawienie zostanie\n"
            "wygenerowane jako plik .xlsx, osobno dla kazdego lekarza, wraz z podsumowaniem.",
            font=theme.font(11), text_color=theme.MUTED, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 24))

        picker = ctk.CTkFrame(self, fg_color="transparent")
        picker.pack(fill="x", padx=20)

        ctk.CTkButton(
            picker, text="Wybierz plik zrodlowy...", command=self.choose_input,
            fg_color=theme.PURPLE, hover_color=theme.PURPLE_DARK,
            font=theme.font(12, "bold"), height=36, corner_radius=10,
        ).pack(side="left")

        self.input_label = ctk.CTkLabel(
            picker, text="Nie wybrano pliku", text_color=theme.MUTED, font=theme.font(11)
        )
        self.input_label.pack(side="left", padx=14)

        self.generate_button = ctk.CTkButton(
            self, text="Generuj zestawienie...", command=self.generate, state="disabled",
            fg_color=theme.MAGENTA, hover_color=theme.MAGENTA_DARK,
            font=theme.font(13, "bold"), height=40, corner_radius=10, width=210,
        )
        self.generate_button.pack(anchor="w", padx=20, pady=24)

        self.status_label = ctk.CTkLabel(
            self, text="", font=theme.font(11), text_color=theme.MUTED, justify="left", wraplength=700
        )
        self.status_label.pack(anchor="w", padx=20)

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="Wybierz raport zrodlowy (np. za tydzien/miesiac)",
            filetypes=[("Raporty", "*.xlsx *.xls *.csv"), ("Wszystkie pliki", "*.*")],
        )
        if path:
            self.input_path = path
            self.input_label.configure(text=path)
            self.generate_button.configure(state="normal")

    def generate(self):
        output_path = filedialog.asksaveasfilename(
            title="Zapisz zestawienie jako...",
            defaultextension=".xlsx",
            filetypes=[("Skoroszyt Excel", "*.xlsx"), ("Wszystkie pliki", "*.*")],
        )
        if not output_path:
            return
        try:
            zestawienie.generate(self.input_path, output_path)
        except Exception as exc:
            self.status_label.configure(text=f"Blad: {exc}", text_color=theme.MAGENTA_DARK)
            messagebox.showerror("Zestawienie", f"Nie udalo sie wygenerowac zestawienia: {exc}")
            return
        self.status_label.configure(text=f"Zapisano: {output_path}", text_color=theme.PURPLE)
        messagebox.showinfo("Zestawienie", f"Zestawienie zapisane: {output_path}")


class App(ctk.CTk):
    def __init__(self, sender, sent_log, is_mock: bool):
        super().__init__()
        self.sender = sender
        self.sent_log = sent_log
        self.is_mock = is_mock

        self.title("Przypomnienia SMS - PSYCHE")
        self.geometry("880x660")
        self.minsize(780, 580)
        self.configure(fg_color=theme.BG)

        try:
            icon_img = Image.open(LOGO_PATH)
            self._icon_photo = ImageTk.PhotoImage(icon_img)
            self.iconphoto(False, self._icon_photo)
        except Exception:
            pass

        self._logo_image = _load_logo_image(36)
        self._build_header()

        if self.is_mock:
            ctk.CTkLabel(
                self,
                text="TRYB TESTOWY: brak klucza API - SMS-y nie sa faktycznie wysylane",
                fg_color=theme.WARNING_BG,
                text_color=theme.WARNING_FG,
                font=theme.font(11, "bold"),
                corner_radius=0,
                height=28,
            ).pack(fill="x")

        self.container = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for frame_cls in (HomeFrame, RemindersFrame, ZestawienieFrame):
            frame = frame_cls(self.container, self)
            self.frames[frame_cls.__name__] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame("HomeFrame")

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=theme.PURPLE, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, image=self._logo_image, text="").pack(side="left", padx=(18, 8), pady=10)

        self.page_title = ctk.CTkLabel(
            header, text="", text_color=theme.WHITE, font=theme.font(15, "bold")
        )
        self.page_title.pack(side="left", padx=(6, 0))

        self.back_button = ctk.CTkButton(
            header,
            text="‹ Menu",
            width=90,
            height=34,
            corner_radius=8,
            fg_color=theme.PURPLE_DARK,
            hover_color=theme.MAGENTA_DARK,
            font=theme.font(12, "bold"),
            command=lambda: self.show_frame("HomeFrame"),
        )

    def show_frame(self, name: str, title: str = ""):
        self.back_button.pack_forget()
        if name != "HomeFrame":
            self.back_button.pack(side="left", padx=(6, 10), pady=14, before=self.page_title)
        self.page_title.configure(text=title if name != "HomeFrame" else "")
        self.frames[name].tkraise()


if __name__ == "__main__":
    from sent_log import SentLog
    from sms_sender import MockSmsSender

    App(sender=MockSmsSender(), sent_log=SentLog(), is_mock=True).mainloop()
