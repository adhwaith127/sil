import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

class SettingsDialog:
    """Configuration settings dialog window"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.dialog = None
        self.vars = {}
        
    def show(self):
        """Show the settings dialog"""
        # Create modal dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Server Configuration")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        
        # Make it modal
        self.dialog.grab_set()
        self.dialog.transient(self.parent)
        
        # Center the dialog
        self.center_dialog()
        
        # Setup the interface
        self.setup_interface()
        
        # Load current values
        self.load_current_values()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def center_dialog(self):
        """Center the dialog on parent window"""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (600 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
    
    def setup_interface(self):
        """Setup the dialog interface"""
        # Main container with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Server Settings Tab
        server_frame = ttk.Frame(notebook, padding="15")
        notebook.add(server_frame, text="Server Settings")
        self.setup_server_tab(server_frame)
        
        # ERP Settings Tab
        erp_frame = ttk.Frame(notebook, padding="15")
        notebook.add(erp_frame, text="ERP Settings")
        self.setup_erp_tab(erp_frame)
        
        # Retry Settings Tab
        retry_frame = ttk.Frame(notebook, padding="15")
        notebook.add(retry_frame, text="Retry Settings")
        self.setup_retry_tab(retry_frame)
        
        # Paths Settings Tab
        paths_frame = ttk.Frame(notebook, padding="15")
        notebook.add(paths_frame, text="Paths & Storage")
        self.setup_paths_tab(paths_frame)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Buttons
        ttk.Button(button_frame, text="Save", command=self.save_settings, 
                  width=12).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel, 
                  width=12).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults, 
                  width=15).pack(side=tk.LEFT)
    
    def setup_server_tab(self, parent):
        """Setup server configuration tab"""
        # Host settings
        ttk.Label(parent, text="Server Host:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        host_frame = ttk.Frame(parent)
        host_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.vars['host'] = tk.StringVar()
        host_entry = ttk.Entry(host_frame, textvariable=self.vars['host'], width=20)
        host_entry.pack(side=tk.LEFT)
        
        ttk.Label(host_frame, text="(0.0.0.0 = listen on all interfaces)", 
                 font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Port settings
        ttk.Label(parent, text="Server Port:", font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        port_frame = ttk.Frame(parent)
        port_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.vars['port'] = tk.IntVar()
        port_spinbox = ttk.Spinbox(port_frame, from_=1024, to=65535, 
                                  textvariable=self.vars['port'], width=10)
        port_spinbox.pack(side=tk.LEFT)
        
        ttk.Label(port_frame, text="(1024-65535, avoid common ports)", 
                 font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Test connection button
        ttk.Button(parent, text="Test Port Availability", 
                  command=self.test_port).grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
    
    def setup_erp_tab(self, parent):
        """Setup ERP configuration tab"""
        # ERP URL
        ttk.Label(parent, text="ERP Server URL:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.vars['erp_url'] = tk.StringVar()
        erp_entry = ttk.Entry(parent, textvariable=self.vars['erp_url'], width=50)
        erp_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(parent, text="Example: http://192.168.0.61:8000", 
                 font=('Segoe UI', 8)).grid(row=2, column=0, sticky=tk.W, pady=(0, 15))
        
        # API Endpoint
        ttk.Label(parent, text="API Endpoint:", font=('Segoe UI', 10, 'bold')).grid(
            row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        self.vars['erp_api'] = tk.StringVar()
        api_entry = ttk.Entry(parent, textvariable=self.vars['erp_api'], width=50)
        api_entry.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Test connection button
        ttk.Button(parent, text="Test ERP Connection", 
                  command=self.test_erp_connection).grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
    
    def setup_retry_tab(self, parent):
        """Setup retry configuration tab"""
        # Retry interval
        ttk.Label(parent, text="Retry Interval (seconds):", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.vars['retry_interval'] = tk.IntVar()
        interval_spinbox = ttk.Spinbox(parent, from_=30, to=3600, 
                                      textvariable=self.vars['retry_interval'], width=10)
        interval_spinbox.grid(row=1, column=0, sticky=tk.W, pady=(0, 15))
        
        ttk.Label(parent, text="How often to retry failed records", 
                 font=('Segoe UI', 8)).grid(row=2, column=0, sticky=tk.W, pady=(0, 15))
        
        # Max attempts
        ttk.Label(parent, text="Maximum Retry Attempts:", font=('Segoe UI', 10, 'bold')).grid(
            row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        self.vars['max_attempts'] = tk.IntVar()
        attempts_spinbox = ttk.Spinbox(parent, from_=1, to=50, 
                                      textvariable=self.vars['max_attempts'], width=10)
        attempts_spinbox.grid(row=4, column=0, sticky=tk.W, pady=(0, 15))
        
        # Max hours
        ttk.Label(parent, text="Maximum Retry Hours:", font=('Segoe UI', 10, 'bold')).grid(
            row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        self.vars['max_hours'] = tk.IntVar()
        hours_spinbox = ttk.Spinbox(parent, from_=1, to=168, 
                                   textvariable=self.vars['max_hours'], width=10)
        hours_spinbox.grid(row=6, column=0, sticky=tk.W, pady=(0, 15))
    
    def setup_paths_tab(self, parent):
        """Setup paths configuration tab"""
        # Base directory
        ttk.Label(parent, text="Base Directory:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        path_frame = ttk.Frame(parent)
        path_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        path_frame.columnconfigure(0, weight=1)
        
        self.vars['base_dir'] = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.vars['base_dir'])
        path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(path_frame, text="Browse...", 
                  command=self.browse_directory).grid(row=0, column=1)
        
        # Info about subdirectories
        info_text = """The following subdirectories will be created automatically:
