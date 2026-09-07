"""Entry point for the AIP subsystem."""
from camera import Camera
from aruco import detect_aruco, draw_aruco
from display import close_display, display_frame
    
def main():
    """Capture and display camera frames until Q, Escape, or Ctrl+C."""
    camera = Camera()

    print("AIP system started. Press Q or Escape in the frame window to quit.")

    try:
        while True:
            # Get the next BGR frame from OAK-D Lite
            frame = camera.get_frame()

            if frame is None:
                continue

            # Pass the same frame to each processing module
            
            # ArUco detection NOTE need to implement positional detection of marker
            corners, ids = detect_aruco(frame)
            
            # valve_result = detect_valve(frame)
            
            # gauge_result = detect_gauge(frame)

            # Annotate the frame with the results of each module
            annotated = draw_aruco(frame, corners, ids)
            
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
