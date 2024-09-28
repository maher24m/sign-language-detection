import cv2
import numpy as np
import mediapipe as mp
from keras.models import load_model

# Define the image size
image_size = 32

# Load the trained ASL model
model = load_model('asl_cnn_model.h5')

# Initialize MediaPipe Hand Detector
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Define the function to preprocess the cropped hand image
def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # flip the camera
    gray = cv2.flip(gray, 1)
    
    gray = cv2.GaussianBlur(gray, (15, 15), 0)
    # Apply thresholding
    _, thresholded = cv2.threshold(gray, 161, 255, cv2.THRESH_BINARY)
    
    # Resize to match the input size of the CNN model
    resized = cv2.resize(thresholded, (image_size, image_size))
    
    # Normalize the pixel values (0-255) to (0-1)
    normalized = resized / 255.0
    
    # Reshape to (1, image_size, image_size, 1) for the CNN input
    reshaped = np.reshape(normalized, (1, image_size, image_size, 1))
    
    return reshaped, thresholded

# Define a function to map prediction index to ASL letter
def predict_asl_letter(prediction):
    asl_letters = 'ABCDEFGHIKLMNOPQRSTUVWXY'  # No J or Z due to motion
    return asl_letters[prediction]

# Start video capture
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Convert the frame to RGB as MediaPipe requires RGB format
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame to detect hands
    result = hands.process(frame_rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            # Get bounding box coordinates around the hand
            h, w, c = frame.shape
            x_min, y_min = w, h
            x_max, y_max = 0, 0
            for landmark in hand_landmarks.landmark:
                x, y = int(landmark.x * w), int(landmark.y * h)
                x_min, y_min = min(x_min, x), min(y_min, y)
                x_max, y_max = max(x_max, x), max(y_max, y)

            # Add a margin to the bounding box to ensure the whole hand is captured
            margin = 30
            x_min = max(0, x_min - margin)
            y_min = max(0, y_min - margin)
            x_max = min(w, x_max + margin)
            y_max = min(h, y_max + margin)

            # Crop the hand region from the frame
            hand_image = frame[y_min:y_max, x_min:x_max]

            # Preprocess the cropped hand image
            preprocessed_image, resized_image = preprocess_image(hand_image)

            # Make prediction using the trained model
            prediction = model.predict(preprocessed_image)
            predicted_label = np.argmax(prediction)
            confidence = np.max(prediction) * 100  # Get the confidence score

            # Convert the predicted label to the corresponding ASL letter
            asl_letter = predict_asl_letter(predicted_label)

            # Draw the bounding box around the hand
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

            # Display the predicted ASL letter and confidence on the frame
            cv2.putText(frame, f'ASL Letter: {asl_letter} ({confidence:.2f}%)', (x_min, y_min - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            # Display the preprocessed image in a separate window
            cv2.imshow('Preprocessed Image', resized_image)

    # Show the frame
    cv2.imshow('ASL Recognition', frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture and close windows
cap.release()
cv2.destroyAllWindows()