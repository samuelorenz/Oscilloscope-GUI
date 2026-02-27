# Guida all'uso della GUI per Oscilloscopio LeCroy

Questa interfaccia grafica (GUI) permette di controllare agevolmente un oscilloscopio LeCroy tramite rete (TCPIP).

## Requisiti
- Python 3.x
- Librerie: `PyQt6`, `pyvisa`, `pyvisa-py` (o NI-VISA)
- Connessione di rete all'oscilloscopio

## Funzionalità
1. **Connessione**: Inserisci l'indirizzo IP del tuo oscilloscopio e clicca su **CONNECT**. La barra di stato ti confermerà l'avvenuta connessione.
2. **Horizontal**: Imposta la base dei tempi (Time/Division).
3. **Vertical**: Controlla il Canale 1 (Attivazione, Volt/Division, Offset).
4. **Trigger**: Imposta la modalità (Auto, Normal, Single, Stop), la sorgente, la pendenza e il livello.
5. **Sync from Scope**: Legge i parametri attuali dall'oscilloscopio e aggiorna l'interfaccia.
6. **Apply Settings**: Invia tutti i parametri impostati sulla GUI all'oscilloscopio.
7. **Get Screenshot**: Cattura e visualizza l'anteprima dello schermo dell'oscilloscopio direttamente nell'interfaccia.

## Esecuzione
Per avviare la GUI, esegui il comando:
```bash
python gui_oscilloscopio_pro.py
```
o se usi il launcher di Windows:
```bash
py gui_oscilloscopio_pro.py
```
