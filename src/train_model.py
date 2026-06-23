import os
import zipfile
import glob
import yaml
import shutil
from ultralytics import YOLO

def find_and_extract_dataset():
    dest_dir = "C:\\Users\\Vansh\\gridlock_hackathon\\dataset"
    yaml_path = os.path.join(dest_dir, "data.yaml")
    
    # 1. Check if dataset is already extracted
    if os.path.exists(yaml_path):
        print(f"[DATASET] Found existing dataset at '{dest_dir}'. Skipping extraction.")
        return True
        
    # 2. Search user's Downloads folder for a zip containing the Indian Helmet Detection Dataset
    downloads_path = os.path.expanduser("~/Downloads")
    print(f"[DATASET] Searching for dataset zip files in '{downloads_path}'...")
    zip_files = glob.glob(os.path.join(downloads_path, "*.zip"))
    
    target_zip = None
    for zpath in zip_files:
        try:
            with zipfile.ZipFile(zpath, 'r') as z:
                # Look for a yaml file in the zip
                names = [f.filename for f in z.filelist]
                yaml_files = [n for n in names if n.endswith("data.yaml") or n.endswith("dataset.yaml")]
                if yaml_files:
                    # Read the yaml file contents to verify classes
                    with z.open(yaml_files[0]) as yf:
                        yaml_content = yaml.safe_load(yf)
                        classes = yaml_content.get("names", {})
                        # Support list or dict of classes
                        class_values = list(classes.values()) if isinstance(classes, dict) else classes
                        # Roboflow files might have class indices as strings ['0', '1', '2', '3', '4'] or class names
                        if any("faceWithNoHelmet" in str(c) for c in class_values) or len(class_values) == 5:
                            target_zip = zpath
                            print(f"[DATASET] Identified correct dataset zip: '{zpath}'")
                            break
        except Exception as e:
            continue
            
    if not target_zip:
        print("[DATASET ERROR] Could not find any zip file in Downloads matching the Indian Helmet Detection Dataset classes.")
        print("Please download the 'Indian Helmet Detection Dataset' from Kaggle:")
        print("Link: https://www.kaggle.com/datasets/aryanvaid13/indian-helmet-detection-dataset")
        print("And make sure the downloaded zip file is in your Downloads folder.")
        return False
        
    # 3. Extract the target zip file
    print(f"[DATASET] Extracting '{target_zip}' to '{dest_dir}'...")
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(target_zip, 'r') as z:
        z.extractall(dest_dir)
    print("[DATASET] Extraction complete.")
    return True

def prepare_data_yaml():
    dest_dir = "C:\\Users\\Vansh\\gridlock_hackathon\\dataset"
    yaml_path = os.path.join(dest_dir, "data.yaml")
    
    if not os.path.exists(yaml_path):
        # Let's check if the zip extracted to a subfolder
        yaml_files = glob.glob(os.path.join(dest_dir, "**", "data.yaml"), recursive=True)
        if yaml_files:
            shutil.copy(yaml_files[0], yaml_path)
        else:
            print("[YAML ERROR] data.yaml not found after extraction.")
            # Let's create a default one
            default_yaml = {
                "train": os.path.join(dest_dir, "train", "images"),
                "val": os.path.join(dest_dir, "valid", "images"),
                "test": os.path.join(dest_dir, "test", "images"),
                "nc": 5,
                "names": {
                    0: "numberPlate",
                    1: "faceWithNoHelmet",
                    2: "faceWithGoodHelmet",
                    3: "faceWithBadHelmet",
                    4: "rider"
                }
            }
            with open(yaml_path, 'w') as f:
                yaml.dump(default_yaml, f)
            print("[DATASET] Created default data.yaml file.")
            
    # Update data.yaml to use absolute paths and descriptive names
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
        
    config["train"] = os.path.join(dest_dir, "train", "images")
    config["val"] = os.path.join(dest_dir, "valid", "images")
    if "test" in config or os.path.exists(os.path.join(dest_dir, "test")):
        config["test"] = os.path.join(dest_dir, "test", "images")
        
    # Enforce correct descriptive labels for Indian Helmet Detection Dataset
    config["names"] = {
        0: "numberPlate",
        1: "faceWithNoHelmet",
        2: "faceWithGoodHelmet",
        3: "faceWithBadHelmet",
        4: "rider"
    }
    config["nc"] = 5
    
    with open(yaml_path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False)
        
    print(f"[DATASET] Updated '{yaml_path}' with absolute path definitions:")
    print(f"  - Train path: {config['train']}")
    print(f"  - Val path: {config['val']}")
    return yaml_path

def train():
    if not find_and_extract_dataset():
        return
        
    yaml_path = prepare_data_yaml()
    
    # Check if GPU is available
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[TRAIN] Starting YOLOv8 training on device: {device.upper()}")
    
    # Clear existing training runs folder if it exists to start fresh
    best_run_dir = os.path.join("C:\\Users\\Vansh\\gridlock_hackathon\\runs", "helmet_training_best")
    if os.path.exists(best_run_dir):
        print(f"[TRAIN] Clearing existing runs directory '{best_run_dir}' for a fresh training session...")
        try:
            shutil.rmtree(best_run_dir)
        except Exception as e:
            print(f"[TRAIN WARNING] Could not clear existing run folder: {e}")
            
    # Initialize YOLOv8 Small model (pretrained) for much higher mAP capacity
    model = YOLO("yolov8s.pt")
    
    # Train the model for 40 epochs with early stopping patience of 10
    epochs = 40
    print(f"[TRAIN] Training model for {epochs} epochs with early stopping...")
    results = model.train(
        data=yaml_path,
        epochs=epochs,
        patience=10,
        imgsz=640,
        device=device,
        workers=0, # Avoid Windows multiprocessing deadlock/hang
        optimizer="AdamW",
        project="C:\\Users\\Vansh\\gridlock_hackathon\\runs",
        name="helmet_training_best"
    )
    
    # Copy best weights to project root
    best_weights = os.path.join("C:\\Users\\Vansh\\gridlock_hackathon\\runs", "helmet_training_best", "weights", "best.pt")
    target_weights = "C:\\Users\\Vansh\\gridlock_hackathon\\helmet_best.pt"
    
    if os.path.exists(best_weights):
        shutil.copy(best_weights, target_weights)
        print(f"[TRAIN SUCCESS] Model trained successfully! Best weights copied to '{target_weights}'.")
    else:
        print(f"[TRAIN WARNING] Trained weights not found at expected path '{best_weights}'. Searching...")
        found_weights = glob.glob("C:\\Users\\Vansh\\gridlock_hackathon\\runs/**/weights/best.pt", recursive=True)
        if found_weights:
            shutil.copy(found_weights[0], target_weights)
            print(f"[TRAIN SUCCESS] Found and copied weights from '{found_weights[0]}' to '{target_weights}'.")
        else:
            print("[TRAIN ERROR] Could not locate trained weights. Training may have failed.")

if __name__ == "__main__":
    train()
