## LeCroy SDA 812zi Professional Suite – Oscilloscope GUI

Interfaccia grafica avanzata in **Python / PyQt6** per il controllo remoto di oscilloscopi **LeCroy** (es. serie SDA, WaveMaster) tramite rete **TCP/IP (LXI)**.

L’obiettivo è sostituire i vecchi pannelli web integrati con una GUI moderna in dark mode, ottimizzata per:

- controllo veloce di **timebase, canali, trigger e misure**
- **live view** dello schermo dello strumento
- salvataggio di **screenshot** e **forme d’onda** per analisi successive

---

### Caratteristiche principali

- **Connessione via TCP/IP** a oscilloscopi LeCroy (`TCPIP::<IP>::INSTR`)
- **Controllo completo dei canali (C1–C4)**:
  - ON/OFF trace
  - Volt/Division, Offset, Coupling, Bandwidth limit, Invert
  - pulsante rapido **SAVE DATA** per esportare la forma d’onda in binario
- **Gestione trigger**:
  - modalità (AUTO, NORM, SINGLE, STOP)
  - tipo (EDGE, WIDTH, GLITCH, TV)
  - sorgente, pendenza, livello
- **Live screen monitor**:
  - aggiornamento periodico dello schermo tramite comando `SCDP`
  - visualizzazione ridimensionata in tempo reale
  - salvataggio screenshot su Desktop (`Screenshots_Oscilloscope`)
- **Misure automatiche**:
  - configurazione parametri (P1, P2, …) tramite VBS
  - lettura di valori come PKPK, MAX, MIN, FREQ, PERIOD
- **Architettura robusta**:
  - worker VISA in **QThread** (`visa_worker.py`) separato dalla GUI (`main_gui.py`)
  - comunicazione thread‑safe tramite **segnali/slot PyQt6**
  - controlli di sicurezza su coupling 50 Ω e tensioni elevate

---

### Requisiti

- **Python** 3.9+ (consigliato)
- Dipendenze Python elencate in `requirements.txt`:
  - `PyQt6`
  - `pyvisa`
  - `pyvisa-py` (oppure NI‑VISA come backend)
- Oscilloscopio LeCroy compatibile, raggiungibile via rete (stesso segmento IP del PC)

Esempio installazione (ambiente virtuale consigliato):

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Se utilizzi NI‑VISA, installa il pacchetto dal sito National Instruments e configura `pyvisa` perché usi quel backend.

---

### Struttura del progetto

- `main.py` – punto di ingresso principale: crea la `QApplication` e apre la finestra `OscilloscopeGUI`.
- `main_gui.py` – GUI principale a 3 colonne (stato sistema, monitor, canali) + menu, timer live, log eventi.
- `visa_worker.py` – worker PyQt che gira in un **QThread**:
  - gestisce connessione VISA, comandi SCPI/VBS, screenshot, misure, export waveform, sync impostazioni.
- `widgets.py` – widget personalizzati, in particolare `ChannelControl` per ciascun canale C1–C4.
- `styles.py` – tema dark stile GitHub (stylesheet globale `STYLE_MAIN`).
- `LEGGIMI.md` – guida utente in italiano (uso operativo).
- `DOCUMENTAZIONE_TECNICA.md` – documentazione tecnica dettagliata (architettura, flussi, comandi).

Il file `gui_oscilloscopio_pro.py` contiene una versione precedente “monolitica” (GUI + worker nello stesso file) e oggi è superato dalla nuova architettura modulare (`main.py` + `main_gui.py` + `visa_worker.py` + `widgets.py` + `styles.py`).

---

### Installazione ed esecuzione

1. **Clona il repository** o copia la cartella del progetto.
2. (Opzionale ma consigliato) crea un **virtualenv** ed installa i requisiti:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

3. Assicurati che l’oscilloscopio sia:
   - accessibile via IP dalla tua macchina
   - configurato per accettare connessioni LXI/TCPIP.

4. Avvia la GUI:

   ```bash
   python main.py
   ```

   In alternativa, puoi avviare direttamente la versione precedente:

   ```bash
   python gui_oscilloscopio_pro.py
   ```

---

### Utilizzo rapido

- **Connessione**
  - Inserisci l’indirizzo IP dell’oscilloscopio nel campo `IP`.
  - Clicca **CONNECT**.
  - Se la connessione va a buon fine, il log mostra l’`*IDN?` e l’interfaccia passa allo stato connesso.

- **Sincronizzazione impostazioni**
  - Clicca **SYNC FROM SCOPE** per leggere:
    - timebase (`TIME_DIV`)
    - stato canali (TRACE, VOLT_DIV, OFFSET, COUPLING, BANDWIDTH, INVERT)
    - parametri di trigger (MODE, TYPE, SRC, LEVEL).
  - La GUI si aggiorna senza generare comandi verso lo strumento.

- **Applicazione impostazioni**
  - Modifica canali, timebase o trigger nella GUI.
  - Clicca **APPLY TO SCOPE** per inviare in blocco i comandi (`send_multiple_commands` nel worker).

- **Live View & Screenshot**
  - Clicca **▶ START LIVE STREAM** per abilitare il live refresh dello schermo:
    - il worker esegue ciclicamente `HCSU` + `SCDP` e invia un `QImage` alla GUI
    - ogni N cicli viene eseguita anche la sincronizzazione delle impostazioni.
  - Clicca **📸 SNAPSHOT** per una cattura singola.
  - Abilita **AUTO-SAVE LIVE** per salvare automaticamente gli screenshot in:
    - `Desktop/Screenshots_Oscilloscope`

- **Misure**
  - Scegli **Source** (C1–C4) e **Type** (PKPK, MAX, MIN, FREQ, PERIOD).
  - In modalità live, ad ogni ciclo il worker aggiorna la tabella con il valore corrente.

Per dettagli più approfonditi vedi `LEGGIMI.md` e `DOCUMENTAZIONE_TECNICA.md`.

---

### Note di sicurezza

- Quando il coupling è impostato a **DC50** (50 Ω) il software:
  - mostra un **warning** esplicito lato GUI (`ChannelControl.validate_coupling_change`)
  - impedisce Volt/Div potenzialmente pericolosi lato worker (`send_command` in `visa_worker.py`),
    bloccando comandi che superano una certa soglia con ingresso a 50 Ω.
- Durante il **cleanup** (chiusura applicazione) il worker:
  - ripristina le impostazioni di hardcopy/screenshot dello strumento
  - rilascia correttamente le risorse VISA.

È comunque responsabilità dell’utente rispettare i limiti di tensione e le specifiche di sicurezza dell’oscilloscopio.

---

### Debug e stato del codice

- I file Python principali (`main.py`, `main_gui.py`, `visa_worker.py`, `widgets.py`, `gui_oscilloscopio_pro.py`) risultano **senza errori di linting** e con struttura coerente.
- La comunicazione tra GUI e worker avviene tramite **QThread** e segnali/slot, senza uso di `threading` nella nuova architettura.
- Il worker implementa controlli di **busy state** per evitare richieste concorrenti e gestisce gli errori VISA con messaggi espliciti nel log.

Se riscontri errori specifici in esecuzione (es. problemi di connessione VISA, crash o comportamenti strani), apri una **issue** su GitHub includendo:

- versione di Python
- versione di PyQt6 / pyvisa / backend VISA
- modello di oscilloscopio LeCroy e firmware
- messaggio di errore comparso nel log o nella console.

