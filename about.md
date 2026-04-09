Here is a clear, file-by-file breakdown of exactly what each specific file does and how data traverses through them like an assembly line.

---

### The Backend (The Engine)

[backend/app.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/app.py:0:0-0:0) **(The Orchestrator)**
This is the master file. When you run `python -m backend.app`, this file starts the Flask web server. It contains the massive "While Loop" that continuously pulls frames from your video, hands those frames sequentially to the other files below to get processed, and then broadcasts the final results to the frontend.

[backend/config.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/config.py:0:0-0:0) **(The Rulebook)**
A simple file containing constant variables. Things like `MAX_FRAME_WIDTH` or `RISK_THRESHOLDS`. It keeps [app.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/app.py:0:0-0:0) clean from hard-coded numbers.

[backend/models/yolo_detector.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/models/yolo_detector.py:0:0-0:0) **(The Eyes - Spatial)**
This file is a wrap-around class for the pre-trained [yolov8n.pt](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/yolov8n.pt:0:0-0:0) model. [app.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/app.py:0:0-0:0) hands it an image, and this file says, *"I found 50 people, here are the X and Y coordinates of their bounding boxes."*

[backend/models/movement_tracker.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/models/movement_tracker.py:0:0-0:0) **(The Eyes - Kinetic)**
This file handles Physics. It uses OpenCV to compare the raw pixels of the "current frame" against the "previous frame" to calculate optical flow. It tells [app.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/app.py:0:0-0:0), *"Based on pixel displacement, the crowd is moving at an average of 4 m/s to the right."*

[backend/models/risk_analyzer.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/models/risk_analyzer.py:0:0-0:0) **(The Brain - Logic)**
Currently, this file takes the numbers from the two files above (Count = 50, Speed = 4 m/s) and uses hard-coded math (e.g., `if speed > X and count > Y`) to return a LOW/MEDIUM/HIGH risk. In the future, this is the exact file where we will load the trained LSTM (`stampede_lstm.pth`) to do the guessing instead of math rules.

---

### The Frontend (The Dashboard)

[frontend/index.html](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/frontend/index.html:0:0-0:0) **(The Skeleton)**
The barebones user interface that we stripped down to just the video player, risk readout, and start/stop buttons.

[frontend/css/style.css](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/frontend/css/style.css:0:0-0:0) **(The Paint)**
The basic monochrome styling that gives the HTML its shape and layout structure.

[frontend/js/dashboard.js](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/frontend/js/dashboard.js:0:0-0:0) **(The Nerves)**
This Javascript file runs in your browser. It acts as the socket listener. When [app.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/app.py:0:0-0:0) finishes processing a single frame, it broadcasts an internet signal containing the new image and risk score. [dashboard.js](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/frontend/js/dashboard.js:0:0-0:0) catches that signal and instantly overwrites the HTML to display the new information.

---

### The New Pipeline (The LSTM Training Files)

These files are completely independent of the running application ([app.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/app.py:0:0-0:0)). You only use these completely separate files specifically when you want to train a new, smarter "Brain" to plug into [risk_analyzer.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/backend/models/risk_analyzer.py:0:0-0:0).

[training/feature_extractor.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/training/feature_extractor.py:0:0-0:0) **(The Data Translator)**
You run this script against a folder of raw MP4 videos. Instead of broadcasting to a web dashboard, it secretly runs YOLO and the Movement tracker as fast as possible in the background and writes the numbers out to a `training_data.csv` spreadsheet file perfectly formatted for machine learning.

[training/train_lstm.py](cci:7://file:///Users/ajaynayakgollarkeri/Desktop/other_projects/college/original/crowd-stampede-detection/training/train_lstm.py:0:0-0:0) **(The Teacher)**
This is the PyTorch script. It opens `training_data.csv`, spins up a blank memory sequence Neural Network (LSTM), and forces it to look at the patterns in the spreadsheet for a few minutes. It then spits out the tiny trained weight file `stampede_lstm.pth`, which you then drag into `backend/models` so `risk_analyzer.py` can load it.

---

### Summary of the Flow:
1.  **Frontend:** User clicks "Upload Video" in `index.html`.
2.  **App.py:** Catches the video and starts the massive loop. Extracts Frame 1.
3.  **Yolo_detector:** Gets Frame 1, counts people.
4.  **Movement_tracker:** Gets Frame 1, compares to Frame 0, calculates speed.
5.  **Risk_analyzer:** Looks at the count and speed, decides the Risk Level is "LOW".
6.  **App.py:** Takes the Risk Level and the original image (drawn with boxes), converts the image to text (`base64`), and emits it over WebSockets.
7.  **Dashboard.js:** Hears the emit, takes the text and converts it back into an image on your screen.
8.  **App.py:** Moves to Frame 2. (Repeats 30 times a second).