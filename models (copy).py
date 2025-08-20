# Service file for biometric attendance system
# Save this as: /etc/systemd/system/attendance-system.service

[Unit]
# What this service does (human description)
Description=Biometric Face Scanner Attendance System
# Wait for internet to be ready before starting
After=network-online.target
Wants=network-online.target

[Service]
# How to run the service
Type=simple

# The actual command to run your Python script
ExecStart=/usr/bin/python3 -u /opt/attendance-system/biometric_server_erp.py


# Which folder to run the script from
WorkingDirectory=/opt/attendance-system

# Which user account should run the script
User=attendance-user
Group=attendance-user

# What to do if script stops or crashes
Restart=always
RestartSec=5

# Don't let the script use too much computer resources
MemoryLimit=500M

# How systemd should log what the script does
StandardOutput=journal
StandardError=journal

[Install]
# When should this service start automatically
WantedBy=multi-user.target
