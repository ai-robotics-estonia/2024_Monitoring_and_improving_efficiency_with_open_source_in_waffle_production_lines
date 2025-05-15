# Zone-Based Person Detection System: Complete Guide

This guide covers how to set up and use a zone-based person detection system that:
1. Detects people in video surveillance footage or live camera feeds
2. Tracks which predefined zones they enter and exit
3. Logs all zone entries and exits with timestamps
4. Creates annotated videos showing people detected and their zone locations

## Installation and Requirements

### 1. Prerequisites

- Python 3.7+
- OpenCV
- NumPy
- MediaPipe

### 2. Installation

Install the required packages:

```bash
pip install opencv-python numpy mediapipe
```

### 3. Download the Code

Save the two Python scripts:
- `zone_definition_tool.py` - For defining zones
- `zone_detection.py` - For performing detection with zones

## System Workflow

The workflow consists of two main steps:

1. **Define zones** on a frame from your video using the Zone Definition Tool
2. **Run detection** on your video with the predefined zones

## Step 1: Defining Zones

Zones are areas in your video that you want to monitor for people entering and exiting. The definition tool lets you create these by clicking points on an actual frame from your video.

### Running the Zone Definition Tool

```bash
python zone_definition_tool.py --video your_surveillance_video.mp4 --frame 100
```

This extracts the 100th frame from your video and opens it in the zone definition interface.

### Zone Definition Interface Controls

- **N**: Create a new zone
  - You'll be prompted to enter a name for the zone
  - If you don't enter a name, it will use the default ("Green Zone", "Orange Zone", etc.)
  
- **Left Click**: Add a point to the current zone boundary
  - Click multiple times to create a polygon shape
  - The coordinates of each point are shown on screen
  
- **C**: Complete the current zone
  - Finalizes the zone you're currently creating
  - Must have at least 3 points
  
- **R**: Reset the current zone
  - Clears all points for the zone you're creating
  - Lets you start over without saving
  
- **D**: Delete an existing zone
  - Shows a list of existing zones
  - Enter the number of the zone to delete
  
- **S**: Save all zones
  - Saves your zones to a JSON file (default: `zones.json`)
  - Also prints the zone coordinates in a format you can copy into code
  
- **Q**: Quit the tool
  - Asks if you want to save before exiting

### Example: Creating Two Zones

1. Run the tool: `python zone_definition_tool.py --video factory.mp4`
2. Press **N** to create a new zone
3. Enter "Production Area" as the zone name
4. Click 4-6 points to outline the production area
5. Press **C** to complete the zone
6. Press **N** again to create a second zone
7. Enter "Storage Area" as the zone name
8. Click points to outline the storage area
9. Press **C** to complete the zone
10. Press **S** to save your zones
11. Press **Q** to quit

Your zones are now saved in `zones.json` and ready for use with the detection system.

## Step 2: Running Person Detection with Zone Tracking

Once you have defined your zones, you can run the detection system on your video.

### Basic Usage

```bash
python zone_detection.py --input your_video.mp4 --output results.mp4
```

This will:
1. Load your zones from `zones.json`
2. Process the input video
3. Detect people in each frame
4. Determine which zone each person is in
5. Log zone entries and exits
6. Create an annotated output video

### Command Line Options

```
--input VIDEO       Path to input video file
--output VIDEO      Path to output video file (optional)
--model MODEL       Path to TFLite model (default: efficientdet.tflite)
--threshold FLOAT   Detection confidence threshold (default: 0.5)
--webcam            Use webcam instead of video file
--gpu               Enable GPU acceleration with CUDA
--zones FILE        Path to zone configuration (default: zones.json)
--log FILE          Path to log file (default: zone_entries.log)
```

### Examples

**Process a video file:**
```bash
python zone_detection.py --input surveillance.mp4 --output annotated.mp4
```

**Use a webcam:**
```bash
python zone_detection.py --webcam --output recording.mp4
```

**Adjust detection sensitivity:**
```bash
python zone_detection.py --input video.mp4 --threshold 0.6
```

**Use a custom zone configuration:**
```bash
python zone_detection.py --input video.mp4 --zones custom_zones.json
```

## Output and Results

### Annotated Video

The output video includes:
- Bounding boxes around detected people
- Person labels with detection confidence
- Color-coded zone areas
- Text showing which zone each person is in
- Zone occupancy statistics

### Zone Entry/Exit Log

A log file (default: `zone_entries.log`) records:
- When each person enters a zone
- When each person exits a zone
- Timestamps for all events

Example log entries:
```
2025-04-09 09:15:23 - Object person_1 (person) entered Production Area
2025-04-09 09:15:25 - Object person_1 (person) exited Production Area
2025-04-09 09:15:25 - Object person_1 (person) entered Storage Area
```

## Advanced Usage

### Using Custom Detection Models

The system uses MediaPipe's EfficientDet Lite model by default, but you can provide your own model:

```bash
python zone_detection.py --input video.mp4 --model your_model.tflite
```

### GPU Acceleration

If you have a CUDA-compatible GPU, you can enable GPU acceleration:

```bash
python zone_detection.py --input video.mp4 --gpu
```

### Troubleshooting

**Low Detection Rate:**
- Try lowering the detection threshold: `--threshold 0.3`
- Ensure adequate lighting in the video

**False Positives:**
- Increase the detection threshold: `--threshold 0.7`

**Performance Issues:**
- Use a lower resolution video
- If available, enable GPU acceleration: `--gpu`

**Zone Detection Problems:**
- Make sure zone boundaries are clearly defined
- Verify the zone configuration file exists
- Check that people detection is working properly first

## Technical Details

### Zone Definition Format

Zones are stored in a JSON file with this structure:

```json
{
  "zone1": {
    "name": "Production Area",
    "color": [0, 255, 0],
    "points": [[100, 100], [400, 100], [400, 400], [100, 400]]
  },
  "zone2": {
    "name": "Storage Area",
    "color": [0, 165, 255],
    "points": [[500, 100], [800, 100], [800, 400], [500, 400]]
  }
}
```

### Detection Algorithm

1. For each frame:
   - Run person detection using MediaPipe
   - Obtain bounding boxes for each detected person
   - For each person:
     - Determine the "foot position" (bottom center of bounding box)
     - Check which zone this position falls within
     - Log if the person has entered a new zone or exited a previous one

### Zone Determination

The system uses a point-in-polygon algorithm to determine if a person is inside a zone. This algorithm:
1. Casts a ray from the person's position
2. Counts how many times the ray crosses zone boundaries
3. If the count is odd, the person is inside the zone

## Additional Notes

- For real-time monitoring systems, consider setting up automated alerts when people enter specific zones
- The zone configuration can be customized manually in the JSON file if needed
- Multiple videos can use the same zone configuration if the camera position remains consistent
