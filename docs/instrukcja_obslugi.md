# Instrukcja obsługi – Przypomnienia SMS PSYCHE

## 1. Wprowadzenie

Aplikacja "Przypomnienia SMS PSYCHE" służy do wysyłania pacjentom automatycznych wiadomości SMS na podstawie raportu wizyt wyeksportowanego z systemu Axon. Aplikacja obsługuje trzy funkcje:

- wysyłanie przypomnień o zbliżającej się wizycie (tryb "5 dni przed"),
- wysyłanie wiadomości o możliwości przełożenia wizyty (tryb "Przypomnienie o przełożeniu"),
- generowanie zestawienia wizyt dla rozliczeń z lekarzami (funkcja "Generuj zestawienia").

Aplikacja **nie łączy się z Axon** i **nie sprawdza dat samodzielnie** – to osoba obsługująca aplikację musi pobrać z Axon raport na właściwy dzień, zanim wyśle wiadomości. Ten krok opisano w rozdziale 2 – jest to najważniejsza zasada w całej instrukcji, ponieważ pomyłka w dacie raportu oznacza wysłanie SMS-ów o niewłaściwej wizycie.

## 2. Najważniejsze: który raport pobrać z Axon

Zanim otworzysz aplikację, pobierz z Axon raport na **odpowiedni dzień w przyszłości** – nie na dzisiaj. Dzień raportu zależy od rodzaju wiadomości, którą chcesz wysłać:

- **Tryb "5 dni przed"** → pobierz z Axon raport wizyt za **5 dni od dzisiaj**.
  Przykład: jeśli dziś jest 20 sierpnia, pobierz raport wizyt na **25 sierpnia**.
- **Tryb "Przypomnienie o przełożeniu"** → pobierz z Axon raport wizyt za **2 dni od dzisiaj**.
  Przykład: jeśli dziś jest 20 sierpnia, pobierz raport wizyt na **22 sierpnia**.

Aplikacja wyśle wiadomości do wszystkich pacjentów znajdujących się w pliku, który wskażesz – niezależnie od tego, na jaki dzień faktycznie jest ten raport. Jeżeli pobierzesz raport na złą datę, aplikacja **tego nie wykryje** – SMS-y zostaną wysłane, tylko będą dotyczyć niewłaściwych wizyt. Zawsze sprawdź datę w nazwie/zawartości pliku przed wysyłką.

## 3. Uruchomienie aplikacji

Uruchom aplikację, klikając dwukrotnie plik `.exe`. Po uruchomieniu zobaczysz ekran główny z dwiema opcjami:

- **Generuj powiadomienia** – wysyłanie SMS-ów do pacjentów (przypomnienia, przełożenia),
- **Generuj zestawienia** – tworzenie zestawienia wizyt do rozliczeń.

Jeżeli u góry okna widzisz żółty pasek z napisem **"TRYB TESTOWY: brak klucza API – SMS-y nie są faktycznie wysyłane"**, oznacza to, że aplikacja nie ma skonfigurowanego połączenia z bramką SMS. W tym trybie żadne wiadomości nie trafiają do pacjentów – wszystko działa tylko "na niby", co przydaje się do testów. Jeśli widzisz ten pasek podczas normalnej pracy, a powinieneś wysyłać prawdziwe SMS-y, skontaktuj się z osobą odpowiedzialną za konfigurację aplikacji.

## 4. Wysyłanie przypomnień SMS – krok po kroku

1. Na ekranie głównym kliknij **Generuj powiadomienia**.
2. Kliknij **Wybierz plik raportu...** i wskaż plik pobrany z Axon (patrz rozdział 2 – upewnij się, że to raport na właściwy dzień). Obsługiwane formaty plików to `.xlsx`, `.xls` i `.csv`.
3. Z listy **Rodzaj wiadomości** wybierz jeden z dwóch trybów:
   - **5 dni przed** – przypomnienie o wizycie za 5 dni,
   - **Przypomnienie o przełożeniu** – wiadomość o możliwości bezpłatnego przełożenia wizyty.
