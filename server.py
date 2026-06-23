import os
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Initialize enforcement pipeline
from src.pipeline import TrafficEnforcementPipeline
pipeline = TrafficEnforcementPipeline("config/settings.yaml")

app = FastAPI(
    title="Trafficly - Automated Helmet Enforcement Dashboard Backend",
    description="FastAPI ASGI engine managing CCTV streams, compliance rate metrics, and ReportLab notice compilation queues."
)

# Mount static web directory
os.makedirs("src/web", exist_ok=True)
app.mount("/static", StaticFiles(directory="src/web"), name="static")

# Mount output directories
os.makedirs("output/challans", exist_ok=True)
os.makedirs("output/crops", exist_ok=True)
app.mount("/api/files/challans", StaticFiles(directory="output/challans"), name="challans")
app.mount("/api/files/crops", StaticFiles(directory="output/crops"), name="crops")

@app.get("/")
def read_root():
    """
    Serves the primary console dashboard.
    """
    html_path = "src/web/index.html"
    if not os.path.exists(html_path):
        return Response(content="<h3>Trafficly web assets loading... Refresh in 3 seconds.</h3>", status_code=202)
    return FileResponse(html_path)

@app.get("/api/stream")
def get_video_stream():
    """
    Streams helmet radar processed video frames as an MJPEG boundary stream.
    """
    return StreamingResponse(
        pipeline.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/stats")
def get_stats():
    """
    Exposes live compliance rates, infractions log count, and status logs.
    """
    return {
        "total_vehicles": int(pipeline.total_vehicles_counted),
        "total_violations": int(pipeline.total_violations_logged),
        "compliance_rate": float(pipeline.compliance_rate),
        "junction_name": pipeline.config['location']['junction_name'],
        "camera_id": pipeline.config['location']['camera_id'],
        "status": "ONLINE" if pipeline.active else "OFFLINE",
        "mode": "CCTV Ingestion Feed" if os.path.exists("dummy.mp4") else "Radar Simulation Feed"
    }

@app.get("/api/challans")
def get_challans():
    """
    Returns the repository list of registered offenses.
    """
    return pipeline.violations_list[::-1]

@app.post("/api/challans/{challan_no}/pay")
def pay_challan(challan_no: str):
    """
    Marks a registered offense notice as PAID in the backend repository.
    """
    for v in pipeline.violations_list:
        if v['challan_no'] == challan_no:
            v['status'] = 'PAID'
            return {"status": "success", "message": f"Challan {challan_no} marked as PAID"}
    return {"status": "error", "message": "Challan not found"}

@app.on_event("shutdown")
def shutdown_event():
    """
    Shutdown pipeline compiling threads.
    """
    pipeline.shutdown()

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
