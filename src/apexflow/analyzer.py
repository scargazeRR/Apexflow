import cv2
import time
from ultralytics import YOLO

def scan_for_highlights(video_path, sensitivity=40, padding=5, min_length=3, progress_callback=None):
    print(f"Starte KI-Analyse für: {video_path}")
    print(f"Aktive Parameter -> Sensitivity: {sensitivity} | Padding: {padding}s | Min Length: {min_length}s")
    
    model = YOLO('yolov8n-pose.pt')
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Fehler: Video konnte nicht geöffnet werden.")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Überspringe Frames, um die Analyse zu beschleunigen (wir analysieren 3 Frames pro Sekunde)
    frame_skip = int(fps / 3) 
    current_frame = 0
    
    highlights = []
    is_in_highlight = False
    highlight_start_time = 0

    while cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        
        if not ret:
            break

        # Verkleinern für schnellere Analyse
        frame_resized = cv2.resize(frame, (640, 360))
        results = model(frame_resized, verbose=False)
        
        timestamp_sec = current_frame / fps
        highlight_detected = False
        
        for r in results:
            if r.keypoints and r.keypoints.xy.numel() > 0:
                keypoints = r.keypoints.xy[0]
                
                try:
                    left_shoulder = keypoints[5]
                    right_shoulder = keypoints[6]
                    
                    # FILTER: Verliert YOLO die Schultern, ignorieren
                    if left_shoulder[0] == 0.0 or right_shoulder[0] == 0.0:
                        continue
                    
                    body_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
                    offset_from_center = abs(body_center_x - 320)
                    
                    if offset_from_center > sensitivity:
                        highlight_detected = True
                        
                except IndexError:
                    pass

        if highlight_detected and not is_in_highlight:
            is_in_highlight = True
            highlight_start_time = max(0, timestamp_sec - padding) 
            print(f"🔥 Interessante Kurve erkannt bei {time.strftime('%M:%S', time.gmtime(timestamp_sec))}!")
            
        elif not highlight_detected and is_in_highlight:
            is_in_highlight = False
            highlight_end_time = timestamp_sec + padding 
            highlights.append((highlight_start_time, highlight_end_time))
            
        current_frame += frame_skip
        
        # Fortschritt an die GUI (Ladebalken) senden
        if progress_callback:
            progress_callback(current_frame / total_frames)

    # Letztes Highlight abschließen, falls das Video mitten in einer Kurve endet
    if is_in_highlight:
        highlights.append((highlight_start_time, (total_frames / fps)))

    cap.release()
    
    # 1. Überschneidende Clips zu einem langen Clip zusammenfügen
    merged_highlights = []
    for start, end in highlights:
        if merged_highlights and start <= merged_highlights[-1][1]:
            merged_highlights[-1] = (merged_highlights[-1][0], max(merged_highlights[-1][1], end))
        else:
            merged_highlights.append((start, end))

    # 2. NEU: Zu kurze Clips (z. B. durch Wackler oder Fehler) ignorieren
    final_highlights = []
    for start, end in merged_highlights:
        clip_duration = end - start
        if clip_duration >= min_length:
            final_highlights.append((start, end))
            
    print(f"Analyse abgeschlossen. {len(final_highlights)} gültige Highlights gefunden (zu kurze ignoriert).")
    return final_highlights