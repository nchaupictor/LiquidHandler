#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#                                 Liquid Handler Routine v3
#                          Date created: 23/11/2016 #Author: N Chau
#Added features: Host raspberry pi as webserver through flask, GUI controlled through server
#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#SETUP
import RPi.GPIO as GPIO
import time
import serial
from flask import Flask,render_template,request,redirect,Response,jsonify
from camera import VideoCamera
import cv2

app = Flask(__name__)


#Open serial port between RPi and Arduino
ser = serial.Serial(
	port = "/dev/ttyACM0",
	baudrate = 250000,
	timeout = 1
)

#Set up GPIO pin for E axis endstop
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11,GPIO.IN)

#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#COORDINATES
offsetX = -1
offsetY = 12.5
#Tip Rack
tipX = 1 -offsetX #4.95
tipY = 116.5 - offsetY
tipZ = 77
tipGap = 9

#Sample Rack
sampleX = 1.5 -offsetX
sampleY = 219.5 - offsetY
sampleGap = 9.1
samplePick = 49

#Return Tip Rack
returnX = 1.5 -offsetX
returnY = 260.75 - offsetY
returnZ = 67
returnGap = 9

#Reservoir 
reserveX = 117 -offsetX
reserveY = 210 +14
reservePick = 70
reserveGap = 17.25

washY = 210 -offsetY
conjGY = washY + 20 -offsetY
detY = washY + 40 -offsetY
conjMY = washY + 50 -offsetY
subY = washY + 60 -offsetY

#Waste Liquid 
wasteLX = 117 - offsetX
wasteLY = 108
wasteLZ = 20

#Waste Tips
wasteTX = 117 -offsetX
wasteTY = 10
wasteTZ = 40

#Slide
slideX = 230 -offsetX
slideY = 150.5 -offsetY
slideYDis = 153.5 -offsetY
slideZ = 43.5
slideGap = 9
slideAspZ = 48
#Gap between slide modules
moduleGap = 15

#Global variables
count = 0
message = ""
submessage = ""
string =""
incubationTime = 0
skip = 0
t0 = 0.0
slideNum = 0
tipEnd = "No"
progressPercent = 0
tipCount = 0
#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#FUNCTIONS 
#Sending Marlin G-code commands to Arduino through serial 
def serialSend(command):
	ser.write(command + "\r\n") #Command string
	out = '' #Clear buffer
	time.sleep(1)
	while ser.inWaiting() > 0: #Read buffer
		out += ser.read(1)
	if out != '':
		print ">>" + out 
	print command
#-----------------------------------------------------------------------------------------
#Picking up Tip
def pickTip (X,Y,Z,count):
	global submessage
	global tipEnd
	global tipCount
	submessage = "Picking tips..."
	tipCount = count
	if count == 12: #Reached the end of tip box
		#tipEnd = True
		while tipEnd == "No":
			try: #Move pipette to ejection area 
				string = stringFormat(wasteTX,wasteTY,None,None,2500)
				serialSend(string)
				serialSend("G1 Z0 F700")
				serialSend("G4 S10")
				print("Please change tip box, press Ctrl + C to resume")
				time.sleep(20)
			except KeyboardInterrupt:
				print("Resuming...")
				tipEnd = False
				count = 0
		count = 0
		tipCount = count 

	tipEnd = "No"
	Y = Y - count * tipGap
	string = stringFormat(X,Y,None,None,3000)
	serialSend(string)
	string = stringFormat(None,None,60,None,750)
	serialSend(string)
	string = stringFormat(None,None,Z,None,400)
	serialSend(string)
	#serialSend("G1 Z75 F200")
	serialSend("G1 Z4 F700")
	serialSend("G28 Z")
	#time.sleep(1)
	count += 1
	return count 
