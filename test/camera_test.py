import cv2



cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # 设置480P宽度
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # 设置480P高度
cap.set(cv2.CAP_PROP_FPS, 30)            # 设置30fps
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # 减少缓冲区，提高实时性
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))
if fps == 0:
    fps = 60
print("width:",width,"height:",height,"fps:",fps)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("frame", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()