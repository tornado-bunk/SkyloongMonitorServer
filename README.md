<p align="center">
    <img src="/tastiera.ico" width="100">
</p>

<h1 align="center">Skyloong Monitor Server</h1>

A lightweight, cross-platform server application that monitors system resources and provides real-time CPU and memory usage data to Skyloong keyboard displays.

#### TESTED ONLY ON SKYLOONG GK104 PRO

## Features
- 🚀 **Real-time monitoring** of CPU and memory usage
- ⌨ **Data transmission** to compatible Skyloong keyboard displays
- 🖥 **System tray integration** for minimal desktop footprint
- 🌗 **Dark/light theme support**
- 🛠 **Debug mode** for troubleshooting
- 🔄 **Daemon mode** for automatic startup

---

## How It Works

### 🏗 Data Collection
The server uses `psutil` to collect real-time system information:
- **CPU usage percentage** across all cores
- **Memory usage percentage**

### 📡 Data Transmission
- **Connection Protocol:** The server listens on **TCP port 1648** and accepts connections from compatible keyboard devices.
- **Data Format:** System information is transmitted as an **8-byte data packet**:
  - **First 4 bytes:** CPU usage as a floating-point number
  - **Last 4 bytes:** Memory usage as a floating-point number

#### 🔄 Communication Flow:
1. **Server sends** the 8-byte data packet to connected clients
2. **Client responds** with a 1-byte acknowledgment
3. **Cycle repeats** approximately **2 times per second**

### 🤝 Client Handling
- Each client connection is handled in a **separate thread**
- The server can handle **multiple simultaneous connections** (MAX 5)
- When a client disconnects, **resources are properly cleaned up**

---

## Installation

### 🖥 Windows
1. **Download** the latest release from the [Releases](https://github.com/tornado-bunk/SkyloongMonitorServer/releases/tag/releasewlinux) page
2. **Run** the executable file `SkyloongServer.exe`

### 🐧Linux (Ubuntu and Debian derivates)
1. **Download** the latest release from the [Releases]([#](https://github.com/tornado-bunk/SkyloongMonitorServer/releases/tag/releasewlinux)) page
2. Make it executable:
   ```bash
   chmod +x SkyloongServer
   ```
3. Run the application:
   ```bash
   ./SkyloongServer
   ```
4. #### Recommended: Use daemon mode to avoid system tray issues:
   ```bash
   ./SkyloongServer --daemon
   ```

## Usage

- **Launch** the application
- **Click** "Start server" to begin monitoring and data transmission
- **Connect** your compatible Skyloong keyboard to receive the data
- **Monitor** active connections and system resource usage

### 🖥 Command-Line Arguments

- `--daemon`: Start the server minimized to system tray and automatically begin serving data

### ⌨ Keyboard Shortcuts

- **Ctrl+D**: Toggle daemon mode (start server and minimize to system tray)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a **Pull Request**.

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

