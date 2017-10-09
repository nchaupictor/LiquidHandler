import cv2
import numpy as np

class VideoCamera(object):
    def __init__(self):
        # Using OpenCV to capture from device 0. If you have trouble capturing
        # from a webcam, comment the line below out and use a video file
        # instead.

        self.video = cv2.VideoCapture(0)
        self.video.set(3,480) #width
        self.video.set(4,360) #height

        # If you decide to use video.mp4, you must have this file in the folder
        # as the main.py.
        # self.video = cv2.VideoCapture('video.mp4')
    
    def __del__(self):
        self.video.release()
        
    
    def get_frame(self):
        success, image = self.video.read()
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.

        #Process image
        gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        #cv2.imwrite("gray.jpg",gray)
        imgCan = cv2.Canny(gray,32.5,100)
        circles  = cv2.HoughCircles(imgCan,cv2.HOUGH_GRADIENT,0.75,0.35,param1=5,param2=8.5,minRadius=5,maxRadius=7)
        if circles is not None:
            print(circles)
            #circles = np.round(circles[0,:]).astype("int")
            circles = np.uint16(np.around(circles))
            for i in circles[0,:]:
                cv2.circle(image,(i[0],i[1]),i[2],(0,255,0),2)
                
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()