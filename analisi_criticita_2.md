# Analisi Criticità Software Oscilloscopio - Fase 2

In questa seconda analisi esploriamo bug latenti, colli di bottiglia e miglioramenti della stabilità basati sul "stress test" logico.

## 1. Gestione Eccezioni e Lock GUI (PRIORITÀ ALTA)

- [ ] **Stato di Blocco Permanenti**: In `apply_synced_settings`, se un'eccezione avviene nel mezzo del parsing (es. dati corrotti dallo strumento), il flag `self._is_gui_updating` rimane a `True`, impedendo all'utente di modificare la GUI per sempre.
  - **Risoluzione**: Usare un blocco `try...finally` per garantire il reset del flag.
- [ ] **Segnali Bloccati post-Errore**: Similmente, se `blockSignals(True)` viene chiamato e il codice crasha prima del `False`, il widget diventa "morto".

## 2. Ottimizzazione Performance (Live View)

- [ ] **Serializzazione Query**: `fetch_all_settings` esegue circa 30 query individuali. Su reti lente o strumenti datati, questo può durare secondi, bloccando il Worker e ritardando i tasti utente.
  - **Risoluzione**: Raggruppare le letture critiche o rendere la sincronizzazione "pigra" (solo canali attivi).
- [ ] **Overhead Segnale Screenshot**: Inviare `bytes` grezzi via segnale e poi convertirli in `QImage` e poi `QPixmap` può essere ottimizzato usando riferimenti o buffer condivisi se la velocità aumenta.

## 3. Robustezza del Codice (Bug Scovati)

- [ ] **Crash su Ridimensionamento Finestra**: Se la finestra viene ridotta a zero (minimizzo), `target_size` in `main_gui.py` potrebbe generare valori non validi per lo scaling.
- [ ] **Esportazione DAT1 Fragile**: `WAVEFORM? DAT1` scarica dati binari che richiedono un parsing specifico dell'header LeCroy (WAVEDESC) per essere utili in CSV/Excel. Attualmente salviamo solo un blob binario grezzo difficile da leggere.
- [ ] **IP Hardcoded Default**: Se lo strumento non risponde, il timeout di 5s durante la prima connessione blocca il thread (corretto in thread, ma manca un tasto "Abort Connect").

## 4. Nuove Feature di Sicurezza

- [ ] **Controllo Protezione Input**: Se un canale è in 50 Ohm, la manopola fisica dell'offset ha limiti diversi (solitamente +/- 5V o meno). Superare questi limiti via software può causare "Internal Error" nello strumento.
- [ ] **Mancanza di Log Permanente**: Gli errori nella console (`log_txt`) si perdono alla chiusura.
  - **Opzione**: Salvare un file `session.log` in automatico.

## 5. Proposta Autotest

- [ ] **Mocking VISA**: Creare uno script che simuli un oscilloscopio per testare la logica di protezione 50 Ohm senza rischiare hardware reale.
