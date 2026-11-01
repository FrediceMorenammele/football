import numpy as np
import os
import cv2
from utils import save_video, read_video
from trackers import Tracker
from team_assigner import TeamAssigner
from player_ball_assginer import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistanceEstimator
import firebase_admin
import supervision as sv
from firebase_admin import credentials, firestore


# Initialize Firebase
cred = credentials.Certificate("footballanalysisapp-f71c3-firebase-adminsdk-fbsvc-9dadc9be59.json")  # Path to your key
firebase_admin.initialize_app(cred)
db = firestore.client()
print("Connection Established")

def save_possession_to_firebase(team_ball_control, tracks):
    final_possession_team = int(team_ball_control[-1])

    team1_possession = (team_ball_control == 1).sum() / len(team_ball_control) * 100
    team2_possession = (team_ball_control == 2).sum() / len(team_ball_control) * 100

    team_stats = {
        1: {'total_distance': 0.0, 'total_speed': 0.0, 'count': 0},
        2: {'total_distance': 0.0, 'total_speed': 0.0, 'count': 0}
    }
    player_stats = {} 


    for frame_data in tracks['players']:
        for player_id, player_data in frame_data.items():
            team = player_data.get('team')
            if team not in (1, 2):
                continue

            speed = player_data.get('speed')
            distance = player_data.get('distance')


            if player_id not in player_stats:
                player_stats[player_id] = {
                    'team': team,
                    'total_distance': 0.0,
                    'total_speed': 0.0,
                    'count': 0
                }


            if speed is not None:
                team_stats[team]['total_speed'] += speed
                team_stats[team]['count'] += 1
                player_stats[player_id]['total_speed'] += speed
                player_stats[player_id]['count'] += 1

            if distance is not None:
                team_stats[team]['total_distance'] += distance
                player_stats[player_id]['total_distance'] += distance


    for team in team_stats:
        if team_stats[team]['count'] > 0:
            team_stats[team]['avg_speed'] = team_stats[team]['total_speed'] / team_stats[team]['count']
        else:
            team_stats[team]['avg_speed'] = 0.0

    for player_id, p in player_stats.items():
        if p['count'] > 0:
            p['avg_speed'] = p['total_speed'] / p['count']
        else:
            p['avg_speed'] = 0.0


    possession_ref = db.collection("Matchs").document("match1")
    possession_ref.set({
        "Date": "2025-09-21",
        "Team1Possession": round(team1_possession, 2),
        "Team2Possession": round(team2_possession, 2),
        "Team1_AvgSpeed": round(team_stats[1]['avg_speed'], 2),
        "Team1_TotalDistance": round(team_stats[1]['total_distance'], 2),
        "Team2_AvgSpeed": round(team_stats[2]['avg_speed'], 2),
        "Team2_TotalDistance": round(team_stats[2]['total_distance'], 2)
    })
    print("✅ Team possession, speed, and distance uploaded to Firebase.")


    players_collection = possession_ref.collection("Players")

    for player_id, stats in player_stats.items():
        players_collection.document(str(player_id)).set({
            "Team": int(stats["team"]),
            "AvgSpeed": round(stats["avg_speed"], 2),
            "TotalDistance": round(stats["total_distance"], 2)
        })

    print(f"✅ Uploaded {len(player_stats)} player stats to Firebase.")


