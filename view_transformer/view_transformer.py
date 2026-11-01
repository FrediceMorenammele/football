import numpy as np
import cv2

class ViewTransformer():
    def __init__(self):
        court_width = 68     # meters
        court_length = 23.32 # meters

        # Points in the video (pixel space)
        self.pixel_vertices = np.array([
            [110, 1035],
            [265, 275],
            [910, 260],
            [1640, 915]
        ], dtype=np.float32)

        # Corresponding points in real-world coordinates
        self.target_vertices = np.array([
            [0, court_width],
            [0, 0],
            [court_width, 0],
            [court_width, court_length]
        ], dtype=np.float32)

        self.perspective_transformer = cv2.getPerspectiveTransform(
            self.pixel_vertices, self.target_vertices
        )

    def transform_point(self, point):
        """Convert a pixel point to real-world coordinates."""
        reshaped_point = point.reshape(-1, 1, 2).astype(np.float32)
        transformed_point = cv2.perspectiveTransform(
            reshaped_point, self.perspective_transformer
        )
        return transformed_point.reshape(-1, 2)

    def add_transformed_positions_to_tracks(self, tracks):
        """Add position_transformed (real-world) to each object track."""
        for object, object_tracks in tracks.items():
            for frame_num, track in enumerate(object_tracks):
                for track_id, track_info in track.items():
                    position = track_info['position_adjusted']
                    position = np.array(position, dtype=np.float32)  # (2,)
                    position_transformed = self.transform_point(position)
                    if position_transformed is not None:
                        position_transformed = position_transformed.squeeze().tolist()
                    tracks[object][frame_num][track_id]['position_transformed'] = position_transformed
