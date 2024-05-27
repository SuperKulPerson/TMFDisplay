'''
Version: 1.2 / 27.05.2024
Minimum Python version: 3.8
Discord: tractorfan
GitHub: https://github.com/SuperKulPerson/TMFDisplay

Version 1.1 > 1.2 / 27.05.2024
Added simple version checking

Version 1.0 > 1.1 / 25.05.2024
Small button text change

Version 1.0.6 > 1.0 / 24.05.2024
New versioning (1.0: Features.Bugfixes/small changes and additions)
Added saving/loading settings

Version 1.0.5 > 1.0.6 / 22.05.2024
Added Checkpoint Timer

Version 1.0.4 > 1.0.5 / 20.05.2024
Added setup option with the ability to set a PID manually and to change game without reloading script.
Added setup function so the script can be loaded at any time and not just when on a map.
Added automatic alt client detection. (Usually Steam)

Version 1.0.3 > 1.0.4
Added Steam compatibility by changing the "steam" variable at the top of the script.

Version 1.0.2 > 1.0.3
Added options to select source and toggle options.
Fixed bug: Script sometimes needed to be reloaded on first load.

Version 1.0.1 > 1.0.2
Added finish detection.
Added automatic max cp detection.

Version 1.0.0 > 1.0.1
Optimized average frame render time by only updating display when the checkpoint changes.
'''

import obspython as obs
import ctypes
import http.client
import json
from datetime import datetime

def get_pid(process_name):
    # Create a buffer to hold process information
    buffer_size = 512
    process_ids = (ctypes.c_uint32 * buffer_size)()
    bytes_returned = ctypes.c_ulong()

    # Call EnumProcesses to get process IDs
    ctypes.windll.psapi.EnumProcesses(ctypes.byref(process_ids), ctypes.sizeof(process_ids), ctypes.byref(bytes_returned))
    total_processes = int(bytes_returned.value / ctypes.sizeof(ctypes.c_uint32))

    # Iterate over process IDs and find the process name
    for i in range(total_processes):
        process_id = process_ids[i]
        process_handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, process_id)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        if process_handle:
            buffer = ctypes.create_string_buffer(512)
            ctypes.windll.psapi.GetModuleBaseNameA(process_handle, None, ctypes.byref(buffer), ctypes.sizeof(buffer))
            if buffer.value.decode().lower() == process_name.lower():
                ctypes.windll.kernel32.CloseHandle(process_handle)
                return process_id
            ctypes.windll.kernel32.CloseHandle(process_handle)
    return None

def address_offsets():
    data = {}
    data['mstime'] = 0x9560CC, [0x0, 0x1C, 0x2B0] #In-game timer in ms.
    data['checkpoint'] = 0x9560CC, [0x0, 0x1C, 0x334] #Current checkpoint.
    data['maxcp'] = 0x9560CC, [0x0, 0x1C, 0x2F8] #Max checkpoint.
    data['cptime'] = 0x95659C, None #Last checkpoint time.
    data['respawn'] = 0x9560CC, [0x0, 0x1C, 0x2C4] #Respawns. (Gets stuck at 999)
    data['speedometer'] = 0x9560CC, [0x0, 0x1C, 0x340] #Car speed. Only positive values.
    return data

def read_address_value(address, process_handle, type):
    if type == bool:
        address_value = ctypes.c_bool()
    else:
        address_value = ctypes.c_int32()
    ctypes.windll.kernel32.ReadProcessMemory(process_handle, address, ctypes.byref(address_value), ctypes.sizeof(address_value), None)
    return address_value.value

def get_final_addresses(base_address, offsets, alt):
    base_address += 0x400000
    if alt:
        base_address += 0x1660
    if not offsets:
        return base_address
    for offset in offsets:
        address_value = read_address_value(base_address, process_handle, None)
        base_address = address_value + offset
        # print(hex(address_value).upper(), hex(offset).upper())
    # print(hex(base_address).upper())
    return base_address

#----------------------------------------------------------------------------------------------#