def generate_heatmap_from_tracks(tracks, pitch_image_path='tracking_data/pitch_reference_1.jpg',
                                 pitch_width=68, pitch_length=23.32, scale=8,
                                 output_path='output_videos/heatmap_overlay.jpg'):
    """
    Generates and overlays a heatmap of player positions onto a football pitch image.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Load the pitch image
    pitch = cv2.imread(pitch_image_path)
    if pitch is None:
        print("⚠️ Could not load pitch image, generating plain heatmap instead.")
        pitch = np.zeros((int(pitch_length * scale), int(pitch_width * scale), 3), dtype=np.uint8)
        pitch[:] = (0, 128, 0)  # fallback green background

    # Resize pitch to match heatmap scale
    heatmap_w = int(pitch_width * scale)
    heatmap_h = int(pitch_length * scale)
    pitch = cv2.resize(pitch, (heatmap_w, heatmap_h))

    # Create heatmap accumulator
    heatmap = np.zeros((heatmap_h, heatmap_w), dtype=np.float32)

    # Loop through all frames and player positions
    for frame_data in tracks["players"]:
        for player_id, player_data in frame_data.items():
            pos = player_data.get("position_transformed")
            if pos is None:
                continue
            x, y = pos
            px = int((x / pitch_width) * heatmap_w)
            py = int((y / pitch_length) * heatmap_h)
            if 0 <= px < heatmap_w and 0 <= py < heatmap_h:
                heatmap[py, px] += 1

    # Smooth and normalize
    heatmap = cv2.GaussianBlur(heatmap, (31, 31), 0)
    heatmap = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # Apply colormap
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    # Blend heatmap with pitch image
    overlay = cv2.addWeighted(pitch, 0.6, heatmap_color, 0.5, 0)

    # Add outline
    cv2.rectangle(overlay, (1, 1), (heatmap_w - 2, heatmap_h - 2), (255, 255, 255), 2)

    # Save
    cv2.imwrite(output_path, overlay)
    print(f"✅ Heatmap overlay saved to: {output_path}")

def main():
    
    # Read Video    
    video_frames = read_video('input_videos/08fd33_4.mp4')
    
    # Initialise Tracker
    tracker = Tracker('models/best.pt')

    tracks = tracker.get_object_tracks(video_frames, read_from_stub=True, stub_path='stubs/track_stubs.pk1')

    # Get Object Positions
    tracker.add_position_to_tracks(tracks)

    # Camera_movement_Estimator
    camera_movement_estimator = CameraMovementEstimator(video_frames[0])
    camera_movement_per_frame = camera_movement_estimator.get_camera_movement(video_frames, read_from_stub=True, stub_path='stubs/camera_movement_stub.pk1')
    camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

    # View Transformer
    view_transformer = ViewTransformer()
    view_transformer.add_transformed_positions_to_tracks(tracks)


    # Interpolate Ball Positions
    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

    # Speed and Distance Estimator
    speed_and_distance_estimator = SpeedAndDistanceEstimator()
    speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

    # Assign Player Teams
    team_assigner = TeamAssigner()
    team_assigner.assign_team_color(video_frames[0], tracks['players'][0])
    for frame_num, player_track in enumerate(tracks['players']):
        for player_id, track in player_track.items():
            team = team_assigner.get_player_team(video_frames[frame_num], track['bbox'], player_id)
            tracks['players'][frame_num][player_id]['team'] = team
            tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]


    # Assign ball Aquisition
    player_assigner = PlayerBallAssigner()
    team_ball_control = []
    for frame_num, player_track in enumerate(tracks['players']):
        ball_bbox = tracks['ball'][frame_num][1]['bbox']
        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
        else:
            team_ball_control.append(team_ball_control[-1])
    team_ball_control = np.array(team_ball_control)
    save_possession_to_firebase(team_ball_control, tracks)


    



    # Save  cropped image of a player
    '''for track_id, player in tracks['players'][0].items():
        bbox = player['bbox']  
        frame = video_frames[0]

        # Crop bbox from frame
        cropped_image = frame[int(bbox[1]):int(bbox[3]), int(bbox[0]):int(bbox[2])]

        # Save the cropped image
        cv2.imwrite(f'output_videos/cropped_img.jpg', cropped_image)
        break
    '''




    
    # Draw object tracks
    output_video_frames =  tracker.draw_annotations(video_frames, tracks, team_ball_control)

    # Draw camera movement
    output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)

    # Draw speed and distance
    # speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)
    speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)  
    
    generate_heatmap_from_tracks(tracks)

    # Save Video
    save_video(output_video_frames, 'output_videos/output_video.avi')



if __name__ == '__main__':
    main()