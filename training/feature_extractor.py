"""
Feature Extractor for LSTM Training
=====================================
This script processes raw crowd videos and outputs a CSV file
containing time-series numerical features per frame.

The LSTM trains entirely on this CSV — no raw video is needed
after this step.

Usage:
    python training/feature_extractor.py --video <path_to_video.mp4> --label <0_or_1> --output training/data/training_data.csv

Arguments:
    --video   : Path to the source video file
    --label   : Ground truth label (0 = Safe/Normal, 1 = Stampede/Panic)
    --output  : Path to append CSV rows into (default: training/data/training_data.csv)
"""

import cv2
import numpy as np
import csv
import os
import argparse
from ultralytics import YOLO


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
YOLO_MODEL = "yolov8n.pt"       # Lightweight model for fast feature extraction
FRAME_SAMPLE_RATE = 5           # Process every Nth frame (5 = ~1 sample/second at 30fps)
YOLO_CONFIDENCE = 0.3           # Only count detections above this confidence


def calculate_optical_flow(prev_gray, curr_gray):
    """
    Calculates optical flow between two grayscale frames.
    Returns:
        avg_speed          : Mean pixel displacement magnitude across the frame
        direction_variance : Spread of motion angles (high = chaotic/erratic)
    """
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray,
        None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2,
        flags=0
    )

    # Magnitude and angle of each pixel's motion vector
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    avg_speed = float(np.mean(magnitude))

    # Direction variance: high = people moving in ALL directions (panic signature)
    # Normalize angles to [0, 1] then measure variance
    direction_variance = float(np.std(angle / (2 * np.pi)))

    return avg_speed, direction_variance


def calculate_density(boxes, frame_area):
    """
    Estimates crowd density as the fraction of frame area
    covered by person bounding boxes.
    """
    if not boxes:
        return 0.0
    covered_area = sum((x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in boxes)
    return min(float(covered_area / frame_area), 1.0)


def extract_features(video_path, label, output_csv, max_seconds=None):
    """
    Main extraction loop. Processes a video file frame by frame,
    extracts crowd metrics, and writes rows to CSV.
    """
    print(f"\nLoading video: {video_path}")
    print(f"Label: {'STAMPEDE/PANIC (1)' if label == 1 else 'SAFE/NORMAL (0)'}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open video {video_path}")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_area = cap.get(cv2.CAP_PROP_FRAME_WIDTH) * cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    # Limit to max_seconds if specified
    max_frame_limit = None
    if max_seconds is not None:
        max_frame_limit = int(fps * max_seconds)
        total_frames = min(total_frames, max_frame_limit)
        print(f"Total frames: {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}, FPS: {fps:.1f} — limiting to first {max_seconds}s ({max_frame_limit} frames)")
    else:
        print(f"Total frames: {total_frames}, FPS: {fps:.1f}")
    print(f"Sampling every {FRAME_SAMPLE_RATE} frames...")
    print(f"Loading YOLO model ({YOLO_MODEL})...")

    model = YOLO(YOLO_MODEL)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # Write CSV header if file does not exist yet
    write_header = not os.path.exists(output_csv)
    csv_file = open(output_csv, "a", newline="")
    writer = csv.writer(csv_file)

    if write_header:
        writer.writerow([
            "frame",
            "crowd_count",
            "density_pct",
            "avg_speed",
            "direction_variance",
            "label"
        ])

    prev_gray = None
    frame_num = 0
    rows_written = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        # Stop if we've hit our frame limit
        if max_frame_limit is not None and frame_num > max_frame_limit:
            break

        # Skip frames to reach desired sample rate
        if frame_num % FRAME_SAMPLE_RATE != 0:
            continue

        # ── Step 1: Detect people using YOLO ──────────────────
        results = model(frame, conf=YOLO_CONFIDENCE, classes=[0], verbose=False)
        boxes = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((x1, y1, x2, y2))

        crowd_count = len(boxes)

        # ── Step 2: Calculate density ──────────────────────────
        density_pct = round(calculate_density(boxes, frame_area) * 100, 2)

        # ── Step 3: Calculate optical flow ────────────────────
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            avg_speed, direction_variance = calculate_optical_flow(prev_gray, curr_gray)
        else:
            avg_speed, direction_variance = 0.0, 0.0

        prev_gray = curr_gray

        # ── Step 4: Write row to CSV ───────────────────────────
        writer.writerow([
            frame_num,
            crowd_count,
            density_pct,
            round(avg_speed, 4),
            round(direction_variance, 4),
            label
        ])
        rows_written += 1

        # Progress update every 50 rows
        if rows_written % 50 == 0:
            pct = int((frame_num / total_frames) * 100)
            print(f"  Progress: {pct}% ({rows_written} rows written so far)...")

    cap.release()
    csv_file.close()

    print(f"\nDone. {rows_written} rows written to: {output_csv}")
    return rows_written


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract crowd features from a single video into a CSV.")
    parser.add_argument("--video",       required=True,  help="Path to the source video file")
    parser.add_argument("--label",       required=True,  type=int, choices=[0, 1], help="0 = Safe, 1 = Stampede")
    parser.add_argument("--output",      default="training/data/training_data.csv", help="Output CSV path")
    parser.add_argument("--max_seconds", type=float, default=None, help="Only process the first N seconds of the video")

    args = parser.parse_args()

    total = extract_features(args.video, args.label, args.output, args.max_seconds)
    print(f"\nFeature Extraction Complete. Total rows in dataset: {total}")
    print(f"Output file: {args.output}")
    print("\nNext step: Run train_lstm.py to train the model on this data.")
