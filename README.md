# Tock Reserver
It's highly recommend to use `reserve_specific.py` instead of `reserve_tfl.py`. If you have multiple dates you can create multiple versions of `reserve_specific.py` and launch them concurrently. `reserve_tfl.py` is only maintained here for legacy reasons. See comments in `reserve_specific.py` for more details.

# Getting Started
Pull the repo and install the python dependencies by running:
```
pip install -r requirements.txt
```

Read the comments in `reserve_specific.py` and edit the settings to suit your needs. Then, to run:
```
python3 reserve_specific.py
```

Since Tock's website may change, it's recommended that you run the script with `TEST_MODE = True` to verify that the script can find a reservation that you know already exists.

OPTIONAL: If the WebDriverException crash resulting from a bug in ChromeDriver is still persisting, you should follow the instructions [here](https://stackoverflow.com/questions/72758996) to install the latest chrome driver and a matching beta version of chrome. Then set `USE_CHROME_BETA` to true in the script. This is especially relevant if you are running this script on an M1/M2 device.