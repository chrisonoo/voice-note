# Aplikacja do Transkrypcji Notatek Głosowych

Ta aplikacja służy do automatycznej transkrypcji plików audio przy użyciu API OpenAI Whisper. Projekt został zoptymalizowany pod kątem prostoty użycia i modułowej, czytelnej struktury kodu.

## Jak to działa?

Aplikacja wykonuje następujące kroki:
1.  Wyszukuje pliki audio (np. `.mp3`, `.wav`, `.m4a`) w folderze `rec/input`.
2.  Konwertuje znalezione pliki do standardowego formatu `.wav` za pomocą `ffmpeg` i zapisuje je w `rec/output`.
3.  Wysyła przekonwertowane pliki do API OpenAI Whisper w celu transkrypcji.
4.  Zapisuje wszystkie uzyskane transkrypcje w jednym, zbiorczym pliku `rec/5_transcriptions.txt`.

Aplikacja tworzy również pliki pomocnicze w folderze `rec`, które pozwalają śledzić postęp i wznowić pracę w przypadku błędu.

## Wymagania

*   Python 3.x
*   `ffmpeg` - musi być zainstalowany i dostępny w ścieżce systemowej (PATH).
*   Klucz API do OpenAI - zapisany w pliku `.env`.

## Instalacja

1.  **Sklonuj repozytorium:**
    ```bash
    git clone <adres-repozytorium>
    cd <nazwa-repozytorium>
    ```

2.  **Utwórz i aktywuj wirtualne środowisko:**
    *   Dla macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
    *   Dla Windows: `python -m venv .venv && .\\.venv\\Scripts\\activate`

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

Aplikację można uruchomić w dwóch trybach: graficznym (GUI) lub tradycyjnym wierszu poleceń (CLI).

### Tryb graficzny (GUI) - zalecany

Tryb graficzny zapewnia interaktywną obsługę i wizualizację postępu.

1.  **Uruchom aplikację** z flagą `--gui`:
    ```bash
    python main.py --gui
    ```
2.  **Postępuj zgodnie z instrukcjami** na ekranie: wybierz folder, wczytaj pliki i rozpocznij transkrypcję.

#### Ułatwione uruchamianie w Windows (opcjonalne)

Aby uruchomić aplikację jednym kliknięciem (bez potrzeby ręcznego aktywowania środowiska wirtualnego i bez widocznego okna terminala), możesz użyć dołączonych skryptów.

1.  **Utwórz skrót:** Kliknij prawym przyciskiem myszy na plik **`run_silent.vbs`** (nie `run_gui.bat`) i wybierz `Utwórz skrót`.
2.  **(Opcjonalnie) Zmień ikonę:** Kliknij prawym przyciskiem na nowo utworzony skrót, wybierz `Właściwości` -> `Zmień ikonę...` i wybierz dowolną ikonę.
3.  **Przenieś skrót** na pulpit lub w inne dogodne miejsce.

Od teraz, dwukrotne kliknięcie skrótu uruchomi aplikację w jej wirtualnym środowisku, a okno terminala nie będzie widoczne.

### Tryb wiersza poleceń (CLI)

Tryb CLI działa tak jak pierwotna wersja aplikacji.

1.  **Umieść swoje pliki audio** w folderze `rec/input`. Możesz tworzyć wewnątrz podfoldery – aplikacja przeszuka je wszystkie.

2.  **Uruchom aplikację** za pomocą komendy:
    ```bash
    python main.py
    ```

3.  **Gotowe!** Po zakończeniu procesu, wszystkie transkrypcje znajdziesz w pliku `rec/5_transcriptions.txt`.

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
    *Uwaga: W tym projekcie używamy tylko `openai` i `python-dotenv`. Po wykonaniu `freeze` warto ręcznie usunąć z pliku inne, niepotrzebne zależności.*


## Struktura projektu

*   `main.py`: Główny plik uruchomieniowy. Jego zadaniem jest wywołanie funkcji z poszczególnych modułów w odpowiedniej kolejności.
*   `src/config.py`: Centralny plik konfiguracyjny, w którym zdefiniowane są wszystkie ścieżki i parametry.
*   `src/audio/`: Moduł odpowiedzialny za operacje na plikach audio (wyszukiwanie, konwersja).
*   `src/whisper/`: Moduł będący "opakowaniem" (wrapperem) dla API OpenAI Whisper.
*   `src/transcribe/`: Moduł zarządzający całym procesem transkrypcji.
*   `rec/`: Folder na wszystkie pliki robocze (wejściowe, przekonwertowane, wyjściowe i pliki stanu).