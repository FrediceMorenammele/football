import cv2
import sys
sys.path.append('../')
from utils import measure_distance, get_foot_position

class SpeedAndDistanceEstimator():
    def __init__(self, frame_rate=24):
        self.frame_rate = frame_rate  # fps

    def add_speed_and_distance_to_tracks(self, tracks):
        """Calculate per-frame speed (km/h) and cumulative distance (m)."""
        total_distance = {}

        for object, object_tracks in tracks.items():
            if object in ['ball', 'referees']:
                continue

            number_of_frames = len(object_tracks)

            for frame_num in range(1, number_of_frames):  # start from frame 1
                for track_id, track_info in object_tracks[frame_num].items():
                    if track_id not in object_tracks[frame_num - 1]:
                        continue

                    start_position = object_tracks[frame_num - 1][track_id].get('position_transformed')
                    end_position = track_info.get('position_transformed')

                    if start_position is None or end_position is None:
                        continue

                    # Distance covered in this frame interval
                    distance_covered = measure_distance(start_position, end_position)

                    # Accumulate distance
                    if object not in total_distance:
                        total_distance[object] = {}
                    if track_id not in total_distance[object]:
                        total_distance[object][track_id] = 0
                    total_distance[object][track_id] += distance_covered

                    # Compute speed (m/s -> km/h)
                    time_elapsed = 1 / self.frame_rate
                    speed_mps = distance_covered / time_elapsed
                    speed_kph = speed_mps * 3.6

                    # Save into track info
                    track_info['speed'] = speed_kph
                    track_info['distance'] = total_distance[object][track_id]

    def draw_speed_and_distance(self, frames, tracks):
        """Overlay speed & distance text on frames."""
        output_frames = []
        for frame_num, frame in enumerate(frames):
            for object, object_tracks in tracks.items():
                if object in ['ball', 'referees']:
                    continue
                for _, track_info in object_tracks[frame_num].items():
                    if 'speed' in track_info and 'distance' in track_info:
                        speed = track_info['speed']
                        distance = track_info['distance']

                        bbox = track_info['bbox']
                        position = get_foot_position(bbox)
                        position = list(position)
                        position[1] += 40  # shift text slightly below feet
                        position = tuple(map(int, position))

                        cv2.putText(frame, f"{speed:.1f} km/h", position,
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                        cv2.putText(frame, f"{distance:.1f} m",
                                    (position[0], position[1] + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            output_frames.append(frame)
        return output_frames