#-----------------------------------------------------------------------------------------
#Picking up Sample
def pickSample (X,Y,count):
	global submessage
	submessage = "Picking sample..."
	Y = Y - count * sampleGap
	string = stringFormat(X,Y,None,None,3000)
	serialSend(string)
	string = stringFormat(None,None,33,None,750)
	serialSend(string)
	string = stringFormat(None,None,None,6,600)
	serialSend(string)
	string = stringFormat(None,None,44,None,400)
	serialSend(string)
	serialSend("G1 E0 F700")
	serialSend("G1 Z0 F700")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------	
#Picking up Fluid
def pickFluid (X,Y,E):
	global submessage
	submessage = "Picking reagent..."
	string = stringFormat(X,Y,None,None,3000)
	serialSend(string)
	string = stringFormat(None,None,60,None,750)
	serialSend(string)
	string = stringFormat(None,None,None,E,700)
	serialSend(string)
	#serialSend("G1 E4.5 F200")
	#serialSend('G1 E9 F200')
	string = stringFormat(None,None,69,None,400)
	serialSend(string)
	serialSend("G1 E0 F700")
	serialSend("G1 Z20 F700")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Dispense 
def dispense (X,Y,count,F):
	global submessage
	submessage = "Dispensing..."
	Y = Y + count * slideGap
	string = stringFormat(X,Y,None,None,F)
	serialSend(string)
	#time.sleep(1)
	#string = stringFormat(None,None,25,None,200)
	#serialSend(string)
	string = stringFormat(None,None,37.5,None,750)
	serialSend(string)
	#time.sleep(1)
	string = stringFormat(None,None,None,6*(count+1),700)
	serialSend(string)
	#time.sleep(1)
	serialSend("G1 E0 F700")
	#time.sleep(2)
#-----------------------------------------------------------------------------------------
#Aspirate
def aspirate (X,Y,count,F):
	global submessage
	submessage = "Aspirating..."
	Y = Y + count * slideGap
	string = stringFormat(X,Y,None,None,F)
	serialSend(string)
	#time.sleep(1)
	string = stringFormat(None,None,None,16-(8*count),700)
	serialSend(string)
	#time.sleep(1)
	#string = stringFormat(None,None,30,None,750)
	#serialSend(string)
	#time.sleep(1)
	#serialSend("G1 E9.5 F200")
	string = stringFormat(None,None,36.75,None,500) #32.5
	serialSend(string)
	#time.sleep(1)
	string = stringFormat(None,None,None,16-(8*(count+1)),700)
	serialSend(string)
	#serialSend("G1 E0 F200")
	serialSend("G1 Z28 F700")
	#time.sleep(2)
#-----------------------------------------------------------------------------------------
#Wash 
def wash (num,firstFlag,count):
	global submessage
	global tipEnd
	global tipCount

	tipCount = count
	for i in xrange(num):
		submessage = "Wash " + str(i + 1) +"..." 
		if (firstFlag == 1 and i == 0):
			count = pickTip(tipX,tipY,tipZ,count)
			pickFluid(reserveX,washY,6)
			dispense(slideX,slideYDis,0,3000)
			aspirate(slideX,slideY,0,3000)
			dispose(wasteLX,wasteLY)
			eject(wasteTX,wasteTY,0)

			count = pickTip(tipX,tipY,tipZ,count)
			pickFluid(reserveX,washY,6)
			dispense(slideX,slideYDis,1,3000)
			aspirate(slideX,slideY,1,3000)
			dispose(wasteLX,wasteLY)
			eject(wasteTX,wasteTY,0)

		else:
			if count == 12: #Reached the end of tip box
				#tipEnd = True
				while tipEnd == "No":
					try: #Move pipette to ejection area 
						string = stringFormat(wasteTX,wasteTY,None,None,2500)
						serialSend(string)
						serialSend("G1 Z0 F700")
						serialSend("G4 S10")
						print("Please change tip box, press Ctrl + C to resume")
						time.sleep(20)
					except KeyboardInterrupt:
						print("Resuming...")
						tipEnd = False
						count = 0
			count = 0
			tipCount = count
			tipEnd = "No"
			count = pickTip(tipX,tipY,tipZ,count)
			pickFluid(reserveX,washY,10)
			dispense(slideX,slideYDis,0,3000)
			dispense(slideX,slideYDis,1,750)
			aspirate(slideX,slideY,0,750)
			aspirate(slideX,slideY,1,750)
			dispose(wasteLX,wasteLY)
			eject(wasteTX,wasteTY,0)
	return count	
