# CrowdSonic 🎵

**Professional Ultrasonic Visualizer** - Transform headless_ultrasonic into a professional Electron application

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- Python 3.11+ (for backend)
- The `headless_ultrasonic` backend running

### Development

```bash
# Install dependencies
npm install

# Build the application
npm run build:dev

# Start the application
npm start

# Development mode (watch for changes)
npm run dev
# In another terminal:
npm run electron:dev
```

## ✨ Features

### Current Implementation (Phase 1)
- ✅ **Professional Dark UI** - Modern, clean interface inspired by professional audio tools
- ✅ **Real-time Connection Management** - Connect to local or remote headless_ultrasonic servers
- ✅ **Dual Visualization Support** - Toggle between Frequency Spectrum and Spectrogram views
- ✅ **Live Status Monitoring** - FPS, peak frequency, amplitude, and data rate tracking
- ✅ **Python Backend Integration** - Automatic management of headless_ultrasonic subprocess
- ✅ **Cross-platform Support** - Built with Electron for Windows, macOS, and Linux

### Architecture
```
CrowdSonic/
├── src/
│   ├── main/           # Electron main process
│   │   ├── main.ts     # App entry point + Python subprocess management
│   │   └── preload.ts  # Secure renderer communication
│   └── renderer/       # React frontend
│       ├── components/ # UI components (Layout, ControlPanel, Canvas, StatusBar)
│       ├── services/   # API client for backend communication
│       └── styles/     # Professional dark theme CSS
├── public/
│   └── index.html      # Base HTML template
└── dist/              # Built application
```

### Technical Stack
- **Frontend**: React + TypeScript + Canvas API
- **Desktop**: Electron with secure IPC
- **Backend**: Python FastAPI (headless_ultrasonic)
- **Communication**: HTTP REST + Server-Sent Events (SSE)
- **Build**: Webpack + TypeScript

## 🎯 Roadmap

### Phase 2: Enhanced Visualization
- [ ] Advanced Canvas rendering with optimized spectrum display
- [ ] Real-time spectrogram with scrolling waterfall
- [ ] Multiple chart types and display options
- [ ] Zoom and pan controls for detailed analysis

### Phase 3: Internationalization
- [ ] i18next integration
- [ ] Support for English, Chinese (中文), and Danish (Dansk)
- [ ] Language switcher in settings

### Phase 4: Advanced Features
- [ ] Remote device management
- [ ] Settings persistence
- [ ] Data export capabilities
- [ ] Custom themes and layouts

### Phase 5: Mobile Support
- [ ] React Native companion app
- [ ] Cross-platform component sharing
- [ ] iOS and Android viewers

## 🔧 Development

### Project Structure

```
└── CrowdSonic/
    ├── Backend Communication    # Python subprocess + HTTP/SSE
    ├── Professional UI         # Dark theme, status bars, controls
    ├── Canvas Visualization     # Real-time frequency/spectrogram display
    ├── Connection Management    # Local/remote backend switching
    └── Cross-platform Support  # Electron + future React Native
```

### Backend Integration

CrowdSonic automatically manages the Python backend:

1. **Startup**: Launches `headless_ultrasonic` as subprocess
2. **Connection**: Tests health endpoint (`/api/health`)
3. **Communication**: Uses existing REST API + SSE streams
4. **Shutdown**: Gracefully terminates Python process

### Available Scripts

```bash
npm run build       # Production build
npm run build:dev   # Development build
npm run start       # Start Electron app
npm run dev         # Watch mode for development
npm run clean       # Clean build directory
npm run dist        # Create distributable package (future)
```

## 🤝 Integration with headless_ultrasonic

CrowdSonic is designed to work seamlessly with the existing `headless_ultrasonic` backend:

- **Zero Backend Changes**: Uses existing API endpoints
- **SSE Streaming**: Connects to `/api/stream` for real-time data
- **Remote Capable**: Can connect to any headless_ultrasonic instance
- **Local First**: Automatically starts local backend if available

## 📦 Building for Distribution

*Coming in Phase 4*

```bash
npm run dist
```

## 🎨 Design Philosophy

CrowdSonic follows professional audio software design principles:

- **Dark Theme**: Reduces eye strain during long analysis sessions
- **Information Density**: Maximum data in minimal space
- **Real-time Feedback**: Immediate visual feedback for all operations
- **Professional Layout**: Familiar layout for audio engineers and researchers

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

**CrowdSonic** - Transforming ultrasonic visualization from headless to professional 🎵