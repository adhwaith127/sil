import json
import os
from typing import Dict, Any

class ConfigurationManager:
    """Manages application configuration with GUI integration"""
    
    def __init__(self, config_file_path="config.json"):
        self.config_file = config_file_path
        self.default_config = {
            # Server Configuration
            "server": {
                "host": "0.0.0.0",
                "port": 8190,
                "base_dir": "E:\\BiometricServer"
            },
            # ERP Configuration  
            "erp": {
                "url": "http://192.168.0.61:8000",
                "api_endpoint": "api/method/sil.test.biometric_to_erp.add_checkin"
            },
            # Retry Configuration
            "retry": {
                "interval_seconds": 180,
                "max_attempts": 10,
                "max_hours": 24
            },
            # Logging Configuration
            "logging": {
                "max_file_size_mb": 50,
                "backup_count": 7,
                "auto_scroll": True
            },
            # GUI Configuration
            "gui": {
                "window_width": 900,
                "window_height": 600,
                "theme": "default"
            }
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to handle new settings
                return self.merge_config(self.default_config, loaded_config)
            else:
                # Create default config file
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """Save configuration to file"""
        try:
            config_to_save = config if config else self.config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """Merge loaded config with defaults to handle missing keys"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, section: str, key: str, default=None):
        """Get configuration value"""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server-specific configuration"""
        return self.config.get("server", {})
    
    def get_erp_config(self) -> Dict[str, Any]:
        """Get ERP-specific configuration"""
        return self.config.get("erp", {})
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry-specific configuration"""
        return self.config.get("retry", {})
    
    def validate_config(self) -> tuple[bool, list]:
        """Validate configuration values"""
        errors = []
        
        # Validate server config
        server_config = self.get_server_config()
        port = server_config.get("port", 8190)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("Port must be between 1 and 65535")
        
        # Validate ERP URL
        erp_config = self.get_erp_config()
        erp_url = erp_config.get("url", "")
        if not erp_url.startswith(("http://", "https://")):
            errors.append("ERP URL must start with http:// or https://")
        
        # Validate retry settings
        retry_config = self.get_retry_config()
        retry_interval = retry_config.get("interval_seconds", 180)
        if not isinstance(retry_interval, int) or retry_interval < 30:
            errors.append("Retry interval must be at least 30 seconds")
        
        max_attempts = retry_config.get("max_attempts", 10)
        if not isinstance(max_attempts, int) or max_attempts < 1:
            errors.append("Max attempts must be at least 1")
        
        return len(errors) == 0, errors
