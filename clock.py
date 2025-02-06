import board
import busio
import adafruit_pca9685
import datetime
import time
import json
import sys
import termios
import tty
import select

# Constants
PWM_FREQUENCY = 60
CALIBRATION_FILE = "calibration_data.json"
FINE_STEP = 50  # Fine tuning step (for left/right arrows)
COARSE_STEP = 500  # Coarse tuning step (for up/down arrows)

# Initialize PCA9685
i2c = busio.I2C(board.SCL, board.SDA)
hat = adafruit_pca9685.PCA9685(i2c)
hat.frequency = PWM_FREQUENCY

# Define PWM channels
clockSeconds = hat.channels[2]
clockMinutes = hat.channels[1]
clockHours = hat.channels[0]


def is_key_pressed():
    """Checks if a key is pressed (non-blocking)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
            return key
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def calibrate_dials():
    """
    Calibration mode to record or adjust PWM values for each step.
    Existing values from the calibration file can be adjusted or skipped.
    Saves the results to the calibration file.
    """
    print(
        "Calibration mode. Use LEFT/RIGHT for fine tuning, UP/DOWN for coarse tuning. Press SPACE to save and advance. Press ENTER to skip."
    )

    # Calibration steps
    seconds_minutes_steps = [0, 10, 20, 30, 40, 50, 60]
    hours_steps = list(range(0, 13))

    # Try to load existing calibration data
    try:
        with open(CALIBRATION_FILE, "r") as f:
            calibration_data = json.load(f)
    except FileNotFoundError:
        calibration_data = {"seconds": {}, "minutes": {}, "hours": {}}

    # Helper function to calibrate a single dial
    def calibrate_dial(channel, steps, label):
        print(f"Calibrating {label} needle...")
        for step in steps:
            current_value = calibration_data.get(label, {}).get(str(step), 0)
            print(
                f"Step {step}: Adjust the needle to {step} using LEFT/RIGHT (fine) or UP/DOWN (coarse). Press SPACE when done, or ENTER to skip."
            )

            if current_value:
                print(f"Existing value for {step}: {current_value}. Press ENTER to skip or adjust.")

            pwm_value = current_value

            # Default PWM value for the channel
            channel.duty_cycle = pwm_value

            # Adjust PWM value until the user confirms or skips
            while True:
                key = is_key_pressed()

                if key == "\n":  # Enter to skip
                    print(f"Skipped adjustment for {label} {step}. Keeping value: {pwm_value}")
                    break
                elif key == " ":  # Spacebar to confirm the position
                    print(f"Recorded PWM value {pwm_value} for {label} {step}.")
                    calibration_data[label][str(step)] = pwm_value
                    break
                elif key == "\x1b":  # Arrow keys (Escape sequences)
                    arrow = sys.stdin.read(2)
                    if arrow == "[D":  # Left arrow key (fine decrement)
                        pwm_value = max(0, pwm_value - FINE_STEP)
                    elif arrow == "[C":  # Right arrow key (fine increment)
                        pwm_value = min(65535, pwm_value + FINE_STEP)
                    elif arrow == "[A":  # Up arrow key (coarse increment)
                        pwm_value = min(65535, pwm_value + COARSE_STEP)
                    elif arrow == "[B":  # Down arrow key (coarse decrement)
                        pwm_value = max(0, pwm_value - COARSE_STEP)

                    # Update the needle position
                    channel.duty_cycle = pwm_value

    # Calibrate each dial
    calibrate_dial(clockSeconds, seconds_minutes_steps, "seconds")
    calibrate_dial(clockMinutes, seconds_minutes_steps, "minutes")
    calibrate_dial(clockHours, hours_steps, "hours")

    # Save the calibration data to a file
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration_data, f, indent=4)
    print(f"Calibration complete. Data saved to {CALIBRATION_FILE}.")


def load_calibration_data():
    """Load calibration data from the file."""
    try:
        with open(CALIBRATION_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"No calibration file found. Please run the program with --calibrate to create one.")
        sys.exit(1)


def interpolate_pwm(calibration, current_value):
    """
    Interpolates PWM values from calibration data for a given current value.
    Args:
        calibration: A dictionary containing calibration data (e.g., seconds, minutes).
        current_value: The current second, minute, or hour to interpolate for.
    Returns:
        The interpolated PWM value.
    """
    keys = sorted(int(k) for k in calibration.keys())
    for i in range(len(keys) - 1):
        if keys[i] <= current_value <= keys[i + 1]:
            lower_key = keys[i]
            upper_key = keys[i + 1]
            lower_pwm = calibration[str(lower_key)]
            upper_pwm = calibration[str(upper_key)]
            # Linear interpolation
            return int(lower_pwm + (upper_pwm - lower_pwm) * ((current_value - lower_key) / (upper_key - lower_key)))
    return int(calibration[str(keys[-1])])  # Default to the last key

def move_needle_smoothly(channel, start_pwm, end_pwm, duration=0.1):
    """
    Smoothly move a needle between two PWM values.
    Args:
        channel: PCA9685 channel controlling the needle.
        start_pwm: Starting PWM value.
        end_pwm: Target PWM value.
        duration: Time duration (seconds) for the smooth transition.
    """
    steps = 50  # Number of steps for smooth motion
    step_time = duration / steps
    pwm_step = (end_pwm - start_pwm) / steps

    current_pwm = start_pwm
    for _ in range(steps):
        current_pwm += pwm_step
        channel.duty_cycle = int(current_pwm)
        time.sleep(step_time)

def run_clock():
    """
    Main clock routine to move the needles based on current time
    using calibrated PWM values.
    """
    calibration_data = load_calibration_data()

    # Store the last known PWM values for smooth transitions
    last_second_pwm = 0
    last_minute_pwm = 0
    last_hour_pwm = 0

    while True:
        # Get the current time
        now = datetime.datetime.now()
        current_second = now.second + now.microsecond / 1_000_000  # Include fractional seconds
        current_minute = now.minute + current_second / 60  # Fractional minute
        current_hour = (now.hour % 12 or 12) + current_minute / 60  # Fractional hour

        # Interpolate PWM values
        second_pwm = interpolate_pwm(calibration_data["seconds"], current_second)
        minute_pwm = interpolate_pwm(calibration_data["minutes"], current_minute)
        hour_pwm = interpolate_pwm(calibration_data["hours"], current_hour)

        # Smoothly move the needles
        move_needle_smoothly(clockSeconds, last_second_pwm, second_pwm, 0.02)
        move_needle_smoothly(clockMinutes, last_minute_pwm, minute_pwm, 0.02)
        move_needle_smoothly(clockHours, last_hour_pwm, hour_pwm, 0.02)

        # Update last PWM values
        last_second_pwm = second_pwm
        last_minute_pwm = minute_pwm
        last_hour_pwm = hour_pwm

        # Sleep briefly before the next update (for smooth continuous operation)
        time.sleep(0.02)

# Main logic
if len(sys.argv) > 1 and sys.argv[1] == "--calibrate":
    calibrate_dials()
else:
    run_clock()

