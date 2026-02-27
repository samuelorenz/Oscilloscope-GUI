import pyvisa
import time

# --- Settings ---
# Modify this address if necessary
OSCILLOSCOPE_IP = '10.0.10.142'

# --- Main Script ---
# Do not modify the code below unless you know what you are doing

# The resource string for the TCPIP connection is in the format: TCPIP::<IP address>::INSTR
resource_string = f'TCPIP::{OSCILLOSCOPE_IP}::INSTR'
instrument = None # Initialize the instrument variable

try:
    # Initialize the VISA resource manager
    print("Initializing VISA resource manager...")
    rm = pyvisa.ResourceManager()

    # Open connection to the oscilloscope
    print(f"Connecting to: {resource_string}")
    instrument = rm.open_resource(resource_string)

    # Set an operation timeout (in milliseconds)
    instrument.timeout = 5000  # 5 seconds

    # Configure response format (removes header from results)
    instrument.write('COMM_HEADER OFF')

    # Query the instrument identifier to verify connection
    idn_response = instrument.query('*IDN?')
    print(f"Connected to -> {idn_response.strip()}")

    # --- Command Examples ---

    # 1. Modify the timebase (Time Division)
    new_timebase = 1e-3  # 1 ms/div
    print(f"\n1. Setting the timebase to {new_timebase} s/div...")
    instrument.write(f'TIME_DIV {new_timebase}')
    time.sleep(1) # Pause for the command to apply
    current_timebase = instrument.query('TIME_DIV?')
    print(f"   -> Current timebase: {current_timebase.strip()}")

    # 2. Modify vertical gain (Volt/Division) on Channel 1
    channel = 'C1'
    new_volt_div = 0.2  # 0.2 V/div
    print(f"\n2. Setting gain for {channel} to {new_volt_div} V/div...")
    instrument.write(f'{channel}:VOLT_DIV {new_volt_div}')
    time.sleep(1) # Pause
    current_volt_div = instrument.query(f'{channel}:VOLT_DIV?')
    print(f"   -> Current gain on {channel}: {current_volt_div.strip()}")
    
    # 3. Activate frequency measurement on Channel 1
    print(f"\n3. Frequency measurement on {channel}...")
    # For LeCroy, complex automation commands often require the VBS prefix
    instrument.write(f'VBS \'app.Measure.P1.Source = "{channel}"\'')
    instrument.write('VBS \'app.Measure.P1.ParamEngine = "Frequency"\'')
    instrument.write('VBS \'app.Measure.P1.View = True\'')
    
    time.sleep(2) # Pause to allow data accumulation
    
    # Use VBS? to query the result value
    try:
        frequency_result = instrument.query('VBS? "Return=app.Measure.P1.Out.Result.Value"')
        print(f"   -> Measured frequency on {channel}: {frequency_result.strip()} Hz")
    except pyvisa.errors.VisaIOError as e:
        print(f"   -> Error reading the frequency: {e}")
        print("      Ensure there is a stable signal on C1 so the oscilloscope can calculate the frequency.")

    # 4. Screen capture
    print("\n4. Capturing screenshot...")
    
    # Preliminary cleanup of the instrument buffer
    try:
        instrument.clear()
    except:
        pass

    # Set hardcopy format
    instrument.write('HCSU DEV, PNG, PORT, NET')
    
    # Send capture command
    print("   -> Requesting image data (SCDP)...")
    instrument.write('SCDP')
    
    # Increase timeout for image transfer
    old_timeout = instrument.timeout
    instrument.timeout = 15000 # 15 seconds
    
    try:
        # Read raw data
        # Note: Some LeCroys send an IEEE header (#9000...) which is unfortunately 
        # sometimes malformed. We read everything and look for the PNG marker.
        raw_data = instrument.read_raw()
        
        # The PNG file always starts with the sequence: \x89PNG\r\n\x1a\n
        png_header = b'\x89PNG\r\n\x1a\n'
        start_index = raw_data.find(png_header)
        
        if start_index != -1:
            image_data = raw_data[start_index:]
            filename = "oscilloscope_screenshot.png"
            
            with open(filename, "wb") as f:
                f.write(image_data)
            
            print(f"   -> Screenshot saved successfully: {filename} ({len(image_data)} bytes)")
            
            # Auto open
            import os
            try:
                os.startfile(filename)
            except:
                print(f"      Unable to automatically open the file, you can find it here: {os.path.abspath(filename)}")
        else:
            print("   -> Error: PNG header not found in received data.")
            # Save a raw dump to understand what it's sending
            with open("debug_buffer.bin", "wb") as f:
                f.write(raw_data)
            print("      Raw data saved to 'debug_buffer.bin' for technical analysis.")

    except Exception as e:
        print(f"   -> Error receiving image: {e}")

    finally:
        instrument.timeout = old_timeout


except pyvisa.errors.VisaIOError as e:
    print(f"\nVISA COMMUNICATION ERROR: {e}")
    print("\nThings to check:")
    print("  - Is the oscilloscope's IP address correct?")
    print("  - Is the oscilloscope connected to the network and powered on?")
    print("  - Is the correct backend installed for pyvisa (e.g. NI-VISA)?")

except Exception as e:
    import traceback
    print(f"\nAN UNEXPECTED ERROR HAS OCCURRED:")
    traceback.print_exc()

finally:
    # Close the connection if it was opened
    if instrument:
        print("\nClosing connection.")
        instrument.close()