4. Kliknij **Wyślij SMS**. Aplikacja przetworzy plik i zacznie wysyłać wiadomości – postęp pojawia się na bieżąco w konsoli (czarne pole tekstowe pod przyciskami).
5. Poczekaj, aż wysyłka się zakończy. Na dole ekranu pojawi się podsumowanie, np. "Wysłano: 12, błędów: 1, pominiętych: 2".

Treść wiadomości (szablon) ustawia się w **Ustawieniach** – patrz rozdział 7.

## 5. Jak czytać konsolę – legenda komunikatów

Podczas wysyłki w konsoli pojawiają się linie zaczynające się od jednego z poniższych słów:

- **OK: [pacjent] ([numer]) – wysłano przypomnienie [tryb]** – wiadomość została wysłana poprawnie do tego numeru.
- **BŁĄD: [pacjent] ([numer]) – [powód]** – wysyłka do tego numeru nie powiodła się (np. błąd bramki SMS, nieprawidłowy numer). Aplikacja próbuje wysłać wiadomość automatycznie do 2 razy, zanim zgłosi błąd.
- **POMINIĘTO: [pacjent] – brak numeru telefonu** – w raporcie nie znaleziono numeru telefonu dla tego pacjenta, więc nic nie zostało wysłane.
- **POMINIĘTO: [pacjent] – przypomnienie już wysłane** – aplikacja pamięta, komu już wysłała wiadomość danego rodzaju na daną wizytę (nawet po zamknięciu programu), i nie wyśle jej drugi raz. Chroni to przed przypadkowym podwójnym wysłaniem tego samego pliku.
- **BŁĄD: nie udało się odczytać pliku: [powód]** – wybrany plik jest uszkodzony, ma zły format lub nie jest raportem z Axon. Sprawdź, czy wybrano właściwy plik.
- **Podsumowanie: Wysłano: X, błędów: Y, pominiętych: Z** – pojawia się na końcu każdej wysyłki i podsumowuje wynik.

Jeśli pacjent ma w raporcie kilka numerów telefonu, aplikacja wysyła SMS na **wszystkie** z nich. Wizyta liczy się jako wysłana, jeśli powiedzie się choćby jedna z prób – nieudane próby do pozostałych numerów są i tak pokazywane jako `BŁĄD`, ale nie liczą się jako całkowita porażka wysyłki.

### Zapisywanie treści konsoli

Przycisk **Zapisz raport...** pozwala zapisać całą zawartość konsoli do pliku tekstowego (`.txt`) – przydatne, jeśli chcesz zachować dowód wysyłki lub przekazać komuś listę błędów do sprawdzenia.

## 6. Generowanie zestawień

Zestawienie to plik `.xlsx` z podsumowaniem wizyt dla każdego lekarza – używany do rozliczeń.

1. Na ekranie głównym kliknij **Generuj zestawienia**.
2. Kliknij **Wybierz plik źródłowy...** i wskaż raport z Axon obejmujący dłuższy okres (np. tydzień lub miesiąc).
3. Kliknij **Generuj zestawienie...** i wskaż, gdzie zapisać wynikowy plik `.xlsx`.

Wynikowy plik zawiera:
- osobny arkusz dla każdego lekarza, z listą wizyt (data, godzina, pacjent, cena, uwagi) i sumą na dole,
- arkusz **Podsumowanie** z sumą dla każdego lekarza oraz sumą łączną.

Wizyty odwołane/nieobecności (wpis w kolumnie Uwagi bez ceny, np. kod "nb-nieobecnosc") są widoczne na liście z odpowiednią adnotacją, ale **nie wliczają się** do sumy danego lekarza. Wizyty bez żadnej ceny ani adnotacji pokazują się z pustym polem ceny – to nie jest błąd, po prostu w raporcie nie było tej informacji.

