'''
Version: 2.0 / 09.06.2024
Minimum Python version: 3.8
Discord: tractorfan
GitHub: https://github.com/SuperKulPerson/TMFDisplay

Performance issues? Try these tips:
-Change the formatting of the Checkpoint Timer.
-Disable antialiasing in your text sources.
-Change the font size in your text sources to something lower.
-Change the update rate to something less frequent.

Version 2.0 > 2.1 / 26.06.2024
Fixed compatibility with TMLoader.

Version 1.3 > 2.0 / 09.06.2024
Added Gear and RPM display.
Added Respawn Counter.
Added Server Timer. Shows the timer of the server even while the HUD is off.
Added FPS Counter. Shows the FPS counter without having to open the debug menu.
Added Timer formatting.
Checkpoint Timer now works while HUD is off.
Hopefully better online support. (Not fully tested)
Added setting to toggle any display to sources off while spectating or the in menu.
Improved alt client detection.
Setup will now restart after finishing or spectating and when exiting a map.
Fixed Checkpoint Counter not updating display on prefix/separator change.
And more!

Version 1.2 > 1.3 / 27.05.2024
Added auto loading settings
Removed load settings button from status

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
import ctypes.wintypes
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

def get_base_address(pid):
	# Define necessary constants
	TH32CS_SNAPMODULE = 0x00000008
	
	# Define necessary structures
	class MODULEENTRY32(ctypes.Structure):
		_fields_ = [
			("dwSize", ctypes.wintypes.DWORD),
			("th32ModuleID", ctypes.wintypes.DWORD),
			("th32ProcessID", ctypes.wintypes.DWORD),
			("GlblcntUsage", ctypes.wintypes.DWORD),
			("ProccntUsage", ctypes.wintypes.DWORD),
			("modBaseAddr", ctypes.wintypes.LPVOID),
			("modBaseSize", ctypes.wintypes.DWORD),
			("hModule", ctypes.wintypes.HMODULE),
			("szModule", ctypes.c_char * 256),
			("szExePath", ctypes.c_char * 260),
		]

	# Create snapshot of all processes and modules
	snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
	
	if snapshot == -1:
		print(f"Failed to create snapshot of processes for PID {pid}.")
		return None

	# Find the main module (executable) of the specified process
	me32 = MODULEENTRY32()
	me32.dwSize = ctypes.sizeof(MODULEENTRY32)

	if not ctypes.windll.kernel32.Module32First(snapshot, ctypes.byref(me32)):
		ctypes.windll.kernel32.CloseHandle(snapshot)
		print(f"Failed to find base address for process with PID {pid}.")
		return None

	base_address = me32.modBaseAddr
	
	# Close the snapshot handle
	ctypes.windll.kernel32.CloseHandle(snapshot)

	return base_address

def address_offsets(data):
	main_data = {}
	main_data['mstime'] = 0x9560CC, [0x0, 0x1C, 0x2B0] # In-game timer in ms. [0]
	main_data['checkpoint'] = 0x9560CC, [0x0, 0x1C, 0x334] # Current checkpoint number.
	main_data['maxcp'] = 0x9560CC, [0x0, 0x1C, 0x2F8] # Max checkpoint.
	main_data['cptime'] = 0x968C44, [0x12C, 0x244, 0x0, 0x2FC, 0x0] # Cptime of cp1. Add 0x8 for each cp to get the cptime of all cps.
	main_data['finish'] = 0x9560CC, [0x0, 0x1C, 0x33C] # 0 = Not finished. 1 = Finished. [4]
	main_data['spectator'] = 0x967524, None # Checks if in spectator mode on a server. 200 = Playing. 500 = Spectating.
	main_data['respawns'] = 0x968C44, [0x454, 0x340] # Counts respawns above 999. Misscounts when resetting a run, but fixes itself after the run has started.
	main_data['hud'] = 0x968C44, [0x454, 0x518, 0x18] # 0 = HUD Off. 1 = HUD On.
	main_data['gear'] = 0x9560CC, [0x4, 0x5C8] # 0 = Backwards gear. Goes up to 5. [8]
	main_data['rpm'] = 0x9560CC, [0x4, 0x5B8] # RPM of the car. Does not work on TMOriginal envis (Probably cus they don't have rpm).
	main_data['fps'] = 0x968C44, [0x454, 0x278] #FPS Counter. Works without toggling the fps counter in-game
	main_data['servertimer'] = 0x968C44, [0x454, 0x518, 0xC8] # Current time on server. Shows 0 if no server timer or offline.
	setup_data = {}
	setup_data['state'] = 0x9560CC, [0x0, 0x1C, 0x124] # 1 = Online menu and party play > on a local network. 2 = Loading map on server. 16 = Select account. 32 = Menu. 64 = Quit game confirmation. 128 = Select mood/mod of map and loading map offline. 256 = Editor. 512 = On a map. 1024 = Finish screen offline. 2048 Replay editor. 4096 = Select replay operation menu. 16384 = During "Please Wait" on server. 32768 = On a map on server. [0]
	setup_data['altstate'] = 0x95772C, [0x0, 0x1C, 0x124] # Same as above. Both of these addresses will not be able to see most of the states, this is intentional to prevent setup() from pre-firing.
	if data == "main_data":
		return main_data
	elif data == "setup_data":
		return setup_data
	return

def read_address_value(address, float):
	if float:
		address_value = ctypes.c_float()
	else:
		address_value = ctypes.c_int32()
	ctypes.windll.kernel32.ReadProcessMemory(process_handle, address, ctypes.byref(address_value), ctypes.sizeof(address_value), None)
	return address_value.value

def get_final_addresses(base_address, offset_address, offsets, alt):
	offset_address += base_address
	if alt:
		offset_address += 0x1660
	if not offsets:
		return offset_address
	for offset in offsets:
		address_value = read_address_value(offset_address, False)
		offset_address = address_value + offset
		# print(hex(address_value).upper(), hex(offset).upper())
	# print(hex(offset_address).upper())
	return offset_address

#----------------------------------------------------------------------------------------------#

#Initialize Variables
tmloader = serverhudservertimer = displayed_server_time = displayed_sourceservertime = displayed_fps = displayed_sourcefps = enabledservertimer = sourceservertimer = prefixservertimer = formatservertimer = enabledfps = sourcefps = prefixfps = current_setup_rate = prefixgear = prefixrpm = sourcerpm = sourcegear = displayed_sourcerpm = displayed_rpm = displayed_gear = displayed_sourcegear = enabledrpm = enabledgear = serverhudcp = displayed_respawns = enabledrespawns = sourcerespawns = prefixrespawns = displayed_sourcerespawns = disabled_displays = display_toggle = spectator = formatcptime = hudcptime = autoload = latest_page = latest_version_date = latest_direct = versionstatus = latest_version = latest_date = autosave = current_update_rate = updater_timer_on = cp0_cptime_display = displayed_mstime_cptime = sourcecp = displayed_checkpoint = displayed_max_checkpoint = displayed_sourcecp = prefixcp = process_handle = enabledcp = finish_reached = setuptimer = settingscopy = setupstage = setupinfo = manualpid = process_handle_pid = pid = pre_prevent_first_load = prevent_first_load = alt = enabledcptime = sourcecptime = displayed_sourcecptime = None
version = "v2.1"
date = "26.06.2024"
update_rate = 10
setup_rate = 500
displayed_checkpoint_time = new_update = 0
process_name = "TmForever.exe"
address_offsets_data = address_offsets("main_data")
address_offsets_setup_data = address_offsets("setup_data")
final_setup_addresses = final_addresses = []

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

def display(sourcename, displayvalue, disable):
	if not sourcename:
		return
	source = obs.obs_get_source_by_name(sourcename)
	if displayvalue:
		source_data = obs.obs_data_create()
		obs.obs_data_set_string(source_data, "text", displayvalue)
		obs.obs_source_update(source, source_data)
		obs.obs_data_release(source_data)
	if disable:
		obs.obs_source_set_enabled(source, False)
	else:
		obs.obs_source_set_enabled(source, True)
	obs.obs_source_release(source)

def format_time(mstime, format):
	if format == 3:
		hours = mstime // 3600000
		minutes = (mstime // 60000) % 60
		seconds = (mstime // 1000) % 60
		centiseconds = (mstime % 1000) // 10
		return "%02d:%02d:%02d.%02d" % (hours, minutes, seconds, centiseconds)
	elif format == 2:
		hours = mstime // 3600000
		minutes = (mstime // 60000) % 60
		seconds = (mstime // 1000) % 60
		return "%02d:%02d:%02d" % (hours, minutes, seconds)
	elif format == 1:
		total_minutes = mstime // 60000
		seconds = (mstime // 1000) % 60
		centiseconds = (mstime % 1000) // 10
		return "%02d:%02d.%02d" % (total_minutes, seconds, centiseconds)
	else:
		total_minutes = mstime // 60000
		seconds = (mstime // 1000) % 60
		return "%02d:%02d" % (total_minutes, seconds)

def checkpoint_updater(current_checkpoint, current_max_checkpoint):
	global displayed_checkpoint, displayed_max_checkpoint, displayed_sourcecp, finish_reached
	
	current_checkpoint = prefixcp + str(current_checkpoint) + seperatorcp + str(current_max_checkpoint - 1)
	
	if not finish_reached and (displayed_checkpoint != current_checkpoint or displayed_max_checkpoint != current_max_checkpoint or displayed_sourcecp != sourcecp):
		
		displayed_checkpoint = current_checkpoint
		displayed_max_checkpoint = current_max_checkpoint
		displayed_sourcecp = sourcecp
		display(sourcecp, current_checkpoint, None)

def checkpoint_time_updater(current_mstime, current_checkpoint_time, current_checkpoint, current_max_checkpoint):
	global formatcptime, finish_reached, displayed_sourcecptime, displayed_mstime_cptime, cp0timedisplay, displayed_checkpoint_time, prefixcptime
	
	if current_checkpoint == 0:
		if cp0timedisplay != displayed_mstime_cptime:
			if cp0timedisplay:
				display(sourcecptime, prefixcptime + cp0timedisplay, None)
			else:
				display(sourcecptime, " ", None)
			displayed_mstime_cptime = cp0timedisplay
		return
	
	if finish_reached:
		if displayed_checkpoint_time != current_checkpoint_time:
			current_mstime -= displayed_checkpoint_time
			displayed_checkpoint_time = current_checkpoint_time
			display(sourcecptime, prefixcptime + format_time(current_mstime, formatcptime), None)
		return
	else:
		current_mstime -= current_checkpoint_time
	
	if displayed_checkpoint_time != current_checkpoint_time or displayed_mstime_cptime != current_mstime or displayed_sourcecptime != sourcecptime:
		displayed_sourcecptime = sourcecptime
		displayed_mstime_cptime = current_mstime
		displayed_checkpoint_time = current_checkpoint_time
		display(sourcecptime, prefixcptime + format_time(current_mstime, formatcptime), None)
		return

def respawn_updater(current_mstime, current_respawns):
	global displayed_respawns, displayed_sourcerespawns, finish_reached
	
	if current_mstime <= 0:
		current_respawns = 0
	
	current_respawns = prefixrespawns + str(current_respawns)
	
	if not finish_reached and (displayed_respawns != current_respawns or displayed_sourcerespawns != sourcerespawns):
		displayed_respawns = current_respawns
		displayed_sourcerespawns = sourcerespawns
		display(sourcerespawns, current_respawns, None)

def gear_updater(current_gear):
	global displayed_gear, displayed_sourcegear
	
	current_gear = prefixgear + str(current_gear)
	
	if displayed_gear != current_gear or displayed_sourcegear != sourcegear:
		displayed_gear = current_gear
		displayed_sourcegear = sourcegear
		display(sourcegear, current_gear, None)

def rpm_updater(current_rpm):
	global displayed_rpm, displayed_sourcerpm
	
	current_rpm = prefixrpm + str(current_rpm)
	
	if displayed_rpm != current_rpm or displayed_sourcerpm != sourcerpm:
		displayed_rpm = current_rpm
		displayed_sourcerpm = sourcerpm
		display(sourcerpm, current_rpm, None)

def fps_updater(current_fps):
	global displayed_fps, displayed_sourcefps
	
	current_fps = prefixfps + str(current_fps)
	
	if displayed_fps != current_fps or displayed_sourcefps != sourcefps:
		displayed_fps = current_fps
		displayed_sourcefps = sourcefps
		display(sourcefps, current_fps, None)

def server_time_updater(current_server_time):
	global displayed_server_time, displayed_sourceservertimer
	
	current_server_time = prefixservertimer + format_time(current_server_time, formatservertimer)
	
	if displayed_server_time != current_server_time or displayed_sourceservertimer != sourceservertimer:
		displayed_server_time = current_server_time
		displayed_sourceservertimer = sourceservertimer
		display(sourceservertimer, current_server_time, None)

def updater():
	global serverhudservertimer, serverhudcp, disabled_displays, spectator, alt, enabledcp, enabledcptime, updater_timer_on, update_rate, current_update_rate, finish_reached
	
	if update_rate != current_update_rate:
		obs.timer_remove(updater)
		obs.timer_add(updater, update_rate)
		current_update_rate = update_rate
	
	hud = read_address_value(final_addresses[7], False)
	spectator_check = read_address_value(final_addresses[5], False)
	ingame_check = read_address_value(final_setup_addresses[alt], False)
	
	if ingame_check in (16384, 32768) and spectator_check == 500:
		spectator = 1
	
	if ingame_check not in (512, 16384, 32768) or (spectator and spectator_check == 200):
		spectator = 0
		setup()
		return
	
	if display_toggle:
		disabled_displays = spectator
		if enabledcp:
			display(sourcecp, None, spectator)
		if enabledcptime:
			display(sourcecptime, None, spectator)
		if enabledrespawns:
			display(sourcerespawns, None, spectator)
		if enabledgear:
			display(sourcegear, None, spectator)
		if enabledrpm:
			display(sourcerpm, None, spectator)
	elif disabled_displays:
		disabled_displays = None
		display(sourcecp, None, None)
		display(sourcecptime, None, None)
		display(sourcerespawns, None, None)
		display(sourcegear, None, None)
		display(sourcerpm, None, None)
	
	if ingame_check in (16384, 32768): #Probably needs rewrite but im lazy rn (whole script tbh)
		if serverhudservertimer:
			display(sourceservertimer, None, hud)
		if serverhudcp and spectator_check == 200:
			display(sourcecp, None, hud)
	elif not display_toggle:
		display(sourceservertimer, None, None)
		display(sourcecp, None, None)
	
	if enabledcptime or enabledrespawns:
		current_mstime = read_address_value(final_addresses[0], False)
	if enabledcp or enabledcptime:
		current_checkpoint = read_address_value(final_addresses[1], False)
	if enabledcp or enabledcptime:
		current_max_checkpoint = read_address_value(final_addresses[2], False)
	if enabledcptime:
		current_checkpoint_time = read_address_value(final_addresses[3] + max(current_checkpoint - 1, 0) * 0x8, False)
	if enabledcp or enabledcptime or enabledrespawns:
		finish_reached = read_address_value(final_addresses[4], False)
	if enabledrespawns:
		current_respawns = read_address_value(final_addresses[6], False)
	if enabledgear:
		current_gear = read_address_value(final_addresses[8], False)
	if enabledrpm:
		current_rpm = int(read_address_value(final_addresses[9], True))
	if enabledfps:
		current_fps = int(read_address_value(final_addresses[10], True))
	if enabledservertimer and ingame_check in (16384, 32768):
		current_server_time = read_address_value(final_addresses[11], False)
	
	if enabledcp:
		if serverhudcp:
			if ingame_check in (16384, 32768) and not hud:
				if display_toggle:
					if spectator_check == 200:
						checkpoint_updater(current_checkpoint, current_max_checkpoint) # this nest... im so done
				else:
					checkpoint_updater(current_checkpoint, current_max_checkpoint)
			elif ingame_check not in (16384, 32768):
				checkpoint_updater(current_checkpoint, current_max_checkpoint)
		else:
			checkpoint_updater(current_checkpoint, current_max_checkpoint)
	if enabledcptime:
		checkpoint_time_updater(current_mstime, current_checkpoint_time, current_checkpoint, current_max_checkpoint)
	if enabledrespawns:
		respawn_updater(current_mstime, current_respawns)
	if enabledgear:
		gear_updater(current_gear)
	if enabledrpm:
		rpm_updater(current_rpm)
	if enabledfps:
		fps_updater(current_fps)
	if enabledservertimer and ingame_check in (16384, 32768):
		if serverhudservertimer:
			if not hud:
				server_time_updater(current_server_time)
				display(sourceservertimer, None, None)
		else:
			server_time_updater(current_server_time)
			display(sourceservertimer, None, None)
		if current_server_time == 0:
			display(sourceservertimer, None, 1)
	
	updater_timer_on = True

def setup(*args): #Get PID > Get Base Address > Alt client and In-Game check > Get final addresses.
	global tmloader, current_setup_rate, finish_reached, disabled_displays, final_setup_addresses, setup_rate, setuptimer, pid, process_handle, setupstage, setupinfo, manualpid, process_handle_pid, final_addresses, alt, updater_timer_on, update_rate
	
	if display_toggle:
		if finish_reached:
			disabled_displays = 0
		else:
			disabled_displays = 1
		
		if enabledcp:
			display(sourcecp, None, disabled_displays)
		if enabledcptime:
			display(sourcecptime, None, disabled_displays)
		if enabledrespawns:
			display(sourcerespawns, None, disabled_displays)
		if enabledgear:
			display(sourcegear, None, disabled_displays)
		if enabledrpm:
			display(sourcerpm, None, disabled_displays)
		if enabledservertimer:
			display(sourceservertimer, None, 1)
		if enabledfps:
			display(sourcefps, None, disabled_displays)
	elif disabled_displays:
		disabled_displays = None
		display(sourcecp, None, None)
		display(sourcecptime, None, None)
		display(sourcerespawns, None, None)
		display(sourcegear, None, None)
		display(sourcerpm, None, None)
		display(sourcefps, None, None)
	
	if updater_timer_on:
		obs.timer_remove(updater)
		updater_timer_on = False
	
	if setup_rate != current_setup_rate and setuptimer:
		obs.timer_remove(setup)
		obs.timer_add(setup, setup_rate)
		current_setup_rate = setup_rate
	
	final_addresses = []
	final_setup_addresses = []
	spectator_check = None
	
	if not manualpid:
		pid = get_pid(process_name)
	
	base_address = get_base_address(pid)
	
	if process_handle and process_handle_pid != pid:
		ctypes.windll.kernel32.CloseHandle(process_handle)
		process_handle = None
		process_handle_pid = pid
	
	if pid and not process_handle:
		process_handle = ctypes.windll.kernel32.OpenProcess(0x10, False, pid)
		process_handle_pid = pid
	
	ingame = False
	
	if process_handle:
		for offsetName, (offsetBase, offsets) in address_offsets_setup_data.items():
			final_setup_addresses.append(get_final_addresses(base_address, offsetBase, offsets, None))
		
		ingame_check = read_address_value(final_setup_addresses[0], False)
		ingame_check_alt = read_address_value(final_setup_addresses[1], False)
		# print(ingame_check, ingame_check_alt, final_setup_addresses)
		if base_address == 0x400000:
			tmloader = 0
		else:
			tmloader = 1
		if ingame_check in (512, 16384, 32768):
			ingame = True
			alt = 0
		elif ingame_check_alt in (512, 16384, 32768):
			ingame = True
			alt = 1
		if 1024 in (ingame_check, ingame_check_alt):
			finish_reached = 1
		else:
			finish_reached = 0
	else:
		if not setuptimer:
			obs.timer_add(setup, setup_rate)
			setuptimer = True
		if manualpid:
			setupinfo = "Set a valid PID."
		else:
			setupinfo = "No PID found, open TMNF/TMUF, or set a PID manually."
		if setupstage != 1:
			print(setupinfo)
			setupstage = 1
		setupinfo = f"<font color=#ff5555><b>{setupinfo}</b></font>"
		return
	
	if ingame:
		for offsetName, (offsetBase, offsets) in address_offsets_data.items():
			final_addresses.append(get_final_addresses(base_address, offsetBase, offsets, alt))
		if setuptimer:
			setuptimer = False
			obs.timer_remove(setup)
		obs.timer_add(updater, update_rate)
		setupinfo = f"Setup Complete. (PID: {str(pid)})"
		print(setupinfo)
		setupinfo = f"<font color=#55ff55><b>{setupinfo}</b></font>"
		setupstage = 3
		# for i, address in enumerate(final_addresses):
			# print(i, hex(address).upper())
		return
	else:
		if not setuptimer:
			obs.timer_add(setup, setup_rate)
			setuptimer = True
		if setupstage != 2:
			setupinfo = f"Load any map. (PID: {str(pid)})"
			print(setupinfo)
			setupinfo = f"<font color=#ff8800><b>{setupinfo}</b></font>"
			setupstage = 2
		return

#-OBS START-#

def script_load(settings):
	print("Script Loaded.")
	
	setup()
	
	global settingscopy
	settingscopy = settings
	
	global autoload
	settings_autoload = obs.obs_data_create_from_json_file(script_path() + "/MainSettings.json")
	if settings_autoload:
		autoload = obs.obs_data_get_bool(settings_autoload, "setting_autoload")
		if autoload:
			print("Autoloaded")
			obs.obs_data_apply(settingscopy, settings_autoload)
			options_update(None, None, settingscopy)

def script_unload():
	global prevent_first_load, pre_prevent_first_load, autosave, settingscopy, setuptimer, process_handle
	if autosave:
		button_save_settings(None, None, None)
	prevent_first_load = pre_prevent_first_load = False
	setuptimer = False
	process_handle = None
	ctypes.windll.kernel32.CloseHandle(process_handle)
	print("Script Unloaded")

def script_defaults(settings):
	obs.obs_data_set_int(settings, "formatservertimer", 0)
	obs.obs_data_set_int(settings, "formatcptime", 0)
	obs.obs_data_set_int(settings, "setting_update_rate", 10)
	obs.obs_data_set_int(settings, "setting_setup_rate", 500)
	obs.obs_data_set_bool(settings, "setup_manualpid", False)
	obs.obs_data_set_bool(settings, "enabledcp", False)
	obs.obs_data_set_bool(settings, "serverhudcp", False)
	obs.obs_data_set_bool(settings, "serverhudservertimer", False)
	obs.obs_data_set_bool(settings, "enabledcptime", False)
	obs.obs_data_set_bool(settings, "enabledrespawns", False)
	obs.obs_data_set_bool(settings, "enabledgear", False)
	obs.obs_data_set_bool(settings, "enabledservertimer", False)
	obs.obs_data_set_bool(settings, "enabledrpm", False)
	obs.obs_data_set_bool(settings, "enabledfps", False)
	obs.obs_data_set_bool(settings, "setting_autosave", False)
	obs.obs_data_set_bool(settings, "setting_autoload", False)
	obs.obs_data_set_bool(settings, "setting_display_toggle", False)
	obs.obs_data_set_string(settings, "sourcefps", "No Source")
	obs.obs_data_set_string(settings, "prefixfps", "FPS: ")
	obs.obs_data_set_string(settings, "sourceservertimer", "No Source")
	obs.obs_data_set_string(settings, "prefixservertimer", "Time left: ")
	obs.obs_data_set_string(settings, "sourcegear", "No Source")
	obs.obs_data_set_string(settings, "prefixgear", "Gear: ")
	obs.obs_data_set_string(settings, "sourcerpm", "No Source")
	obs.obs_data_set_string(settings, "prefixrpm", "RPM: ")
	obs.obs_data_set_string(settings, "sourcerespawns", "No Source")
	obs.obs_data_set_string(settings, "prefixrespawns", "Respawns: ")
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
		
		exclude = ["statussetup", "statuscp", "statuscptime", "examplesourcecp", "examplecp", "examplesourcecptime", "examplecptime", "setup_altclient", "setup_status", "setup_currentpid", "options", "setup_setpid", "setup_manualpid", "setting_version", "examplerespawns", "statusrespawns", "examplesourcerespawns", "statusgear", "statusrpm", "examplerpm", "examplegear", "examplesourcerpm", "examplesourcegear", "statusservertimer", "statusfps", "examplefps", "examplesourcefps", "exampleservertimer", "examplesourceservertimer"]
		
		obs.obs_data_apply(filtered_settings, settingscopy)
		for name in exclude:
			obs.obs_data_erase(filtered_settings, name)
		saved = obs.obs_data_save_json(filtered_settings, script_path() + "/MainSettings.json")
		obs.obs_data_release(filtered_settings)
		if saved:
			print("Saved Successfully")
		else:
			print(f"Failed to save to {script_path()}MainSettings.json\nTry making a file with the same name and save again.")
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
	global tmloader, serverhudservertimer, enabledservertimer, sourceservertimer, prefixservertimer, formatservertimer, enabledfps, sourcefps, prefixfps, setup_rate, sourcegear, sourcerpm, prefixgear, prefixrpm, enabledrpm, enabledgear, serverhudcp, enabledrespawns, sourcerespawns, prefixrespawns, display_toggle, formatcptime, hudcptime, latest_page, latest_direct, new_update, versionstatus, autosave, pre_prevent_first_load, prevent_first_load, sourcecp, prefixcp, seperatorcp, enabledcp, setupinfo, pid, manualpid, alt, setuptimer, enabledcptime, sourcecptime, cp0timedisplay, prefixcptime, update_rate
	
	property_list = []
	
	property_list.append(p_statusrefresh := obs.obs_properties_get(props, "statusrefresh")) # Wish there was a better way of doing this :'(
	property_list.append(p_statussetup := obs.obs_properties_get(props, "statussetup"))
	property_list.append(p_statuscp := obs.obs_properties_get(props, "statuscp"))
	property_list.append(p_statuscptime := obs.obs_properties_get(props, "statuscptime"))
	property_list.append(p_statusrespawns := obs.obs_properties_get(props, "statusrespawns"))
	property_list.append(p_statusgear := obs.obs_properties_get(props, "statusgear"))
	property_list.append(p_statusrpm := obs.obs_properties_get(props, "statusrpm"))
	property_list.append(p_statusfps := obs.obs_properties_get(props, "statusfps"))
	property_list.append(p_statusservertimer := obs.obs_properties_get(props, "statusservertimer"))
	
	property_list.append(p_enabledcp := obs.obs_properties_get(props, "enabledcp"))
	property_list.append(p_sourcecp := obs.obs_properties_get(props, "sourcecp"))
	property_list.append(p_prefixcp := obs.obs_properties_get(props, "prefixcp"))
	property_list.append(p_seperatorcp := obs.obs_properties_get(props, "seperatorcp"))
	property_list.append(p_serverhudcp := obs.obs_properties_get(props, "serverhudcp"))
	property_list.append(p_examplesourcecp := obs.obs_properties_get(props, "examplesourcecp"))
	property_list.append(p_examplecp := obs.obs_properties_get(props, "examplecp"))
	
	property_list.append(p_enabledcptime := obs.obs_properties_get(props, "enabledcptime"))
	property_list.append(p_sourcecptime := obs.obs_properties_get(props, "sourcecptime"))
	property_list.append(p_cp0timedisplay := obs.obs_properties_get(props, "cp0timedisplay"))
	property_list.append(p_prefixcptime := obs.obs_properties_get(props, "prefixcptime"))
	property_list.append(p_formatcptime := obs.obs_properties_get(props, "formatcptime"))
	property_list.append(p_examplesourcecptime := obs.obs_properties_get(props, "examplesourcecptime"))
	property_list.append(p_examplecptime := obs.obs_properties_get(props, "examplecptime"))
	
	property_list.append(p_enabledrespawns := obs.obs_properties_get(props, "enabledrespawns"))
	property_list.append(p_sourcerespawns := obs.obs_properties_get(props, "sourcerespawns"))
	property_list.append(p_prefixrespawns := obs.obs_properties_get(props, "prefixrespawns"))
	property_list.append(p_examplesourcerespawns := obs.obs_properties_get(props, "examplesourcerespawns"))
	property_list.append(p_examplerespawns := obs.obs_properties_get(props, "examplerespawns"))
	
	property_list.append(p_enabledgear := obs.obs_properties_get(props, "enabledgear"))
	property_list.append(p_sourcegear := obs.obs_properties_get(props, "sourcegear"))
	property_list.append(p_sourcerpm := obs.obs_properties_get(props, "sourcerpm"))
	property_list.append(p_prefixgear := obs.obs_properties_get(props, "prefixgear"))
	property_list.append(p_prefixrpm := obs.obs_properties_get(props, "prefixrpm"))
	property_list.append(p_examplesourcegear := obs.obs_properties_get(props, "examplesourcegear"))
	property_list.append(p_examplegear := obs.obs_properties_get(props, "examplegear"))
	property_list.append(p_examplesourcerpm := obs.obs_properties_get(props, "examplesourcerpm"))
	property_list.append(p_examplerpm := obs.obs_properties_get(props, "examplerpm"))   
	
	property_list.append(p_enabledfps := obs.obs_properties_get(props, "enabledfps"))
	property_list.append(p_sourcefps := obs.obs_properties_get(props, "sourcefps"))
	property_list.append(p_prefixfps := obs.obs_properties_get(props, "prefixfps"))
	property_list.append(p_examplesourcefps := obs.obs_properties_get(props, "examplesourcefps"))
	property_list.append(p_examplefps := obs.obs_properties_get(props, "examplefps"))
	
	property_list.append(p_enabledservertimer := obs.obs_properties_get(props, "enabledservertimer"))
	property_list.append(p_sourceservertimer := obs.obs_properties_get(props, "sourceservertimer"))
	property_list.append(p_prefixservertimer := obs.obs_properties_get(props, "prefixservertimer"))
	property_list.append(p_formatservertimer := obs.obs_properties_get(props, "formatservertimer"))
	property_list.append(p_serverhudservertimer := obs.obs_properties_get(props, "serverhudservertimer"))
	property_list.append(p_examplesourceservertimer := obs.obs_properties_get(props, "examplesourceservertimer"))
	property_list.append(p_exampleservertimer := obs.obs_properties_get(props, "exampleservertimer"))
	
	property_list.append(p_setup_refresh := obs.obs_properties_get(props, "setup_refresh"))
	property_list.append(p_setup_currentpid := obs.obs_properties_get(props, "setup_currentpid"))
	property_list.append(p_setup_setpidbutton := obs.obs_properties_get(props, "setup_setpidbutton"))
	property_list.append(p_setup_manualpid := obs.obs_properties_get(props, "setup_manualpid"))
	property_list.append(p_setup_setpid := obs.obs_properties_get(props, "setup_setpid"))
	property_list.append(p_setup_start := obs.obs_properties_get(props, "setup_start"))
	property_list.append(p_setup_status := obs.obs_properties_get(props, "setup_status"))
	property_list.append(p_setup_altclient := obs.obs_properties_get(props, "setup_altclient"))
	property_list.append(p_setup_tmloader := obs.obs_properties_get(props, "setup_tmloader"))
	
	property_list.append(p_setting_update_rate := obs.obs_properties_get(props, "setting_update_rate"))
	property_list.append(p_setting_setup_rate := obs.obs_properties_get(props, "setting_setup_rate"))
	property_list.append(p_setting_save_settings := obs.obs_properties_get(props, "setting_save_settings"))
	property_list.append(p_setting_load_settings := obs.obs_properties_get(props, "setting_load_settings"))
	property_list.append(p_setting_autosave := obs.obs_properties_get(props, "setting_autosave"))
	property_list.append(p_setting_autoload := obs.obs_properties_get(props, "setting_autoload"))
	property_list.append(p_setting_display_toggle := obs.obs_properties_get(props, "setting_display_toggle"))
	property_list.append(p_setting_check_version := obs.obs_properties_get(props, "setting_check_version"))
	property_list.append(p_setting_version := obs.obs_properties_get(props, "setting_version"))
	property_list.append(p_setting_download_direct := obs.obs_properties_get(props, "setting_download_direct"))
	property_list.append(p_setting_download_page := obs.obs_properties_get(props, "setting_download_page"))
	
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
	
	if text_sources_list:
		source_list = [p_sourcecp, p_sourcecptime, p_sourcerespawns, p_sourcegear, p_sourcerpm, p_sourcefps, p_sourceservertimer]
		for source in source_list:
			obs.obs_property_list_clear(source)
			obs.obs_property_list_add_string(source, "No Source", None)
			for name in text_sources_list:
				obs.obs_property_list_add_string(source, name, name)
	
	#-Checkpoint Counter-#
	enabledcp = obs.obs_data_get_bool(settingscopy, "enabledcp")
	sourcecp = obs.obs_data_get_string(settingscopy, "sourcecp")
	seperatorcp = obs.obs_data_get_string(settingscopy, "seperatorcp")
	prefixcp = obs.obs_data_get_string(settingscopy, "prefixcp")
	serverhudcp = obs.obs_data_get_bool(settingscopy, "serverhudcp")
	
	if not sourcecp:
		sourcecp = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcecp", sourcecp)
	obs.obs_data_set_string(settingscopy, "examplecp", prefixcp + "3" + seperatorcp + "17")
	#-Checkpoint Counter End-#
	
	#-Checkpoint Timer-#
	enabledcptime = obs.obs_data_get_bool(settingscopy, "enabledcptime")
	sourcecptime = obs.obs_data_get_string(settingscopy, "sourcecptime")
	cp0timedisplay = obs.obs_data_get_string(settingscopy, "cp0timedisplay")
	prefixcptime = obs.obs_data_get_string(settingscopy, "prefixcptime")
	formatcptime = obs.obs_data_get_int(settingscopy, "formatcptime")
	
	if not sourcecptime:
		sourcecptime = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcecptime", sourcecptime)
	obs.obs_data_set_string(settingscopy, "examplecptime", prefixcptime + format_time(5025678, formatcptime))
	#-Checkpoint Timer End-#
	
	#-Respawn Counter-#
	enabledrespawns = obs.obs_data_get_bool(settingscopy, "enabledrespawns")
	sourcerespawns = obs.obs_data_get_string(settingscopy, "sourcerespawns")
	prefixrespawns = obs.obs_data_get_string(settingscopy, "prefixrespawns")
	
	if not sourcerespawns:
		sourcerespawns = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcerespawns", sourcerespawns)
	obs.obs_data_set_string(settingscopy, "examplerespawns", prefixrespawns + "35")
	#-Respawn Counter End-#
	
	#-Gear-#
	enabledgear = obs.obs_data_get_bool(settingscopy, "enabledgear")
	enabledrpm = enabledgear
	sourcegear = obs.obs_data_get_string(settingscopy, "sourcegear")
	sourcerpm = obs.obs_data_get_string(settingscopy, "sourcerpm")
	prefixgear = obs.obs_data_get_string(settingscopy, "prefixgear")
	prefixrpm = obs.obs_data_get_string(settingscopy, "prefixrpm")
	
	if not sourcegear:
		sourcegear = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcegear", sourcegear)
	obs.obs_data_set_string(settingscopy, "examplegear", prefixgear + "2")
	if not sourcerpm:
		sourcerpm = "No Source"
		enabledrpm = False
	obs.obs_data_set_string(settingscopy, "examplesourcerpm", sourcerpm)
	obs.obs_data_set_string(settingscopy, "examplerpm", prefixrpm + "5372")
	#-Gear End-#
	
	#-FPS-#
	enabledfps = obs.obs_data_get_bool(settingscopy, "enabledfps")
	sourcefps = obs.obs_data_get_string(settingscopy, "sourcefps")
	prefixfps = obs.obs_data_get_string(settingscopy, "prefixfps")
	
	if not sourcefps:
		sourcefps = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcefps", sourcefps)
	obs.obs_data_set_string(settingscopy, "examplefps", prefixfps + "157")
	#-FPS End-#
	
	#-Server Timer-#
	enabledservertimer = obs.obs_data_get_bool(settingscopy, "enabledservertimer")
	sourceservertimer = obs.obs_data_get_string(settingscopy, "sourceservertimer")
	prefixservertimer = obs.obs_data_get_string(settingscopy, "prefixservertimer")
	formatservertimer = obs.obs_data_get_int(settingscopy, "formatservertimer")
	serverhudservertimer = obs.obs_data_get_bool(settingscopy, "serverhudservertimer")
	
	if not sourceservertimer:
		sourceservertimer = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourceservertimer", sourceservertimer)
	obs.obs_data_set_string(settingscopy, "exampleservertimer", prefixservertimer + format_time(5025678, formatservertimer))
	#-Server Timer End-#
	
	#-Setup-#
	manualpid = obs.obs_data_get_bool(settingscopy, "setup_manualpid")
	
	if setuptimer and prevent_first_load:
		setup()
	
	obs.obs_data_set_string(settingscopy, "setup_altclient", str(bool(alt)))
	obs.obs_data_set_string(settingscopy, "setup_tmloader", str(bool(tmloader)))
	
	obs.obs_data_set_string(settingscopy, "setup_status", setupinfo)
	
	if pid:
		obs.obs_data_set_string(settingscopy, "setup_currentpid", str(pid))
	else:
		obs.obs_data_set_string(settingscopy, "setup_currentpid", "<font color=#ff8800><b>None</b></font>")
	#-Setup End-#
	
	#-Settings-#
	update_rate = obs.obs_data_get_int(settingscopy, "setting_update_rate")
	setup_rate = obs.obs_data_get_int(settingscopy, "setting_setup_rate")
	autosave = obs.obs_data_get_bool(settingscopy, "setting_autosave")
	autoload = obs.obs_data_get_bool(settingscopy, "setting_autoload")
	display_toggle = obs.obs_data_get_bool(settingscopy, "setting_display_toggle")
	obs.obs_data_set_string(settingscopy, "setting_version", versionstatus)
	
	#-Settings End-#
	
	#-Status-#
	status_disabled = "<font color=#ff8800><b>Disabled</b></font>"
	status_enabled = "<font color=#55ff55><b>Enabled</b></font>"
	status_enabled_nosource = "<font color=#ff5555><b>Enabled, NO SOURCE.</b></font>"
	
	obs.obs_data_set_string(settingscopy, "statussetup", setupinfo)

	status_source = [(sourcecp, "statuscp", enabledcp), (sourcecptime, "statuscptime", enabledcptime), (sourcerespawns, "statusrespawns", enabledrespawns), (sourcegear, "statusgear", enabledgear), (sourcerpm , "statusrpm", enabledrpm), (sourcefps, "statusfps", enabledfps), (sourceservertimer, "statusservertimer", enabledservertimer)]
	
	for source, status, enabled in status_source:
		obs.obs_data_set_string(settingscopy, status, status_disabled)
		if source == "No Source" or not source:
			if enabled:
				obs.obs_data_set_string(settingscopy, status, status_enabled_nosource)
		else:
			if enabled:
				obs.obs_data_set_string(settingscopy, status, status_enabled)
	
	#-Status End-#
	
	s_option = obs.obs_data_get_string(settingscopy, "options")
	
	for p_name in property_list:
		obs.obs_property_set_visible(p_name, False)
	
	if s_option == "Status":
		obs.obs_property_set_visible(p_statusrefresh, True)
		obs.obs_property_set_visible(p_statussetup, True)
		obs.obs_property_set_visible(p_statuscp, True)
		obs.obs_property_set_visible(p_statuscptime, True)
		obs.obs_property_set_visible(p_statusrespawns, True)
		obs.obs_property_set_visible(p_statusgear, True)
		obs.obs_property_set_visible(p_statusfps, True)
		obs.obs_property_set_visible(p_statusservertimer, True)
		
		if sourcerpm and sourcerpm != "No Source":
			obs.obs_property_set_visible(p_statusrpm, True)
		
	elif s_option == "Checkpoint Counter":
		obs.obs_property_set_visible(p_enabledcp, True)
		obs.obs_property_set_visible(p_sourcecp, True)
		obs.obs_property_set_visible(p_prefixcp, True)
		obs.obs_property_set_visible(p_seperatorcp, True)
		obs.obs_property_set_visible(p_serverhudcp, True)
		obs.obs_property_set_visible(p_examplesourcecp, True)
		obs.obs_property_set_visible(p_examplecp, True)
		
	elif s_option == "Checkpoint Timer":
		obs.obs_property_set_visible(p_enabledcptime, True)
		obs.obs_property_set_visible(p_sourcecptime, True)
		obs.obs_property_set_visible(p_cp0timedisplay, True)
		obs.obs_property_set_visible(p_prefixcptime, True)
		obs.obs_property_set_visible(p_formatcptime, True)
		obs.obs_property_set_visible(p_examplesourcecptime, True)
		obs.obs_property_set_visible(p_examplecptime, True)
		
	elif s_option == "Respawn Counter":
		obs.obs_property_set_visible(p_enabledrespawns, True)
		obs.obs_property_set_visible(p_sourcerespawns, True)
		obs.obs_property_set_visible(p_prefixrespawns, True)
		obs.obs_property_set_visible(p_examplesourcerespawns, True)
		obs.obs_property_set_visible(p_examplerespawns, True)
		
	elif s_option == "Gear":
		obs.obs_property_set_visible(p_enabledgear, True)
		obs.obs_property_set_visible(p_sourcegear, True)
		obs.obs_property_set_visible(p_sourcerpm, True)
		obs.obs_property_set_visible(p_prefixgear, True)
		obs.obs_property_set_visible(p_examplesourcegear, True)
		obs.obs_property_set_visible(p_examplegear, True)
		
		if sourcerpm and sourcerpm != "No Source":
			obs.obs_property_set_visible(p_prefixrpm, True)
			obs.obs_property_set_visible(p_examplesourcerpm, True)
			obs.obs_property_set_visible(p_examplerpm, True)
		
	elif s_option == "FPS":
		obs.obs_property_set_visible(p_enabledfps, True)
		obs.obs_property_set_visible(p_sourcefps, True)
		obs.obs_property_set_visible(p_prefixfps, True)
		obs.obs_property_set_visible(p_examplesourcefps, True)
		obs.obs_property_set_visible(p_examplefps, True)
		
	elif s_option == "Server Timer":
		obs.obs_property_set_visible(p_enabledservertimer, True)
		obs.obs_property_set_visible(p_sourceservertimer, True)
		obs.obs_property_set_visible(p_prefixservertimer, True)
		obs.obs_property_set_visible(p_formatservertimer, True)
		obs.obs_property_set_visible(p_serverhudservertimer, True)
		obs.obs_property_set_visible(p_examplesourceservertimer, True)
		obs.obs_property_set_visible(p_exampleservertimer, True)
		
	elif s_option == "Setup":
		obs.obs_property_set_visible(p_setup_refresh, True)
		obs.obs_property_set_visible(p_setup_currentpid, True)
		obs.obs_property_set_visible(p_setup_manualpid, True)
		obs.obs_property_set_visible(p_setup_status, True)
		obs.obs_property_set_visible(p_setup_altclient, True)
		obs.obs_property_set_visible(p_setup_tmloader, True)
		if manualpid:
			obs.obs_property_set_visible(p_setup_setpid, True)
			obs.obs_property_set_visible(p_setup_setpidbutton, True)
		if not setuptimer:
			obs.obs_property_set_visible(p_setup_start, True)
		
	elif s_option == "Settings":
		obs.obs_property_set_visible(p_setting_update_rate, True)
		obs.obs_property_set_visible(p_setting_setup_rate, True)
		obs.obs_property_set_visible(p_setting_save_settings, True)
		obs.obs_property_set_visible(p_setting_load_settings, True)
		obs.obs_property_set_visible(p_setting_autosave, True)
		obs.obs_property_set_visible(p_setting_autoload, True)
		obs.obs_property_set_visible(p_setting_display_toggle, True)
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
	obs.obs_property_list_add_string(p, "Respawn Counter", "Respawn Counter")
	obs.obs_property_list_add_string(p, "Gear", "Gear")
	obs.obs_property_list_add_string(p, "FPS", "FPS")
	obs.obs_property_list_add_string(p, "Server Timer", "Server Timer")
	obs.obs_property_list_add_string(p, "Setup", "Setup")
	obs.obs_property_list_add_string(p, "Settings", "Settings")
	obs.obs_property_set_modified_callback(p, options_update)
	
	#-Status-#
	p = obs.obs_properties_add_button(props, "statusrefresh", "Refresh Status", button)
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_text(props, "statussetup", "Setup:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "statuscp", "Checkpoint Counter:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "statuscptime", "Checkpoint Timer:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "statusrespawns", "Respawn Counter:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "statusgear", "Gear:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "statusrpm", "RPM:", obs.OBS_TEXT_INFO) #Hidden until rpm source is chosen
	p = obs.obs_properties_add_text(props, "statusfps", "FPS:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "statusservertimer", "Server Timer:", obs.OBS_TEXT_INFO)
	#-Status End-#
	
	#-Checkpoint Counter-#
	p = obs.obs_properties_add_bool(props, "enabledcp", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcecp", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	
	p = obs.obs_properties_add_text(props, "prefixcp", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_text(props, "seperatorcp", "Separator", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_bool(props, "serverhudcp", "Server and HUD Toggle")
	obs.obs_property_set_long_description(p, "While on a server, the cp counter will only show while HUD is off.\nUseful if you play HUD off but don't want two cp counters on screen at once")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourcecp", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "examplecp", "Example:", obs.OBS_TEXT_INFO)
	#-Checkpoint Counter End-#
	
	#-Checkpoint Timer-#
	p = obs.obs_properties_add_bool(props, "enabledcptime", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcecptime", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixcptime", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "cp0timedisplay", "CP 0", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_long_description(p, "What to display on Checkpoint 0.\nEmpty: Invisible")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_list(props, "formatcptime", "Timer Format", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
	obs.obs_property_list_add_int(p, "01:23:45.67", 3)
	obs.obs_property_list_add_int(p, "01:23:45", 2)
	obs.obs_property_list_add_int(p, "83:45.67", 1)
	obs.obs_property_list_add_int(p, "83:45", 0)
	
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourcecptime", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "examplecptime", "Example:", obs.OBS_TEXT_INFO)
	#-Checkpoint Timer End-#
	
	#-Respawn Counter-#
	p = obs.obs_properties_add_bool(props, "enabledrespawns", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcerespawns", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixrespawns", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourcerespawns", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "examplerespawns", "Example:", obs.OBS_TEXT_INFO)
	#-Respawn Counter End-#
	
	#-Gear-#
	p = obs.obs_properties_add_bool(props, "enabledgear", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcegear", "Gear Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcerpm", "RPM Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	obs.obs_property_set_long_description(p, "Optional")
	
	p = obs.obs_properties_add_text(props, "prefixgear", "Gear Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourcegear", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "examplegear", "Example:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "prefixrpm", "RPM Prefix", obs.OBS_TEXT_DEFAULT) #Hidden until rpm source is chosen
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourcerpm", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "examplerpm", "Example:", obs.OBS_TEXT_INFO)
	#-Gear End-#
	
	#-FPS-#
	p = obs.obs_properties_add_bool(props, "enabledfps", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcefps", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixfps", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourcefps", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "examplefps", "Example:", obs.OBS_TEXT_INFO)
	#-FPS End-#
	
	#-Server Timer-#
	p = obs.obs_properties_add_bool(props, "enabledservertimer", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourceservertimer", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixservertimer", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_list(props, "formatservertimer", "Timer Format", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
	obs.obs_property_list_add_int(p, "01:23:45.67", 3)
	obs.obs_property_list_add_int(p, "01:23:45", 2)
	obs.obs_property_list_add_int(p, "83:45.67", 1)
	obs.obs_property_list_add_int(p, "83:45", 0)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_bool(props, "serverhudservertimer", "HUD Toggle")
	obs.obs_property_set_long_description(p, "Server timer will only show while HUD is off.")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "examplesourceservertimer", "Source:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "exampleservertimer", "Example:", obs.OBS_TEXT_INFO)
	#-Server Timer End-#
	
	#-Setup-#
	p = obs.obs_properties_add_button(props, "setup_refresh", "Refresh Setup", button)
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_button(props, "setup_start", "Start Setup", button) #Not shown while setup is running.
	obs.obs_property_set_modified_callback(p, button_start_setup)
	p = obs.obs_properties_add_bool(props, "setup_manualpid", "Manual PID")
	obs.obs_property_set_modified_callback(p, options_update)
	obs.obs_property_set_long_description(p, "Useful for when a PID is not found or while multiple games are open.\nTask manager > right click any column > toggle PID on.")
	p = obs.obs_properties_add_int(props, "setup_setpid", "PID to set:", 0, 10000000, 4)
	p = obs.obs_properties_add_button(props, "setup_setpidbutton", "Set PID", button)
	obs.obs_property_set_modified_callback(p, button_set_pid)
	p = obs.obs_properties_add_text(props, "setup_currentpid", "Current PID:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "setup_status", "Status:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "setup_altclient", "Alt Client:", obs.OBS_TEXT_INFO)
	obs.obs_property_set_long_description(p, "Usually a TmForever.exe from Steam.")
	p = obs.obs_properties_add_text(props, "setup_tmloader", "TMLoader:", obs.OBS_TEXT_INFO)
	#-Setup End-#
	
	#-Settings-#
	p = obs.obs_properties_add_int(props, "setting_update_rate", "Update rate", 10, 5000, 10)
	obs.obs_property_set_long_description(p, "How often the script reads from the game and displays to sources.")
	obs.obs_property_int_set_suffix(p, "ms")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_int(props, "setting_setup_rate", "Setup rate", 10, 5000, 10)
	obs.obs_property_set_long_description(p, "How often the script tries to setup.\nWARNING: Below 100ms could cause lag.\nRecommended: (250ms-500ms)")
	obs.obs_property_int_set_suffix(p, "ms")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_button(props, "setting_save_settings", "Save to \"MainSettings.json\"", button)
	obs.obs_property_set_modified_callback(p, button_save_settings)
	p = obs.obs_properties_add_button(props, "setting_load_settings", "Load from \"MainSettings.json\"", button)
	obs.obs_property_set_modified_callback(p, button_load_settings)
	p = obs.obs_properties_add_bool(props, "setting_autosave", "Autosave on exit")
	obs.obs_property_set_long_description(p, f"Saves to \"{script_path()}MainSettings.json\"\nIMPORTANT: The file must already exist to autosave unless you have write permissions for the scripts folder.")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_bool(props, "setting_autoload", "Autoload on script load")
	obs.obs_property_set_long_description(p, f"Loads from \"{script_path()}MainSettings.json\"")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_bool(props, "setting_display_toggle", "Toggle display while not playing")
	obs.obs_property_set_long_description(p, "Makes every text source invisible while spectating, loading, in menu, etc.\nException: Server Timer and FPS counter will show while spectating.")
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