#Initializing Variables
latest_page = latest_version_date = latest_direct = versionstatus = latest_version = latest_date = autosave = current_update_rate = updater_timer_on = cp0_cptime_display = displayed_mstime = sourcecp = displayed_checkpoint = displayed_max_checkpoint = displayed_sourcecp = prefixcp = process_handle = enabledcp = finish_reached = setuptimer = settingscopy = setupstage = setupinfo = manualpid = process_handle_pid = pid = pre_prevent_first_load = prevent_first_load = alt = enabledcptime = sourcecptime = displayed_sourcecptime = None
version = "v1.2"
date = "27.05.2024"
update_rate = 10
displayed_checkpoint_time = new_update = 0
process_name = "TmForever.exe"
address_offsets_data = address_offsets()
final_addresses = []

def get_latest():
    conn = http.client.HTTPSConnection("api.github.com")
    endpoint = f"/repos/SuperKulPerson/TMFDisplay/releases/latest"
    
    conn.request("GET", endpoint, headers={"User-Agent": "Python-Client"})
    response = conn.getresponse()
    
    if response.status == 200:
        data = response.read().decode()
        release = json.loads(data)
        release_tag = release['tag_name']
        release_date = release['published_at']
        release_page = release['html_url']
        release_assets = release['assets']
        release_direct = [asset['browser_download_url'] for asset in release_assets][0]
        return release_tag, release_date, release_direct, release_page
    
    print("Get latest version failed")
    return None, None, None, None