#-----------------------------------------------------------------------------------------
#Dispose 
def dispose (X,Y):
	global submessage
	submessage = "Disposing..."
	serialSend("G1 Z10 F700")
	string = stringFormat(X,Y,None,None,3000)
	serialSend(string)
	string = stringFormat(None,None,19,None,750)
	serialSend(string)
	serialSend("G1 E16 F700")
	serialSend("G1 E0 F700")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Eject
def eject (X,Y,count):
	global submessage
	submessage = "Ejecting tips..."
	serialSend("G1 Z10 F550")
	Y = Y - count * returnGap
	string = stringFormat(X,Y,None,None,3000)
	serialSend(string)
	string = stringFormat(None,None,40,None,750)
	serialSend(string)
	serialSend("G1 E22.5 F400") 
	serialSend("G1 E5 F700")
	serialSend("G1 Z2 F7000")
	homeE()
	serialSend("G28 Z")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Home E axis 
def homeE ():
	time.sleep(1)
	Eend = 1 #E axis endstop status
	try:
		while Eend:
			if GPIO.input(11):
				print "HIGH"
				serialSend("G1 E2 F700") #Lower E by 2mm after switch closed
				serialSend("G90")
				Eend = 0
			else:
				print "LOW"
				serialSend("G91") #Relative Positioning
				serialSend("G1 E-1 F700") #Raise E by 2mm until switch closed
		#serialSend("M114")
		serialSend("G92 E0")
		#serialSend("M114")
		#serialSend("G1 E10 F250")
	except KeyboardInterrupt:
		GPIO.cleanup() 
		serialSend("M81")
#------------------------------------------------------------------------------------------
#G-Code string formatter
def stringFormat (X = None,Y = None,Z = None, E = None,F = None): #Overload last variable for single Z and F commands
	global string 
	if Z is None and E is None:
		tempX = " X" + str(X)
		tempY = " Y" + str(Y)
		tempF = " F" + str(F)
		string = "G1" + tempX + tempY + tempF
	elif X is None and Y is None and E is None:
		tempZ = " Z" + str(Z)
		tempF = " F" + str(F)
		string = "G1" + tempZ + tempF
	elif X is None and Y is None and Z is None:
		tempE = " E" + str(E)
		tempF = " F" + str(F)
		string = "G1" + tempE + tempF		
	else:
		print("Incorrect String Syntax")

	time.sleep(2)
	return string
#------------------------------------------------------------------------------------------
#Incubation 
def incubation(seconds):
	global submessage
	global skip
	serialSend("G1 Z20 F750")
	serialSend("G4 S3")
	time.sleep(5)
	submessage = "Incubating..."
	#a = raw_input('Press any key to start incubation')
	#Incubate 30 minutes or keypress
	try:
		incubationTime = seconds/60
		print("%d Minute Incubation (or Ctrl + C to skip)" % incubationTime)
		for j in xrange(seconds,0,-1):
			s = str(j) + "s"
			get_incubationTime(j)
			#print("\r{0}".format(j)),
			print(s)
			time.sleep(1)
			if skip == 1:
				skip = 0 
				break
		#return incubationTime
		get_incubationTime(0)
	except KeyboardInterrupt:
		print("Incubation Skipped")
