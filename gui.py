import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import employees_store
import reminder_logic
import report_parser
import templates_store
import zestawienie
from sms_sender import send_with_retry

REMINDER_MODES = [
    ("5-day", "5 dni przed", "template_5day"),
    ("2-day", "2 dni przed", "template_2day"),
    ("reschedule", "Przypomnienie o przelozeniu", "template_reschedule"),
]
_MODE_LABELS = [label for _, label, _ in REMINDER_MODES]
_MODE_BY_LABEL = {label: (key, template_key) for key, label, template_key in REMINDER_MODES}


class SettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Ustawienia")
        self.geometry("620x560")

        self.templates = templates_store.load()
        self.employees = [dict(e) for e in employees_store.load()]

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        templates_tab = ttk.Frame(notebook)
        employees_tab = ttk.Frame(notebook)
        notebook.add(templates_tab, text="Szablony")
        notebook.add(employees_tab, text="Pracownicy")

        self._build_templates_tab(templates_tab)
        self._build_employees_tab(employees_tab)

        ttk.Button(self, text="Zapisz", command=self.save).pack(pady=(0, 10))

    def _build_templates_tab(self, parent):
        ttk.Label(parent, text="Szablon przypomnienia (5 dni przed wizyta):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.template_5day = scrolledtext.ScrolledText(parent, height=5, wrap="word")
        self.template_5day.pack(fill="x", padx=10)
        self.template_5day.insert("1.0", self.templates["template_5day"])

        ttk.Label(parent, text="Szablon przypomnienia (2 dni przed wizyta):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.template_2day = scrolledtext.ScrolledText(parent, height=5, wrap="word")
        self.template_2day.pack(fill="x", padx=10)
        self.template_2day.insert("1.0", self.templates["template_2day"])

        ttk.Label(
            parent,
            text="Dostepne pola: {imie_nazwisko} {data} {godzina} {lekarz} {rodzaj_wizyty} "
            "{koszt_info} {clinic_name} {clinic_phone} {clinic_address}",
            foreground="gray",
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 10))

        ttk.Label(parent, text="Szablon przypomnienia o mozliwosci przelozenia wizyty:").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.template_reschedule = scrolledtext.ScrolledText(parent, height=4, wrap="word")
        self.template_reschedule.pack(fill="x", padx=10)
        self.template_reschedule.insert("1.0", self.templates["template_reschedule"])

        ttk.Label(
            parent,
            text="Ta wiadomosc jest zawsze taka sama - brak pol z danymi pacjenta/wizyty "
            "(dostepne tylko {clinic_name} {clinic_phone} {clinic_address}).",
            foreground="gray",
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 10))

        form = ttk.Frame(parent)
        form.pack(fill="x", padx=10)

        ttk.Label(form, text="Nazwa przychodni:").grid(row=0, column=0, sticky="w", pady=2)
        self.clinic_name = ttk.Entry(form, width=40)
        self.clinic_name.grid(row=0, column=1, sticky="we", pady=2)
        self.clinic_name.insert(0, self.templates["clinic_name"])

        ttk.Label(form, text="Telefon do odwolan:").grid(row=1, column=0, sticky="w", pady=2)
        self.clinic_phone = ttk.Entry(form, width=40)
        self.clinic_phone.grid(row=1, column=1, sticky="we", pady=2)
        self.clinic_phone.insert(0, self.templates["clinic_phone"])

        ttk.Label(form, text="Adres przychodni:").grid(row=2, column=0, sticky="w", pady=2)
        self.clinic_address = ttk.Entry(form, width=40)
        self.clinic_address.grid(row=2, column=1, sticky="we", pady=2)
        self.clinic_address.insert(0, self.templates["clinic_address"])

        form.columnconfigure(1, weight=1)

    def _build_employees_tab(self, parent):
        columns = ("specialization", "name")
        self.employees_tree = ttk.Treeview(parent, columns=columns, show="headings", height=14)
        self.employees_tree.heading("specialization", text="Specjalizacja")
        self.employees_tree.heading("name", text="Nazwisko i imie")
        self.employees_tree.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        for emp in self.employees:
            self.employees_tree.insert("", "end", values=(emp["specialization"], emp["name"]))

        form = ttk.Frame(parent)
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Specjalizacja:").grid(row=0, column=0, sticky="w")
        self.new_specialization = ttk.Entry(form, width=20)
        self.new_specialization.grid(row=0, column=1, padx=(5, 15))

        ttk.Label(form, text="Nazwisko i imie:").grid(row=0, column=2, sticky="w")
        self.new_name = ttk.Entry(form, width=25)
        self.new_name.grid(row=0, column=3, padx=(5, 15))

        ttk.Button(form, text="Dodaj", command=self._add_employee).grid(row=0, column=4)
        ttk.Button(parent, text="Usun zaznaczonego", command=self._remove_employee).pack(
            anchor="w", padx=10, pady=(0, 10)
        )

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
                "template_2day": self.template_2day.get("1.0", "end").strip(),
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