def format_date(iso_date_str):
    dt = datetime.strptime(iso_date_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%d.%m.%Y")

def check_version():
    global versionstatus, new_update, latest_direct, latest_version_date, latest_page
    
    latest_version, latest_date, latest_direct, latest_page = get_latest()
    
    version_date = version + " / " + date
    
    if latest_version and latest_date:
        latest_date = format_date(latest_date)
        latest_version_date = latest_version + " / " + latest_date
    
        if version != latest_version:
            new_update = 3
            versionstatus = f"<font color=#ff8800><b>New version available: {latest_version_date}</b></font>"
        else:
            new_update = 2
            versionstatus = f"<font color=#55ff55><b>On latest version: {version_date}</b></font>"
        return
    new_update = 1
    versionstatus = f"<font color=#ff5555><b>Could not get the latest version.</b></font>"
    return

def display(sourcename, displayvalue): #Displays text to a text source. Possible optimization: For timers, reducing the source and data creation/release amount to only once can save about 10% on frame render times.
    if not sourcename or not displayvalue:
        # print("No Source or No Display value")
        return
    source = obs.obs_get_source_by_name(sourcename)
    source_data = obs.obs_data_create()
    obs.obs_data_set_string(source_data, "text", displayvalue)
    obs.obs_source_update(source, source_data)
    obs.obs_data_release(source_data)
    obs.obs_source_release(source)

def format_time(mstime):
    hours = mstime // 3600000
    minutes = (mstime // 60000) % 60
    seconds = (mstime // 1000) % 60
    centiseconds = (mstime % 1000) // 10
    return "%02d:%02d:%02d.%02d" % (hours, minutes, seconds, centiseconds)

def finish_checker(current_checkpoint, current_max_checkpoint):
    global finish_reached
    
    if current_checkpoint == current_max_checkpoint and not finish_reached:
        # print("finish/true")
        finish_reached = True
    elif current_checkpoint != current_max_checkpoint and finish_reached:
        # print("false")
        finish_reached = False

def checkpoint_updater(current_checkpoint, current_max_checkpoint):
    global displayed_checkpoint, displayed_max_checkpoint, displayed_sourcecp, finish_reached, final_addresses, process_handle
    
    # print("A", current_checkpoint, current_max_checkpoint)
    # print("B", final_addresses[0], final_addresses[1], final_addresses[2])
    # print("C", process_handle)
    
    if not finish_reached and (displayed_checkpoint != current_checkpoint or displayed_max_checkpoint != current_max_checkpoint or displayed_sourcecp != sourcecp):
        # print("Display")
        displayed_checkpoint = current_checkpoint
        displayed_max_checkpoint = current_max_checkpoint
        displayed_sourcecp = sourcecp
        current_checkpoint = prefixcp + str(current_checkpoint) + seperatorcp + str(current_max_checkpoint - 1)
        display(sourcecp, current_checkpoint)
    # print("updated")

def checkpoint_time_updater(current_mstime, current_checkpoint_time, current_checkpoint, current_max_checkpoint):
    global final_addresses, process_handle, finish_reached, displayed_sourcecptime, displayed_mstime, cp0timedisplay, displayed_checkpoint_time, prefixcptime
    
    if current_checkpoint == 0:
        if cp0timedisplay != displayed_mstime:
            if cp0timedisplay:
                display(sourcecptime, prefixcptime + cp0timedisplay)
            else:
                display(sourcecptime, " ")
            displayed_mstime = cp0timedisplay
        return
    
    if finish_reached:
        if displayed_checkpoint_time != current_checkpoint_time:
            current_mstime -= displayed_checkpoint_time
            displayed_checkpoint_time = current_checkpoint_time
            display(sourcecptime, prefixcptime + format_time(current_mstime))
        return
    else:
        current_mstime -= current_checkpoint_time
    
    if displayed_checkpoint_time != current_checkpoint_time or displayed_mstime != current_mstime or displayed_sourcecptime != sourcecptime:
        displayed_sourcecptime = sourcecptime
        displayed_mstime = current_mstime
        displayed_checkpoint_time = current_checkpoint_time
        display(sourcecptime, prefixcptime + format_time(current_mstime))
        return

def updater():
    global enabledcp, enabledcptime, updater_timer_on, update_rate, current_update_rate
    if update_rate != current_update_rate:
        obs.timer_remove(updater)
        obs.timer_add(updater, update_rate)
        # print("before", current_update_rate)
        current_update_rate = update_rate
        # print("after", current_update_rate)
    
    if enabledcptime:
        current_mstime = int(read_address_value(final_addresses[0], process_handle, None)) #If optimization is needed, try batch address reading in future.
    if enabledcp or enabledcptime:
        current_checkpoint = int(read_address_value(final_addresses[1], process_handle, None))
    if enabledcp or enabledcptime:
        current_max_checkpoint = int(read_address_value(final_addresses[2], process_handle, None))
    if enabledcptime:
        current_checkpoint_time = int(read_address_value(final_addresses[3], process_handle, None))
    
    if enabledcp or enabledcptime:
        finish_checker(current_checkpoint, current_max_checkpoint)
    
    if enabledcp:
        checkpoint_updater(current_checkpoint, current_max_checkpoint)
    if enabledcptime:
        checkpoint_time_updater(current_mstime, current_checkpoint_time, current_checkpoint, current_max_checkpoint)
    updater_timer_on = True

def setup(*args): #Get PID > Alt client check > In-Game check > Get final addresses.
    global setuptimer, pid, process_handle, setupstage, setupinfo, manualpid, process_handle_pid, final_addresses, alt, updater_timer_on, update_rate
    
    if updater_timer_on:
        obs.timer_remove(updater)
        updater_timer_on = False
    
    if final_addresses:
        final_addresses = []
    
    if not manualpid:
        pid = get_pid(process_name)
    
    if process_handle and process_handle_pid != pid:
        # print("Proc hand unset")
        ctypes.windll.kernel32.CloseHandle(process_handle)
        process_handle = None
        process_handle_pid = pid
    
    if pid and not process_handle:
        # print("Proc hand set")
        process_handle = ctypes.windll.kernel32.OpenProcess(0x10, False, pid)
        process_handle_pid = pid
    
    if process_handle:
        alt = bool(read_address_value(0xCCCD48, process_handle, bool)) #Checks if TmForever.exe an alt client (usually Steam). Address: Base + 0x977B4C
    else:
        if not setuptimer:
            obs.timer_add(setup, 1000)
            setuptimer = True
        if manualpid:
            setupinfo = "Set a valid PID."
        else:
            setupinfo = "No PID found, open TMNF/TMUF, or set a PID manually."
        if setupstage != 1:
            print(setupinfo)
            setupstage = 1
        setupinfo = "<font color=#ff8800><b>" + setupinfo + "</b></font>"
        return
    
    ingame_address = 0xD77B4C #Address: Base + 0x977B4C
    
    if alt:
        ingame_address += 0x1660
    
    ingame = bool(read_address_value(ingame_address, process_handle, bool)) #Checks if in-game (on a map).
    
    if ingame:
        for offsetName, (offsetBase, offsets) in address_offsets_data.items():
            final_addresses.append(get_final_addresses(offsetBase, offsets, alt))
        if setuptimer:
            setuptimer = False
        obs.timer_remove(setup)
        obs.timer_add(updater, update_rate)
        setupinfo = "Setup Complete. (PID: " + str(pid) + ")"
        print(setupinfo)
        setupinfo = "<font color=#55ff55><b>" + setupinfo + "</b></font>"
        setupstage = 3
        return
    else:
        if not setuptimer:
            obs.timer_add(setup, 1000)
            setuptimer = True
        if setupstage != 2:
            setupinfo = "Load any map to finish the setup."
            print(setupinfo)
            setupinfo = "<font color=#ff8800><b>" + setupinfo + "</b></font>"
            setupstage = 2
        return

#-OBS START-#

def script_load(settings):
    print("Script Loaded.")
    
    setup()
    
    global settingscopy
    settingscopy = settings

def script_unload():
    global prevent_first_load, pre_prevent_first_load, autosave, settingscopy, setuptimer
    if autosave:
        button_save_settings(None, None, None)
        print("Autosaved")
    prevent_first_load = pre_prevent_first_load = False
    obs.timer_remove(updater)
    obs.timer_remove(setup)
    setuptimer = False
    ctypes.windll.kernel32.CloseHandle(process_handle)
    print("Script Unloaded")

def script_defaults(settings):
    obs.obs_data_set_int(settings, "setting_update_rate", 10)
    obs.obs_data_set_bool(settings, "setup_manualpid", False)
    obs.obs_data_set_bool(settings, "enabledcp", False)
    obs.obs_data_set_bool(settings, "enabledcptime", False)
    obs.obs_data_set_bool(settings, "setting_autosave", False)
    obs.obs_data_set_string(settings, "cp0timedisplay", "")
    obs.obs_data_set_string(settings, "options", "Status")
    obs.obs_data_set_string(settings, "sourcecp", "No Source")
    obs.obs_data_set_string(settings, "prefixcp", "CP: ")
    obs.obs_data_set_string(settings, "seperatorcp", "/")
    obs.obs_data_set_string(settings, "sourcecptime", "No Source")
    obs.obs_data_set_string(settings, "prefixcptime", "CP Time: ") 

def button_check_version(props, prop, *settings):
    global prevent_first_load, new_update
    if prevent_first_load:
        check_version()
    
    options_update(props, None, settingscopy)
    return True

def button_save_settings(props, prop, *settings):
    global prevent_first_load, settingscopy
    if prevent_first_load:
        filtered_settings = obs.obs_data_create()
        
        exclude = ["statussetup", "statuscp", "statuscptime", "examplesourcecp", "examplecp", "examplesourcecptime", "examplecptime", "setup_altclient", "setup_status", "setup_currentpid", "options", "setup_setpid", "setup_manualpid", "setting_version"]
        
        obs.obs_data_apply(filtered_settings, settingscopy)
        for name in exclude:
            obs.obs_data_erase(filtered_settings, name)
        obs.obs_data_save_json(filtered_settings, script_path() + "/MainSettings.json")
        obs.obs_data_release(filtered_settings)
    return True

def button_load_settings(props, prop, *settings):
    global prevent_first_load, settingscopy
    if prevent_first_load:
        settingsload = obs.obs_data_create_from_json_file(script_path() + "/MainSettings.json")
        if settingsload:
            obs.obs_data_apply(settingscopy, settingsload)
            options_update(None, None, settingscopy)
            options_update(None, None, settingscopy) #Refresh twice to fully update
        else:
            print("No Settings")
        obs.obs_data_release(settingsload)
    return True

def button_set_pid(props, prop, *settings):
    global pid, manualpid, setuptimer, prevent_first_load
    if manualpid:
        pid = obs.obs_data_get_int(settingscopy, "setup_setpid")
    
    if setuptimer and prevent_first_load:
        setup()
    
    options_update(props, None, settingscopy)
    return True

def button_start_setup(props, prop, *settings):
    global setuptimer, prevent_first_load
    
    if not setuptimer and prevent_first_load:
        setup()
    
    options_update(props, None, settingscopy)
    return True

def options_update(props, prop, *settings):
    global latest_page, latest_direct, new_update, versionstatus, autosave, pre_prevent_first_load, prevent_first_load, sourcecp, prefixcp, seperatorcp, enabledcp, setupinfo, setupstage, pid, manualpid, alt, setuptimer, enabledcptime, sourcecptime, cp0timedisplay, prefixcptime, update_rate
    
    s_option = obs.obs_data_get_string(settingscopy, "options")
    s_sourcecp = obs.obs_data_get_string(settingscopy, "sourcecp")
    s_sourcecptime = obs.obs_data_get_string(settingscopy, "sourcecptime")
    
    property_list = []
    
    property_list.append(p_status_load_settings := obs.obs_properties_get(props, "status_load_settings"))
    property_list.append(p_statusrefresh := obs.obs_properties_get(props, "statusrefresh"))
    property_list.append(p_statussetup := obs.obs_properties_get(props, "statussetup"))
    property_list.append(p_statuscp := obs.obs_properties_get(props, "statuscp"))
    property_list.append(p_statuscptime := obs.obs_properties_get(props, "statuscptime"))
    
    property_list.append(p_enabledcp := obs.obs_properties_get(props, "enabledcp"))
    property_list.append(p_source := obs.obs_properties_get(props, "sourcecp"))
    property_list.append(p_prefixcp := obs.obs_properties_get(props, "prefixcp"))
    property_list.append(p_seperatorcp := obs.obs_properties_get(props, "seperatorcp"))
    property_list.append(p_examplesourcecp := obs.obs_properties_get(props, "examplesourcecp"))
    property_list.append(p_examplecp := obs.obs_properties_get(props, "examplecp"))
    
    property_list.append(p_enabledcptime := obs.obs_properties_get(props, "enabledcptime"))
    property_list.append(p_sourcecptime := obs.obs_properties_get(props, "sourcecptime"))
    property_list.append(p_cp0timedisplay := obs.obs_properties_get(props, "cp0timedisplay"))
    property_list.append(p_prefixcptime := obs.obs_properties_get(props, "prefixcptime"))
    property_list.append(p_examplesourcecptime := obs.obs_properties_get(props, "examplesourcecptime"))
    property_list.append(p_examplecptime := obs.obs_properties_get(props, "examplecptime"))
    
    property_list.append(p_setup_refresh := obs.obs_properties_get(props, "setup_refresh"))
    property_list.append(p_setup_currentpid := obs.obs_properties_get(props, "setup_currentpid"))
    property_list.append(p_setup_setpidbutton := obs.obs_properties_get(props, "setup_setpidbutton"))
    property_list.append(p_setup_manualpid := obs.obs_properties_get(props, "setup_manualpid"))
    property_list.append(p_setup_setpid := obs.obs_properties_get(props, "setup_setpid"))
    property_list.append(p_setup_start := obs.obs_properties_get(props, "setup_start"))
    property_list.append(p_setup_status := obs.obs_properties_get(props, "setup_status"))
    property_list.append(p_setup_altclient := obs.obs_properties_get(props, "setup_altclient"))
    
    property_list.append(p_setting_update_rate := obs.obs_properties_get(props, "setting_update_rate"))
    property_list.append(p_setting_save_settings := obs.obs_properties_get(props, "setting_save_settings"))
    property_list.append(p_setting_load_settings := obs.obs_properties_get(props, "setting_load_settings"))
    property_list.append(p_setting_autosave := obs.obs_properties_get(props, "setting_autosave"))
    property_list.append(p_setting_check_version := obs.obs_properties_get(props, "setting_check_version"))
    property_list.append(p_setting_version := obs.obs_properties_get(props, "setting_version"))
    property_list.append(p_setting_download_direct := obs.obs_properties_get(props, "setting_download_direct"))
    property_list.append(p_setting_download_page := obs.obs_properties_get(props, "setting_download_page"))
    
    
    #-Status-#
    status_disabled = "<font color=#ff8800><b>Disabled</b></font>"
    status_enabled = "<font color=#55ff55><b>Enabled</b></font>"
    status_enabled_nosource = "<font color=#ff5555><b>Enabled, NO SOURCE.</b></font>"
    
    obs.obs_data_set_string(settingscopy, "statussetup", setupinfo)
    obs.obs_data_set_string(settingscopy, "statuscp", status_disabled)
    obs.obs_data_set_string(settingscopy, "statuscptime", status_disabled)
    
    if s_sourcecp == "No Source" or not s_sourcecp:
        if enabledcp:
            obs.obs_data_set_string(settingscopy, "statuscp", status_enabled_nosource)
    else:
        if enabledcp:
            obs.obs_data_set_string(settingscopy, "statuscp", status_enabled)        
    if s_sourcecptime == "No Source" or not s_sourcecptime:
        if enabledcptime:
            obs.obs_data_set_string(settingscopy, "statuscptime", status_enabled_nosource)
    else:
        if enabledcptime:
            obs.obs_data_set_string(settingscopy, "statuscptime", status_enabled)
    
    
    #-Status End-#
    
    #-Checkpoint Counter-#
    enabledcp = obs.obs_data_get_bool(settingscopy, "enabledcp")
    sourcecp = obs.obs_data_get_string(settingscopy, "sourcecp")
    seperatorcp = obs.obs_data_get_string(settingscopy, "seperatorcp")
    prefixcp = obs.obs_data_get_string(settingscopy, "prefixcp")
    
    obs.obs_data_set_string(settingscopy, "examplesourcecp", sourcecp)
    obs.obs_data_set_string(settingscopy, "examplecp", prefixcp + "3" + seperatorcp + "17")
    #-Checkpoint Counter End-#
    
    #-Checkpoint Timer-#
    enabledcptime = obs.obs_data_get_bool(settingscopy, "enabledcptime")
    sourcecptime = obs.obs_data_get_string(settingscopy, "sourcecptime")
    cp0timedisplay = obs.obs_data_get_string(settingscopy, "cp0timedisplay")
    prefixcptime = obs.obs_data_get_string(settingscopy, "prefixcptime")
    
    obs.obs_data_set_string(settingscopy, "examplesourcecptime", sourcecptime)
    obs.obs_data_set_string(settingscopy, "examplecptime", prefixcptime + "01:24:35.98")
    #-Checkpoint Timer End-#
    
    #-Setup-#
    manualpid = obs.obs_data_get_bool(settingscopy, "setup_manualpid")
    
    if setuptimer and prevent_first_load:
        setup()
    
    obs.obs_data_set_string(settingscopy, "setup_altclient", str(alt))
    
    obs.obs_data_set_string(settingscopy, "setup_status", setupinfo)
    
    if pid:
        obs.obs_data_set_string(settingscopy, "setup_currentpid", str(pid))
    else:
        obs.obs_data_set_string(settingscopy, "setup_currentpid", "<font color=#ff8800><b>None</b></font>")
    #-Setup End-#
    
    #-Settings-#
    update_rate = obs.obs_data_get_int(settingscopy, "setting_update_rate")
    autosave = obs.obs_data_get_bool(settingscopy, "setting_autosave")
    obs.obs_data_set_string(settingscopy, "setting_version", versionstatus)
    
    #-Settings End-#
    
    for p_name in property_list:
        obs.obs_property_set_visible(p_name, False)
    
    if s_option == "Status":
        obs.obs_property_set_visible(p_statusrefresh, True)
        obs.obs_property_set_visible(p_status_load_settings, True)
        obs.obs_property_set_visible(p_statussetup, True)
        obs.obs_property_set_visible(p_statuscp, True)
        obs.obs_property_set_visible(p_statuscptime, True)

    elif s_option == "Checkpoint Counter":
        obs.obs_property_set_visible(p_enabledcp, True)
        obs.obs_property_set_visible(p_source, True)
        obs.obs_property_set_visible(p_prefixcp, True)
        obs.obs_property_set_visible(p_seperatorcp, True)
        obs.obs_property_set_visible(p_examplesourcecp, True)
        obs.obs_property_set_visible(p_examplecp, True)
        
    elif s_option == "Checkpoint Timer":
        obs.obs_property_set_visible(p_enabledcptime, True)
        obs.obs_property_set_visible(p_sourcecptime, True)
        obs.obs_property_set_visible(p_cp0timedisplay, True)
        obs.obs_property_set_visible(p_prefixcptime, True)
        obs.obs_property_set_visible(p_examplesourcecptime, True)
        obs.obs_property_set_visible(p_examplecptime, True)
        
    elif s_option == "Setup":
        obs.obs_property_set_visible(p_setup_refresh, True)
        obs.obs_property_set_visible(p_setup_currentpid, True)
        obs.obs_property_set_visible(p_setup_manualpid, True)
        obs.obs_property_set_visible(p_setup_status, True)
        obs.obs_property_set_visible(p_setup_altclient, True)
        if manualpid:
            obs.obs_property_set_visible(p_setup_setpid, True)
            obs.obs_property_set_visible(p_setup_setpidbutton, True)
        if setupstage == 3:
            obs.obs_property_set_visible(p_setup_start, True)
        
    elif s_option == "Settings":
        obs.obs_property_set_visible(p_setting_update_rate, True)
        obs.obs_property_set_visible(p_setting_save_settings, True)
        obs.obs_property_set_visible(p_setting_load_settings, True)
        obs.obs_property_set_visible(p_setting_autosave, True)
        obs.obs_property_set_visible(p_setting_check_version, True)
        if new_update >= 1:
            obs.obs_property_set_visible(p_setting_version, True)
        if new_update == 3:
            obs.obs_property_set_visible(p_setting_download_direct, True)
            obs.obs_property_button_set_url(p_setting_download_direct, latest_direct)
            obs.obs_property_set_visible(p_setting_download_page, True)
            obs.obs_property_button_set_url(p_setting_download_page, latest_page)
    
    if prop == 10 and pre_prevent_first_load: #Scuffed way of preventing setup() from being called multiple times at script start.
        prevent_first_load = True
    return True

def script_properties():
    props = obs.obs_properties_create()
    p = obs.obs_properties_add_list(props, "options", "Options", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p, "Status", "Status")
    obs.obs_property_list_add_string(p, "Checkpoint Counter", "Checkpoint Counter")
    obs.obs_property_list_add_string(p, "Checkpoint Timer", "Checkpoint Timer")
    obs.obs_property_list_add_string(p, "Setup", "Setup")
    obs.obs_property_list_add_string(p, "Settings", "Settings")
    obs.obs_property_set_modified_callback(p, options_update)
    
    text_sources_list = []
    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            name = obs.obs_source_get_name(source)
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id == "text_gdiplus" or source_id == "text_ft2_source":
                name = obs.obs_source_get_name(source)
                text_sources_list.append(name)
        obs.source_list_release(sources)
    
    #-Status-#
    p = obs.obs_properties_add_button(props, "status_load_settings", "Load from \"MainSettings.json\"", button)
    obs.obs_property_set_modified_callback(p, button_load_settings)
    p = obs.obs_properties_add_button(props, "statusrefresh", "Refresh Status", button)
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_text(props, "statussetup", "Setup:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_text(props, "statuscp", "Checkpoint Counter:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_text(props, "statuscptime", "Checkpoint Timer:", obs.OBS_TEXT_INFO)
    
    
    #-Status End-#
    
    #-Checkpoint Counter-#
    p = obs.obs_properties_add_bool(props, "enabledcp", "Enabled")
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_list(props, "sourcecp", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p, "No Source", None)
    obs.obs_property_set_modified_callback(p, options_update)
    for name in text_sources_list:
        obs.obs_property_list_add_string(p, name, name)
    
    p = obs.obs_properties_add_text(props, "prefixcp", "Prefix", obs.OBS_TEXT_DEFAULT)
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_text(props, "seperatorcp", "Separator", obs.OBS_TEXT_DEFAULT)
    obs.obs_property_set_modified_callback(p, options_update)
    
    p = obs.obs_properties_add_text(props, "examplesourcecp", "Source:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_text(props, "examplecp", "Example:", obs.OBS_TEXT_INFO)
    #-Checkpoint Counter End-#
    
    #-Checkpoint Timer-#
    p = obs.obs_properties_add_bool(props, "enabledcptime", "Enabled")
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_list(props, "sourcecptime", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(p, "No Source", None)
    obs.obs_property_set_modified_callback(p, options_update)
    for name in text_sources_list:
        obs.obs_property_list_add_string(p, name, name)
    
    p = obs.obs_properties_add_text(props, "prefixcptime", "Prefix", obs.OBS_TEXT_DEFAULT)
    obs.obs_property_set_modified_callback(p, options_update)
    
    p = obs.obs_properties_add_text(props, "cp0timedisplay", "CP 0", obs.OBS_TEXT_DEFAULT)
    obs.obs_property_set_modified_callback(p, options_update)
    obs.obs_property_set_long_description(p, "What to display on Checkpoint 0.\nEmpty: Invisible")
    
    p = obs.obs_properties_add_text(props, "examplesourcecptime", "Source:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_text(props, "examplecptime", "Example:", obs.OBS_TEXT_INFO)
    #-Checkpoint Timer End-#
    
    #-Setup-#
    p = obs.obs_properties_add_button(props, "setup_refresh", "Refresh Setup", button)
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_button(props, "setup_start", "Start Setup", button) #Not shown when setup is running.
    obs.obs_property_set_modified_callback(p, button_start_setup)
    p = obs.obs_properties_add_bool(props, "setup_manualpid", "Manual PID")
    obs.obs_property_set_modified_callback(p, options_update)
    obs.obs_property_set_long_description(p, "Useful for when a PID is not found or when multiple games are open.\nTask manager > right click any column > toggle PID on.")
    p = obs.obs_properties_add_int(props, "setup_setpid", "PID to set:", 0, 10000000, 4)
    p = obs.obs_properties_add_button(props, "setup_setpidbutton", "Set PID", button)
    obs.obs_property_set_modified_callback(p, button_set_pid)
    p = obs.obs_properties_add_text(props, "setup_currentpid", "Current PID:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_text(props, "setup_status", "Status:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_text(props, "setup_altclient", "Alt Client:", obs.OBS_TEXT_INFO)
    obs.obs_property_set_long_description(p, "Usually a TmForever.exe from Steam.")
    #-Setup End-#
    
    #-Settings-#
    p = obs.obs_properties_add_int(props, "setting_update_rate", "Update rate", 1, 5000, 10)
    obs.obs_property_set_long_description(p, "How often the script reads from the game and displays to sources.")
    obs.obs_property_int_set_suffix(p, "ms")
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_button(props, "setting_save_settings", "Save to \"MainSettings.json\"", button)
    obs.obs_property_set_modified_callback(p, button_save_settings)
    p = obs.obs_properties_add_button(props, "setting_load_settings", "Load from \"MainSettings.json\"", button)
    obs.obs_property_set_modified_callback(p, button_load_settings)
    p = obs.obs_properties_add_bool(props, "setting_autosave", "Autosave to \"MainSettings.json\" on exit")
    obs.obs_property_set_modified_callback(p, options_update)
    p = obs.obs_properties_add_button(props, "setting_check_version", "Check for update", button)
    obs.obs_property_set_modified_callback(p, button_check_version)
    p = obs.obs_properties_add_text(props, "setting_version", "Version:", obs.OBS_TEXT_INFO)
    p = obs.obs_properties_add_button(props, "setting_download_direct", "Direct download", button)
    obs.obs_property_button_set_type(p, obs.OBS_BUTTON_URL)
    p = obs.obs_properties_add_button(props, "setting_download_page", "Download page", button)
    obs.obs_property_button_set_type(p, obs.OBS_BUTTON_URL)
    
    #-Settings End-#
    
    global settingscopy, pre_prevent_first_load
    options_update(props, 10, settingscopy)
    pre_prevent_first_load = True
    
    return props

def button():
    return

def script_description():
    return "<font><b>" + version + " / " + date + "</b></font>"
