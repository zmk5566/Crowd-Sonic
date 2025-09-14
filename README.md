# CrowdSonic 🎵

**Professional Ultrasonic Visualizer** - Real-time visualization tool for ultrasonic data analysis

CrowdSonic is a cross-platform desktop application built with Electron that transforms ultrasonic data into intuitive real-time visualizations. It provides a professional-grade interface for connecting to headless_ultrasonic backends and displaying spectrum and spectrogram data in real-time.

## ✨ Key Features

### 🎯 Core Capabilities
- **Real-time Data Visualization** - Supports both frequency spectrum and spectrogram display modes
- **Professional Dark Theme** - Reduces eye strain during extended analysis sessions
- **Cross-platform Support** - Available for Windows, macOS, and Linux
- **Smart Connection Management** - Automatically manages local backend processes and supports remote connections
- **Live Status Monitoring** - Real-time display of FPS, peak frequency, amplitude, and data rates
- **Zero-config Setup** - Built-in headless_ultrasonic backend for immediate use

### 🔧 Technical Stack
- **Frontend**: React + TypeScript + Canvas API
- **Desktop Framework**: Electron with secure IPC
- **Backend**: Python FastAPI (headless_ultrasonic)
- **Communication**: HTTP REST + Server-Sent Events (SSE)
- **Build System**: Webpack + TypeScript

## 📥 Download & Installation

**Get the latest version now!**

Visit the [Releases page](../../releases) to download the installer for your platform:

### macOS
- **Apple Silicon (M1/M2/M3)**: `CrowdSonic-1.0.0-arm64.dmg`
- **Intel Processors**: `CrowdSonic-1.0.0-intel64.dmg`
- **Universal Build**: `CrowdSonic-1.0.0-mac.zip`

### Windows
- `CrowdSonic-1.0.0-win.exe` (Coming Soon)

### Linux
- `CrowdSonic-1.0.0-linux.AppImage` (Coming Soon)

> 💡 **Tip**: Simply download and run - no additional dependencies or configuration required!

## 🚀 Quick Start

### For End Users
1. Download the appropriate installer from [Releases](../../releases)
2. Install and launch CrowdSonic
3. The app will automatically start the built-in ultrasonic detection backend
4. Start visualizing ultrasonic data in real-time!

### For Developers

#### Prerequisites
- Node.js 18+
- Python 3.11+ (for backend development)

#### Development Setup
```bash
# Clone the repository
git clone https://github.com/your-repo/Simple-UAC-Visualizer.git
cd Simple-UAC-Visualizer/CrowdSonic

# Install dependencies
npm install

# Development mode (with file watching)
npm run dev
# In another terminal:
npm run electron:dev

# Or build and run
npm run build:dev
npm start
```

#### Building Releases
```bash
# Build production version
npm run build

# Create distributable packages
npm run dist                    # Current platform
npm run dist:mac-universal      # macOS Universal
npm run dist:mac-intel          # macOS Intel
npm run dist:mac-arm            # macOS Apple Silicon
```

## 📸 What You'll See

CrowdSonic provides an intuitive real-time data visualization interface:

- **Spectrum Analyzer** - Real-time frequency distribution display
- **Spectrogram View** - Waterfall-style time-frequency visualization
- **Status Dashboard** - Live system performance metrics
- **Connection Manager** - Easy switching between local and remote backends

## 🛠 Feature Deep Dive

### Data Visualization
- **Dual Display Modes**: Seamlessly switch between spectrum analysis and spectrogram views
- **Real-time Rendering**: High-performance Canvas-based real-time rendering
- **Adaptive Scaling**: Automatic range adjustment for optimal visual clarity

### Connection Management
- **Local-first**: Automatically launches and manages local Python backend
- **Remote Connectivity**: Connect to any headless_ultrasonic instance
- **Health Monitoring**: Continuous backend connection status monitoring

### User Experience
- **Professional Interface**: Inspired by professional audio software design principles
- **Instant Feedback**: Real-time visual feedback for all operations
- **Information Density**: Maximum data visibility in minimal space

## 🔄 Backend Integration

CrowdSonic seamlessly integrates with the headless_ultrasonic backend:

- **Zero-modification Integration**: Uses existing API endpoints without backend changes
- **SSE Streaming**: Real-time data via `/api/stream` endpoint
- **Process Management**: Automatic backend startup, monitoring, and shutdown
- **Error Recovery**: Smart reconnection and error handling mechanisms

## 🗺 Roadmap

### Immediate Goals
- [x] Windows and Linux releases
- [ ] Enhanced visualization options and controls
- [ ] Data export functionality
- [ ] Settings persistence

### Medium-term Goals
- [ ] Multi-language support (Chinese, English, Danish)

### Long-term Vision
- [ ] Mobile companion app (React Native)
- [ ] Cloud data synchronization
- [ ] Advanced data analysis tools (Machine learning enhanced)
- [ ] Data recording/retrival
- [ ] Team collaboration features

## 🤝 Contributing

We welcome community contributions! To get started:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support & Feedback

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

---

**CrowdSonic** - Making ultrasonic data visible and understandable 🎵
