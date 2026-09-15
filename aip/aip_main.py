"""Entry point for the AIP subsystem."""
import argparse

from camera import Camera
from aruco import detect_aruco, draw_aruco
from display import close_display, display_frame
from pose import PoseEstimator
    
def main():
    """Capture and display camera frames until Q, Escape, or Ctrl+C."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marker-size-mm", type=float, default=200.0,
                        help="Outer black square side length in millimetres (default: 200)")
    args = parser.parse_args()
    estimator = PoseEstimator(args.marker_size_mm / 1000)
    camera = Camera()

    print("AIP system started. Press Q or Escape in the frame window to quit.")

    try:
        while True:
            # Get the next BGR frame from OAK-D Lite
            frame = camera.get_frame()

            if frame is None:
                continue

            # Pass the same frame to each processing module
            
            # Identify each marker and locate the camera relative to it.
            corners, ids = detect_aruco(frame)
            poses = estimator.estimate(frame, corners, ids)
            
            # valve_result = detect_valve(frame)
            
            # gauge_result = detect_gauge(frame)

            # Annotate the frame with the results of each module
            annotated = draw_aruco(frame, corners, ids)
            estimator.draw(annotated, poses)
            
            if not display_frame(annotated):
                break
            
            
    except KeyboardInterrupt:
        print("Stopping AIP system")

    finally:
        try:
            camera.close()
        finally:
            close_display()


if __name__ == "__main__":
    main()
