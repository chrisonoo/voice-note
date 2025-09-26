# Aplikacja do Transkrypcji Notatek Głosowych

Ta aplikacja służy do automatycznej transkrypcji plików audio przy użyciu API OpenAI Whisper. Projekt został napisany z myślą o modułowości i czytelności kodu, oferując zarówno interfejs graficzny (GUI), jak i tradycyjny tryb wiersza poleceń (CLI).

## Kluczowe Funkcje

*   **Dwa tryby pracy:** Interaktywny interfejs graficzny (GUI) lub szybki tryb wiersza poleceń (CLI).
*   **Zarządzanie stanem:** Aplikacja używa bazy danych SQLite do zapisywania stanu plików, co pozwala na wstrzymywanie i wznawianie pracy.
*   **Konwersja w locie:** Automatycznie konwertuje różne formaty audio (np. `.mp3`, `.m4a`) do formatu `.wav` za pomocą `ffmpeg`.
*   **Przetwarzanie w tle:** W trybie GUI wszystkie operochłonne zadania (konwersja, transkrypcja) są wykonywane w osobnych wątkach, co zapobiega "zamrażaniu" interfejsu.

## Wymagania

*   Python 3.x
*   `ffmpeg` - musi być zainstalowany i dostępny w ścieżce systemowej (PATH).
*   Klucz API do OpenAI - zapisany w pliku `.env`.

## Instalacja

1.  **Sklonuj repozytorium:**
    ```bash
    git clone <adres-repozytorium>
    ```
    ```bash
    cd <nazwa-repozytorium>
    ```

2.  **Utwórz i aktywuj wirtualne środowisko:**
    *   Dla macOS/Linux:
        ```bash
        python3 -m venv .venv
        ```
        ```bash
        source .venv/bin/activate
        ```
    *   Dla Windows:
        ```bash
        python -m venv .venv
        ```
        ```bash
        .venv\Scripts\activate
        ```

3.  **Zainstaluj zależności:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Skonfiguruj klucz API:**
    *   Utwórz plik o nazwie `.env` w głównym katalogu projektu.
    *   W pliku `.env` dodaj swój klucz API w następującym formacie:
        ```
        API_KEY_WHISPER="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        ```

## Jak używać?

Aplikację można uruchomić w dwóch trybach.

### Tryb graficzny (GUI) - zalecany

Tryb graficzny zapewnia interaktywną obsługę i wizualizację całego procesu.

1.  **Uruchom aplikację** z flagą `--gui`:
    ```bash
    python main.py --gui
    ```
2.  **Postępuj zgodnie z instrukcjami** na ekranie:
    *   Kliknij "Wybierz pliki", aby dodać pliki audio.
    *   Zaznacz pliki, które chcesz przetworzyć.
    *   Kliknij "Wczytaj Pliki", aby przekonwertować je do formatu WAV.
    *   Kliknij "Start", aby rozpocząć proces transkrypcji.

#### Ułatwione uruchamianie w Windows

Aby uruchomić aplikację jednym kliknięciem (bez potrzeby ręcznego aktywowania środowiska wirtualnego i bez widocznego okna terminala), możesz użyć dołączonych skryptów.

1.  **Utwórz skrót:** Kliknij prawym przyciskiem myszy na plik **`run_silent.vbs`** (nie `run_gui.bat`) i wybierz `Utwórz skrót`.
2.  **(Opcjonalnie) Zmień ikonę:** Kliknij prawym przyciskiem na nowo utworzony skrót, wybierz `Właściwości` -> `Zmień ikonę...` i wybierz dowolną ikonę.
3.  **Przenieś skrót** na pulpit lub w inne dogodne miejsce.

### Tryb wiersza poleceń (CLI)

Tryb CLI służy do szybkiego przetwarzania plików z jednego folderu.

1.  **Uruchom aplikację**, podając ścieżkę do folderu z plikami audio za pomocą flagi `--input-dir`:
    ```bash
    python main.py --input-dir /sciezka/do/twoich/plikow
    ```
    *Aplikacja rekursywnie przeszuka cały podany folder i jego podfoldery.*

2.  **Opcjonalnie**, jeśli chcesz przetwarzać pliki dłuższe niż 5 minut, dodaj flagę `-l` lub `--allow-long`:
    ```bash
    python main.py --input-dir /sciezka/do/plikow --allow-long
    ```

3.  **Gotowe!** Po zakończeniu procesu, wszystkie transkrypcje zostaną zapisane w bazie danych w folderze `tmp/`.

## Architektura Aplikacji

Poniższe schematy ilustrują budowę i przepływ danych w aplikacji.

### Schemat Bazy Danych

Aplikacja używa pojedynczej tabeli `files` w bazie SQLite do śledzenia stanu każdego pliku audio w procesie.

```mermaid
erDiagram
    files {
        INTEGER id PK "Klucz główny"
        TEXT source_file_path UK "Ścieżka do oryginalnego pliku"
        TEXT tmp_file_path "Ścieżka do pliku .wav w folderze tmp"
        BOOLEAN is_selected "Czy plik jest zaznaczony w GUI"
        BOOLEAN is_loaded "Czy plik został przekonwertowany do .wav"
        BOOLEAN is_processed "Czy plik ma już transkrypcję"
        TEXT transcription "Wynik transkrypcji"
        REAL duration_seconds "Czas trwania pliku w sekundach"
    }
```