#----------------------------------------------------------------------------------------
#Main Program 
def runProgram():
	global count
	count = 0
	global message
	global submessage
	global progressPercent
	#INITIALISATION PHASE
	print "Initialisation..."
	message = "Initialisation..."
	serialSend("M114")
	#Initialise and maintain heater at 40deg
	serialSend("M140 S40 R37.5")
	print "Heater ON"
	message = "Heater ON"
	#Turn on fan 
	serialSend("M106")
	print "Fan ON"
	message = "Fan ON"

	#Set jerk 
	serialSend("M205 X10")
	#serialSend("M204 T2000") #Default Acceleration
	#serialSend("M203 X3000 Y3000 Z1000 E1000") #Feed Rate
	#serialSend("M210 Z900") #Homing Feed Rate

	#Start camera
	#cam = cv2.VideoCapture(0)
	#img = cam.read()

	#cv2.namedWindow("camera", cv2.CV_WINDOW_AUTOSIZE)
	#cv2.imshow("camera",img)

	#Home XYZ 
	print "Homing..."
	message = "Homing..."
	serialSend("G28 Z") #Home Z first to avoid collisions 
	serialSend("G28 XY")

	#Home E
	homeE()
	print "Homing COMPLETE"
	message = "Homing COMPLETE"
	progressPercent = 1

#----------------------------------------------------------------------------------------
	#MAIN PHASE
	#User input for number of slide and modules
	message = "Enter the number of slides"
	while slideNum == 0:
		print "Enter number of slides: "
		time.sleep(1)
	time.sleep(0.5)
	message = str(slideNum) + " slides selected"
	#numSlide = 2
	#numSlide = int(raw_input("Enter the number of slides: "))
	#print "Number of slides selected: %d" %(numSlide)

	#if numSlide == 1:
		#numMod = int(raw_input("Enter the number of modules: "))
		#print "Number of modules selected: %d" %(numMod)

	#Loop through main program
	#Dispense samples
	#count = 12
	print("Dispensing Samples...")
	for i in xrange(2):
		message = "Step 1.0 - Dispensing Sample " + str(i + 1)
		pickTip(tipX,tipY,tipZ,i)
		#pickTip(tipX,tipY,tipZ,12)
		pickSample(sampleX,sampleY,i)
		dispense(slideX,slideYDis,i,3000)
		count += 1
		eject(returnX,returnY,i)

	#30 minute incubation
	progressPercent = 5
	incubationTime = incubation(1800)
	progressPercent = 10

	print("Aspirating Samples...")
	#Aspirate and dispose tips 
	for i in xrange(2):
		message = "Step 1.0 - Aspirating Sample " + str(i + 1)
		pickTip(returnX,returnY,returnZ,i)
		aspirate(slideX,slideY,i,3000)
		dispose(wasteLX,wasteLY)
		eject(wasteTX,wasteTY,0)
	progressPercent = 15
	print("Washing Samples...")
	#Wash , first wash flag set to 1
	count = wash(3,1,count)
	print("Count:  %d" % count)
	progressPercent = 20

	#Dispense ConjG , Det , Sub
	for k in xrange(3):
		if k == 0:
			message = "Step 2.0 - Dispensing ConjG"
		elif k == 1: 
			message = "Step 3.0 - Dispensing Det"
		else:
			message = "Step 4.0 - Dispensing Sub"
		print("Dispensing %d..." %(k+1))
		count = pickTip(tipX,tipY,tipZ,count)
		pickFluid(reserveX,conjGY+(reserveGap*k),10)
		dispense(slideX,slideYDis,0,3000)
		dispense(slideX,slideYDis,1,750)
		progressPercent += 10

		if k == 2: #5 minute incubation for substrate 
			IncubationTime = incubation(300) 
			progressPercent += 10
		else:
			IncubationTime = incubation(1800)
			progressPercent += 10
				
		print("Aspirating %d..." %(k+1))
		aspirate(slideX,slideY,0,3000)
		aspirate(slideX,slideY,1,750)
		dispose(wasteLX,wasteLY)
		eject(wasteTX,wasteTY,0)

		if k == 2: #Wash once for substrate
			submessage = "Final Wash"
			print("Final Wash")
			progressPercent += 10
			count = wash(1,0,count)
		else:
			print("Washing %d..." %(k+1))
			count =	wash(3,0,count)

	message = "Final Incubation"
	print("Final Incubation")
	progressPercent += 5
	IncubationTime = incubation(1800)

	progressPercent = 100
	message = "Assay Complete"
	print("Assay Complete")
	
