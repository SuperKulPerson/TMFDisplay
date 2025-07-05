# TMFDisplay
TMFDisplay is a [Python](https://www.python.org/) script for [OBS](https://github.com/obsproject/obs-studio) that reads the memory of Trackmania Nations/United Forever and displays it to text sources.

[demo.webm](https://github.com/SuperKulPerson/TMFDisplay/assets/153872437/e95b7e3b-e1dc-43ab-a8c3-915ea6a45c0e)

## Requirements
- Windows.
- Python 3.8 to 3.12. OBS does not support Python 3.13 yet.
- Latest OBS.

## Install
1. In OBS, `Tools` > `Scripts` > `Python Settings` set your Python folder. The directory should look something like this: `C:/Users/User/AppData/Local/Programs/Python/Python312`
2. Download the latest script, and place it in `C:\Program Files\obs-studio\data\obs-plugins\frontend-tools\scripts`
3. In OBS, `Tools` > `Scripts` press the + button, and open the script.

## Usage
- To display a checkpoint counter, create a new text source in your scene and name it anything. In the script, click the options dropdown and select `Checkpoint Counter`, enable it, and select the text source you made earlier. Repeat for anything else you want to display.
- To save your settings, click the options dropdown and select `Settings`, there you can save your settings and turn on auto-save/load.
- Important about settings: If saving settings fail, it is usually a folder permission problem. Simply create an empty "MainSettings.json" file and place it in the scripts folder. Alternatively, you can change the folder permissions of the script folder.

## Troubleshoot
- If it says `No properties available` when opening the script, make sure OBS and Python is up to date and that a Python install path is selected in the `Python Settings` tab.
- If the script picks the wrong client, select the `Setup` option, set the new manual PID, and click Start Setup. The script will automatically always pick the first opened game.

## Current Features
- Checkpoint counter.
- Checkpoint timer.
- Predict finish time.
- Respawn counter.
- Gear/RPM.
- FPS.
- Server timer.

## Future
The next big version (3.0) will most likely be a rewrite. The current script is an unplanned mess, which makes it difficult to add new features. I will still do bugfixes and add some features if there is any demand.

# TMFDisplay Inputs
TMFDisplay Inputs is a separate lua script I made to learn obs sources and some graphics. It works without setting up any hotkeys, it can display keyboard and pad inputs, and you can make your own input textures. The script can be found in the "TMFDisplay Inputs" folder.

![input example](https://github.com/user-attachments/assets/58528bac-69ca-4f6c-b5da-77dbb07b0bd5)

### Advantages
- Easy to set up.
- Works with pad and keyboard inputs.
- No hotkeys are needed, instead it reads the inputs from the game.
- Customizable textures.

### Disadvantages
- Only reads from one client at a time. (It is possible to duplicate the script and change the "input.id" variable to fix this.)
- Only works on TMForever games.
