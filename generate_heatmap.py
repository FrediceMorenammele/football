import cv2
import numpy as np
import os

# === Settings ===
VIDEO_PATH = "input_videos/08fd33_4.mp4"   # change if needed
OUT_HEATMAP = "output_videos/player_heatmap.jpg"
OUT_OVERLAY = "output_videos/player_heatmap_overlay.jpg"  # optional overlay on first frame
SCALE = 8                # pixels per meter for bird-eye image (tweak for size/detail)
BG_SAMPLES = 8           # how many frames to sample to build median background
HEATMAP_SAMPLES = 120    # how many frames to sample across the video to build heatmap
BLUR_KSIZE = (15, 15)    # smoothing kernel on final heatmap
DIFF_THRESH = 30         # threshold for motion detection (gray diff -> mask)
MIN_FRAME_READ = 20      # fallback minimum number of samples
# ==================

os.makedirs(os.path.dirname(OUT_HEATMAP), exist_ok=True)

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
ret, first_frame = cap.read()
if not ret:
    cap.release()
    raise RuntimeError("Failed to read first frame")

h, w = first_frame.shape[:2]

# === Homography (from your ViewTransformer earlier) ===
src_pts = np.array([
    [110, 1035],
    [265, 275],
    [910, 260],
    [1640, 915]
], dtype=np.float32)

# pitch dimensions used previously
court_width_m = 68.0
court_length_m = 23.32

dst_w = int(court_width_m * SCALE)
dst_h = int(court_length_m * SCALE)

dst_pts = np.array([
    [0, dst_h],
    [0, 0],
    [dst_w, 0],
    [dst_w, dst_h]
], dtype=np.float32)

M = cv2.getPerspectiveTransform(src_pts, dst_pts)
heatmap_accum = np.zeros((dst_h, dst_w), dtype=np.float32)

# Build median background from a few samples
num_bg_samples = max(3, min(BG_SAMPLES, frame_count))
bg_indices = np.linspace(0, max(0, frame_count - 1), num=num_bg_samples, dtype=int)
bg_frames = []
for idx in bg_indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
    ok, f = cap.read()
    if not ok:
        continue
    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    bg_frames.append(gray)
if not bg_frames:
    cap.release()
    raise RuntimeError("Couldn't collect background frames")

bg_median = np.median(np.stack(bg_frames, axis=0), axis=0).astype(np.uint8)

# Sample a limited number of frames evenly across the video
target_samples = max(MIN_FRAME_READ, min(HEATMAP_SAMPLES, int((frame_count / max(1,fps)) * 4)))
indices = np.linspace(0, max(0, frame_count - 1), num=target_samples, dtype=int)

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
processed = 0
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
    ok, f = cap.read()
    if not ok:
        continue
    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray, bg_median)
    _, mask = cv2.threshold(diff, DIFF_THRESH, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=1)
    warped = cv2.warpPerspective(mask, M, (dst_w, dst_h), flags=cv2.INTER_LINEAR)
    heatmap_accum += (warped.astype(np.float32) / 255.0)
    processed += 1

cap.release()

if processed == 0:
    raise RuntimeError("No frames processed for heatmap (try increasing samples or check video)")

# Smooth and colorize
heatmap_blur = cv2.GaussianBlur(heatmap_accum, BLUR_KSIZE, 0)
heatmap_norm = cv2.normalize(heatmap_blur, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
# add a pitch outline for context
cv2.rectangle(heatmap_color, (1,1), (dst_w-2, dst_h-2), (255,255,255), 2)
cv2.imwrite(OUT_HEATMAP, heatmap_color)
print(f"Heatmap saved to {OUT_HEATMAP} (processed samples: {processed})")

# OPTIONAL: overlay heatmap on first frame (inverse-warp to video-plane)
# Resize heatmap_color to first_frame size by inverse-warping or simple overlay at corner.
# Here we optionally place the top-down heatmap at top-left (scaled) onto the first frame.
overlay = first_frame.copy()
# scale up or down heatmap to fit small corner, or inverse-warp for exact alignment.
corner_h = int(dst_h)
corner_w = int(dst_w)
if corner_h < overlay.shape[0] and corner_w < overlay.shape[1]:
    # resize small heatmap to fit corner for visualization
    resized = cv2.resize(heatmap_color, (corner_w, corner_h))
    alpha = 0.6
    overlay[0:corner_h, 0:corner_w] = cv2.addWeighted(overlay[0:corner_h, 0:corner_w], 1-alpha, resized, alpha, 0)
    cv2.imwrite(OUT_OVERLAY, overlay)
    print(f"Overlay image saved to {OUT_OVERLAY}")
