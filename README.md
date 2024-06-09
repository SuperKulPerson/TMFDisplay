# TMFDisplay
TMFDisplay is a [Python](https://www.python.org/) script for [OBS](https://github.com/obsproject/obs-studio) that reads the memory of Trackmania Nations/United Forever and displays it to text sources.

[demo.webm](https://github.com/SuperKulPerson/TMFDisplay/assets/153872437/e95b7e3b-e1dc-43ab-a8c3-915ea6a45c0e)

## Requirements
- Windows.
- Python 3.8 or newer.

## Install
- In OBS, `Tools` > `Scripts` > `Python Settings` set your Python folder. The directory should look something like this: `C:/Users/User/AppData/Local/Programs/Python/Python312`
- Download the latest script, press the + button in `Tools` > `Scripts`, move the script there and load it.

## Usage
- Before you load the script, you should create your text sources.
- For the script to function, it must first setup. Simply follow what the setup status says, and click the refresh button for the next step. Alternatively, open the script log for live updates.
- If the automatic setup fails or picks the wrong game, select the `Setup` option, and set the PID of the game you want to setup. The script will always pick the first opened game to setup.
- Once the setup is complete, select what features you want to enable, and save your settings.
- Important about settings: If saving settings fail, it is usually a folder permission problem. Simply create an empty "MainSettings.json" file and place it in the scripts folder. Alternatively, you can change the folder permissions of the script folder.

## Current Features
- Checkpoint counter.
- Checkpoint timer.
- Respawn counter.
- Gear/RPM.
- FPS.
- Server Timer.

## Future
The next big version (3.0) will most likely be a rewrite. The current script is an unplanned mess, which makes it difficult to add new features. I will still do bugfixes and add some additions if there is any demand.
