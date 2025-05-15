import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import argparse
import os
import urllib.request
import json
from datetime import datetime
import time

# Visualization constants
MARGIN = 0
ROW_SIZE = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
TEXT_COLOR = (255, 0, 0)  # red
ZONE_COLORS = {
    "zone1": (0, 255, 0),  # Green
    "zone2": (0, 165, 255),  # Orange
    "zone3": (0, 0, 255),  # Red
    "zone4": (255, 0, 255),  # Purple
}


class ZoneMonitor:
    def __init__(self, zones_config=None, log_file="zone_entries.log"):
        """Initialize the zone monitor with predefined zones.

        Args:
            zones_config: Path to a JSON file containing zone definitions
                          or a dictionary of zone definitions
            log_file: Path to write zone entry/exit events
        """
        self.zones = {}
        self.log_file = log_file
        self.last_detections = {}  # {object_id: {"zone": zone_name, "timestamp": time}}

        if zones_config:
            if isinstance(zones_config, str) and os.path.exists(zones_config):
                with open(zones_config, "r") as f:
                    self.zones = json.load(f)
            elif isinstance(zones_config, dict):
                self.zones = zones_config
        else:
            # Default zones (can be adjusted based on your image)
            self.zones = {
                "zone1": {
                    "name": "Production Area",
                    "color": ZONE_COLORS["zone1"],
                    "points": [(100, 100), (400, 100), (400, 400), (100, 400)],
                },
                "zone2": {
                    "name": "Storage Area",
                    "color": ZONE_COLORS["zone2"],
                    "points": [(500, 100), (800, 100), (800, 400), (500, 400)],
                },
            }

    def save_zones(self, config_path):
        """Save the current zone configuration to a file."""
        with open(config_path, "w") as f:
            json.dump(self.zones, f, indent=2)

    def point_in_polygon(self, point, polygon):
        """Check if a point is inside a polygon using ray casting algorithm."""
        x, y = point
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def check_zone(self, point):
        """Check which zone a point belongs to. Returns zone name or None."""
        for zone_id, zone_info in self.zones.items():
            if self.point_in_polygon(point, zone_info["points"]):
                return zone_id
        return None

    def draw_zones(self, frame):
        """Draw all zones on the frame."""
        for zone_id, zone_info in self.zones.items():
            points = np.array(zone_info["points"], np.int32)
            points = points.reshape((-1, 1, 2))

            # Draw filled polygon with transparency
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], zone_info["color"])
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

            # Draw zone outline
            cv2.polylines(frame, [points], True, zone_info["color"], 2)

            # Add zone name
            centroid_x = sum(p[0] for p in zone_info["points"]) // len(
                zone_info["points"]
            )
            centroid_y = sum(p[1] for p in zone_info["points"]) // len(
                zone_info["points"]
            )
            cv2.putText(
                frame,
                zone_info["name"],
                (centroid_x, centroid_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

    def log_zone_event(self, object_id, category, zone_id, event_type):
        """Log when an object enters or exits a zone."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        zone_name = self.zones[zone_id]["name"] if zone_id in self.zones else "Unknown"

        log_entry = (
            f"{timestamp} - Object {object_id} ({category}) {event_type} {zone_name}\n"
        )

        print(log_entry.strip())

        with open(self.log_file, "a") as f:
            f.write(log_entry)

    def define_zone_interactively(self, frame, zone_id, zone_name, color):
        """Allow user to define a zone by clicking on the frame."""
        points = []
        window_name = "Define Zone - Click to add points, press 'c' to complete"

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                cv2.circle(frame, (x, y), 5, color, -1)
                # Show coordinates on screen
                coord_text = f"({x}, {y})"
                cv2.putText(
                    frame,
                    coord_text,
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )

                if len(points) > 1:
                    cv2.line(frame, points[-2], points[-1], color, 2)
                cv2.imshow(window_name, frame)

        clone = frame.copy()

        # Add instructions on the frame
        instructions = [
            "Click to add points",
            "Press 'c' to complete zone",
            "Press 'r' to reset zone",
            "Press ESC to cancel",
        ]

        for i, inst in enumerate(instructions):
            cv2.putText(
                frame,
                inst,
                (10, 30 + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

        cv2.imshow(window_name, frame)
        cv2.setMouseCallback(window_name, mouse_callback)

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord("c") and len(points) > 2:
                # Close the polygon
                cv2.line(frame, points[-1], points[0], color, 2)
                cv2.imshow(window_name, frame)
                cv2.waitKey(500)
                break
            elif key == ord("r"):
                # Reset
                frame = clone.copy()
                for i, inst in enumerate(instructions):
                    cv2.putText(
                        frame,
                        inst,
                        (10, 30 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                    )
                points = []
                cv2.imshow(window_name, frame)
            elif key == 27:  # ESC key
                points = []
                break

        cv2.destroyWindow(window_name)

        if points:
            self.zones[zone_id] = {"name": zone_name, "color": color, "points": points}
            return True
        return False


def visualize(image, detection_result, zone_monitor):
    """Draws bounding boxes on the input image and checks for zone intersections.
    Only processes 'person' detections, ignoring all others."""
    zone_occupancy = {}  # Track which objects are in which zones
    person_count = 0

    for detection in detection_result.detections:
        # Get category name for this detection
        category = detection.categories[0]
        category_name = category.category_name

        # Skip if not a person
        if category_name.lower() != "person":
            continue

        # Keep track of person count for unique IDs
        person_count += 1

        # Draw bounding_box
        bbox = detection.bounding_box
        start_point = bbox.origin_x, bbox.origin_y
        end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
        cv2.rectangle(image, start_point, end_point, TEXT_COLOR, 3)

        # Get detection info
        probability = round(category.score, 2)

        # Generate a unique object ID
        object_id = f"person_{person_count}"

        # Check bottom center point of bounding box for zone detection
        # (this is typically where the feet would be for a person)
        foot_point = (bbox.origin_x + bbox.width // 2, bbox.origin_y + bbox.height)
        zone_id = zone_monitor.check_zone(foot_point)

        # Draw a circle at the foot point
        cv2.circle(image, foot_point, 5, (0, 255, 255), -1)

        # Add zone information to the label
        result_text = f"Person ({probability})"
        if zone_id:
            result_text += f" - {zone_monitor.zones[zone_id]['name']}"

            # Track zone entries/exits
            current_time = time.time()

            if object_id not in zone_monitor.last_detections:
                # New person detected
                zone_monitor.log_zone_event(object_id, "Person", zone_id, "entered")
            elif zone_monitor.last_detections[object_id]["zone"] != zone_id:
                # Person changed zones
                zone_monitor.log_zone_event(
                    object_id,
                    "Person",
                    zone_monitor.last_detections[object_id]["zone"],
                    "exited",
                )
                zone_monitor.log_zone_event(object_id, "Person", zone_id, "entered")

            # Update last known position
            zone_monitor.last_detections[object_id] = {
                "zone": zone_id,
                "timestamp": current_time,
                "category": "Person",
            }

            # Count occupancy
            if zone_id not in zone_occupancy:
                zone_occupancy[zone_id] = []
            zone_occupancy[zone_id].append(object_id)

        # Draw label and score
        text_location = (MARGIN + bbox.origin_x, MARGIN + ROW_SIZE + bbox.origin_y)
        cv2.putText(
            image,
            result_text,
            text_location,
            cv2.FONT_HERSHEY_PLAIN,
            FONT_SIZE,
            TEXT_COLOR,
            FONT_THICKNESS,
        )

    # Draw zone occupancy stats on the frame
    y_offset = 30
    for zone_id, occupants in zone_occupancy.items():
        if zone_id in zone_monitor.zones:
            zone_name = zone_monitor.zones[zone_id]["name"]
            zone_color = zone_monitor.zones[zone_id]["color"]
            text = f"{zone_name}: {len(occupants)} people"
            cv2.putText(
                image,
                text,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                zone_color,
                2,
            )
            y_offset += 30

    # Cleanup old detections (people that haven't been seen for a while)
    current_time = time.time()
    objects_to_remove = []
    for obj_id, info in zone_monitor.last_detections.items():
        if current_time - info["timestamp"] > 2.0:  # 2 second timeout
            objects_to_remove.append(obj_id)
            if "zone" in info:
                zone_monitor.log_zone_event(
                    obj_id, info["category"], info["zone"], "exited (timeout)"
                )

    for obj_id in objects_to_remove:
        zone_monitor.last_detections.pop(obj_id, None)

    return image


def process_video(
    input_path,
    output_path=None,
    model_path="efficientdet.tflite",
    score_threshold=0.55,
    use_webcam=False,
    use_gpu=False,
    zones_config=None,
    define_zones=False,
    log_file="zone_entries.log",
):
    """Process a video with person detection and zone monitoring."""
    # Set up the object detector
    base_options = python.BaseOptions(model_asset_path=model_path)

    # Configure GPU acceleration if requested
    if use_gpu:
        base_options.use_gpu = True
        print("Using GPU acceleration with CUDA")

    options = vision.ObjectDetectorOptions(
        base_options=base_options, score_threshold=score_threshold
    )
    detector = vision.ObjectDetector.create_from_options(options)

    # Initialize the zone monitor
    zone_monitor = ZoneMonitor(zones_config, log_file)

    # Open video capture
    if use_webcam:
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        print(f"Error: Could not open {'webcam' if use_webcam else 'video file'}")
        return

    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Create video writer if output path is specified
    out = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    print(f"Processing video {'from webcam' if use_webcam else f'from {input_path}'}")
    print(f"Only tracking PEOPLE - all other objects will be ignored")

    # Allow user to define zones if requested
    if define_zones:
        # Read a frame to use for zone definition
        success, frame = cap.read()
        if not success:
            print("Could not read frame for zone definition")
            return

        # Define zones interactively
        zone_ids = list(ZONE_COLORS.keys())
        for i, (zone_id, color) in enumerate(ZONE_COLORS.items()):
            zone_name = input(f"Enter name for {zone_id} (or press Enter to skip): ")
            if zone_name:
                print(
                    f"Define {zone_name} by clicking points on the image. Press 'c' when complete, 'r' to reset."
                )
                zone_monitor.define_zone_interactively(
                    frame.copy(), zone_id, zone_name, color
                )

        # Save the zone configuration
        config_path = "zones.json"
        zone_monitor.save_zones(config_path)
        print(f"Zones saved to {config_path}")

        # Reset video capture to start of file
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Initialize log file
    with open(log_file, "w") as f:
        f.write(f"Person Zone Monitoring Log - Started at {datetime.now()}\n")
        f.write("-" * 50 + "\n")

    frame_count = 0
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame_count += 1
        if frame_count % 10 == 0:
            print(f"Processed {frame_count} frames")

        # Convert to RGB for MediaPipe (it expects RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect objects
        detection_result = detector.detect(mp_image)

        # Draw zones
        zone_monitor.draw_zones(rgb_frame)

        # Draw bounding boxes, labels, and check for zone intersections
        # Only for person detections
        annotated_frame = visualize(rgb_frame.copy(), detection_result, zone_monitor)

        # Convert back to BGR for OpenCV display/saving
        annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)

        # Display the frame
        cv2.imshow("Person Detection with Zone Monitoring", annotated_frame)

        # Write frame to output video if specified
        if out:
            out.write(annotated_frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Release resources
    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()

    if output_path:
        print(f"Output saved to {output_path}")
    print(f"Zone entry/exit events saved to {log_file}")


def download_model(model_path):
    """Download the model file if it doesn't exist."""
    if os.path.exists(model_path):
        return True

    print(f"Model file {model_path} not found. Downloading...")
    try:
        # URL for EfficientDet Lite0 model
        model_url = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float32/latest/efficientdet_lite2.tflite"
        urllib.request.urlretrieve(model_url, model_path)
        print(f"Model downloaded successfully to {model_path}")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Person Detection with Zone Monitoring"
    )
    parser.add_argument("--input", type=str, help="Path to input video file")
    parser.add_argument("--output", type=str, help="Path to output video file")
    parser.add_argument(
        "--model", type=str, help="Path to TFLite model", default="efficientdet.tflite"
    )
    parser.add_argument(
        "--threshold", type=float, help="Detection score threshold", default=0.5
    )
    parser.add_argument(
        "--webcam", action="store_true", help="Use webcam instead of video file"
    )
    parser.add_argument(
        "--gpu", action="store_true", help="Enable GPU acceleration using CUDA"
    )
    parser.add_argument(
        "--zones",
        type=str,
        default="zones.json",
        help="Path to JSON file containing zone definitions (default: zones.json)",
    )
    parser.add_argument(
        "--log",
        type=str,
        default="person_zone_entries.log",
        help="Path to write zone entry/exit events",
    )

    args = parser.parse_args()

    # Download the model if it doesn't exist
    if not download_model(args.model):
        print("Could not obtain the model file. Exiting.")
        return

    # Ensure input is provided if not using webcam
    if not args.webcam and not args.input:
        parser.error("--input is required when not using --webcam")

    # If using input file, ensure it exists
    if not args.webcam and not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found")
        return

    # Check for zone configuration file
    if not os.path.exists(args.zones):
        print(f"Warning: Zone configuration file {args.zones} not found.")
        print("You can create one using the zone_definition_tool.py script.")

        # Create a default zone configuration for the factory floor
        # These coordinates are estimates and should be adjusted
        default_zones = {
            "zone1": {
                "name": "Production Area",
                "color": ZONE_COLORS["zone1"],
                "points": [(100, 200), (500, 200), (500, 500), (100, 500)],
            },
            "zone2": {
                "name": "Storage Area",
                "color": ZONE_COLORS["zone2"],
                "points": [(550, 200), (900, 200), (900, 500), (550, 500)],
            },
        }

        # Ask if user wants to use default zones
        print("\nWould you like to:")
        print("1. Use default zone configuration")
        print("2. Run without zone monitoring")
        choice = input("Enter choice (1/2): ")

        if choice == "1":
            print("Using default zone configuration")
            # Save default zones to file
            with open(args.zones, "w") as f:
                json.dump(default_zones, f, indent=2)
            zones_config = default_zones
        else:
            print("Running without zone monitoring")
            zones_config = None
    else:
        # Load zones from file
        with open(args.zones, "r") as f:
            zones_config = json.load(f)
        print(f"Loaded {len(zones_config)} zones from {args.zones}")

    process_video(
        input_path=args.input,
        output_path=args.output,
        model_path=args.model,
        score_threshold=args.threshold,
        use_webcam=args.webcam,
        use_gpu=args.gpu,
        zones_config=zones_config,
        define_zones=False,  # No longer using interactive definition
        log_file=args.log,
    )


if __name__ == "__main__":
    main()
