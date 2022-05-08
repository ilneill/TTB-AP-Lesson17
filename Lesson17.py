# Using an Arduino with Python LESSON 17: Controlling Paddle Position with a Joystick.
# https://www.youtube.com/watch?v=cT1JdSNwuhM
# https://toptechboy.com/

# Internet References:
# https://www.glowscript.org/docs/VPythonDocs/index.html

import time
import serial
from vpython import *
import numpy as np

# vPython refresh rate.
vPythonRefreshRate = 100

# Buzzer enable, or not - it can get annoying after a while.
buzzerEnable = True

# A place on which to put our things...
arena = canvas(title = "<b><i>Arduino with Python - A Playable 3D Pong Game!</i></b>", background = color.cyan, width = 800, height = 600, autoscale = False)

# A function to draw a zone cube.
def drawZoneCube(rPos = vector(0, 0, 0), cubeSize = 1, sides = 0b111111, name = "NoName"):
    wallThickness = cubeSize / 50
    wallThicknessLeft = wallThicknessRight = wallThicknessBottom = wallThicknessTop = wallThicknessBack = wallThicknessFront = 0
    if (sides & 0b100000):
        wallLeft   = box(color = color.gray(0.5), opacity = 0.5, pos = vector(-cubeSize / 2,  0, 0) + rPos, size = vector(wallThickness, cubeSize, cubeSize))
        wallThicknessLeft = wallThickness
    if (sides & 0b010000):
        wallRight  = box(color = color.gray(0.5), opacity = 0.5, pos = vector( cubeSize / 2,  0, 0) + rPos, size = vector(wallThickness, cubeSize, cubeSize))
        wallThicknessRight = wallThickness
    if (sides & 0b001000):
        wallBottom = box(color = color.gray(0.5), opacity = 0.5, pos = vector( 0, -cubeSize / 2, 0) + rPos, size = vector(cubeSize, wallThickness, cubeSize))
        wallThicknessBottom = wallThickness
    if (sides & 0b000100):
        wallTop    = box(color = color.gray(0.5), opacity = 0.5, pos = vector( 0,  cubeSize / 2, 0) + rPos, size = vector(cubeSize, wallThickness, cubeSize))
        wallThicknessTop = wallThickness
    if (sides & 0b000010):
        wallBack   = box(color = color.gray(0.5), opacity = 0.5, pos = vector( 0, 0, -cubeSize / 2) + rPos, size = vector(cubeSize, cubeSize, wallThickness))
        wallThicknessBack = wallThickness
    if (sides & 0b000001):
        wallFront  = box(color = color.gray(0.5), opacity = 0.5, pos = vector( 0, 0,  cubeSize / 2) + rPos, size = vector(cubeSize, cubeSize, wallThickness))
        wallThicknessFront = wallThickness
    # If there is a room name, display it centered horizontally and vertically.
    if (name != "NoName"):
        boxIdentifier = text(text = name, color = color.blue, opacity = 0.25, align = "center", height = cubeSize / 4, pos = vector( 0, - cubeSize / 4 / 2, 0) + rPos, axis = vector(1, 0, 0))
    # Return the cube boundaries -> [x-left, x-right, y-bottom, y-top, z-back, z-front].
    return([(-cubeSize / 2 + wallThicknessLeft / 2 + rPos.x), (cubeSize / 2 - wallThicknessRight / 2 + rPos.x),
            (-cubeSize / 2 + wallThicknessBottom / 2 + rPos.y), (cubeSize / 2 - wallThicknessTop / 2 + rPos.y),
            (-cubeSize / 2 + wallThicknessBack / 2 + rPos.z), (cubeSize / 2 - wallThicknessFront / 2 + rPos.z)])