class MainWindow(tk.Tk):
    def __init__(self, sender, sent_log, is_mock: bool):
        super().__init__()
        self.sender = sender
        self.sent_log = sent_log
        self.is_mock = is_mock
        self.report_path: str | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()

        self.title("Przypomnienia SMS - PSYCHE")
        self.geometry("760x560")

        if self.is_mock:
            banner = tk.Label(
                self,
                text="TRYB TESTOWY: brak klucza API - SMS-y nie sa faktycznie wysylane",
                bg="#ffcc00",
                fg="black",
            )
            banner.pack(fill="x")

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Button(top, text="Wybierz plik raportu...", command=self.choose_file).pack(side="left")
        self.file_label = ttk.Label(top, text="Nie wybrano pliku")
        self.file_label.pack(side="left", padx=10)

        ttk.Button(top, text="Ustawienia...", command=self.open_settings).pack(side="right")

        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill="x", padx=10)
        ttk.Label(mode_frame, text="Rodzaj wiadomosci:").pack(side="left")
        self.reminder_mode = tk.StringVar(value=_MODE_LABELS[0])
        ttk.Combobox(
            mode_frame, textvariable=self.reminder_mode, values=_MODE_LABELS,
            state="readonly", width=30,
        ).pack(side="left", padx=(10, 0))

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=(0, 10))

        self.send_button = ttk.Button(
            actions, text="Wyslij SMS", command=self.start_pipeline, state="disabled"
        )
        self.send_button.pack(side="left")

        ttk.Button(actions, text="Zapisz raport...", command=self.save_report).pack(
            side="left", padx=(10, 0)
        )

        ttk.Button(actions, text="Generuj zestawienie...", command=self.generate_zestawienie).pack(
            side="left", padx=(10, 0)
        )

        self.console = scrolledtext.ScrolledText(self, height=20, state="disabled", wrap="word")
        self.console.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.summary_label = ttk.Label(self, text="")
        self.summary_label.pack(padx=10, pady=(0, 10), anchor="w")

        self.after(100, self._drain_log_queue)

    def choose_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Raporty", "*.xlsx *.xls *.csv"), ("Wszystkie pliki", "*.*")]
        )
        if path:
            self.report_path = path
            self.file_label.config(text=path)
            self.send_button.config(state="normal")

    def open_settings(self):
        SettingsWindow(self)

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

    def generate_zestawienie(self):
        input_path = filedialog.askopenfilename(
            title="Wybierz raport zrodlowy (np. za tydzien/miesiac)",
            filetypes=[("Raporty", "*.xlsx *.xls *.csv"), ("Wszystkie pliki", "*.*")],
        )
        if not input_path:
            return
        output_path = filedialog.asksaveasfilename(
            title="Zapisz zestawienie jako...",
            defaultextension=".xlsx",
            filetypes=[("Skoroszyt Excel", "*.xlsx"), ("Wszystkie pliki", "*.*")],
        )
        if not output_path:
            return
        try:
            zestawienie.generate(input_path, output_path)
        except Exception as exc:
            messagebox.showerror("Zestawienie", f"Nie udalo sie wygenerowac zestawienia: {exc}")
            return
        messagebox.showinfo("Zestawienie", f"Zestawienie zapisane: {output_path}")

    def log(self, message: str):
        self._log_queue.put(message)

    def _drain_log_queue(self):
        try:
            while True:
                message = self._log_queue.get_nowait()
                self.console.config(state="normal")
                self.console.insert("end", message + "\n")
                self.console.see("end")
                self.console.config(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def start_pipeline(self):
        if not self.report_path:
            return
        self.send_button.config(state="disabled")
        self.summary_label.config(text="")
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
            self.after(0, lambda: self.send_button.config(state="normal"))
            return

        sent_count = failed_count = skipped_count = 0

        for visit in visits:
            if not visit.phones:
                self.log(f"POMINIETO: {visit.patient_name} - brak numeru telefonu")
                skipped_count += 1
                continue

            if self.sent_log.already_sent(visit.pesel, visit.appointment_date, rtype):
                self.log(f"POMINIETO: {visit.patient_name} - przypomnienie juz wyslane")
                skipped_count += 1
                continue

            rodzaj_wizyty = employees_store.resolve_rodzaj_wizyty(visit.doctor, employees)
            message = reminder_logic.build_message(visit, templates[template_key], templates, rodzaj_wizyty)

            any_success = False
            for phone in visit.phones:
                result = send_with_retry(self.sender, phone, message)
                if result.success:
                    any_success = True
                    self.log(f"OK: {visit.patient_name} ({phone}) - wyslano przypomnienie {rtype}")
                else:
                    self.log(f"BLAD: {visit.patient_name} ({phone}) - {result.error}")

            if any_success:
                self.sent_log.mark_sent(visit.pesel, visit.appointment_date, rtype)
                sent_count += 1
            else:
                failed_count += 1

        summary = f"Wyslano: {sent_count}, bledow: {failed_count}, pominietych: {skipped_count}"
        self.log(f"Podsumowanie: {summary}")
        self.after(0, lambda: self.summary_label.config(text=summary))
        self.after(0, lambda: self.send_button.config(state="normal"))


if __name__ == "__main__":
    from sms_sender import MockSmsSender
    from sent_log import SentLog

    MainWindow(sender=MockSmsSender(), sent_log=SentLog(), is_mock=True).mainloop()