### Przepływ Danych (Logika Backendu)

Diagram pokazuje, jak poszczególne moduły współpracują ze sobą w celu przetworzenia plików audio.

```mermaid
graph TD
    subgraph "Wejście"
        User_CLI["Użytkownik (CLI)"]
        User_GUI["Użytkownik (GUI)"]
    end

    subgraph "Orkiestracja"
        Main["main.py"]
    end

    subgraph "Moduły Rdzenia"
        Audio["src/audio/\n(konwersja, walidacja)"]
        Transcribe["src/transcribe/\n(proces transkrypcji)"]
        Whisper["src/whisper/\n(wrapper API)"]
        Database["src/database.py\n(stan aplikacji)"]
    end

    subgraph "Zależności Zewnętrzne"
        FFmpeg["ffmpeg"]
        OpenAI_API["OpenAI API"]
    end

    User_CLI --> Main
    User_GUI --> Main

    Main --> Audio
    Main --> Transcribe

    Audio --> Database
    Audio --> FFmpeg

    Transcribe --> Database
    Transcribe --> Whisper

    Whisper --> OpenAI_API

    style Database fill:#f9f,stroke:#333,stroke-width:2px
```

### Struktura Interfejsu Graficznego (GUI)

Diagram przedstawia relacje między kluczowymi klasami odpowiedzialnymi za budowę i logikę interfejsu użytkownika.

```mermaid
graph TD
    subgraph "Główne Okno (core/main_window.py)"
        App["App (ctk.CTk)"]
    end

    subgraph "Budowniczy UI (core/interface_builder.py)"
        IB["InterfaceBuilder"]
    end

    subgraph "Kontrolery Logiki (controllers/)"
        BSC["ButtonStateController"]
        FH["FileHandler"]
        TC["TranscriptionController"]
        PM["PanelManager"]
    end

    subgraph "Narzędzia (utils/)"
        AP["AudioPlayer"]
    end

    subgraph "Widżety (widgets/)"
        FSP["FileSelectionPanel"]
        TOP["TranscriptionOutputPanel"]
        style FSP fill:#ccf,stroke:#333,stroke-width:2px
        style TOP fill:#ccf,stroke:#333,stroke-width:2px
    end

    subgraph "Backend"
        DB["database.py"]
        Audio["audio/"]
        Transcribe["transcribe/"]
    end

    App --> IB
    App --> BSC
    App --> FH
    App --> TC
    App -- "tworzy" --> PM
    App -- "tworzy" --> AP

    IB -- "tworzy" --> FSP
    IB -- "tworzy" --> TOP

    FH -- "używa" --> Audio
    FH -- "używa" --> DB

    TC -- "używa" --> Transcribe
    TC -- "używa" --> DB

    PM -- "aktualizuje" --> FSP
    PM -- "aktualizuje" --> TOP
    PM -- "używa" --> DB

    BSC -- "zarządza stanem" --> IB

    AP -- "odtwarza audio z" --> FSP
```

## Zarządzanie Zależnościami

Aby upewnić się, że korzystasz z najnowszych wersji bibliotek, możesz okresowo je aktualizować.

1.  **Sprawdź dostępne aktualizacje:**
    ```bash
    pip list --outdated
    ```

2.  **Zaktualizuj biblioteki:**
    ```bash
    pip install --upgrade -r requirements.txt
    ```

3.  **Zapisz nowe wersje w pliku:**
    Po aktualizacji, wygeneruj nowy plik `requirements.txt`, aby zapisać zmiany.
    ```bash
    pip freeze > requirements.txt
    ```

## Struktura projektu

*   `main.py`: Główny plik uruchomieniowy, który parsuje argumenty i uruchamia odpowiedni tryb (CLI/GUI).
*   `src/`: Główny folder z kodem źródłowym aplikacji.
    *   `config.py`: Centralny plik konfiguracyjny (ścieżki, parametry API).
    *   `database.py`: Moduł do zarządzania bazą danych SQLite.
    *   `audio/`: Moduł do operacji na plikach audio (wyszukiwanie, konwersja, sprawdzanie długości).
    *   `transcribe/`: Moduł zarządzający procesem transkrypcji.
    *   `whisper/`: Moduł będący "opakowaniem" (wrapperem) dla API OpenAI Whisper.
    *   `gui/`: Moduł zawierający cały kod interfejsu graficznego.
        *   `core/`: Główne okno aplikacji i "budowniczy" interfejsu.
        *   `controllers/`: Klasy zarządzające logiką GUI (np. stanem przycisków, obsługą plików).
        *   `widgets/`: Niestandardowe komponenty GUI (np. panele list plików).
        *   `utils/`: Narzędzia pomocnicze dla GUI (np. odtwarzacz audio).
*   `tmp/`: Folder na wszystkie pliki robocze (baza danych, przekonwertowane pliki .wav).