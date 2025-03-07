# View the time-lapse here
https://www.youtube.com/watch?v=Q9yi_VHp-4A

# Guide for Setting Up and Running the Analog Voltmeter Clock

This guide provides step-by-step instructions to set up and run the Analog Voltmeter Clock using a Raspberry Pi Zero W, Adafruit PWM/Servo Bonnet, and analog voltmeters for hours, minutes, and seconds.

## Required Components

- **Analog Voltmeter (x3)**
  - DC 62T2/65C5 3V Class 2.5 Analog Voltmeter  
  - [AliExpress Link](https://www.aliexpress.us/item/2251832716993909.html)

- **PWM/Servo Controller**
  - Adafruit 16-Channel PWM/Servo Bonnet for Raspberry Pi  
  - [Adafruit Link](https://www.adafruit.com/product/3416)

- **Microcontroller**
  - Raspberry Pi Zero W  
  - [Raspberry Pi Link](https://www.raspberrypi.com/products/raspberry-pi-zero-w/)

- **Optional: PiSugar Battery Pack**
  - PiSugar 2 for Raspberry Pi Zero W  
  - [Tindie Link](https://www.tindie.com/products/pisugar/pisugar-2-battery-for-raspberry-pi-zero/)

- **Miscellaneous Components**
  - Micro-USB cable and power adapter.
  - Soldering iron (if headers need to be soldered onto the Raspberry Pi or PWM bonnet).

## Wiring Configuration

### Connect the PWM Bonnet to the Raspberry Pi
Align the 40-pin GPIO header on the Adafruit PWM/Servo Bonnet with the Raspberry Pi's GPIO pins. Push down firmly.

### Connect the Voltmeters to the PWM Bonnet
Assign each voltmeter to a specific PWM channel:
- **Seconds Needle (clockSeconds):** PWM Channel 2
- **Minutes Needle (clockMinutes):** PWM Channel 1
- **Hours Needle (clockHours):** PWM Channel 0

#### Wiring details for each voltmeter:
- **GND Pin:** Connect to the GND terminal of the PWM bonnet.
- **VCC Pin:** Connect to the respective PWM channel terminal.

### Power Supply
Use a micro-USB cable and power adapter to supply power to the Raspberry Pi and PWM Bonnet.

### Optional: PiSugar RTC Battery Pack
Attach the PiSugar 2 battery pack to the Raspberry Pi Zero W to enable portable power and real-time clock functionality.

3D Printable Files for the housing can be found at [Printables](https://www.printables.com/model/1125061-raspberry-pi-clock-boxes).

## Software Setup

### 1. Install Raspberry Pi OS
- Download and install the **Raspberry Pi Imager** from the [official Raspberry Pi website](https://www.raspberrypi.com/software/).
- Insert an SD card into your computer and open the Raspberry Pi Imager.
- Select your Raspberry Pi Device, assuming Raspberry Pi Zero W.
- Choose **OS** and select **Raspberry Pi OS (other)**, then select **Raspberry Pi OS Lite**.
- Select storage.
- On the next screen, select **Edit Settings** and set:
  - **Hostname**
  - **Username and Password**
  - **Configure the Wireless LAN**
  - **Wireless LAN Country**
  - **Locale Settings**
- Click the **Services** tab and select **Enable SSH with password authentication**.
- Click **Save** and confirm you wish to overwrite the SD card.
- Write the OS to the SD card and then insert it into the Raspberry Pi.
- Boot up the Raspberry Pi and run the following commands to update the system:
  ```sh
  sudo apt update && sudo apt upgrade -y
  ```

### 2. Enable I2C on the Raspberry Pi
```sh
sudo raspi-config
```
Navigate to **Interface Options > I2C** and enable it.

Reboot the Raspberry Pi:
```sh
sudo reboot
```

### 3. Install Required Python Libraries
```sh
sudo apt update && sudo apt install python3-pip -y
sudo pip3 install adafruit-circuitpython-pca9685
```

## Running the Clock Software

### Download the Clock Code
Save the provided Python code as `clock.py` in the directory `/home/pi/`.

### Calibrate the Voltmeters
Before running the clock, calibrate the voltmeters to ensure accurate positioning of the needles.
Run the calibration mode:
```sh
python3 clock.py --calibrate
```
Follow the on-screen instructions to fine-tune the PWM values for each step (hours, minutes, seconds). Calibration data will be saved to `calibration_data.json`.

### Run the Clock
```sh
python3 clock.py
```

## How the Code Works

### Key Components

#### PWM Channels for Voltmeters:
- **clockSeconds:** Controls the seconds needle (PWM Channel 2).
- **clockMinutes:** Controls the minutes needle (PWM Channel 1).
- **clockHours:** Controls the hours needle (PWM Channel 0).

#### Calibration (`--calibrate`):
- The program adjusts the PWM values for specific positions of the voltmeter needles (e.g., 0, 10, 20, etc.).
- Calibration data is saved in `calibration_data.json`.

#### Time Interpolation:
- The `interpolate_pwm` function calculates intermediate PWM values for fractional times (e.g., 10:30:45).

#### Smooth Transitions:
- The `move_needle_smoothly` function ensures the voltmeter needles move smoothly between positions.

### Code Structure
```python
# Initialization:
i2c = busio.I2C(board.SCL, board.SDA)
hat = adafruit_pca9685.PCA9685(i2c)
hat.frequency = 60

# Assign channels:
clockSeconds = hat.channels[2]
clockMinutes = hat.channels[1]
clockHours = hat.channels[0]

# Calibration:
python3 clock.py --calibrate

# Clock Execution:
python3 clock.py
```

## Adding the Clock to Startup

To run the clock automatically on boot:

### Create a Systemd Service
```sh
sudo nano /etc/systemd/system/analog-clock.service
```

### Service Configuration
Add the following to the file:
```ini
[Unit]
Description=Analog Voltmeter Clock
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/programs/prod
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 /home/pi/programs/prod/clock.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Enable the Service
```sh
sudo systemctl daemon-reload
sudo systemctl enable analog-clock.service
sudo systemctl start analog-clock.service
```

### Check Service Status
```sh
sudo systemctl status analog-clock.service
```

## Troubleshooting

- **No Calibration File Found:** Run `python3 clock.py --calibrate` to create one.
- **PWM Not Working:** Verify the I2C connection with:
```sh
sudo i2cdetect -y 1
```