#----------------------------------------------------------------------------------------
	#SHUTDOWN PHASE

	#Turn off heater
	serialSend("M140 S0")
	message = "Heater OFF"
	print "Heater OFF"

	#Turn off fan 
	serialSend("M107")
	message = "Fan OFF"
	print "Fan OFF"

	#Home XYZ
	serialSend("G28 Z")
	serialSend("G28 XY")

	#Home E 
	homeE()
	message = "Homing COMPLETE"
	print "Homing COMPLETE"


#------------------------------------------------------------------------------------------
#Server side functions
#Initialise timer 
def timer(init):
	current = time.time()
	elapsed = current - init 
	elapsed = round(elapsed,1)
	return elapsed
#------------------------------------------------------------------------------------------
#Extract incubation countdown timer
def get_incubationTime(s):
	global incubationTime
	incubationTime = s 
	return incubationTime

#------------------------------------------------------------------------------------------
#URL State Checker 
@app.route("/")
def index():
	template_data = {
		'time' : timer(t0),
		'command' : string,
		'incubationTime' : (incubationTime),
		'message' : message,
		'submessage' : submessage,
		'progressPercent' : (progressPercent)
	}
	return render_template('main.html',**template_data)
#Initialise USB (Izone) Camera Feed
def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
#Check for button states of main program
@app.route("/<state>")
def startProgram(state = None):
	if state == 'Start': 
		global t0
		t0 = time.time() #Start timing
		runProgram()
		#serialSend("M106")
		time.sleep(0.5)
	if state == 'Stop':
		global message
		print("STOP PRESSED")
		message = "EMERGENCY STOP"
		serialSend("M112") #Emergency Stop 
		ser.reset_input_buffer() #Flush buffer 
		time.sleep(0.5)
		return redirect('/')
	if state == 'Skip': 
		global skip
		global incubationTime
		skip = 1 
		print("INCUBATION SKIPPED")
		incubationTime = 0
		time.sleep(0.5)
		return redirect('/')
		
	template_data = {
		'title' : state,
		'time' : timer(t0),
		'command' : string,
		'incubationTime' : (incubationTime),
		'message' : message,
		'submessage' : submessage,
        'progressPercent' : (progressPercent)
	}
	return render_template('main.html', **template_data)
#----------------------------------------------------------------------------------------
#URL JSON refresher  for updated string information
@app.route("/refresh")
def refresh():
	json = jsonify({'time': timer(t0), 'command': string, 'incubationTime' : incubationTime, 'message': message, 'submessage' : submessage, 'progressPercent' : (progressPercent), 'tipCount' : tipCount})
	return json	
#----------------------------------------------------------------------------------------
#URL JSON refresher for progress bar 
@app.route("/progress", methods = ['GET'])
def progress():
	progJ = progressPercent
	return jsonify(progJ=progJ)
#----------------------------------------------------------------------------------------
#Form for slide number submission
@app.route("/slide",methods = ['GET','POST'])
def slideform():
	global slideNum
	if request.method == "POST":
		try:
			text = request.form['text']
			slideNum = int(text)
			print(slideNum)
			message = text + " slides selected"
		except:
			print("Cannot obtain form data")
	return redirect("/")

#----------------------------------------------------------------------------------------
#Form for tip box change 
@app.route("/tip",methods = ['GET','POST'])
def tipform():
	global tipEnd 
	if request.method == "POST":
		try:
			text = request.form['tipChange']
			tipEnd = text
			print("Tip Status: ")
			print(tipEnd)
		except:
			print("Cannot obtain form data")
	return redirect("/")

#----------------------------------------------------------------------------------------
#Return video stream back to /index from /video_feed
@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
#----------------------------------------------------------------------------------------
if __name__ == "__main__":
	app.run(host = '0.0.0.0',port = 80,threaded = True)


#----------------------------------------------------------------------------------------
#                                      	     END
#----------------------------------------------------------------------------------------
