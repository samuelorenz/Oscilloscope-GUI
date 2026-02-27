# Professional Dark Theme for LeCroy SDA Suite

# Professional Dark Theme for LeCroy SDA Suite - Premium Version

STYLE_MAIN = """
    QMainWindow { background-color: #0b0e14; }
    QMenuBar { background-color: #161b22; color: #c9d1d9; border-bottom: 1px solid #30363d; font-weight: 500; }
    QMenuBar::item:selected { background-color: #30363d; border-radius: 4px; }
    QMenu { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; }
    QMenu::item:selected { background-color: #1f6feb; }
    
    QGroupBox {
        border: 1px solid #30363d; border-radius: 10px; font-weight: bold;
        color: #58a6ff; margin-top: 15px; padding-top: 20px; background-color: #10151c;
    }
    
    QLabel { color: #8b949e; font-size: 12px; font-family: 'Inter', sans-serif; }
    
    QLineEdit, QComboBox, QDoubleSpinBox {
        background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d;
        border-radius: 6px; padding: 6px; min-height: 28px;
    }
    QLineEdit:focus, QComboBox:focus { border: 1px solid #58a6ff; }
    
    QPushButton { 
        background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; 
        border-radius: 6px; padding: 8px 12px; font-weight: 600; font-size: 12px;
    }
    QPushButton:hover { background-color: #30363d; border: 1px solid #8b949e; }
    QPushButton:pressed { background-color: #0d1117; }
    
    QPushButton#connect_btn { background-color: #238636; color: white; border: none; }
    QPushButton#connect_btn:hover { background-color: #2ea043; }
    
    QPushButton#apply_btn_dirty { background-color: #d29922; color: black; border: none; font-weight: bold; }
    QPushButton#apply_btn_clean { background-color: #21262d; color: #7ee787; border: 1px solid #30363d; }
    
    QTabWidget::pane { border: 1px solid #30363d; background: #10151c; border-radius: 6px; top: -1px; }
    QTabBar::tab { 
        background: #0b0e14; color: #8b949e; border: 1px solid #30363d; 
        padding: 10px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px;
        margin-right: 2px;
    }
    QTabBar::tab:selected { background: #10151c; color: #58a6ff; border-bottom: none; }
    
    QScrollArea { border: none; background-color: transparent; }
    
    QTextEdit { 
        background-color: #010409; color: #7ee787; border: 1px solid #30363d; 
        border-radius: 6px; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;
    }
    
    /* Channel Accents */
    QGroupBox#C1 { color: #e3b341; border-color: #e3b341; }
    QGroupBox#C2 { color: #f85149; border-color: #f85149; }
    QGroupBox#C3 { color: #58a6ff; border-color: #58a6ff; }
    QGroupBox#C4 { color: #3fb950; border-color: #3fb950; }
    
    #heartbeat_on { background-color: #3fb950; border-radius: 5px; }
    #heartbeat_off { background-color: #30363d; border-radius: 5px; }
"""