• logs/ - Server and attendance logs
• database/ - SQLite queue database  
• queue/ - Temporary queue files
• error_logs/ - Error-specific logs"""
        
        ttk.Label(parent, text=info_text, font=('Segoe UI', 8), 
                 justify=tk.LEFT).grid(row=2, column=0, columnspan=2, 
                                      sticky=tk.W, pady=(0, 15))
    
    def load_current_values(self):
        """Load current configuration values into the form"""
        server_config = self.config_manager.get_server_config()
        erp_config = self.config_manager.get_erp_config()
        retry_config = self.config_manager.get_retry_config()
        
        self.vars['host'].set(server_config.get('host', '0.0.0.0'))
        self.vars['port'].set(server_config.get('port', 8190))
        self.vars['base_dir'].set(server_config.get('base_dir', 'E:\\BiometricServer'))
        
        self.vars['erp_url'].set(erp_config.get('url', 'http://192.168.0.61:8000'))
        self.vars['erp_api'].set(erp_config.get('api_endpoint', 'api/method/sil.test.biometric_to_erp.add_checkin'))
        
        self.vars['retry_interval'].set(retry_config.get('interval_seconds', 180))
        self.vars['max_attempts'].set(retry_config.get('max_attempts', 10))
        self.vars['max_hours'].set(retry_config.get('max_hours', 24))
    
    def test_port(self):
        """Test if the specified port is available"""
        import socket
        try:
            port = self.vars['port'].get()
            host = self.vars['host'].get()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host if host != '0.0.0.0' else 'localhost', port))
            sock.close()
            
            if result == 0:
                messagebox.showwarning("Port Test", f"Port {port} is already in use!")
            else:
                messagebox.showinfo("Port Test", f"Port {port} is available!")
        except Exception as e:
            messagebox.showerror("Port Test Error", f"Error testing port: {e}")
    
    def test_erp_connection(self):
        """Test ERP server connectivity"""
        import requests
        try:
            url = self.vars['erp_url'].get()
            if not url:
                messagebox.showwarning("ERP Test", "Please enter ERP URL first")
                return
                
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("ERP Test", "ERP server is reachable!")
            else:
                messagebox.showwarning("ERP Test", f"ERP server returned status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("ERP Test Error", f"Cannot reach ERP server: {e}")
    
    def browse_directory(self):
        """Browse for base directory"""
        directory = filedialog.askdirectory(
            title="Select Base Directory for Biometric Server",
            initialdir=self.vars['base_dir'].get()
        )
        if directory:
            self.vars['base_dir'].set(directory)
    
    def reset_defaults(self):
        """Reset all values to defaults"""
        result = messagebox.askyesno("Reset Defaults", 
                                   "Reset all settings to default values?")
        if result:
            defaults = self.config_manager.default_config
            
            self.vars['host'].set(defaults['server']['host'])
            self.vars['port'].set(defaults['server']['port'])
            self.vars['base_dir'].set(defaults['server']['base_dir'])
            
            self.vars['erp_url'].set(defaults['erp']['url'])
            self.vars['erp_api'].set(defaults['erp']['api_endpoint'])
            
            self.vars['retry_interval'].set(defaults['retry']['interval_seconds'])
            self.vars['max_attempts'].set(defaults['retry']['max_attempts'])
            self.vars['max_hours'].set(defaults['retry']['max_hours'])
    
    def save_settings(self):
        """Save the settings and close dialog"""
        try:
            # Update configuration
            self.config_manager.set('server', 'host', self.vars['host'].get())
            self.config_manager.set('server', 'port', self.vars['port'].get())
            self.config_manager.set('server', 'base_dir', self.vars['base_dir'].get())
            
            self.config_manager.set('erp', 'url', self.vars['erp_url'].get())
            self.config_manager.set('erp', 'api_endpoint', self.vars['erp_api'].get())
            
            self.config_manager.set('retry', 'interval_seconds', self.vars['retry_interval'].get())
            self.config_manager.set('retry', 'max_attempts', self.vars['max_attempts'].get())
            self.config_manager.set('retry', 'max_hours', self.vars['max_hours'].get())
            
            # Validate configuration
            valid, errors = self.config_manager.validate_config()
            if not valid:
                error_msg = "Configuration errors:\n" + "\n".join(errors)
                messagebox.showerror("Configuration Error", error_msg)
                return
            
            # Save to file
            if self.config_manager.save_config():
                messagebox.showinfo("Settings Saved", 
                                   "Configuration saved successfully!\n\nRestart the server for changes to take effect.")
                self.dialog.destroy()
            else:
                messagebox.showerror("Save Error", "Failed to save configuration file!")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving settings: {e}")
    
    def cancel(self):
        """Cancel and close dialog"""
        self.dialog.destroy()
