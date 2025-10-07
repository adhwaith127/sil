import win32serviceutil
import win32service
import win32event
import sys
import os
import subprocess
import time
import logging
import signal
import threading


class BiometricWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BiometricServer"
    _svc_display_name_ = "Biometric WebSocket Server"
    _svc_description_ = "WebSocket server for biometric device communication with ERPNext integration"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True
        self.process = None
        
        # Set up service directory
        self.service_dir = r"C:\BiometricServer"
        
        # Set up logging for the service wrapper
        self.setup_service_logging()
        
    def setup_service_logging(self):
        """Set up logging for the Windows service wrapper"""
        log_file = os.path.join(self.service_dir, 'windows_service.log')
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - [SERVICE] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.logger = logging.getLogger('BiometricService')
        
    def SvcStop(self):
        """Stop the service"""
        self.logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False
        
        # Terminate the biometric server process
        if self.process:
            try:
                self.logger.info("Terminating biometric server process")
                self.process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                timeout = 10
                while timeout > 0 and self.process.poll() is None:
                    time.sleep(1)
                    timeout -= 1
                
                # Force kill if still running
                if self.process.poll() is None:
                    self.logger.warning("Force killing biometric server process")
                    self.process.kill()
                    
                self.logger.info("Biometric server process stopped")
                
            except Exception as e:
                self.logger.error(f"Error stopping biometric server process: {str(e)}")
        
    def SvcDoRun(self):
        """Main service execution"""
        try:
            self.logger.info("Biometric Windows Service starting")
            
            # Verify directory exists
            if not os.path.exists(self.service_dir):
                self.logger.error(f"Service directory does not exist: {self.service_dir}")
                return
            
            # Change to service directory
            os.chdir(self.service_dir)
            self.logger.info(f"Working directory set to: {self.service_dir}")
            
            # Verify main script exists
            main_script = os.path.join(self.service_dir, "biometric_to_server.py")
            if not os.path.exists(main_script):
                self.logger.error(f"Main script not found: {main_script}")
                return
                
            self.logger.info("Starting main service loop")
            
            # Main service loop with restart capability
            restart_delay = 5  # seconds
            max_restart_attempts = 10
            restart_count = 0
            
            while self.is_alive:
                try:
                    self.logger.info(f"Starting biometric server process (attempt {restart_count + 1})")
                    
                    # Start the biometric server process
                    self.process = subprocess.Popen([
                        sys.executable, 
                        main_script
                    ], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    cwd=self.service_dir
                    )
                    
                    self.logger.info(f"Biometric server process started with PID: {self.process.pid}")
                    restart_count = 0  # Reset counter on successful start
                    
                    # Monitor the process
                    while self.is_alive and self.process.poll() is None:
                        # Check every second if service should stop
                        time.sleep(1)
                    
                    # Process ended
                    if self.process.poll() is not None:
                        return_code = self.process.returncode
                        stdout, stderr = self.process.communicate()
                        
                        if return_code != 0:
                            self.logger.error(f"Biometric server exited with code {return_code}")
                            if stderr:
                                self.logger.error(f"STDERR: {stderr.decode('utf-8', errors='ignore')}")
                            if stdout:
                                self.logger.info(f"STDOUT: {stdout.decode('utf-8', errors='ignore')}")
                        else:
                            self.logger.info("Biometric server process ended normally")
                    
                    # If service is still supposed to be alive, restart
                    if self.is_alive:
                        restart_count += 1
                        
                        if restart_count <= max_restart_attempts:
                            self.logger.info(f"Restarting in {restart_delay} seconds...")
                            time.sleep(restart_delay)
                            
                            # Increase delay for subsequent restarts
                            restart_delay = min(restart_delay * 2, 60)  # Max 60 seconds
                        else:
                            self.logger.error(f"Maximum restart attempts ({max_restart_attempts}) reached. Stopping service.")
                            break
                            
                except Exception as e:
                    self.logger.error(f"Error in service loop: {str(e)}")
                    
                    if self.is_alive:
                        restart_count += 1
                        if restart_count <= max_restart_attempts:
                            self.logger.info(f"Retrying in {restart_delay} seconds...")
                            time.sleep(restart_delay)
                        else:
                            self.logger.error("Too many errors. Stopping service.")
                            break
                            
        except Exception as e:
            self.logger.error(f"Fatal error in service: {str(e)}")
        finally:
            self.logger.info("Biometric Windows Service stopped")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)


