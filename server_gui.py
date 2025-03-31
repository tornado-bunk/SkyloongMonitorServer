import socket
import struct
import time
import threading
import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import sys
from PIL import Image, ImageTk, ImageDraw
import pystray
import io
import os

def resource_path(relative_path):
    """Ottiene il percorso assoluto alle risorse, funziona sia in sviluppo che in PyInstaller"""
    try:
        # PyInstaller crea una cartella temp e memorizza il percorso in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Server class for the Keyboard Data Server
# This class handles the server operations, including starting, stopping, and managing client connections.
class KeyboardDataServer:
    def __init__(self, host='0.0.0.0', port=1648, debug=False):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.running = False
        self.debug = debug
        self.server_thread = None
        self.on_log = None
        self.on_connection_change = None
        self.on_status_change = None
        self.on_system_stats = None
        
    def log(self, message, always_show=False):
        """Prints the message only if in debug mode or if always_show is True"""
        if self.debug or always_show:
            print(message)
            if self.on_log:
                self.on_log(message)
            
    def start(self):
        """Starts the server and listens for connections"""
        if self.running:
            return False
            
        try:
            # Create the server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            # Listen for incoming connections (max 5)
            self.server_socket.listen(5)
            self.running = True
            
            self.log(f"Server stared on {self.host}:{self.port}", always_show=True)
            
            if self.on_status_change:
                self.on_status_change(True)
                
            # Start the server thread
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            return True
                
        except Exception as e:
            self.log(f"Error during the starting of the server: {e}", always_show=True)
            if self.server_socket:
                self.server_socket.close()
            return False
    
    def run_server(self):
        """Main loop of the server"""
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
        
        # Update system stats periodically
        while self.running:
            # Send system stats to the GUI
            if self.on_system_stats:
                # Get CPU and memory usage
                cpu = self.get_cpu_percent()
                mem = self.get_memory_percent()
                self.on_system_stats(cpu, mem)
            # Sleep for a while before the next update
            time.sleep(0.5)
            
    def accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                # Set a timeout for the accept call
                self.server_socket.settimeout(1) 
                try:
                    # Accept a new client connection
                    client_socket, client_address = self.server_socket.accept()
                    self.log(f"New connection from {client_address}", always_show=True)
                    
                    # Start a new thread to handle the client
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Add the client to the list (not used, will be removed)
                    self.clients.append((client_socket, client_address))
                    
                    # Notify the GUI about the new connection
                    if self.on_connection_change:
                        self.on_connection_change(len(self.clients))
                
                # If no connection is accepted within the timeout, continue
                except socket.timeout:
                    continue
                    
            except Exception as e:
                # If the server is still running, log the error
                if self.running:
                    self.log(f"Error in accepting the connection: {e}")
    
    def handle_client(self, client_socket, client_address):
        """Handles communication with a connected client"""
        try:
            while self.running:
                # Generate the 8-byte data packet with real CPU and memory information (as in the original app)
                data = self.get_system_data_packet()
                
                # Send the data to the client
                client_socket.send(data)
                
                # Log the sent data (detailed only in debug mode)
                cpu_percent = self.get_cpu_percent()
                mem_percent = self.get_memory_percent()
                self.log(f"Data sent to: {client_address}: CPU: {cpu_percent}%, Memory: {mem_percent}%")
                
                # Wait for the client's response (ACK - 1 byte) (as in the original app)
                try:
                    client_socket.settimeout(1)
                    response = client_socket.recv(1)
                    if not response:
                        self.log(f"Client {client_address} disconnected", always_show=True)
                        break
                    
                    self.log(f"Ricevuto da {client_address}: {response.hex()}")
                except socket.timeout:
                    # If the client does not respond within the timeout, log the error
                    if not self.running:
                        break
                    continue
                
                time.sleep(0.3)
                
        except Exception as e:
            self.log(f"Error with the client {client_address}: {e}")
        finally:
            # Close the client socket and remove it from the list
            try:
                client_socket.close()
                if (client_socket, client_address) in self.clients:
                    self.clients.remove((client_socket, client_address))
                    
                    # Notify the GUI about the disconnection
                    if self.on_connection_change:
                        self.on_connection_change(len(self.clients))
            except:
                pass
            self.log(f"Connection with {client_address} closed", always_show=True)
    
    def get_cpu_percent(self):
        """Obtains the CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    def get_memory_percent(self):
        """Obtains the memory usage percentage"""
        return psutil.virtual_memory().percent
    
    def get_system_data_packet(self):
        """Generates an 8-byte data packet with CPU and memory information"""
        cpu_percent = self.get_cpu_percent() / 100.0
        mem_percent = self.get_memory_percent() / 100.0 
        
        packet = struct.pack('<ff', cpu_percent, mem_percent)
        return packet
    
    def stop(self):
        """Stops the server and closes all connections"""
        if not self.running:
            return
            
        self.running = False

        # Close all client connections
        for client_socket, _ in self.clients:
            try:
                client_socket.close()
            except:
                pass
        self.clients = []
        
        # Close the server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Notify the GUI about the server status change
        if self.on_status_change:
            self.on_status_change(False)
            
        # Notify the GUI about the disconnection
        if self.on_connection_change:
            self.on_connection_change(0)
            
        self.log("Server stopped", always_show=True)

# GUI class for the Keyboard Data Server
class ServerGUI:
    def __init__(self, root, daemon_mode=False):
        self.root = root
        self.root.title("Skyloong Display Server")
        self.root.geometry("400x450")
        self.root.minsize(400, 450)
        
        # Icon for the system tray
        self.icon_data = self.create_icon_image()
        self.icon_image = Image.open(io.BytesIO(self.icon_data))
        self.icon = None
        
        # Daemon mode flag
        self.daemon_mode = daemon_mode

        self.server = KeyboardDataServer()
        self.server.on_log = self.update_log
        self.server.on_connection_change = self.update_connection_status
        self.server.on_status_change = self.update_server_status
        self.server.on_system_stats = self.update_system_stats
        
        # Add keyboard shortcuts
        self.root.bind("<Control-d>", self.toggle_daemon_mode)  # Ctrl+D for daemon mode
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create layout
        self.setup_ui()
        
        # Configure the system tray
        self.setup_tray()
        
        # If starting in daemon mode, start server and minimize
        if self.daemon_mode:
            self.after_init_daemon_mode()
            
    def after_init_daemon_mode(self):
        """Actions to take after initialization when in daemon mode"""
        # Use after to ensure the window is fully loaded before we start the server
        self.root.after(100, lambda: self.start_server_and_minimize())
        
    def start_server_and_minimize(self):
        """Start the server and minimize to system tray"""
        if not self.server.running:
            self.server.debug = self.debug_var.get()
            if self.server.start():
                self.update_log("Server started in daemon mode")
                self.hide_window()
    
    def toggle_daemon_mode(self, event=None):
        """Toggle daemon mode (start server and minimize to tray)"""
        if not self.server.running:
            self.start_server_and_minimize()
        else:
            self.hide_window()
        return "break"  # Prevent the event from being processed further
    
    def create_icon_image(self):
        """Create the icon image for the system tray"""
        try:
            # Load the icon from the ICO file
            icon_path = resource_path("tastiera.ico")
            icon = Image.open(icon_path)
            # Use the first image if the ICO contains multiple formats
            if hasattr(icon, 'seek'):
                icon.seek(0)
                
            # Convert to bytes
            output = io.BytesIO()
            icon.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            print(f"Impossible to load the icon: {e}")
            # Fallback to a default icon (green circle)
            width = 64
            height = 64
            
            # Create a new image with a transparent background
            image = Image.new('RGBA', (width, height), color=(0,0,0,0))
            draw = ImageDraw.Draw(image)
            
            # Draw a green circle
            center = width // 2
            radius = width // 3
            draw.ellipse(
                [(center - radius, center - radius), 
                 (center + radius, center + radius)], 
                fill=(0, 180, 0, 255)
            )
            
            # Convert to bytes
            output = io.BytesIO()
            image.save(output, format='PNG')
            output.seek(0)
            
            return output.getvalue()
    
    def setup_tray(self):
        menu = (
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Start server', self.start_server),
            pystray.MenuItem('Stop server', self.stop_server),
            pystray.MenuItem('Exit', self.exit_application)
        )
        self.icon = pystray.Icon("skyloong_monitor", self.icon_image, "Skyloong Monitor", menu)
    
    def setup_ui(self):
        """Create the GUI layout"""
        # Principal frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame for controls
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=5)
        
        # Start and stop buttons
        self.start_button = ttk.Button(control_frame, text="Start server", command=self.start_server)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop server", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Checkbox for debug
        self.debug_var = tk.BooleanVar(value=False)
        self.debug_check = ttk.Checkbutton(control_frame, text="Debug", variable=self.debug_var,
                                         command=self.toggle_debug)
        self.debug_check.grid(row=0, column=2, padx=5, pady=5)
        
        # Checkbox for dark mode
        self.theme_var = tk.BooleanVar(value=False)
        self.theme_check = ttk.Checkbutton(control_frame, text="Dark Mode", variable=self.theme_var,
                                         command=self.toggle_theme)
        self.theme_check.grid(row=0, column=3, padx=5, pady=5)

        # Add help text for keyboard shortcuts
        help_text = "Shortcuts: Ctrl+D = Daemon Mode (Start and minimize)"
        ttk.Label(control_frame, text=help_text, font=("", 8)).grid(row=1, column=0, columnspan=4, pady=(0, 5))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        # Server status
        ttk.Label(status_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.server_status_label = ttk.Label(status_frame, text="Inactive", foreground="red")
        self.server_status_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Active connections
        ttk.Label(status_frame, text="Connections:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.connections_label = ttk.Label(status_frame, text="0")
        self.connections_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # System frame
        system_frame = ttk.LabelFrame(main_frame, text="System", padding=10)
        system_frame.pack(fill=tk.X, pady=5)
        
        # CPU
        ttk.Label(system_frame, text="CPU:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.cpu_var = tk.DoubleVar(value=0.0)
        self.cpu_progressbar = ttk.Progressbar(system_frame, orient=tk.HORIZONTAL, length=200, mode='determinate', 
                                             variable=self.cpu_var)
        self.cpu_progressbar.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        self.cpu_label = ttk.Label(system_frame, text="0%")
        self.cpu_label.grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Memory
        ttk.Label(system_frame, text="Memory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.mem_var = tk.DoubleVar(value=0.0)
        self.mem_progressbar = ttk.Progressbar(system_frame, orient=tk.HORIZONTAL, length=200, mode='determinate',
                                             variable=self.mem_var)
        self.mem_progressbar.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self.mem_label = ttk.Label(system_frame, text="0%")
        self.mem_label.grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Frame for logs
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Text area for logs
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollba rfor logs
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Start updating system stats
        self.update_system_stats_periodically()
    
    def update_system_stats_periodically(self):
        """Update system stats periodically"""
        if not hasattr(self, 'root') or not self.root:
            return
        
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        self.update_system_stats(cpu, mem)
        
        # Update the system stats every 500ms
        if not self.server.running:
            self.root.after(500, self.update_system_stats_periodically)
    
    def update_log(self, message):
        """Update the log text area with a new message"""
        if self.debug_var.get() or message.startswith("Server "):
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
    
    def update_connection_status(self, num_connections):
        """Update the connection status label with the number of active connections"""
        self.connections_label.config(text=str(num_connections))
    
    def update_server_status(self, is_running):
        """Update the server status label"""
        if is_running:
            self.server_status_label.config(text="Active", foreground="green")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.debug_check.config(state=tk.DISABLED)  
        else:
            self.server_status_label.config(text="Inactive", foreground="red")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.debug_check.config(state=tk.NORMAL)
    
    def update_system_stats(self, cpu, mem):
        """Update the CPU and memory usage labels and progress bars"""
        self.cpu_var.set(cpu)
        self.mem_var.set(mem)
        self.cpu_label.config(text=f"{cpu:.1f}%")
        self.mem_label.config(text=f"{mem:.1f}%")
    
    def start_server(self):
        """Start the server"""
        self.server.debug = self.debug_var.get()
        if self.server.start():
            self.update_log("Server started")
            if self.server.debug:
                self.update_log("DEBUG mode enabled")
        else:
            self.update_log("Error starting server")
            messagebox.showerror("Error", "Unable to start the server")
    
    def stop_server(self):
        """Stop the server"""
        self.server.stop()
        self.update_log("Server stopped")
    
    def toggle_debug(self):
        """Changes the debug mode"""
        self.server.debug = self.debug_var.get()
    
    def toggle_theme(self):
        """Changes the theme of the GUI"""
        self.is_dark_mode = self.theme_var.get()
        if self.is_dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    # ugly but it bothers my eyes less
    def apply_dark_theme(self):
        """Apply the dark theme"""
        self.root.configure(bg="#333333")
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure colors for dark mode
        style.configure("TFrame", background="#333333")
        style.configure("TLabelframe", background="#333333")
        style.configure("TLabelframe.Label", background="#333333", foreground="white")
        style.configure("TButton", background="#555555", foreground="white")
        style.configure("TCheckbutton", background="#333333", foreground="white")
        style.configure("TLabel", background="#333333", foreground="white")
        
        # Update colors of the text widget
        self.log_text.configure(bg="#222222", fg="#DDDDDD", insertbackground="white")
        
        # Update colors of the progress bars
        style.configure("Horizontal.TProgressbar", background="green", troughcolor="#555555")

    def apply_light_theme(self):
        """Apply the light theme"""
        self.root.configure(bg="SystemButtonFace")
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure colors for light mode
        style.configure("TFrame", background="SystemButtonFace")
        style.configure("TLabelframe", background="SystemButtonFace")
        style.configure("TLabelframe.Label", background="SystemButtonFace", foreground="black")
        style.configure("TButton", background="SystemButtonFace", foreground="black")
        style.configure("TCheckbutton", background="SystemButtonFace", foreground="black")
        style.configure("TLabel", background="SystemButtonFace", foreground="black")
        
        # Update colors of the text widget
        self.log_text.configure(bg="white", fg="black", insertbackground="black")
        
        # Update colors of the progress bars
        style.configure("Horizontal.TProgressbar", background="green", troughcolor="#E6E6E6")
    
    def on_close(self):
        """Handle the window close event"""
        if self.server.running:
            response = messagebox.askyesnocancel("Exit", "The server is still running.\n"
                                                        "Do you want to stop the server and exit?\n\n"
                                                        "Yes = Stop and exit\n"
                                                        "No = Minimize to system tray\n"
                                                        "Cancel = Return to the app")

            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.server.stop()
                self.exit_application()
            else:  # No
                self.hide_window()
        else:
            self.exit_application()
    
    def hide_window(self):
        """Hide the main window and show the system tray icon"""
        self.root.withdraw()
        if self.icon is not None and not self.icon.visible:
            threading.Thread(target=self.icon.run, daemon=True).start()
    
    def show_window(self):
        """Show the main window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def exit_application(self):
        """Exit the application"""
        if self.server.running:
            self.server.stop()
        
        if self.icon is not None and self.icon.visible:
            self.icon.stop()
            
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Skyloong Display Server")
    parser.add_argument("--daemon", action="store_true", help="Start server in daemon mode")
    args = parser.parse_args()
    
    root = tk.Tk()
    try:
        # Set the icon for the main window
        try:
            # Load the icon from the ICO file
            icon_path = resource_path("tastiera.ico")
            if sys.platform == 'win32':
                root.iconbitmap(icon_path)
            else:
                icon = Image.open(icon_path)
                if hasattr(icon, 'seek'):
                    icon.seek(0)
                photo = ImageTk.PhotoImage(icon)
                root.iconphoto(True, photo)
        except Exception as e:
            print(f"Unable to load icon: {e}")
            
        app = ServerGUI(root, daemon_mode=args.daemon)
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()