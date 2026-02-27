import pyvisa
try:
    rm = pyvisa.ResourceManager('@py')
    print("Resources found:", rm.list_resources())
except Exception as e:
    print("Error:", e)
