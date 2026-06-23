import os
import argparse
from src.pipeline import TrafficEnforcementPipeline

def main():
    parser = argparse.ArgumentParser(description="Bengaluru Traffic Police ASTraM Automated Traffic Enforcement System")
    parser.add_argument("--config", type=str, default="config/settings.yaml", help="Path to settings.yaml configuration file")
    parser.add_argument("--video", type=str, default=None, help="Path to video file or camera index (e.g., '0' for webcam)")
    parser.add_argument("--mock", action="store_true", help="Force execution of the mock hardware-fallback simulation")
    parser.add_argument("--web", action="store_true", help="Launch the localhost web dashboard server")
    
    args = parser.parse_args()
    
    if args.web:
        import uvicorn
        print("[SYSTEM] Launching BTP ASTraM Localhost Web Dashboard on http://127.0.0.1:8000...")
        uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")
        return
        
    # Establish absolute paths where necessary
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(script_dir, config_path)
        
    if not os.path.exists(config_path):
        print(f"[SYSTEM ERROR] Configuration settings file not found: {config_path}")
        return
        
    print("[SYSTEM] Initializing Bengaluru Traffic Police ASTraM enforcement system...")
    pipeline = TrafficEnforcementPipeline(config_path)
    
    try:
        if args.mock:
            # Force simulation fallback mode
            pipeline.run_simulated_pipeline()
        elif args.video is not None:
            # Real camera source or video path
            pipeline.init_yolo()
            # If digit string, cast to integer index for opencv webcam capture
            source = args.video
            if source.isdigit():
                source = int(source)
            success = pipeline.run_real_pipeline(source)
            if not success:
                print("[SYSTEM] Live stream launch failed. Launching simulation mode instead...")
                pipeline.run_simulated_pipeline()
        else:
            # Auto-detect hardware/dependencies and decide mode
            print("[SYSTEM] Scanning system resources and dependencies...")
            pipeline.init_yolo()
            if pipeline.real_mode:
                print("[SYSTEM] YOLO dependencies verified. Attempting connection to Webcam [0]...")
                success = pipeline.run_real_pipeline(0)
                if not success:
                    print("[SYSTEM] Webcam [0] offline. Falling back to simulation mode...")
                    pipeline.run_simulated_pipeline()
            else:
                print("[SYSTEM] YOLO weights or packages missing. Entering self-contained simulation mode...")
                pipeline.run_simulated_pipeline()
                
    except KeyboardInterrupt:
        print("\n[SYSTEM] Interrupt signal received. Closing pipelines...")
    finally:
        pipeline.shutdown()
        print("[SYSTEM] Cleanup finished. All outputs saved in 'C:\\Users\\Vansh\\gridlock_hackathon\\output\\'")

if __name__ == "__main__":
    main()
