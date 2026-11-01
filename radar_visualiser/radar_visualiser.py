import cv2
import numpy as np

class RadarVisualizer:
    def __init__(self, width=400, height=200):
        self.width = width
        self.height = height
        self.pitch_width = 68     # meters
        self.pitch_length = 23.32 # meters

    def draw_radar(self, tracks, frame_num):
        # Create empty radar (green background)
        radar = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        radar[:] = (0, 128, 0)  # dark green pitch

        # Draw pitch outline
        cv2.rectangle(radar, (0, 0), (self.width-1, self.height-1), (255, 255, 255), 2)

        for object, object_tracks in tracks.items():
            if frame_num >= len(object_tracks):
                continue
            for track_id, track_info in object_tracks[frame_num].items():
                pos = track_info.get("position_transformed", None)
                if pos is None:
                    continue

                x, y = pos
                # Map real-world coords -> radar coords
                rx = int((x / self.pitch_width) * self.width)
                ry = int((y / self.pitch_length) * self.height)

                # Different colors for ball vs players
                if object == "ball":
                    color = (0, 255, 255)  # yellow
                else:
                    color = (0, 0, 255) if track_id % 2 == 0 else (255, 0, 0)  # red/blue

                cv2.circle(radar, (rx, ry), 5, color, -1)
                cv2.putText(radar, str(track_id), (rx+6, ry-6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        return radar
