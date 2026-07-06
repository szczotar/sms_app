import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import reminder_logic
import report_parser
import templates_store
from sms_sender import send_with_retry

STATUS_DO_REALIZACJI = "Do realizacji"


class SettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Ustawienia - szablony SMS")
        self.geometry("560x520")

        self.templates = templates_store.load()

        ttk.Label(self, text="Szablon przypomnienia (5 dni przed wizyta):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.template_5day = scrolledtext.ScrolledText(self, height=6, wrap="word")
        self.template_5day.pack(fill="x", padx=10)
        self.template_5day.insert("1.0", self.templates["template_5day"])

        ttk.Label(self, text="Szablon przypomnienia (2 dni przed wizyta):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.template_2day = scrolledtext.ScrolledText(self, height=6, wrap="word")
        self.template_2day.pack(fill="x", padx=10)
        self.template_2day.insert("1.0", self.templates["template_2day"])

        ttk.Label(
            self,
            text="Dostepne pola: {imie_nazwisko} {data} {godzina} {lekarz} "
            "{clinic_name} {clinic_phone} {clinic_address}",
            foreground="gray",
        ).pack(anchor="w", padx=10, pady=(2, 10))

        form = ttk.Frame(self)
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

        ttk.Button(self, text="Zapisz", command=self.save).pack(pady=10)

    def save(self):
        templates_store.save(
            {
                "template_5day": self.template_5day.get("1.0", "end").strip(),
                "template_2day": self.template_2day.get("1.0", "end").strip(),
                "clinic_name": self.clinic_name.get().strip(),
                "clinic_phone": self.clinic_phone.get().strip(),
                "clinic_address": self.clinic_address.get().strip(),
            }
        )
        messagebox.showinfo("Ustawienia", "Zapisano szablony.")
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
        self.geometry("760x520")

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

        self.send_button = ttk.Button(
            self, text="Wyslij SMS", command=self.start_pipeline, state="disabled"
        )
        self.send_button.pack(padx=10, pady=(0, 10), anchor="w")

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
        thread = threading.Thread(target=self._run_pipeline, args=(self.report_path,), daemon=True)
        thread.start()

    def _run_pipeline(self, path: str):
        templates = templates_store.load()
        try:
            visits = report_parser.load_report(path)
        except Exception as exc:
            self.log(f"BLAD: nie udalo sie odczytac pliku: {exc}")
            self.after(0, lambda: self.send_button.config(state="normal"))
            return

        sent_count = failed_count = skipped_count = 0

        for visit in visits:
            rtype = reminder_logic.reminder_type(visit.appointment_date)
            if rtype is None:
                skipped_count += 1
                continue

            if visit.status != STATUS_DO_REALIZACJI:
                self.log(
                    f"POMINIETO: {visit.patient_name} - nierozpoznany status '{visit.status}'"
                )
                skipped_count += 1
                continue

            if not visit.phone:
                self.log(f"POMINIETO: {visit.patient_name} - brak numeru telefonu")
                skipped_count += 1
                continue

            if self.sent_log.already_sent(visit.pesel, visit.appointment_date, rtype):
                self.log(f"POMINIETO: {visit.patient_name} - przypomnienie juz wyslane")
                skipped_count += 1
                continue

            template_key = "template_5day" if rtype == "5-day" else "template_2day"
            message = reminder_logic.build_message(visit, templates[template_key], templates)
            result = send_with_retry(self.sender, visit.phone, message)

            if result.success:
                self.sent_log.mark_sent(visit.pesel, visit.appointment_date, rtype)
                sent_count += 1
                self.log(f"OK: {visit.patient_name} ({visit.phone}) - wyslano przypomnienie {rtype}")
            else:
                failed_count += 1
                self.log(f"BLAD: {visit.patient_name} ({visit.phone}) - {result.error}")

        summary = f"Wyslano: {sent_count}, bledow: {failed_count}, pominietych: {skipped_count}"
        self.log(f"Podsumowanie: {summary}")
        self.after(0, lambda: self.summary_label.config(text=summary))
        self.after(0, lambda: self.send_button.config(state="normal"))


if __name__ == "__main__":
    from sms_sender import MockSmsSender
    from sent_log import SentLog

    MainWindow(sender=MockSmsSender(), sent_log=SentLog(), is_mock=True).mainloop()
