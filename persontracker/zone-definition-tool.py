import cv2
import numpy as np
import json
import argparse
import os
from datetime import datetime


class ZoneDefinitionTool:
    def __init__(self, image_path=None, config_path="zones.json"):
        """Initialize the zone definition tool.

        Args:
            image_path: Path to an image file to use as background
            config_path: Path to save the zone configuration
        """
        self.config_path = config_path
        self.image_path = image_path
        self.zones = {}
        self.current_zone = None
        self.current_zone_id = None
        self.current_color = None
        self.drawing = False
        self.points = []
        self.mouse_position = (0, 0)

        # Define some colors for zones
        self.colors = {
            "green": (0, 255, 0),
            "orange": (0, 165, 255),
            "red": (0, 0, 255),
            "purple": (255, 0, 255),
            "blue": (255, 165, 0),
            "cyan": (255, 255, 0),
            "magenta": (255, 0, 255),
            "yellow": (0, 255, 255),
        }

        # Load existing zones if the config file exists
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.zones = json.load(f)
                print(f"Loaded {len(self.zones)} zones from {config_path}")
            except:
                print(f"Failed to load zones from {config_path}")

    def get_next_color(self):
        """Get the next unused color from the color list."""
        for color_name, color_value in self.colors.items():
            used = False
            for zone in self.zones.values():
                if tuple(zone["color"]) == color_value:
                    used = True
                    break
            if not used:
                return color_name, color_value

        # If all colors are used, return a random color
        return "custom", (
            np.random.randint(0, 256),
            np.random.randint(0, 256),
            np.random.randint(0, 256),
        )

    def get_next_zone_id(self):
        """Get the next available zone ID."""
        for i in range(1, 100):
            zone_id = f"zone{i}"
            if zone_id not in self.zones:
                return zone_id
        return f"zone{len(self.zones) + 1}"

    def draw_zones(self, frame):
        """Draw all defined zones on the frame."""
        for zone_id, zone_info in self.zones.items():
            points = np.array(zone_info["points"], np.int32)
            points = points.reshape((-1, 1, 2))

            # Draw filled polygon with transparency
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], zone_info["color"])
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

            # Draw zone outline
            cv2.polylines(frame, [points], True, zone_info["color"], 2)

            # Add zone name and ID
            centroid_x = sum(p[0] for p in zone_info["points"]) // len(
                zone_info["points"]
            )
            centroid_y = sum(p[1] for p in zone_info["points"]) // len(
                zone_info["points"]
            )

            # Draw text with background for better visibility
            text = f"{zone_info['name']} ({zone_id})"
            (text_width, text_height), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
            )

            # Draw text background
            cv2.rectangle(
                frame,
                (centroid_x - 5, centroid_y - text_height - 5),
                (centroid_x + text_width + 5, centroid_y + 5),
                (0, 0, 0),
                -1,
            )

            # Draw text
            cv2.putText(
                frame,
                text,
                (centroid_x, centroid_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

    def draw_current_zone(self, frame):
        """Draw the zone currently being defined."""
        if not self.points:
            return

        # Draw points and lines
        for i, point in enumerate(self.points):
            cv2.circle(frame, point, 5, self.current_color, -1)

            # Show coordinates on screen
            coord_text = f"({point[0]}, {point[1]})"
            cv2.putText(
                frame,
                coord_text,
                (point[0] + 5, point[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

            # Draw lines between points
            if i > 0:
                cv2.line(frame, self.points[i - 1], point, self.current_color, 2)

        # If we have at least one point, draw a line from the last point to the current mouse position
        if self.drawing and len(self.points) > 0:
            cv2.line(frame, self.points[-1], self.mouse_position, self.current_color, 2)

        # Draw preview of completed polygon
        if len(self.points) > 2:
            preview_frame = frame.copy()
            points_array = np.array(self.points + [self.mouse_position], np.int32)
            points_array = points_array.reshape((-1, 1, 2))

            cv2.fillPoly(preview_frame, [points_array], self.current_color)
            cv2.addWeighted(preview_frame, 0.2, frame, 0.8, 0, frame)

            # Draw closing line to first point when not drawing
            if not self.drawing:
                cv2.line(frame, self.points[-1], self.points[0], self.current_color, 2)

    def draw_help_text(self, frame):
        """Draw help text on the frame."""
        help_text = [
            "Controls:",
            "N: Create New Zone",
            "C: Complete Current Zone",
            "R: Reset Current Zone",
            "D: Delete Selected Zone",
            "S: Save All Zones",
            "Q: Quit Without Saving",
            "",
            "Current Status:",
        ]

        if self.current_zone:
            help_text.append(f"Defining: {self.current_zone} ({self.current_zone_id})")
            help_text.append(f"Points: {len(self.points)}")
        else:
            help_text.append("No zone selected")

        help_text.append(f"Total Zones: {len(self.zones)}")

        # Add a semi-transparent background for the help text
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (300, 10 + 25 * len(help_text)), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Draw the text
        for i, line in enumerate(help_text):
            cv2.putText(
                frame,
                line,
                (20, 30 + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events."""
        # Update mouse position
        self.mouse_position = (x, y)

        # Handle left click to add a point
        if event == cv2.EVENT_LBUTTONDOWN and self.current_zone:
            self.points.append((x, y))
            self.drawing = True

    def save_zones(self):
        """Save the zones to the config file."""
        with open(self.config_path, "w") as f:
            json.dump(self.zones, f, indent=2)
        print(f"Saved {len(self.zones)} zones to {self.config_path}")

    def run(self):
        """Run the zone definition tool."""
        # Load or create the image
        if self.image_path and os.path.exists(self.image_path):
            frame = cv2.imread(self.image_path)
            original_frame = frame.copy()
        else:
            # Create a blank canvas with grid
            frame = np.zeros((800, 1200, 3), dtype=np.uint8)

            # Draw a grid
            for x in range(0, 1200, 100):
                cv2.line(frame, (x, 0), (x, 800), (50, 50, 50), 1)
                # Add coordinate label
                cv2.putText(
                    frame,
                    str(x),
                    (x + 5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (200, 200, 200),
                    1,
                )

            for y in range(0, 800, 100):
                cv2.line(frame, (0, y), (1200, y), (50, 50, 50), 1)
                # Add coordinate label
                cv2.putText(
                    frame,
                    str(y),
                    (5, y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (200, 200, 200),
                    1,
                )

            original_frame = frame.copy()

        # Create window and set mouse callback
        window_name = "Zone Definition Tool"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_callback)

        # Main loop
        while True:
            # Create a fresh copy of the frame
            display_frame = original_frame.copy()

            # Draw all existing zones
            self.draw_zones(display_frame)

            # Draw the current zone being defined
            self.draw_current_zone(display_frame)

            # Draw help text
            self.draw_help_text(display_frame)

            # Display the frame
            cv2.imshow(window_name, display_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            # 'n' to create a new zone
            if key == ord("n"):
                self.current_zone_id = self.get_next_zone_id()
                color_name, color_value = self.get_next_color()
                self.current_color = color_value

                # Prompt for zone name
                zone_name = input(
                    f"Enter name for {self.current_zone_id} (default: {color_name.capitalize()} Zone): "
                )
                if not zone_name:
                    zone_name = f"{color_name.capitalize()} Zone"

                self.current_zone = zone_name
                self.points = []
                self.drawing = False
                print(f"Started defining {self.current_zone} ({self.current_zone_id})")

            # 'c' to complete the current zone
            elif key == ord("c"):
                if self.current_zone and len(self.points) > 2:
                    self.zones[self.current_zone_id] = {
                        "name": self.current_zone,
                        "color": self.current_color,
                        "points": self.points,
                    }
                    print(
                        f"Completed zone: {self.current_zone} ({self.current_zone_id}) with {len(self.points)} points"
                    )

                    # Reset for next zone
                    self.current_zone = None
                    self.current_zone_id = None
                    self.current_color = None
                    self.points = []
                    self.drawing = False
                else:
                    print("Need at least 3 points to complete a zone")

            # 'r' to reset the current zone
            elif key == ord("r"):
                if self.current_zone:
                    self.points = []
                    self.drawing = False
                    print(f"Reset zone: {self.current_zone}")

            # 'd' to delete a zone
            elif key == ord("d"):
                if self.zones:
                    # List available zones
                    print("Available zones:")
                    for idx, (zone_id, zone_info) in enumerate(self.zones.items()):
                        print(f"{idx+1}. {zone_info['name']} ({zone_id})")

                    # Prompt for zone to delete
                    try:
                        selection = input(
                            "Enter number of zone to delete (or press Enter to cancel): "
                        )
                        if selection:
                            idx = int(selection) - 1
                            if 0 <= idx < len(self.zones):
                                zone_id = list(self.zones.keys())[idx]
                                zone_name = self.zones[zone_id]["name"]
                                del self.zones[zone_id]
                                print(f"Deleted zone: {zone_name} ({zone_id})")
                            else:
                                print("Invalid selection")
                    except ValueError:
                        print("Invalid input")

            # 's' to save zones
            elif key == ord("s"):
                self.save_zones()

                # Generate and display the zone coordinates
                self.print_zone_coordinates()

            # 'q' to quit
            elif key == ord("q") or key == 27:  # 'q' or ESC
                save_prompt = input("Save zones before quitting? (y/n): ")
                if save_prompt.lower() == "y":
                    self.save_zones()
                    self.print_zone_coordinates()
                break

        cv2.destroyAllWindows()

    def print_zone_coordinates(self):
        """Print the zone coordinates in a format that can be copied into code."""
        if not self.zones:
            print("No zones defined")
            return

        print("\n" + "=" * 50)
        print("ZONE COORDINATES")
        print("=" * 50)
        print("You can copy these into your code:")
        print()
        print("sample_zones = {")

        for i, (zone_id, zone_info) in enumerate(self.zones.items()):
            print(f'    "{zone_id}": {{')
            print(f"        \"name\": \"{zone_info['name']}\",")
            print(f"        \"color\": {zone_info['color']},")
            print(f"        \"points\": {zone_info['points']}")
            if i < len(self.zones) - 1:
                print("    },")
            else:
                print("    }")

        print("}")
        print("=" * 50)


def extract_frame_from_video(video_path, frame_number=100):
    """Extract a specific frame from a video file.

    Args:
        video_path: Path to the video file
        frame_number: Which frame to extract (default: 100)

    Returns:
        The extracted frame as a numpy array, or None if extraction failed
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} not found")
        return None

    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_path}")
            return None

        # Get total frame count
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_number >= total_frames:
            print(
                f"Warning: Requested frame {frame_number} exceeds total frames {total_frames}"
            )
            print(f"Using last frame instead")
            frame_number = total_frames - 1

        # Set position to the requested frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        # Read the frame
        ret, frame = cap.read()

        # Release the video capture
        cap.release()

        if ret:
            print(f"Successfully extracted frame {frame_number} from {video_path}")
            return frame
        else:
            print(f"Error: Could not read frame {frame_number} from {video_path}")
            return None

    except Exception as e:
        print(f"Error extracting frame: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Zone Definition Tool")
    parser.add_argument(
        "--image",
        type=str,
        help="Path to background image for zone definition",
        default=None,
    )
    parser.add_argument(
        "--video",
        type=str,
        help="Path to video file to extract frame from",
        default=None,
    )
    parser.add_argument(
        "--frame",
        type=int,
        help="Frame number to extract from video (default: 100)",
        default=100,
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to save zone configuration",
        default="zones.json",
    )

    args = parser.parse_args()

    # Determine image source - either direct image file or frame from video
    image_path = args.image

    # If video is provided, extract the specified frame and use it as background
    if args.video:
        print(f"Extracting frame {args.frame} from {args.video} for zone definition...")
        extracted_frame = extract_frame_from_video(args.video, args.frame)

        if extracted_frame is not None:
            # Save the frame as a temporary image
            temp_image_path = "temp_frame.jpg"
            cv2.imwrite(temp_image_path, extracted_frame)
            image_path = temp_image_path
            print(f"Saved extracted frame to {temp_image_path}")

    # Create and run the tool
    tool = ZoneDefinitionTool(image_path, args.config)
    tool.run()

    # Clean up temporary file if it was created
    if args.video and os.path.exists("temp_frame.jpg"):
        try:
            os.remove("temp_frame.jpg")
            print("Removed temporary frame image")
        except:
            pass


if __name__ == "__main__":
    main()
