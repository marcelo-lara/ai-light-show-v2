# Legacy Definition

## 🎯 Overview

AI Light Show is a proof-of-concept system that demonstrates how artificial intelligence can be used to create dynamic lighting displays synchronized to music. The system analyzes audio files to extract musical features like beats, tempo, key signatures, and chord progressions, then uses this information to generate appropriate lighting effects through DMX-controlled fixtures.

## 🏗️ Architecture

### Backend (Python/FastAPI)

The backend is built with **FastAPI** and provides a comprehensive set of APIs for audio analysis, AI processing, and DMX control.


#### Core Components

- **FastAPI Application** (`backend/app.py`): Main application entry point with CORS configuration and route management
- **DMX Controller** (`backend/services/dmx_dispatcher.py`): Art-Net DMX protocol implementation for lighting fixture control
- **Timeline Engine** (`backend/timeline_engine.py`): Real-time cue execution and playback synchronization
- **Render Engine** (`backend/render_engine.py`): DMX universe rendering and fixture state management

#### AI & Audio Analysis

- **Essentia Analysis** (`backend/ai/essentia_analysis.py`): Advanced audio feature extraction including:
  - Beat detection and tempo analysis
  - Chord progression recognition
  - Key signature detection
  - Harmonic content analysis (HPCP)
  - Musical structure segmentation

- **Demucs Audio Separation** (`backend/ai/demucs_split.py`): Source separation for isolating drums, vocals, and instruments

- **Drum Classification** (`backend/ai/drums_infer.py`): ML-based drum pattern recognition and classification


#### Data Models & Services

- **Application State** (`backend/models/app_state.py`): Centralized state management
- **Song Metadata** (`backend/models/song_metadata.py`): Structured audio analysis data
- **Cue Service** (`backend/services/cue_service.py`): Lighting cue management and persistence
- **WebSocket Service** (`backend/services/websocket_service.py`): Real-time client communication

#### API Routes

- **DMX Router** (`backend/routers/dmx.py`): Fixture control and DMX universe management
- **Songs Router** (`backend/routers/songs.py`): Audio file management and analysis
- **AI Router** (`backend/routers/ai_router.py`): AI-powered lighting generation
- **WebSocket Router** (`backend/routers/websocket.py`): Real-time communication

### Frontend (Preact/Vite)

The frontend is a modern single-page application built with **Preact** and **Vite**, providing an intuitive interface for lighting design and control.
The communication with the backend is entirely managed by WebSockets.

#### Key Components

- **Audio Player** (`AudioPlayer.jsx`): Waveform visualization and playback control using WaveSurfer.js
- **Chat Assistant** (`ChatAssistant.jsx`): Natural language interface for lighting control
- **Song Analysis** (`SongAnalysis.jsx`): Visual representation of audio analysis results
- **Fixtures Control** (`Fixtures.jsx`, `FixtureCard.jsx`): Manual fixture control and monitoring
- **Actions Sheet** (`ActionsSheet.jsx`): Timeline-based fixture actions editing and visualization
- **Arrangement View** (`SongArrangement.jsx`): Musical structure visualization
- **Chord Display** (`ChordsCard.jsx`): Real-time chord progression display

#### Technology Stack

- **Preact**: Lightweight React alternative for component-based UI
- **Vite**: Fast build tool and development server
- **TailwindCSS**: Utility-first CSS framework for styling
- **WaveSurfer.js**: Audio waveform visualization and interaction
- **Socket.IO**: Real-time WebSocket communication with backend
- **React Toastify**: User notification system

## 🎵 Features

### Audio Analysis
- **Beat Detection**: Precise beat tracking using multi-feature analysis
- **Tempo Analysis**: BPM detection and tempo stability analysis
- **Chord Recognition**: Chord detection and progression identification
- **Key Detection**: Musical key and scale recognition
- **Structure Analysis**: Automatic detection of verses, choruses, bridges, etc.
- **Source Separation**: Isolation of drums, vocals, and instruments

### AI-Powered Lighting
- **Natural Language Control**: Create lighting cues using plain English commands
- **Intelligent Suggestions**: AI-generated lighting recommendations based on musical content
- **Pattern Recognition**: Automatic detection of musical patterns for synchronized effects
- **Beat Synchronization**: Precise timing alignment with musical beats

### DMX Control
- **Art-Net Protocol**: Industry-standard DMX over Ethernet
- **Multi-Fixture Support**: Control various lighting fixture types (RGB and moving heads)
- **Real-time Rendering**: 44 FPS DMX universe updates
- **Fixture Effects Rendering**: Creates dmx frames from named actions (e.g. flash -> set rbg to 255, then fade to 0 in 2 seconds)
- **Chase Sequences**: Complex multi-fixture actions to create lighting patterns (e.g. left to right blue chaser)

### User Interface
- **Visual Timeline**: Drag-and-drop cue editing with waveform display
- **Real-time Monitoring**: Live fixture status and DMX channel values
- **Interactive Waveform**: Click-to-seek audio navigation
- **Responsive Design**: Works on desktop and tablet devices
