import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import argparse
import os
import urllib.request
import sys

# Visualization constants
MARGIN = 0
ROW_SIZE = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
TEXT_COLOR = (255, 0, 0)  # red


def visualize(image, detection_result):
    """Draws bounding boxes on the input image and return it."""
    for detection in detection_result.detections:
        # Draw bounding_box
        bbox = detection.bounding_box
        start_point = bbox.origin_x, bbox.origin_y
        end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
        cv2.rectangle(image, start_point, end_point, TEXT_COLOR, 3)

        # Draw label and score
        category = detection.categories[0]
        category_name = category.category_name
        probability = round(category.score, 2)
        result_text = category_name + " (" + str(probability) + ")"
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

    return image


def process_video(
    input_path,
    output_path=None,
    model_path="efficientdet.tflite",
    score_threshold=0.40,
    use_webcam=False,
    use_gpu=False,
):
    """Process a video with object detection."""
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

        # Draw bounding boxes and labels
        annotated_frame = visualize(rgb_frame.copy(), detection_result)

        # Convert back to BGR for OpenCV display/saving
        annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)

        # Display the frame
        cv2.imshow("Object Detection", annotated_frame)

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
    parser = argparse.ArgumentParser(description="Object Detection on Video")
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

    args = parser.parse_args()

    # Download the model if it doesn't exist
    if not download_model(args.model):
        print("Could not obtain the model file. Exiting.")
        return
        print(f"Error: Model file {args.model} not found")
        return

    # Ensure input is provided if not using webcam
    if not args.webcam and not args.input:
        parser.error("--input is required when not using --webcam")

    # If using input file, ensure it exists
    if not args.webcam and not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found")
        return

    process_video(
        input_path=args.input,
        output_path=args.output,
        model_path=args.model,
        score_threshold=args.threshold,
        use_webcam=args.webcam,
        use_gpu=args.gpu,
    )


if __name__ == "__main__":
    main()
