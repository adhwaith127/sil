#!/usr/bin/env python3
"""
Settings Dialog for Biometric Server
Provides GUI interface for configuration management
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os


class SettingsDialog:
    """Settings dialog for configuring the biometric server"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.dialog = None
        self.result = None
        
        # Entry widgets dictionary
        self.entries = {}
    
    def show(self):
        """Display the settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Server Settings")
        self.dialog.geometry("600x550")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.center_dialog()
        
        # Create UI
        self.create_ui()
        
        # Wait for dialog to close
        self.parent.wait_window(self.dialog)
        
        return self.result
    
    def center_dialog(self):
        """Center the dialog on parent window"""
        self.dialog.update_idletasks()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def create_ui(self):
        """Create the settings UI"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        current_row = 0
        
        # ===== Server Settings =====
        server_label = ttk.Label(main_frame, text="Server Settings", 
                                font=('Segoe UI', 11, 'bold'))
        server_label.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        current_row += 1
        
        # Host
        ttk.Label(main_frame, text="Host:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['host'] = ttk.Entry(main_frame, width=40)
        self.entries['host'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['host'].insert(0, self.config_manager.get_server_config().get('host', '0.0.0.0'))
        current_row += 1
        
        # Port
        ttk.Label(main_frame, text="Port:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['port'] = ttk.Entry(main_frame, width=40)
        self.entries['port'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['port'].insert(0, str(self.config_manager.get_server_config().get('port', 8190)))
        current_row += 1
        
        # Base Directory
        ttk.Label(main_frame, text="Base Directory:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        base_dir_frame = ttk.Frame(main_frame)
        base_dir_frame.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        base_dir_frame.columnconfigure(0, weight=1)
        
        self.entries['base_dir'] = ttk.Entry(base_dir_frame)
        self.entries['base_dir'].grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.entries['base_dir'].insert(0, self.config_manager.get_server_config().get('base_dir', r'E:\BiometricServer'))
        
        browse_btn = ttk.Button(base_dir_frame, text="Browse", command=self.browse_directory, width=10)
        browse_btn.grid(row=0, column=1, padx=(5, 0))
        current_row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=2, 
                                                            sticky=(tk.W, tk.E), pady=15)
        current_row += 1
        
        # ===== ERP Settings =====
        erp_label = ttk.Label(main_frame, text="ERP Settings", 
                             font=('Segoe UI', 11, 'bold'))
        erp_label.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        current_row += 1
        
        # ERP URL
        ttk.Label(main_frame, text="ERP URL:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['erp_url'] = ttk.Entry(main_frame, width=40)
        self.entries['erp_url'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['erp_url'].insert(0, self.config_manager.get_erp_config().get('url', 'http://192.168.0.61:8000'))
        current_row += 1
        
        # ERP API Endpoint
        ttk.Label(main_frame, text="API Endpoint:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['erp_api'] = ttk.Entry(main_frame, width=40)
        self.entries['erp_api'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['erp_api'].insert(0, 
            self.config_manager.get_erp_config().get('api_endpoint', 
            'api/method/sil.test.biometric_to_erp.add_checkin'))
        current_row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=2, 
                                                            sticky=(tk.W, tk.E), pady=15)
        current_row += 1
        
        # ===== Retry Settings =====
        retry_label = ttk.Label(main_frame, text="Retry Settings", 
                               font=('Segoe UI', 11, 'bold'))
        retry_label.grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        current_row += 1
        
        # Retry Interval
        ttk.Label(main_frame, text="Retry Interval (seconds):").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['retry_interval'] = ttk.Entry(main_frame, width=40)
        self.entries['retry_interval'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['retry_interval'].insert(0, 
            str(self.config_manager.get_retry_config().get('interval_seconds', 180)))
        current_row += 1
        
        # Max Attempts
        ttk.Label(main_frame, text="Max Retry Attempts:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['max_attempts'] = ttk.Entry(main_frame, width=40)
        self.entries['max_attempts'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['max_attempts'].insert(0, 
            str(self.config_manager.get_retry_config().get('max_attempts', 10)))
        current_row += 1
        
        # Max Hours
        ttk.Label(main_frame, text="Max Retry Hours:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.entries['max_hours'] = ttk.Entry(main_frame, width=40)
        self.entries['max_hours'].grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.entries['max_hours'].insert(0, 
            str(self.config_manager.get_retry_config().get('max_hours', 24)))
        current_row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=current_row, column=0, columnspan=2, pady=(20, 0))
        
        save_btn = ttk.Button(button_frame, text="Save", command=self.save_settings, width=15)
        save_btn.grid(row=0, column=0, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel, width=15)
        cancel_btn.grid(row=0, column=1, padx=5)
        
        reset_btn = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults, width=15)
        reset_btn.grid(row=0, column=2, padx=5)
    
    def browse_directory(self):
        """Open directory browser"""
        current_dir = self.entries['base_dir'].get()
        directory = filedialog.askdirectory(
            title="Select Base Directory",
            initialdir=current_dir if os.path.exists(current_dir) else "/"
        )
        if directory:
            self.entries['base_dir'].delete(0, tk.END)
            self.entries['base_dir'].insert(0, directory)
    
    def validate_settings(self):
        """Validate all settings before saving"""
        errors = []
        
        # Validate port
        try:
            port = int(self.entries['port'].get())
            if port < 1 or port > 65535:
                errors.append("Port must be between 1 and 65535")
        except ValueError:
            errors.append("Port must be a valid number")
        
        # Validate retry interval
        try:
            interval = int(self.entries['retry_interval'].get())
            if interval < 1:
                errors.append("Retry interval must be at least 1 second")
        except ValueError:
            errors.append("Retry interval must be a valid number")
        
        # Validate max attempts
        try:
            attempts = int(self.entries['max_attempts'].get())
            if attempts < 1:
                errors.append("Max retry attempts must be at least 1")
        except ValueError:
            errors.append("Max retry attempts must be a valid number")
        
        # Validate max hours
        try:
            hours = int(self.entries['max_hours'].get())
            if hours < 1:
                errors.append("Max retry hours must be at least 1")
        except ValueError:
            errors.append("Max retry hours must be a valid number")
        
        # Validate base directory
        base_dir = self.entries['base_dir'].get().strip()
        if not base_dir:
            errors.append("Base directory cannot be empty")
        
        # Validate ERP URL
        erp_url = self.entries['erp_url'].get().strip()
        if not erp_url.startswith(('http://', 'https://')):
            errors.append("ERP URL must start with http:// or https://")
        
        return errors
    
    def save_settings(self):
        """Save settings to configuration"""
        # Validate first
        errors = self.validate_settings()
        if errors:
            messagebox.showerror("Validation Error", 
                               "Please fix the following errors:\n\n" + "\n".join(errors))
            return
        
        try:
            # Update server config
            self.config_manager.update_server_config(
                host=self.entries['host'].get().strip(),
                port=int(self.entries['port'].get()),
                base_dir=self.entries['base_dir'].get().strip()
            )
            
            # Update ERP config
            self.config_manager.update_erp_config(
                url=self.entries['erp_url'].get().strip(),
                api_endpoint=self.entries['erp_api'].get().strip()
            )
            
            # Update retry config
            self.config_manager.update_retry_config(
                interval_seconds=int(self.entries['retry_interval'].get()),
                max_attempts=int(self.entries['max_attempts'].get()),
                max_hours=int(self.entries['max_hours'].get())
            )
            
            self.result = True
            messagebox.showinfo("Success", 
                              "Settings saved successfully!\n\nChanges will take effect on next server restart.")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        result = messagebox.askyesno("Confirm Reset", 
                                     "Are you sure you want to reset all settings to defaults?")
        if result:
            defaults = self.config_manager.get_default_config()
            
            # Update entries with defaults
            self.entries['host'].delete(0, tk.END)
            self.entries['host'].insert(0, defaults['server']['host'])
            
            self.entries['port'].delete(0, tk.END)
            self.entries['port'].insert(0, str(defaults['server']['port']))
            
            self.entries['base_dir'].delete(0, tk.END)
            self.entries['base_dir'].insert(0, defaults['server']['base_dir'])
            
            self.entries['erp_url'].delete(0, tk.END)
            self.entries['erp_url'].insert(0, defaults['erp']['url'])
            
            self.entries['erp_api'].delete(0, tk.END)
            self.entries['erp_api'].insert(0, defaults['erp']['api_endpoint'])
            
            self.entries['retry_interval'].delete(0, tk.END)
            self.entries['retry_interval'].insert(0, str(defaults['retry']['interval_seconds']))
            
            self.entries['max_attempts'].delete(0, tk.END)
            self.entries['max_attempts'].insert(0, str(defaults['retry']['max_attempts']))
            
            self.entries['max_hours'].delete(0, tk.END)
            self.entries['max_hours'].insert(0, str(defaults['retry']['max_hours']))
    
    def cancel(self):
        """Cancel and close dialog"""
        self.result = False
        self.dialog.destroy()