# A bat that can have its color, position and size changed.
class drawBat():
    def __init__(self, rPos = vector(0, 0, 0), batSize = 1, inActiveColor = color.gray(0.5)):
        batThickness = batSize / 10
        self.centerPos = vector(0, 0, batThickness / 2) + rPos
        self.inActiveColor = inActiveColor
        self.bat = box(color = self.inActiveColor, opacity = 0.25, pos = self.centerPos, size = vector(batSize, batSize, batThickness))
        self.bounds = [-batSize      / 2 + rPos.x,                    batSize      / 2 + rPos.x,
                       -batSize      / 2 + rPos.y,                    batSize      / 2 + rPos.y,
                       -batThickness / 2 + batThickness / 2 + rPos.z, batThickness / 2 + batThickness / 2 + rPos.z,]
    def updateColor(self, batColor = "inactive"):
        if batColor == "inactive":
            self.bat.color = self.inActiveColor
        else:
            self.bat.color = batColor
    def updatePos(self, chgPos = vector(0, 0, 0)):
        # Move the bat.
        self.bat.pos.x = self.centerPos.x + chgPos.x
        self.bat.pos.y = self.centerPos.y + chgPos.y
        # Update the bounds for collision detection.
        self.bounds[0] = -batSize / 2 + self.bat.pos.x
        self.bounds[1] =  batSize / 2 + self.bat.pos.x
        self.bounds[2] = -batSize / 2 + self.bat.pos.y
        self.bounds[3] =  batSize / 2 + self.bat.pos.y
    def updateSize(self, batSize = 1):
        batThickness = batSize / 10
        self.bat.size = vector(batSize, batSize, batThickness)

# Calculate a Dallas/Maxim CRC8 checksum. Literally, the Arduino code translated...
def calcCRC8(data2Check = ""):
    chksumCRC8 = 0
    for character in data2Check:
        dataByte = ord(character)               # Get the ASCII value of the byte to be processed.
        for bitCounter in range(8):
            sum = ((dataByte ^ chksumCRC8) & 1)
            chksumCRC8 >>= 1
            if sum:
                chksumCRC8 ^= 0x8c
            dataByte >>= 1
    return chksumCRC8

# Standard sizes!
zoneSize = 10
batSize = zoneSize / 2 # Yes, I know a big bat, but it will not stay big!
batMoveScaler = zoneSize - batSize # Used later!
arena.range = 2 * zoneSize + zoneSize / 10 # Ensure the game arena is consistantly placed on the canvas.

# Zone 1.
zone1Centre = vector(-zoneSize, 0, zoneSize)
zone1 = drawZoneCube(zone1Centre, zoneSize, 0b111100, "1")
# Zone 2.
zone2Centre = vector(-zoneSize, 0, 0)
zone2 = drawZoneCube(zone2Centre, zoneSize, 0b111100, "2")
# Zone 3.
zone3Centre = vector(-zoneSize, 0, -zoneSize)
zone3 = drawZoneCube(zone3Centre, zoneSize, 0b101110, "3")
# Zone 4.
zone4Centre = vector( zoneSize, 0, zoneSize)
zone4 = drawZoneCube(zone4Centre, zoneSize, 0b111100, "4")
# Zone 5.
zone5Centre = vector( zoneSize, 0, 0)
zone5 = drawZoneCube(zone5Centre, zoneSize, 0b111100, "5")
# Zone 6.
zone6Centre = vector( zoneSize, 0, -zoneSize)
zone6 = drawZoneCube(zone6Centre, zoneSize, 0b011110, "6")
# Zone 7.
zone7Centre = vector( 0, 0, -zoneSize)
zone7 = drawZoneCube(zone7Centre, zoneSize, 0b001111, "7")
# Zone 1 bat.
bat1Centre = vector(-zoneSize, 0, 1.5 * zoneSize)
bat1 = drawBat(bat1Centre, batSize)
# Zone 4 bat.
bat2Centre = vector( zoneSize, 0, 1.5 * zoneSize)
bat2 = drawBat(bat2Centre, batSize)

# The ball.
ball1Radius = 0.05 * zoneSize
ball1 = sphere(color = color.green, opacity = 1, radius = ball1Radius, pos = zone7Centre)

# Game end messages.
gameOverMessage = text(text = "Game Over!", color = color.red, opacity = 0, align = "center", height = zoneSize / 5, pos = vector(0, zoneSize / 2, zoneSize * 1.5), axis = vector(1, 0, 0))
playAgainMessage = text(text = "Press RETURN to play again...", color = color.red, opacity = 0, align = "center", height = zoneSize / 8, pos = vector(0, -(zoneSize / 2 + zoneSize / 8), zoneSize * 1.5), axis = vector(1, 0, 0))

