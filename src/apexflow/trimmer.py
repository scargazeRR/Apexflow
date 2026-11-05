import os
import subprocess
import imageio_ffmpeg

def extract_clips(video_path, highlights, output_dir="./exports"):
    if not highlights:
        print("Keine Highlights zum Schneiden gefunden.")
        return []

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(video_path)
    name, ext = os.path.splitext(base_name)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Temporärer Ordner für die Einzelschnipsel
    temp_dir = os.path.join(output_dir, "temp_clips")
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"\nSchneide {len(highlights)} Segmente...")
    clip_paths = []
    
    # 1. Alle Clips einzeln schneiden
    for i, (start_time, end_time) in enumerate(highlights):
        temp_filepath = os.path.join(temp_dir, f"clip_{i:03d}{ext}")
        duration = end_time - start_time
        
        cmd = [
            ffmpeg_exe, "-y", 
            "-ss", str(start_time), "-i", video_path, 
            "-t", str(duration), "-c", "copy", temp_filepath
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            clip_paths.append(temp_filepath)
        except Exception as e:
            print(f"Fehler bei Segment {i}: {e}")
            
    # 2. Textdatei für FFmpeg Concat vorbereiten
    concat_list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for cp in clip_paths:
            # FFmpeg verlangt Forward-Slashes im Pfad, auch unter Windows
            f.write(f"file '{os.path.abspath(cp).replace(os.sep, '/')}'\n")
            
    # 3. Clips zu einem Video zusammenfügen (Lossless)
    final_output = os.path.join(output_dir, f"APEX_HIGHLIGHTS_{name}{ext}")
    print("Füge Clips zum finalen Video zusammen...")
    
    concat_cmd = [
        ffmpeg_exe, "-y", 
        "-f", "concat", "-safe", "0", 
        "-i", concat_list_path, 
        "-c", "copy", final_output
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # 4. Aufräumen (Temp-Ordner und Einzelschnipsel restlos löschen)
    for cp in clip_paths:
        try: os.remove(cp)
        except: pass
    try: os.remove(concat_list_path)
    except: pass
    try: os.rmdir(temp_dir)
    except: pass
    
    print(f"✅ Finales Highlight-Video erstellt: {final_output}")
    return [final_output]