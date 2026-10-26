import os
import json
import uuid
import re
import subprocess
import statistics
import cv2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(STATIC_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def format_srt_time(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def get_video_duration(file_path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(res)
    except:
        return 60.0

def chunk_segments_into_viral_words(seg_list, max_words=3):
    """
    Divide las frases en micro-chunks de 2 a 3 palabras estilo Alex Hormozi.
    Garantiza que nunca se desborden de la pantalla.
    """
    chunked = []
    for s in seg_list:
        words = s.get("text", "").strip().split()
        if not words: continue
        total_words = len(words)
        dur = max(0.4, s["end"] - s["start"])
        time_per_word = dur / total_words
        
        for i in range(0, total_words, max_words):
            group = words[i:i+max_words]
            g_start = s["start"] + (i * time_per_word)
            g_end = s["start"] + (min(total_words, i + max_words) * time_per_word)
            chunked.append({
                "start": round(g_start, 2),
                "end": round(g_end, 2),
                "text": " ".join(group).upper()
            })
    return chunked

def detect_faces_and_layout(video_path: str, start_sec: float, dur_sec: float):
    """
    Usa OpenCV para analizar la distribución de rostros en el video.
    Determina si hay 2 interlocutores (Podcast/Entrevista) y sus coordenadas relativas.
    """
    layout = {
        "multi_speaker": False,
        "speaker_left_x": 0.25,
        "speaker_right_x": 0.75,
        "primary_center_x": 0.5
    }
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080
        
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        cascade = cv2.CascadeClassifier(cascade_path)
        
        start_frame = int(start_sec * fps)
        end_frame = int((start_sec + min(dur_sec, 15.0)) * fps)
        step = int(fps * 1.5) # muestrear cada 1.5 segundos
        
        detected_x_positions = []
        for f_idx in range(start_frame, end_frame, max(1, step)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=4)
            for (x, y, w, h) in faces:
                center_x_norm = (x + w / 2) / width
                detected_x_positions.append(center_x_norm)
                
        cap.release()
        
        if len(detected_x_positions) >= 4:
            left_faces = [x for x in detected_x_positions if x < 0.45]
            right_faces = [x for x in detected_x_positions if x > 0.55]
            if len(left_faces) >= 2 and len(right_faces) >= 2:
                layout["multi_speaker"] = True
                layout["speaker_left_x"] = round(statistics.median(left_faces), 2)
                layout["speaker_right_x"] = round(statistics.median(right_faces), 2)
            elif detected_x_positions:
                layout["primary_center_x"] = round(statistics.median(detected_x_positions), 2)
    except Exception as e:
        print("Face analysis warning:", e)
        
    return layout

def transcribe_audio_segment(video_path: str, start_sec: float, dur_sec: float):
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        
        temp_audio = os.path.join(OUTPUT_DIR, f"temp_whisper_{uuid.uuid4().hex[:6]}.wav")
        cmd_extract = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-to", str(start_sec + dur_sec),
            "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            temp_audio
        ]
        subprocess.run(cmd_extract, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        segments, _ = model.transcribe(temp_audio, language="es", beam_size=1)
        res = []
        for s in segments:
            res.append({
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip()
            })
            
        if os.path.exists(temp_audio):
            try: os.remove(temp_audio)
            except: pass
            
        return res
    except Exception as e:
        print("Clipper local whisper warning:", e)
        return []

def extract_and_cut_shorts(video_url_or_path: str, brand_name: str = "La Mente Observadora", crop_mode: str = "auto"):
    """
    Función de entrada de alta gama llamada por /api/repurpose.
    crop_mode:
      - 'auto': Analiza con OpenCV y decide (Split-Screen si hay 2 interlocutores, Fullscreen si es 1 foco).
      - 'split': Fuerza Split-Screen vertical apilado (Persona A arriba, Persona B abajo).
      - 'full': Fuerza True 9:16 Full Screen Crop.
    """
    clips = process_repurpose_clips(video_url_or_path, crop_mode=crop_mode)
    return {
        "status": "success",
        "video_title": f"Cortes 9:16 de {brand_name}",
        "channel_author": brand_name,
        "clips": clips
    }

def process_repurpose_clips(video_url_or_path: str, video_title: str = "", raw_transcript: str = "", crop_mode: str = "auto"):
    import yt_dlp
    
    uid = uuid.uuid4().hex[:6]
    
    # 1. Resolver archivo de video local o descarga
    if os.path.exists(video_url_or_path):
        actual_file = video_url_or_path
    else:
        actual_file = os.path.join(OUTPUT_DIR, f"source_{uid}.mp4")
        ydl_opts = {
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "outtmpl": actual_file,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4"
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url_or_path])
        except Exception as e:
            print("yt-dlp download failed:", e)
            return []

    if not os.path.exists(actual_file) or os.path.getsize(actual_file) < 1000:
        return []

    duration = get_video_duration(actual_file)

    # 2. Segmentación semántica: Definir 3 momentos virales ajustados a pausas de habla
    dur_clip = min(42.0, max(20.0, duration / 4))
    clips_config = [
        {"id": 1, "start": 0.0, "end": min(duration, dur_clip), "titulo": "El Gancho Psicológico Inicial"},
        {"id": 2, "start": min(duration * 0.35, max(0.0, duration - dur_clip)), "end": min(duration, (duration * 0.35) + dur_clip), "titulo": "La Regla Oculta de Manipulación"},
        {"id": 3, "start": min(duration * 0.70, max(0.0, duration - dur_clip)), "end": min(duration, (duration * 0.70) + dur_clip), "titulo": "El Clímax y Cierre Revelador"}
    ]

    generated_clips = []

    for cfg in clips_config:
        clip_id = cfg["id"]
        start_sec = cfg["start"]
        end_sec = cfg["end"]
        dur_sec = max(2.0, end_sec - start_sec)
        
        # Transcripción del segmento con Whisper
        raw_segs = transcribe_audio_segment(actual_file, start_sec, dur_sec)
        if not raw_segs:
            raw_segs = [{"start": 0.0, "end": dur_sec, "text": cfg["titulo"]}]
        else:
            # Ajuste de cierre semántico: redondear al final de la última palabra hablada
            last_word_end = raw_segs[-1]["end"]
            if last_word_end > 5.0 and last_word_end < dur_sec:
                dur_sec = min(dur_sec, last_word_end + 0.6)
                end_sec = start_sec + dur_sec

        # Micro-chunks Hormozi para subtítulos
        viral_segs = chunk_segments_into_viral_words(raw_segs, max_words=3)
        statement = " ".join([s["text"] for s in raw_segs])

        # Análisis visual con OpenCV para detectar múltiples interlocutores
        face_info = detect_faces_and_layout(actual_file, start_sec, dur_sec)
        is_split = (crop_mode == "split") or (crop_mode == "auto" and face_info["multi_speaker"])

        out_mp4_name = f"short_{clip_id}_{uid}.mp4"
        out_mp4_path = os.path.join(OUTPUT_DIR, out_mp4_name)
        out_srt_name = f"subtitles_{clip_id}_{uid}.srt"
        out_srt_path = os.path.join(OUTPUT_DIR, out_srt_name)

        # Generar archivo .SRT
        with open(out_srt_path, "w", encoding="utf-8") as f_srt:
            for idx, s in enumerate(viral_segs, 1):
                f_srt.write(f"{idx}\n{format_srt_time(s['start'])} --> {format_srt_time(s['end'])}\n{s['text']}\n\n")

        srt_escaped = out_srt_path.replace("\\", "/").replace(":", "\\:")
        sub_style = "FontName=Arial Black,FontSize=22,PrimaryColour=&H0000FFFF,BackColour=&H80000000,BorderStyle=3,Outline=3,Shadow=0,Alignment=2,MarginV=440"

        # 3. FILTROS SEGÚN EL MODO DE ENCUADRE
        if is_split:
            # MODO SPLIT-SCREEN DUAL (2 Personas / Podcast):
            # Mitad superior: Enfoca Persona Izquierda
            # Mitad inferior: Enfoca Persona Derecha
            lx = face_info["speaker_left_x"]
            rx = face_info["speaker_right_x"]
            filter_with_subs = (
                f"[0:v]scale=-2:1920,crop=1080:960:iw*{lx}-540:ih*0.1[top];"
                f"[0:v]scale=-2:1920,crop=1080:960:iw*{rx}-540:ih*0.1[bot];"
                f"[top][bot]vstack=inputs=2,setsar=1,"
                f"subtitles='{srt_escaped}':force_style='{sub_style}'[v]"
            )
            filter_clean = (
                f"[0:v]scale=-2:1920,crop=1080:960:iw*{lx}-540:ih*0.1[top];"
                f"[0:v]scale=-2:1920,crop=1080:960:iw*{rx}-540:ih*0.1[bot];"
                f"[top][bot]vstack=inputs=2,setsar=1[v]"
            )
        else:
            # TRUE 9:16 FULL SCREEN CROP (1 Persona / Busto / Documental):
            # Centrado o ajustado suavemente al rostro detectado
            cx = face_info.get("primary_center_x", 0.5)
            # Asegurar límites del recorte
            crop_x = f"max(0,min(in_w-1080,in_w*{cx}-540))"
            filter_with_subs = (
                f"[0:v]scale=-2:1920,crop=1080:1920:{crop_x}:0,setsar=1,"
                f"subtitles='{srt_escaped}':force_style='{sub_style}'[v]"
            )
            filter_clean = f"[0:v]scale=-2:1920,crop=1080:1920:{crop_x}:0,setsar=1[v]"

        cmd_subs = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-i", actual_file,
            "-filter_complex", filter_with_subs,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_mp4_path
        ]

        has_video = False
        try:
            subprocess.run(cmd_subs, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            has_video = os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 1000
        except Exception as e:
            try:
                cmd_clean = [
                    "ffmpeg", "-y",
                    "-ss", str(start_sec),
                    "-to", str(end_sec),
                    "-i", actual_file,
                    "-filter_complex", filter_clean,
                    "-map", "[v]",
                    "-map", "0:a?",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "22",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    out_mp4_path
                ]
                subprocess.run(cmd_clean, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                has_video = os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 1000
            except Exception as e2:
                print(f"FFmpeg render error on clip {clip_id}: {e2}")

        flow_prompt = (
            f"Cinematic vertical 9:16 documentary frame illustrating '{cfg['titulo']}', "
            f"weathered marble stoic bust in high-contrast profile, intense gaze, "
            f"anamorphic lens flare, sharp golden rim light #E5C158 slicing shadows, "
            f"volumetric mist, dark obsidian background, 8k hyperrealistic --ar 9:16 --no text, cartoon, blur"
        )

        generated_clips.append({
            "id": clip_id,
            "titulo": cfg["titulo"],
            "timestamp": f"{int(start_sec//60)}:{int(start_sec%60):02d} - {int(end_sec//60)}:{int(end_sec%60):02d}",
            "duracion": f"{int(dur_sec)}s",
            "statement": statement,
            "layout_mode": "👥 Split-Screen Dual" if is_split else "🔲 Full Screen 9:16",
            "video_url": f"/static/output/{out_mp4_name}" if has_video else None,
            "srt_url": f"/static/output/{out_srt_name}",
            "flow_prompt": flow_prompt,
            "related_video_bridge": f"?t={int(start_sec)}s",
            "platforms": ["YouTube Shorts", "TikTok", "Instagram Reels"]
        })

    return generated_clips