# Connect to the Arduino on the correct serial port!
serialOK = True
try:
    # My Arduino happens to connect as serial port 'com3'. Yours may be different!
    arduinoDataStream = serial.Serial('com3', 115200)
    # Give the serial port time to connect.
    time.sleep(1)
except serial.SerialException as err:
    serialOK = False
    print("Serial port not found!")

# Initialise the sensor reading variables.
jstkXValue = jstkYValue = 512  # Joystick centered.
jstkZValue = jstkZValueOld = 1 # Button not pressed.

# Set some beep durations (milliseconds).
if buzzerEnable:
    newZoneBeepDuration = 150
    wallBounceBeepDuration = 20
    gameOverBeepDuration = 750
else:
    newZoneBeepDuration = wallBounceBeepDuration = gameOverBeepDuration = 0

# An infinite loop: When is True, True? It is always True!
while True:
    # Lets play the game.
    gameOver = False
    hitCounter = 0

    # Set up the active bat.
    batInUse = 1
    bat = bat1
    bat.updateColor(color.red)

    # A random position change vector for the ball.
    ball1Change = vector((np.random.rand() - 0.5) / (zoneSize / 2), (np.random.rand() - 0.5) / (zoneSize / 2), (np.random.rand() - 0.5) / (zoneSize / 2))

    # Initialise the variable for Arduino binary display LEDs.
    LEDsArduino = 0

    # A not so infinite loop now.
    while not gameOver:
        rate(vPythonRefreshRate) # The vPython rate command is obligatory in animation loops.

        if serialOK:
            # Wait until all the data has been received from the Arduino.
            while arduinoDataStream.in_waiting == 0:
                rate(vPythonRefreshRate)
            # Read the CSV data from the Arduino.
            arduinoDataPacket = arduinoDataStream.readline()
            # Convert the CSV data from a byte stream to a CSV string.
            arduinoDataPacket = str(arduinoDataPacket, 'utf-8')
            # Strip the CRLF from the end of the CSV string.
            arduinoDataPacket = arduinoDataPacket.strip('\r\n')
            # Check if there is a CRC8 checksum.
            if "!" in arduinoDataPacket:
                # Convert the CSV string into data and CRC8 checksum parts.
                (sensorData, chksumCRC8) = arduinoDataPacket.split("!")
            else:
                sensorData = arduinoDataPacket         # Assuming we only have the sensor data.
                chksumCRC8 = str(calcCRC8(sensorData)) # No CRC8 checksum provided, so create one (as a string).
            # Split the sensor data if the CRC8 checksum passes.
            if chksumCRC8.isdigit() and calcCRC8(sensorData) == int(chksumCRC8):
                # Convert the sensorData string into separate variables.
                (jstkXValue, jstkYValue, jstkZValue) = sensorData.split(",")
                # Convert the string variables to numbers.
                jstkXValue = int(jstkXValue)
                jstkYValue = int(jstkYValue)
                jstkZValue = int(jstkZValue)
                # print("Joystick: X=%d, Y=%d, Z=%d" % (jstkXValue, jstkYValue, jstkZValue))
            else:
                print("Received data CRC Fail!")

        # We have not yet worked out where ball1 is.
        ball1Location = 0
        wall1Bounce = False
        ball1InZone0 = ball1InZone1 = ball1InZone2 = ball1InZone3 = ball1InZone4 = ball1InZone5 = ball1InZone6 = ball1InZone7 = False
        # Check if ball1 is about to, or has, escaped from the open ends of zone1 or zone4.
        if ((ball1.pos.z + ball1Radius + ball1Change.z) >= zone1[5] or (ball1.pos.z + ball1Radius + ball1Change.z) >= zone4[5]):
            ball1InZone0 = True
        # Check where ball1 is going, and set the boundaries.
        if (((zone1[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone1[1])
            or (zone1[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone1[1]))
            and ((zone1[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone1[3])
            or (zone1[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone1[3]))
            and ((zone1[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone1[5])
            or (zone1[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone1[5]))):
            bounds1 = zone1
            ball1InZone1 = True
            ball1Location = 1
        if (((zone2[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone2[1])
            or (zone2[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone2[1]))
            and ((zone2[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone2[3])
            or (zone2[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone2[3]))
            and ((zone2[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone2[5])
            or (zone2[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone2[5]))):
            bounds1 = zone2
            ball1InZone2 = True
            ball1Location = 2
        if (((zone3[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone3[1])
            or (zone3[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone3[1]))
            and ((zone3[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone3[3])
            or (zone3[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone3[3]))
            and ((zone3[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone3[5])
            or (zone3[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone3[5]))):
            bounds1 = zone3
            ball1InZone3 = True
            ball1Location = 3
        if (((zone4[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone4[1])
            or (zone4[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone4[1]))
            and ((zone4[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone4[3])
            or (zone4[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone4[3]))
            and ((zone4[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone4[5])
            or (zone4[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone4[5]))):
            bounds1 = zone4
            ball1InZone4 = True
            ball1Location = 4
        if (((zone5[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone5[1])
            or (zone5[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone5[1]))
            and ((zone5[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone5[3])
            or (zone5[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone5[3]))
            and ((zone5[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone5[5])
            or (zone5[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone5[5]))):
            bounds1 = zone5
            ball1InZone5 = True
            ball1Location = 5
        if (((zone6[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone6[1])
            or (zone6[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone6[1]))
            and ((zone6[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone6[3])
            or (zone6[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone6[3]))
            and ((zone6[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone6[5])
            or (zone6[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone6[5]))):
            bounds1 = zone6
            ball1InZone6 = True
            ball1Location = 6
        if (((zone7[0] <= (ball1.pos.x + ball1Radius + ball1Change.x) and (ball1.pos.x + ball1Radius + ball1Change.x) <= zone7[1])
            or (zone7[0] <= (ball1.pos.x - ball1Radius + ball1Change.x) and (ball1.pos.x - ball1Radius + ball1Change.x) <= zone7[1]))
            and ((zone7[2] <= (ball1.pos.y + ball1Radius + ball1Change.y) and (ball1.pos.y + ball1Radius + ball1Change.y) <= zone7[3])
            or (zone7[2] <= (ball1.pos.y - ball1Radius + ball1Change.y) and (ball1.pos.y - ball1Radius + ball1Change.y) <= zone7[3]))
            and ((zone7[4] <= (ball1.pos.z + ball1Radius + ball1Change.z) and (ball1.pos.z + ball1Radius + ball1Change.z) <= zone7[5])
            or (zone7[4] <= (ball1.pos.z - ball1Radius + ball1Change.z) and (ball1.pos.z - ball1Radius + ball1Change.z) <= zone7[5]))):
            bounds1 = zone7
            ball1InZone7 = True
            ball1Location = 7

        # A ball with a radius can be in 2 zones, so set the bounds to be where it is travelling to.
        if (ball1InZone1 and ball1InZone2):
            if (ball1Change.z > 0):
                bounds1 = zone1
                ball1Location = 1
            if (ball1Change.z < 0):
                bounds1 = zone2
                ball1Location = 2
        if (ball1InZone2 and ball1InZone3):
            if (ball1Change.z > 0):
                bounds1 = zone2
                ball1Location = 2
            if (ball1Change.z < 0):
                bounds1 = zone3
                ball1Location = 3
        if (ball1InZone3 and ball1InZone7):
            if (ball1Change.x < 0):
                bounds1 = zone3
                ball1Location = 3
            if (ball1Change.x > 0):
                bounds1 = zone7
                ball1Location = 7
        if (ball1InZone4 and ball1InZone5):
            if (ball1Change.z > 0):
                bounds1 = zone4
                ball1Location = 4
            if (ball1Change.z < 0):
                bounds1 = zone5
                ball1Location = 5
        if (ball1InZone5 and ball1InZone6):
            if (ball1Change.z > 0):
                bounds1 = zone5
                ball1Location = 5
            if (ball1Change.z < 0):
                bounds1 = zone6
                ball1Location = 6
        if (ball1InZone6 and ball1InZone7):
            if (ball1Change.x > 0):
                bounds1 = zone6
                ball1Location = 6
            if (ball1Change.x < 0):
                bounds1 = zone7
                ball1Location = 7

        # If the joystick button is pressed, change active bat.
        if (jstkZValue == 0 and jstkZValueOld != 0):
            if (batInUse == 1):
                batInUse = 2
                bat = bat2
                bat1.updateColor() # Change the color of the inactive bat.
            else:
                batInUse = 1
                bat = bat1
                bat2.updateColor() # Change the color of the inactive bat.
        bat.updateColor(color.red) # Change the color of the active bat.
        jstkZValueOld = jstkZValue

        # Move active bat.
        batPosX = ((jstkXValue / 1024.0) - 0.5) * batMoveScaler
        batPosY = ((jstkYValue / 1024.0) - 0.5) * batMoveScaler
        bat.updatePos(vector(batPosX, batPosY, 0))

        # Move ball1.
        ball1.pos += ball1Change
        # If ball1 is about to escape, is the active bat in the right place to keep it in the arena?
        if ball1InZone0:
            if (bat.bounds[0] <= ball1.pos.x <= bat.bounds[1]
                and bat.bounds[2] <= ball1.pos.y <= bat.bounds[3]):
                hitCounter += 1
                print("Hit! (%d)" % hitCounter)
                # Increase the difficulty: Make the bats a bit smaller.
                if hitCounter < 10:
                    batSize -= zoneSize / 20
                    batMoveScaler = zoneSize - batSize
                    bat1.updateSize(batSize)
                    bat2.updateSize(batSize)
            else:
                print("Miss!")
                gameOver = True
                gameOverMessage.opacity = 1
                playAgainMessage.opacity = 1
                ball1.color = color.red
        # Check if ball1 has hit a boundary, and if it is moving towards that boundary, reverse the direction.
        if (((bounds1[0] + ball1Radius) >= ball1.pos.x and ball1Change.x < 0)
            or (ball1.pos.x >= (bounds1[1] - ball1Radius) and ball1Change.x > 0)):
            ball1Change.x = -ball1Change.x
            wall1Bounce = True
        if (((bounds1[2] + ball1Radius) >= ball1.pos.y and ball1Change.y < 0)
            or (ball1.pos.y >= (bounds1[3] - ball1Radius) and ball1Change.y > 0)):
            ball1Change.y = -ball1Change.y
            wall1Bounce = True
        if (((bounds1[4] + ball1Radius) >= ball1.pos.z and ball1Change.z < 0)
            or (ball1.pos.z >= (bounds1[5] - ball1Radius) and ball1Change.z > 0)):
            ball1Change.z = -ball1Change.z
            wall1Bounce = True

        # Update the real world, if it is connected.
        if serialOK:
            # Construct the command to send to the Arduino.
            arduinoCmd = False
            if not gameOver:
                # Only send an LED update and a low beep to the Arduino if the ball location status has changed from the last time.
                if ball1Location != LEDsArduino:
                    # Construct the command to send to the Arduino.
                    arduinoCmd = "LEDs=%d,Beep=L%d" % (ball1Location, newZoneBeepDuration) # This is 2 commands (subject and action, x2).
                    # Update the current Arduino LEDs status.
                    LEDsArduino = ball1Location
                # Only send a high beep to the Arduino if the ball has hit a wall.
                if not arduinoCmd and wall1Bounce:
                    arduinoCmd = "Beep=H%d" %  wallBounceBeepDuration # This is the command (subject and action).
            else:
                arduinoCmd = "LEDs=%d,Beep=L%d" % (0, gameOverBeepDuration) # This is 2 commands (subject and action, x2).
            if arduinoCmd:
                chksumCRC8 = calcCRC8(arduinoCmd)                 # This is the CRC8 checksum of the command.
                arduinoCmd = "%s!%d\n" % (arduinoCmd, chksumCRC8) # Put them together, separated by the delimiter, and terminate with a newline.
                # Encode and send the command to the Arduino. 
                arduinoDataStream.write(arduinoCmd.encode())

    # Start another game when the player is ready.
    input("Press RETURN to play again...")

    # Get ready for the next game.
    gameOverMessage.opacity = 0
    playAgainMessage.opacity = 0
    # Reset the bats.
    batSize = zoneSize / 2
    batMoveScaler = zoneSize - batSize
    bat1.updateSize(batSize)
    bat2.updateSize(batSize)
    bat1.updateColor()
    bat1.updatePos(vector(0, 0, 0))
    bat2.updateColor()
    bat2.updatePos(vector(0, 0, 0))
    # Reset up the ball.
    ball1.color = color.green
    ball1.pos = zone7Centre

    # Flush the serial buffer. Prevents trouble if the game has been waiting for a while.
    arduinoDataStream.reset_input_buffer()

# EOF
