import pyvisa
import time

# --- Impostazioni ---
# Modifica questo indirizzo se necessario
OSCILLOSCOPE_IP = '10.0.10.142'

# --- Script Principale ---
# Non modificare il codice sottostante se non sai cosa stai facendo

# Il resource string per la connessione TCPIP è nel formato: TCPIP::<indirizzo IP>::INSTR
resource_string = f'TCPIP::{OSCILLOSCOPE_IP}::INSTR'
instrument = None # Inizializza la variabile instrument

try:
    # Inizializza il gestore delle risorse VISA
    print("Inizializzazione del gestore risorse VISA...")
    rm = pyvisa.ResourceManager()

    # Apri la connessione con l'oscilloscopio
    print(f"Connessione a: {resource_string}")
    instrument = rm.open_resource(resource_string)

    # Imposta un timeout per le operazioni (in millisecondi)
    instrument.timeout = 5000  # 5 secondi

    # Configura il formato delle risposte (rimuove l'intestazione dai risultati)
    instrument.write('COMM_HEADER OFF')

    # Interroga l'identificativo dello strumento per verificare la connessione
    idn_response = instrument.query('*IDN?')
    print(f"Connesso a -> {idn_response.strip()}")

    # --- Esempi di Comandi ---

    # 1. Modifica della base dei tempi (Time Division)
    new_timebase = 1e-3  # 1 ms/div
    print(f"\n1. Impostazione della base dei tempi a {new_timebase} s/div...")
    instrument.write(f'TIME_DIV {new_timebase}')
    time.sleep(1) # Pausa per l'applicazione del comando
    current_timebase = instrument.query('TIME_DIV?')
    print(f"   -> Base dei tempi attuale: {current_timebase.strip()}")

    # 2. Modifica del guadagno verticale (Volt/Divisione) sul Canale 1
    channel = 'C1'
    new_volt_div = 0.2  # 0.2 V/div
    print(f"\n2. Impostazione del guadagno di {channel} a {new_volt_div} V/div...")
    instrument.write(f'{channel}:VOLT_DIV {new_volt_div}')
    time.sleep(1) # Pausa
    current_volt_div = instrument.query(f'{channel}:VOLT_DIV?')
    print(f"   -> Guadagno attuale su {channel}: {current_volt_div.strip()}")
    
    # 3. Attivazione della misura della frequenza sul Canale 1
    print(f"\n3. Misura della frequenza su {channel}...")
    # Per i LeCroy, i comandi di automazione complessi spesso richiedono il prefisso VBS
    instrument.write(f'VBS \'app.Measure.P1.Source = "{channel}"\'')
    instrument.write('VBS \'app.Measure.P1.ParamEngine = "Frequency"\'')
    instrument.write('VBS \'app.Measure.P1.View = True\'')
    
    time.sleep(2) # Pausa per permettere l'accumulo dei dati
    
    # Utilizziamo VBS? per interrogare il valore del risultato
    try:
        frequency_result = instrument.query('VBS? "Return=app.Measure.P1.Out.Result.Value"')
        print(f"   -> Frequenza misurata su {channel}: {frequency_result.strip()} Hz")
    except pyvisa.errors.VisaIOError as e:
        print(f"   -> Errore durante la lettura della frequenza: {e}")
        print("      Assicurati che ci sia un segnale stabile su C1 affinché l'oscilloscopio possa calcolare la frequenza.")

    # 4. Cattura dell'immagine dello schermo
    print("\n4. Cattura dello screenshot in corso...")
    
    # Pulizia preliminare del buffer dello strumento
    try:
        instrument.clear()
    except:
        pass

    # Imposta il formato dell'hardcopy
    instrument.write('HCSU DEV, PNG, PORT, NET')
    
    # Invia il comando di cattura
    print("   -> Richiesta dati immagine (SCDP)...")
    instrument.write('SCDP')
    
    # Aumentiamo il timeout per il trasferimento dell'immagine
    old_timeout = instrument.timeout
    instrument.timeout = 15000 # 15 secondi
    
    try:
        # Leggiamo i dati grezzi
        # Nota: Alcuni LeCroy inviano un'intestazione IEEE (#9000...) che purtroppo 
        # a volte è malformata. Leggiamo tutto e cerchiamo il marker PNG.
        raw_data = instrument.read_raw()
        
        # Il file PNG inizia sempre con la sequenza: \x89PNG\r\n\x1a\n
        png_header = b'\x89PNG\r\n\x1a\n'
        start_index = raw_data.find(png_header)
        
        if start_index != -1:
            image_data = raw_data[start_index:]
            filename = "screenshot_oscilloscopio.png"
            
            with open(filename, "wb") as f:
                f.write(image_data)
            
            print(f"   -> Screenshot salvato con successo: {filename} ({len(image_data)} byte)")
            
            # Apertura automatica
            import os
            try:
                os.startfile(filename)
            except:
                print(f"      Impossibile aprire il file automaticamente, lo trovi qui: {os.path.abspath(filename)}")
        else:
            print("   -> Errore: Intestazione PNG non trovata nei dati ricevuti.")
            # Salviamo un dump per capire cosa sta inviando
            with open("debug_buffer.bin", "wb") as f:
                f.write(raw_data)
            print("      Dati grezzi salvati in 'debug_buffer.bin' per analisi tecnica.")

    except Exception as e:
        print(f"   -> Errore durante la ricezione dell'immagine: {e}")

    finally:
        instrument.timeout = old_timeout


except pyvisa.errors.VisaIOError as e:
    print(f"\nERRORE DI COMUNICAZIONE VISA: {e}")
    print("\nCosa controllare:")
    print("  - L'indirizzo IP dell'oscilloscopio è corretto?")
    print("  - L'oscilloscopio è connesso alla rete e acceso?")
    print("  - Hai installato il backend corretto per pyvisa (es. NI-VISA)?")

except Exception as e:
    import traceback
    print(f"\nSI È VERIFICATO UN ERRORE INASPETTATO:")
    traceback.print_exc()

finally:
    # Chiudi la connessione se è stata aperta
    if instrument:
        print("\nChiusura della connessione.")
        instrument.close()