## 7. Ustawienia – Szablony wiadomości

W oknie **Generuj powiadomienia** kliknij **Ustawienia...**, a następnie zakładkę **Szablony**.

Można tu edytować:
- **Szablon przypomnienia (5 dni przed wizytą)** – treść SMS-a wysyłanego w trybie "5 dni przed",
- **Szablon przypomnienia o możliwości przełożenia wizyty** – treść SMS-a w trybie przełożenia (ta wiadomość jest zawsze taka sama – nie zawiera danych konkretnej wizyty),
- **Nazwa przychodni**, **Telefon do odwołań**, **Adres przychodni** – dane używane w treści wiadomości.

### Dostępne pola w szablonie "5 dni przed"

W treści szablonu można używać poniższych pól – aplikacja automatycznie zastąpi je danymi z raportu:

| Pole | Co zostanie wstawione |
|---|---|
| `{imie_nazwisko}` | imię i nazwisko pacjenta |
| `{data}` | data wizyty (np. "25 sierpnia 2026") |
| `{godzina}` | godzina wizyty (np. "14:00") |
| `{lekarz}` | tytuł i nazwisko lekarza/specjalisty (np. "dr Kowalski") |
| `{rodzaj_wizyty}` | "sesji", "konsultacji lekarskiej" lub "wizycie" – zależnie od specjalizacji (patrz rozdział 8) |
| `{koszt_info}` | zdanie z ceną wizyty (np. " Koszt wizyty: 100 zł.") – puste, jeśli w raporcie nie było ceny |
| `{clinic_name}`, `{clinic_phone}`, `{clinic_address}` | dane przychodni wpisane powyżej |

Szablon przełożenia nie zawiera pól dotyczących pacjenta/wizyty – dostępne są tylko `{clinic_name}`, `{clinic_phone}`, `{clinic_address}`.

Wiadomości są zawsze wysyłane **bez polskich znaków diakrytycznych** (ą, ć, ę, ł, ń, ó, ś, ź, ż są automatycznie zamieniane na zwykłe litery) – dotyczy to również imion, nazwisk i nazwy lekarza wstawianych automatycznie. Robimy tak, żeby SMS mieścił się w tańszym limicie znaków. Nie trzeba nic w tym celu robić ręcznie – zamiana następuje automatycznie tuż przed wysyłką.

Po wprowadzeniu zmian kliknij **Zapisz** na dole okna Ustawień.

## 8. Ustawienia – Pracownicy

W tym samym oknie Ustawień, w zakładce **Pracownicy**, znajduje się lista lekarzy/specjalistów z ich specjalizacją. Lista ta służy do:

- doboru tytułu przed nazwiskiem w wiadomości ("dr" dla psychiatrów, "mgr" dla pozostałych specjalizacji),
- doboru słowa wstawianego w polu `{rodzaj_wizyty}`:
  - psychiatra → "konsultacji lekarskiej",
  - inna specjalizacja → "sesji".

Jeśli nazwisko lekarza z raportu **nie znajduje się** na tej liście, aplikacja i tak wyśle wiadomość – użyje neutralnego słowa "wizycie" zamiast "sesji"/"konsultacji lekarskiej" i nie doda tytułu przed nazwiskiem. Wysyłka nie zostaje zablokowana ani pominięta z tego powodu.

Aby dodać pracownika: wpisz specjalizację i nazwisko w polach na dole listy, kliknij **Dodaj**. Aby usunąć: zaznacz wiersz na liście i kliknij **Usuń zaznaczonego**. Pamiętaj, żeby na końcu kliknąć **Zapisz**.

## 9. Najczęstsze pytania i problemy

