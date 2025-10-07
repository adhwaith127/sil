#!/usr/bin/env python3
"""
Configuration Manager for Biometric Server
Handles loading, saving, and accessing configuration settings
"""

import json
import os
from typing import Dict, Any


class ConfigurationManager:
    """Manages application configuration with JSON file storage"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file, create default if not exists"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
                return self.get_default_config()
        else:
            # Create default config file
            default_config = self.get_default_config()
            self.save_config(default_config)
            return default_config
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8190,
                "base_dir": r"E:\BiometricServer"
            },
            "erp": {
                "url": "http://192.168.0.61:8000",
                "api_endpoint": "api/method/sil.test.biometric_to_erp.add_checkin"
            },
            "retry": {
                "interval_seconds": 180,
                "max_attempts": 10,
                "max_hours": 24
            },
            "gui": {
                "window_width": 950,
                "window_height": 650,
                "auto_scroll": True
            }
        }
    
    def save_config(self, config: Dict[str, Any] = None):
        """Save configuration to JSON file"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration section"""
        return self.config.get("server", {})
    
    def get_erp_config(self) -> Dict[str, Any]:
        """Get ERP configuration section"""
        return self.config.get("erp", {})
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration section"""
        return self.config.get("retry", {})
    
    def get_gui_config(self) -> Dict[str, Any]:
        """Get GUI configuration section"""
        return self.config.get("gui", {})
    
    def update_server_config(self, **kwargs):
        """Update server configuration"""
        if "server" not in self.config:
            self.config["server"] = {}
        self.config["server"].update(kwargs)
        self.save_config()
    
    def update_erp_config(self, **kwargs):
        """Update ERP configuration"""
        if "erp" not in self.config:
            self.config["erp"] = {}
        self.config["erp"].update(kwargs)
        self.save_config()
    
    def update_retry_config(self, **kwargs):
        """Update retry configuration"""
        if "retry" not in self.config:
            self.config["retry"] = {}
        self.config["retry"].update(kwargs)
        self.save_config()
    
    def update_gui_config(self, **kwargs):
        """Update GUI configuration"""
        if "gui" not in self.config:
            self.config["gui"] = {}
        self.config["gui"].update(kwargs)
        self.save_config()