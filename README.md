<div align="center">

# Trafficly
### Smart Traffic Enforcement Platform

**Automated multi-class traffic violation detection, ANPR plate recognition, and e-challan generation**

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Custom%20Trained-00FFFF?style=flat-square)](https://ultralytics.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Engineered by [Vanshul Lalwani](https://github.com/vanshul04) · Bengaluru Traffic Police · ASTraM Compliance System*

</div>

---

## Overview

Trafficly is a production-grade automated traffic enforcement system built for smart city deployments. It uses a custom-trained YOLOv8s computer vision model to detect violations in real-time CCTV feeds, automatically reads license plates via ANPR, and generates official e-challan PDF notices with UPI payment QR codes.

The platform is built to be **extensible** — helmet detection is the first active module, with signal jump detection, over-speeding, and triple riding planned as upcoming additions.

---

## Features

| Module | Status | Description |
|--------|--------|-------------|
| Helmet Detection | ✅ Active | YOLOv8s custom-trained on 5-class dataset |
| ANPR Plate Reading | ✅ Active | OpenCV-based license plate recognition |
| e-Challan Generation | ✅ Active | PDF notices via ReportLab |
| UPI Payment QR | ✅ Active | Auto-generated QR per challan |
| Live Dashboard | ✅ Active | Streamlit dark-mode enforcement UI |
| MJPEG Stream | ✅ Active | Real-time annotated video via FastAPI |
| Violation Map | ✅ Active | Leaflet.js + OpenStreetMap dark tiles |
| Signal Jump Detection | 🔜 Planned | — |
| Over-Speeding | 🔜 Planned | — |
| Triple Riding | 🔜 Planned | — |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CCTV / Video Feed                │
└─────────────────────┬───────────────────────────────┘
                      │
          ┌───────────▼────────────┐
          │   YOLOv8s Pipeline     │
          │  Multi-class Detection │
          │  ByteTrack Tracking    │
          └───────────┬────────────┘
                      │
          ┌───────────▼────────────┐
          │   ANPR Engine          │
          │  License Plate OCR     │
          └───────────┬────────────┘
                      │
          ┌───────────▼────────────┐
          │   Challan Engine       │
          │  PDF + QR Generation   │
          └───────────┬────────────┘
                      │
     ┌────────────────▼──────────────────┐
     │          FastAPI Backend          │
     │  /api/stream  /api/stats          │
     │  /api/challans  /api/files/*      │
     └────────────────┬──────────────────┘
                      │
     ┌────────────────▼──────────────────┐
     │       Streamlit Dashboard         │
     │  Live Monitor · Map · Archive     │
     │  Developer Profile                │
     └───────────────────────────────────┘
```

---

## Tech Stack

- **Detection Model** — YOLOv8s (custom-trained, 40 epochs, 5 classes)
- **Tracking** — ByteTrack multi-object tracker
- **Backend** — FastAPI + Uvicorn ASGI
- **Frontend** — Streamlit with full custom CSS design system
- **Video** — OpenCV MJPEG streaming
- **Maps** — Leaflet.js + CartoDB Dark tiles (OpenStreetMap)
- **PDF** — ReportLab e-challan generation
- **Payments** — UPI QR code integration
- **Charts** — Plotly Graph Objects

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/vanshul04/trafficly.git
cd trafficly
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure settings

Edit `config/settings.yaml` with your camera source and junction details.

### 4. Run the system

**Start the backend (FastAPI + enforcement pipeline):**
```bash
python main.py --web
```

**Start the dashboard (in a new terminal):**
```bash
streamlit run dashboard_main.py --server.port 8501
```

### 5. Open the dashboard

```
http://localhost:8501
```

---

## Model Details

| Parameter | Value |
|-----------|-------|
| Architecture | YOLOv8s |
| Classes | `rider`, `with_helmet`, `without_helmet`, `number_plate`, `motorcycle` |
| Epochs | 40 |
| Weights file | `helmet_best.pt` |
| mAP50 (rider) | 88.6% |
| Overall mAP50 | 60.0% |

> **Note:** Model weights (`*.pt`) are excluded from this repository due to file size. Contact the developer for access or retrain using `python src/train_model.py`.

---

## Project Structure

```
trafficly/
├── assets/                 # Dashboard UI images
├── config/
│   └── settings.yaml       # Camera, junction, model config
├── src/
│   ├── pipeline.py         # Main enforcement pipeline
│   ├── train_model.py      # YOLOv8 training script
│   ├── challan_pdf.py      # e-Challan PDF generator
│   └── ...
├── dashboard_main.py       # Streamlit dashboard (4 tabs)
├── server.py               # FastAPI application
├── main.py                 # System entrypoint
└── requirements.txt
```

---

## Dashboard Tabs

1. **Live Monitoring** — Real-time CCTV stream with violation log, spotlight card, compliance donut chart
2. **Violation Map** — Interactive OpenStreetMap with violation markers per junction
3. **Citation Archive** — Searchable, filterable full citation database with PDF downloads
4. **About Developer** — System info, tech stack, developer profile

---

## Developer

**Vanshul Lalwani**
Lead AI & Full-Stack MLOps Developer

- GitHub: [github.com/vanshul04](https://github.com/vanshul04)
- Email: [vanshullalwani43@gmail.com](mailto:vanshullalwani43@gmail.com)

This system was engineered independently as a comprehensive technical solution for urban mobility and smart city management. By combining state-of-the-art multi-object tracking computer vision pipelines with a seamless financial payment layer, this architecture streamlines automated violation tracking and penalty processing for law enforcement networks.

---

## License

MIT License — © 2026 Vanshul Lalwani
