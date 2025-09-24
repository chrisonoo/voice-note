# Project Generator

Ten projekt zawiera skrypt Pythona (`app.py`), który generuje strukturę pełnej aplikacji internetowej, w tym backend Node.js i frontend React.

## Instalacja

Aby uruchomić skrypt generatora projektu, należy skonfigurować wirtualne środowisko Pythona i zainstalować wymagane zależności.

### 1. Utwórz wirtualne środowisko

Środowisko wirtualne pozwala na oddzielne zarządzanie zależnościami dla danego projektu.

**Dla systemów macOS i Linux:**
```bash
python3 -m venv venv
```

**Dla systemu Windows:**
```bash
python -m venv venv
```

### 2. Aktywuj wirtualne środowisko

Przed rozpoczęciem instalacji lub używania pakietów należy aktywować środowisko wirtualne.

**Dla systemów macOS i Linux:**
```bash
source venv/bin/activate
```

**Dla systemu Windows:**
```bash
.\venv\Scripts\activate
```

### 3. Zainstaluj zależności

Zainstaluj wymagane pakiety Pythona za pomocą `pip` i pliku `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Aktualizacja zależności

Aby upewnić się, że korzystasz z najnowszych wersji bibliotek, możesz sprawdzić dostępność aktualizacji i zaktualizować plik `requirements.txt`.

### 1. Sprawdź nieaktualne pakiety

Użyj poniższego polecenia, aby wyświetlić listę pakietów, które mają nowsze wersje:

```bash
pip list --outdated
```

### 2. Zaktualizuj pakiety

Aby zaktualizować konkretny pakiet, użyj polecenia:

```bash
pip install -U nazwa_pakietu
```

Możesz również zaktualizować wszystkie pakiety z pliku `requirements.txt` za pomocą jednego polecenia:

```bash
pip install -r requirements.txt --upgrade
```

### 3. Zapisz zmiany w `requirements.txt`

Po zaktualizowaniu pakietów należy wygenerować nowy plik `requirements.txt`, aby zapisać zmiany:

```bash
pip freeze > requirements.txt
```

## Uruchomienie generatora

Po zainstalowaniu zależności możesz uruchomić skrypt `app.py`, aby wygenerować całą strukturę projektu:

```bash
python app.py
```

Skrypt utworzy w bieżącym katalogu foldery `backend` i `frontend` wraz z całą strukturą plików aplikacji.