**Niektórzy lekarze mają wizyty zapisane w modułach, więc np. jedna wizyta to w raporcie z Axon dwa/trzy osobne wiersze dla tego samego pacjenta o tej samej godzinie. Czy pacjent dostanie kilka SMS-ów, a w zestawieniu cena policzy się kilka razy?**
Nie. Aplikacja automatycznie rozpoznaje takie wiersze (ten sam pacjent, ten sam dzień, ten sam lekarz **i ta sama godzina wizyty**) i traktuje je jako jedną wizytę – wysyła jeden SMS, a w zestawieniu cena wizyty liczy się tylko raz, nawet jeśli w raporcie pojawiła się przy każdym module.

**Pacjent ma tego samego dnia u tego samego lekarza dwie wizyty pod rząd (np. dwie godziny, jedna po drugiej) – czy to się nie zleje w zestawieniu w jedną wizytę?**
Nie – to są dwie różne godziny, więc aplikacja liczy je jako dwie osobne wizyty: każda dostaje swój SMS i osobną pozycję (cenę) w zestawieniu. To samo dotyczy sytuacji, gdy ten sam pacjent ma tego samego dnia osobną wizytę u **innego** lekarza – również zostaje ona osobną wizytą.

**Wysłałem/am ten sam plik drugi raz przez pomyłkę – czy pacjenci dostaną SMS dwa razy?**
Nie. Aplikacja zapamiętuje, komu i jaki rodzaj przypomnienia już wysłano dla danej wizyty (nawet po zamknięciu programu) i przy ponownej próbie pokaże w konsoli "POMINIĘTO: ... – przypomnienie już wysłane" zamiast wysyłać SMS ponownie.

**W konsoli widzę dużo "POMINIĘTO: ... – brak numeru telefonu". Co robić?**
Oznacza to, że w raporcie z Axon dla tego pacjenta nie ma numeru telefonu. Sprawdź eksport w Axon – to nie jest błąd aplikacji, tylko brak danych źródłowych.

**Widzę "BŁĄD" przy niektórych pacjentach mimo że numer telefonu wygląda poprawnie. Co teraz?**
Sprawdź treść błędu w nawiasie w konsoli – zwykle wskazuje, czy problem leży po stronie bramki SMS (np. przerwa w połączeniu) czy nieprawidłowego numeru. Aplikacja sama ponawia próbę 2 razy przed zgłoszeniem błędu, więc powtórne kliknięcie "Wyślij SMS" nie pomoże, jeśli numer jest faktycznie błędny.

**Czy mogę przerwać wysyłkę w trakcie?**
Nie ma przycisku "Anuluj" – poczekaj do końca. Jeśli wybrano zły plik/tryb, poczekaj na zakończenie, sprawdź w konsoli kto już dostał SMS (linie "OK:"), i w razie potrzeby skontaktuj się telefonicznie z pozostałymi pacjentami zamiast wysyłać poprawiony plik (może to spowodować podwójne SMS-y do części pacjentów, jeśli zmieni się np. rodzaj wiadomości).

**Pasek "TRYB TESTOWY" jest cały czas widoczny.**
Oznacza to, że aplikacja nie ma skonfigurowanego połączenia z bramką SMS i żadne wiadomości nie są faktycznie wysyłane. Skontaktuj się z osobą odpowiedzialną za konfigurację aplikacji – to nie jest coś, co da się naprawić z poziomu ustawień w aplikacji.

## 10. Dobre praktyki

- Zawsze sprawdzaj datę raportu pobranego z Axon przed wysyłką (rozdział 2) – to najczęstsze źródło pomyłek.
- Po zakończeniu wysyłki przejrzyj podsumowanie i konsolę – jeśli liczba błędów/pominiętych jest wysoka, sprawdź przyczynę zamiast ignorować.
- Plik z raportem z Axon zawiera dane osobowe pacjentów (imiona, nazwiska, PESEL, numery telefonów) – nie przesyłaj go dalej mailem ani nie zostawiaj w miejscach dostępnych dla osób postronnych.
