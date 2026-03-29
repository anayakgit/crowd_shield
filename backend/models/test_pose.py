
import mediapipe as mp

print("MediaPipe version:", mp.__version__)
print("Has solutions:", hasattr(mp, "solutions"))

pose = mp.solutions.pose.Pose()
print("Pose model loaded successfully")
