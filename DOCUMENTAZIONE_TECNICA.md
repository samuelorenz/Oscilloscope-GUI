# DOCUMENTAZIONE TECNICA: LeCroy SDA 812zi Professional Suite

Questa documentazione fornisce una spiegazione dettagliata del funzionamento, dell'architettura e delle tecnologie utilizzate nel software di controllo per oscilloscopi LeCroy.

---

## 1. Obiettivo del Software
Il software permette il controllo remoto completo di oscilloscopi LeCroy (serie SDA, WaveMaster, ecc.) tramite connessione Ethernet (TCP/IP). È progettato per offrire un'interfaccia moderna (stile GitHub Dark) che superi le limitazioni dei vecchi pannelli Web integrati negli strumenti.

## 2. Architettura Tecnologica
Il sistema è costruito interamente in **Python 3** utilizzando i seguenti componenti chiave:

### A. Interfaccia Grafica (PyQt6)
L'interfaccia è basata sul framework **PyQt6**, scelto per:
- **Alte Prestazioni**: Gestione fluida di immagini PNG grandi provenienti dallo schermo dell'oscilloscopio.
- **Styling Avanzato**: Uso di fogli di stile (CSS-like) per un'estetica professionale e dark mode.
- **Segnali e Slot**: Un sistema di comunicazione thread-safe che permette al "motore" del programma di parlare con la "grafica" senza far bloccare la finestra.

### B. Comunicazione VISA (PyVISA)
Per parlare con l'oscilloscopio viene utilizzato lo standard industriale **VISA** (Virtual Instrument Software Architecture).
- **Backend**: Utilizza `pyvisa` che si interfaccia con le librerie NI-VISA o Keysight installate sul PC.
- **Protocollo**: TCP/IP (LXI). L'oscilloscopio viene identificato tramite l'indirizzo IP con la stringa: `TCPIP::<IP>::INSTR`.

### C. Linguaggio Comandi (LeCroy VBS)
Oltre ai comandi standard SCPI (es. `*IDN?`), il software sfrutta la potenza del **LeCroy Automation Object Model** tramite comandi **VBS** (Visual Basic Scripting). 
- Questo permette di accedere a funzioni profonde dello strumento (es. `app.Measure.P1.Out.Result.Value`) che non sarebbero accessibili con i comandi testuali semplici.

---

## 3. Struttura del Codice (I File)

- **`main.py`**: Il punto di ingresso. Inizializza l'applicazione `QApplication` e avvia la finestra principale.
- **`main_gui.py`**: Il cuore visivo. Gestisce il layout a 3 colonne, i timer per il Live View e la logica di visualizzazione dei dati.
- **`visa_worker.py`**: Il "motore" in background. Esegue i comandi reali. È separato dalla GUI per evitare che il programma si blocchi ("Non risponde") se la rete è lenta.
- **`widgets.py`**: Contiene componenti personalizzati, come i controlli dei canali (Vertical) e i popup di sicurezza.
- **`styles.py`**: Contiene le definizioni estetiche (colori, bordi, animazioni) per mantenere il codice GUI pulito.

---

## 4. Funzionamento dei Moduli Chiave

### Il Sistema Live View
1. Un **Timer** scatta ogni 1.2 secondi.
2. Viene avviato un **Thread separato** che chiede all'oscilloscopio lo screenshot tramite il comando `SCDP`.
3. L'oscilloscopio invia il dump binario dello schermo.
4. Il Worker cerca l'header PNG (`\x89PNG...`) nei dati grezzi.
5. L'immagine viene passata alla GUI, ridimensionata proporzionalmente e mostrata nel monitor centrale.

### Gestione dei Canali (Vertical)
Ogni canale ha controlli indipendenti per Volt/Div, Offset e Accoppiamento.
- **Sicurezza 50 Ohm**: Se l'utente seleziona "DC50", il software intercetta l'azione e mostra un avviso di pericolo prima di inviare il comando allo strumento (protezione contro sovratensioni).

### Esportazione Dati
Il software può scaricare l'intera forma d'onda del canale selezionato in formato binario (`.bin`), utile per analisi successive in MATLAB o Excel.

---

## 5. Istruzioni per l'Uso

1. **Connessione**: Inserire l'IP dello strumento e cliccare su **CONNECT**. Se la connessione riesce, il pallino (Heartbeat) diventerà verde.
2. **Sincronizzazione**: Cliccare **SYNC FROM SCOPE** per leggere le impostazioni attuali dell'oscilloscopio e popolare l'interfaccia.
3. **Live View**: Cliccare **START LIVE** per vedere lo schermo dell'oscilloscopio in tempo reale.
4. **Snapshot**: Usa il tasto 📸 per salvare un'immagine fissa sul tuo Desktop nella cartella `Screenshots_Oscilloscope`.
5. **Auto-Apply**: Se la casella è spuntata, ogni modifica sulla GUI (es. cambio Volt/Div) viene inviata istantaneamente all'oscilloscopio.

---

## 6. Sicurezza
Il software include comandi forzati per:
- Impedire all'oscilloscopio di salvare screenshot internamente o sulla chiavetta USB (evita errori "Disk Full" o "USB Not Found").
- Forzare l'uscita dei dati sulla porta di rete remota.

---
*Documentazione redatta per Samuele Lorenzoni - Febbraio 2026*