def install_service():
    """Install the Windows service"""
    try:
        win32serviceutil.InstallService(
            BiometricWindowsService,
            BiometricWindowsService._svc_name_,
            BiometricWindowsService._svc_display_name_,
            description=BiometricWindowsService._svc_description_
        )
        print(f"Service '{BiometricWindowsService._svc_display_name_}' installed successfully")
        print("Use 'net start BiometricServer' to start the service")
    except Exception as e:
        print(f"Failed to install service: {str(e)}")


def remove_service():
    """Remove the Windows service"""
    try:
        win32serviceutil.RemoveService(BiometricWindowsService._svc_name_)
        print(f"Service '{BiometricWindowsService._svc_display_name_}' removed successfully")
    except Exception as e:
        print(f"Failed to remove service: {str(e)}")


def start_service():
    """Start the Windows service"""
    try:
        win32serviceutil.StartService(BiometricWindowsService._svc_name_)
        print(f"Service '{BiometricWindowsService._svc_display_name_}' started successfully")
    except Exception as e:
        print(f"Failed to start service: {str(e)}")


def stop_service():
    """Stop the Windows service"""
    try:
        win32serviceutil.StopService(BiometricWindowsService._svc_name_)
        print(f"Service '{BiometricWindowsService._svc_display_name_}' stopped successfully")
    except Exception as e:
        print(f"Failed to stop service: {str(e)}")


def service_status():
    """Check service status"""
    try:
        import win32service
        scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        try:
            service_handle = win32service.OpenService(scm, BiometricWindowsService._svc_name_, win32service.SERVICE_QUERY_STATUS)
            try:
                status = win32service.QueryServiceStatusEx(service_handle)
                state = status['CurrentState']
                
                states = {
                    win32service.SERVICE_STOPPED: "STOPPED",
                    win32service.SERVICE_START_PENDING: "START PENDING",
                    win32service.SERVICE_STOP_PENDING: "STOP PENDING",
                    win32service.SERVICE_RUNNING: "RUNNING",
                    win32service.SERVICE_CONTINUE_PENDING: "CONTINUE PENDING",
                    win32service.SERVICE_PAUSE_PENDING: "PAUSE PENDING",
                    win32service.SERVICE_PAUSED: "PAUSED"
                }
                
                print(f"Service Status: {states.get(state, 'UNKNOWN')}")
                
            finally:
                win32service.CloseServiceHandle(service_handle)
        finally:
            win32service.CloseServiceHandle(scm)
    except Exception as e:
        print(f"Failed to get service status: {str(e)}")


def show_help():
    """Show help message"""
    print("""
Biometric Windows Service Management

Commands:
  install    - Install the Windows service
  remove     - Remove the Windows service  
  start      - Start the service
  stop       - Stop the service
  restart    - Restart the service
  status     - Show service status
  debug      - Run in debug mode (console)
  help       - Show this help message

Examples:
  python biometric_windows_service.py install
  python biometric_windows_service.py start
  python biometric_windows_service.py status
  python biometric_windows_service.py debug

Service Details:
  Name: BiometricServer
  Display Name: Biometric WebSocket Server  
  Directory: C:\\BiometricServer
  Main Script: biometric_to_server.py
    """)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Default behavior - let Windows service framework handle
        win32serviceutil.HandleCommandLine(BiometricWindowsService)
    else:
        command = sys.argv[1].lower()
        
        if command == 'install':
            install_service()
        elif command == 'remove':
            remove_service()
        elif command == 'start':
            start_service()
        elif command == 'stop':
            stop_service()
        elif command == 'restart':
            stop_service()
            time.sleep(2)
            start_service()
        elif command == 'status':
            service_status()
        elif command == 'debug':
            # Run in debug mode (console)
            print("Running in debug mode - Press Ctrl+C to stop")
            service = BiometricWindowsService([])
            service.SvcDoRun()
        elif command == 'help':
            show_help()
        else:
            print(f"Unknown command: {command}")
            show_help()