# Analisi Criticità Software Oscilloscopio LeCroy

In questa analisi sono elencate le problematiche tecniche e funzionali rilevate nel codice attuale, con le relative opzioni di risoluzione.

## 1. Architettura e Threading (PRIORITÀ MASSIMA)

- [x] **Thread Pile-up**: Risolto con sistema "chain-link" (SingleShot timer + Segnali).
- [ ] **Blocco Interfaccia**: (Opzione B suggerita per futuro).
- [ ] **Mancanza di Coda**: (Da implementare se necessario).

## 2. Affidabilità Comunicazione

- [x] **Timeout Variabili**: Implementati timeout dinamici (1s base, 15s screenshot).
- [x] **Cleanup Risorse**: Sessioni VISA chiuse correttamente in `closeEvent`.

## 3. Gestione Screenshot e Memoria

- [x] **Carico CPU**: Ridimensionamento immagini spostato nel thread del Worker.
- [x] **Header PNG Fragile**: Aggiunto controllo integrità con verifica del footer PNG `IEND`.

## 4. Esperienza Utente (UX)

- [x] **Feedback Assente**: Aggiunta Status Bar con log in tempo reale delle risposte dello strumento.
- [ ] **Scaling Monitor**: (Supporto migliorato, ma layout flessibile da rifinire).

## 5. Sicurezza Strumento

- [x] **Protezione 50 Ohm**: Software impedisce voltaggi > 5V se lo strumento è in modalità 50 Ohm.
- [x] **Stato Errori**: Controllo automatico dello "Status Register" (`*ESR?`) dopo ogni comando.

## 6. Sincronizzazione (Auto-Sync)

- [x] **Sync Passivo**: Sincronizzazione automatica parametri principali ogni 5 cicli di refresh.

---
*Prossimo passo suggerito: Partire dal Punto 1 (Thread Pile-up) usando l'Opzione B (Chain-link timer).*
