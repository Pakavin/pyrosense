import cv2
from ultralytics import YOLO
from datetime import datetime
import threading   
import boto3
import math
import os

from dotenv import load_dotenv
load_dotenv()
#--------------- Credentials Configuration ---------------#
device = "dfa49df0-600a-480e-aedf-9cc140857424"
region_name = "us-east-2"
aws_access_key_id = "AKIAQEIP3ENALXA6DWFI"
aws_secret_access_key = "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"
model_path = "./best.pt"
#---------------------------------------------------------#

onlock = False
def unlock_bucket():
    global onlock
    onlock = False

padding = 100

class FireDetector():
    def __init__(self):
        self.model = YOLO(model_path)

        self.s3_resource = boto3.resource('s3',
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

    def detect(self, img):
        global padding, onlock

        results = self.model(img, stream=True)

        for r in results:

            boxes = r.boxes
            for box in boxes:

                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                confidence = math.ceil((box.conf[0]*100))/100

                if confidence > 0.7 and int(box.cls[0]) == 2:

                    #cls = int(box.cls[0])
                    #org = [x1, y1]                
                    #font = cv2.FONT_HERSHEY_SIMPLEX
                    #fontScale = 1
                    #color = (255, 0, 0)
                    #thickness = 2

                    #cv2.putText(img, CLASS_NAMES[cls], org, font, fontScale, color, thickness)


                    if not onlock:
                        crop_img = img[max(0, y1-padding): min(480, y2+padding), max(0, x1-padding): min(640, x2+padding)]
                        cv2.imwrite("detected.jpeg", crop_img)    
                        self.s3_resource.Bucket("pyrosensecamerabucket").upload_file("detected.jpeg", device+"/"+datetime.now()
    .strftime("%Y%m%d_%H%M%S")+".jpeg")
                        
                        onlock = True
                        threading.Timer(5, unlock_bucket).start()
                        

                    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)


class Camera:
    def __init__(self, name, ip, detector):
        super().__init__()
        self.name = name
        self.cap = cv2.VideoCapture(ip)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.detector = detector
        
    def run(self):
        while True:
            success, img = self.cap.read()
            print(success)
            self.detector.detect(img)

            cv2.imshow(self.name, img)
            if cv2.waitKey(1) == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()


def main():
    detector = FireDetector()
    cam = Camera("test", 0, detector)
    cam.run()


if __name__ == "__main__":
    #print(os.environ["REGION_NAME"])
    main()
    #detector = FireDetector()
    #img = cv2.imread("./test.jpg")
    #detector.send(detector.encode_image(cv2.imread("test.jpg")))
    #img = cv2.imread("./test.jpg")
    #print(len(detector.encode_image(img)))