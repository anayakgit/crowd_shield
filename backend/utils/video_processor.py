import cv2
import numpy as np
import os
from datetime import datetime

# frame = cv2.resize(frame , (640,640))

class VideoProcessor:
    """Handle video file and webcam input processing"""
    
    def __init__(self):
        self.current_source = None
        self.is_webcam = False
        self.frame_count = 0
        
    def open_video_file(self, video_path):
        """Open a video file for processing"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        self.current_source = cv2.VideoCapture(video_path)
        self.is_webcam = False
        
        if not self.current_source.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")
        
        # Get video properties
        fps = self.current_source.get(cv2.CAP_PROP_FPS)
        total_frames = int(self.current_source.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.current_source.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.current_source.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        return {
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'duration': total_frames / fps if fps > 0 else 0
        }
    
    def open_webcam(self, camera_index=0):
        """Open webcam for live processing (tries AVFoundation on macOS first)."""
        import platform

        backends_to_try = []
        if platform.system() == 'Darwin':
            backends_to_try.append(cv2.CAP_AVFOUNDATION)
        backends_to_try.append(cv2.CAP_ANY)  # default / auto-detect

        cap = None
        for backend in backends_to_try:
            try:
                c = cv2.VideoCapture(camera_index, backend)
                if c.isOpened():
                    # Do a test read — on macOS, isOpened() can return True
                    # even when camera permission has been denied.
                    ret, _ = c.read()
                    if ret:
                        cap = c
                        break
                    else:
                        c.release()
                else:
                    c.release()
            except Exception:
                pass

        if cap is None:
            raise ValueError(
                f"Failed to open webcam at index {camera_index}. "
                "On macOS, make sure Terminal (or your IDE) has Camera access "
                "in System Settings → Privacy & Security → Camera."
            )

        self.current_source = cap
        self.is_webcam = True

        # Set resolution
        self.current_source.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.current_source.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        width  = int(self.current_source.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.current_source.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return {
            'width':     width,
            'height':    height,
            'is_webcam': True,
        }

    def open_stream_url(self, url):
        """Open a YouTube URL or any RTSP/HTTP stream via yt-dlp / cv2."""
        stream_url = url

        # If it looks like a YouTube URL, resolve the actual stream URL
        if 'youtube.com' in url or 'youtu.be' in url:
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'quiet':  True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    stream_url = info['url']
                    print(f"[stream] Resolved YouTube URL -> {stream_url[:80]}...")
            except ImportError:
                raise ValueError("yt-dlp is not installed. Run: pip install yt-dlp")
            except Exception as e:
                raise ValueError(f"Failed to resolve YouTube stream: {e}")

        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            raise ValueError(f"Failed to open stream: {url}")

        # Quick read test
        ret, _ = cap.read()
        if not ret:
            cap.release()
            raise ValueError(f"Stream opened but produced no frames: {url}")

        # Seek back to start for video-on-demand streams
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.current_source = cap
        self.is_webcam       = False

        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps    = cap.get(cv2.CAP_PROP_FPS)

        return {
            'width':      width,
            'height':     height,
            'fps':        fps,
            'stream_url': stream_url[:120],
        }

    def read_frame(self):
        """Read next frame from current source"""
        if self.current_source is None:
            return None, False
        
        ret, frame = self.current_source.read()
        
        if ret:
            self.frame_count += 1
            # skip frames for faster processing 
            if self.frame_count % 3 !=0:
                return self.read_frame()
            return frame, True
        else:
            return None, False
    
    def release(self):
        """Release current video source"""
        if self.current_source is not None:
            self.current_source.release()
            self.current_source = None
            self.frame_count = 0
    
    def resize_frame(self, frame, max_width=1280):
        """Resize frame while maintaining aspect ratio"""
        if frame is None:
            return None
        
        height, width = frame.shape[:2]
        
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
            frame = cv2.resize(frame, (new_width, new_height))
        
        return frame
    
    def save_frame(self, frame, output_dir='static/frames'):
        """Save a frame as an image"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f'frame_{timestamp}.jpg'
        filepath = os.path.join(output_dir, filename)
        
        cv2.imwrite(filepath, frame)
        return filepath
    
    def extract_frames(self, video_path, output_dir, frame_skip=5):
        """Extract frames from video at intervals"""
        os.makedirs(output_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        frame_paths = []
        count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if count % frame_skip == 0:
                timestamp = f'{count:06d}'
                filename = f'frame_{timestamp}.jpg'
                filepath = os.path.join(output_dir, filename)
                cv2.imwrite(filepath, frame)
                frame_paths.append(filepath)
            
            count += 1
        
        cap.release()
        return frame_paths
    
    @staticmethod
    def encode_frame_to_jpeg(frame, quality=85):
        """Encode frame to JPEG for web streaming"""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        return buffer.tobytes()
    
    @staticmethod
    def create_heatmap_overlay(frame, density_grid, alpha=0.5):
        """Create heatmap overlay on frame"""
        height, width = frame.shape[:2]
        
        # Resize density grid to match frame size
        heatmap = cv2.resize(density_grid, (width, height), interpolation=cv2.INTER_LINEAR)
        
        # Normalize to 0-255
        if heatmap.max() > 0:
            heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
        else:
            heatmap = heatmap.astype(np.uint8)
        
        # Apply colormap (JET: blue=low, red=high)
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        # Blend with original frame
        overlay = cv2.addWeighted(frame, 1 - alpha, heatmap_colored, alpha, 0)
        
        return overlay
    
    @staticmethod
    def draw_directional_arrows(frame, density_grid, arrow_length=50):
        """Draw arrows pointing from high to low density areas"""
        annotated = frame.copy()
        grid_h, grid_w = density_grid.shape
        frame_h, frame_w = frame.shape[:2]
        
        cell_h = frame_h // grid_h
        cell_w = frame_w // grid_w
        
        for y in range(grid_h):
            for x in range(grid_w):
                current_density = density_grid[y, x]
                
                # Only draw arrows in high-density areas
                if current_density > 2:  # Threshold
                    # Find direction to lowest density neighbor
                    min_density = current_density
                    best_dir = None
                    
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < grid_h and 0 <= nx < grid_w:
                            if density_grid[ny, nx] < min_density:
                                min_density = density_grid[ny, nx]
                                best_dir = (dx, dy)
                    
                    # Draw arrow if direction found
                    if best_dir is not None:
                        center_x = x * cell_w + cell_w // 2
                        center_y = y * cell_h + cell_h // 2
                        
                        end_x = int(center_x + best_dir[0] * arrow_length)
                        end_y = int(center_y + best_dir[1] * arrow_length)
                        
                        cv2.arrowedLine(annotated, (center_x, center_y), (end_x, end_y),
                                       (0, 255, 255), 3, tipLength=0.4)
        
        return annotated
