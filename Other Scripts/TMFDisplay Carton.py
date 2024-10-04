'''
Version: 1.0 / 03.09.2024 / Edit of TMFDisplay 2.3
Minimum Python version: 3.8
Discord: tractorfan
GitHub: https://github.com/SuperKulPerson/TMFDisplay
'''

# MINOR TODO: Fix respawn being added on script refresh

import obspython as obs # type: ignore
import ctypes
import ctypes.wintypes

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
	main_data['mstime'] = 0x9560CC, (0x0, 0x1C, 0x2B0) # In-game timer in ms. [0]
	main_data['checkpoint'] = 0x9560CC, (0x0, 0x1C, 0x334) # Current checkpoint number.
	main_data['maxcp'] = 0x9560CC, (0x0, 0x1C, 0x2F8) # Max checkpoint.
	main_data['cptime'] = 0x968C44, (0x12C, 0x244, 0x0, 0x2FC, 0x0) # Cptime of cp1. Add 0x8 for each cp to get the cptime of all cps.
	main_data['finish'] = 0x9560CC, (0x0, 0x1C, 0x33C) # 0 = Not finished. 1 = Finished. [4]
	main_data['respawns'] = 0x968C44, (0x454, 0x340) # Misscounts when resetting a run, but fixes itself after the run has started.
	main_data['fps'] = 0x9731E0, (0x84,) # FPS Counter. Works without toggling the fps counter in-game.
	main_data['carpos'] = 0x97541C, (0x8C, 0x0, 0x58, 0x1F4) # Car Position x. Offset by 0x4, 0x8 for y, z.
	setup_data = {}
	setup_data['state'] = 0x9560CC, (0x0, 0x1C, 0x124) # 1 = Online menu and party play > on a local network. 2 = Loading map on server. 16 = Select account. 32 = Menu. 64 = Quit game confirmation. 128 = Select mood/mod of map and loading map offline. 256 = Editor. 512 = On a map. 1024 = Finish screen offline. 2048 Replay editor. 4096 = Select replay operation menu. 16384 = During "Please Wait" on server. 32768 = On a map on server. [0]
	setup_data['altstate'] = 0x95772C, (0x0, 0x1C, 0x124) # Same as above. Both of these addresses will not be able to see most of the states, this is intentional to prevent setup() from pre-firing.
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
last_respawns = enabledcprespawns = cp0cprespawndisplay = displayed_cprespawns = displayed_sourcecprespawns = typetotal_time = enabledtotal_time = sourcetotal_time = formattotal_time = displayed_total_time = displayed_sourcetotal_time = current_attempts = triggered = sourceattempts = enabledattempts = sourceattempts = displayed_sourceattempts = displayed_attempts = convert_timer = cp0respawndisplay = tmloader = displayed_fps = displayed_sourcefps = enabledfps = sourcefps = prefixfps = current_setup_rate = displayed_respawns = enabledrespawns = sourcerespawns = prefixrespawns = displayed_sourcerespawns = disabled_displays = display_toggle = spectator = formatcptime = autoload = autosave = current_update_rate = updater_timer_on = cp0_cptime_display = displayed_mstime_cptime = sourcecp = displayed_checkpoint = displayed_max_checkpoint = displayed_sourcecp = prefixcp = process_handle = enabledcp = finish_reached = setuptimer = settingscopy = setupstage = setupinfo = manualpid = process_handle_pid = pid = pre_prevent_first_load = prevent_first_load = alt = enabledcptime = sourcecptime = displayed_sourcecptime = None
version = "v1.0"
date = "21.08.2024"
update_rate = 10
setup_rate = 500
displayed_checkpoint_time = respawn_type = total_time_save1 = total_time1 = total_time_save2 = total_time2 = last_total_time2 = total_respawns = last_total_respawns = 0
process_name = "TmForever.exe"
address_offsets_data = address_offsets("main_data")
address_offsets_setup_data = address_offsets("setup_data")
final_setup_addresses = final_addresses = []
settings_name = "MainSettingsCarton.json"
settings_name_path = None # Initialized in script_load()
cp_respawns = []

class Trigger:
    def __init__(self, pos1, pos2):
        self.min_x = min(pos1[0], pos2[0])
        self.max_x = max(pos1[0], pos2[0])

        self.min_y = min(pos1[1], pos2[1])
        self.max_y = max(pos1[1], pos2[1])

        self.min_z = min(pos1[2], pos2[2])
        self.max_z = max(pos1[2], pos2[2])

    def is_inside(self, position):
        return (self.min_x <= position[0] <= self.max_x and
                self.min_y <= position[1] <= self.max_y and
                self.min_z <= position[2] <= self.max_z)
	
'''
add_trigger 398.699 127.014 634.044 407.464 130.071 640.746
add_trigger 458.474 87.954 640.166 468.359 88.244 643.839
add_trigger 576.042 148.675 359.444 599.187 153.627 370.513
add_trigger 335.173 189.065 612.431 336.561 190.066 622.755
add_trigger 655.049 100.916 735.056 656.762 101.686 741.327
add_trigger 727.489 99.683 663.189 735.276 104.795 671.524
'''

#Create Triggers
trigger_positions = (
    ((398.699, 127.014, 634.044), (407.464, 130.071, 640.746)), # 0 Wire
    ((468.359, 87.954, 643.839), (458.474, 88.244, 640.166)), # 0 End
    ((599.187, 153.627, 359.444), (576.042, 148.675, 370.513)), # 1 Road
    ((335.173, 189.065, 612.431,), (336.561, 190.066, 622.755)), # 1 Pipe
	((655.049, 100.916, 735.056), (656.762, 101.686, 741.327)), # 2 Pipe
	((727.489, 99.683, 671.524), (735.276, 104.795, 663.189)) # 2 End
)

all_triggers = (
    tuple(Trigger(c1, c2) for c1, c2 in (trigger_positions[0], trigger_positions[1])), 
    tuple(Trigger(c1, c2) for c1, c2 in (trigger_positions[2], trigger_positions[3])),
    tuple(Trigger(c1, c2) for c1, c2 in (trigger_positions[4], trigger_positions[5]))
)

triggered = [None, None]
attempts = [
	[0, 0],
	[0, 0],
	[0, 0]
]

attempts_message = [
	["Wire Attempts:", "End Attempts:"],
	["Road Lands:", "Pipe Lands:"],
	["Pipe Lands:", "End Attempts:"]
]

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
	if convert_timer and format <= 1 and mstime >= 3600000:
		format += 2
	if format == 3:
		hours = mstime // 3600000
		minutes = (mstime // 60000) % 60
		seconds = (mstime // 1000) % 60
		centiseconds = (mstime % 1000) // 10
		return "%d:%02d:%02d.%02d" % (hours, minutes, seconds, centiseconds)
	elif format == 2:
		hours = mstime // 3600000
		minutes = (mstime // 60000) % 60
		seconds = (mstime // 1000) % 60
		return "%d:%02d:%02d" % (hours, minutes, seconds)
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
	
	current_checkpoint = prefixcp + str(current_checkpoint) + seperatorcp + str(current_max_checkpoint)
	
	if displayed_checkpoint != current_checkpoint or displayed_max_checkpoint != current_max_checkpoint or displayed_sourcecp != sourcecp:
		displayed_checkpoint = current_checkpoint
		displayed_max_checkpoint = current_max_checkpoint
		displayed_sourcecp = sourcecp
		
		if not finish_reached:
			display(sourcecp, current_checkpoint, None)
		else:
			display(sourcecp, prefixcp + str(current_max_checkpoint) + seperatorcp + str(current_max_checkpoint), None)

def checkpoint_time_updater(current_mstime, current_checkpoint_time, current_checkpoint):
	global formatcptime, finish_reached, displayed_sourcecptime, displayed_mstime_cptime, cp0timedisplay, displayed_checkpoint_time, prefixcptime
	
	if current_checkpoint == 0:
		if cp0timedisplay != displayed_mstime_cptime:
			if cp0timedisplay:
				display(sourcecptime, prefixcptime + cp0timedisplay, None)
			else:
				display(sourcecptime, None, True)
			displayed_mstime_cptime = cp0timedisplay
		return
	
	if finish_reached:
		if displayed_checkpoint_time != current_checkpoint_time:
			current_mstime -= read_address_value(final_addresses[3] + max(current_checkpoint - 2, 0) * 0x8, False)
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

def respawn_updater(current_respawns, current_checkpoint):
	global respawn_type, displayed_respawns, displayed_sourcerespawns, finish_reached, cp0respawndisplay
	
	if current_checkpoint == 0 and respawn_type:
		current_respawns = 0
		if cp0respawndisplay != displayed_respawns:
			if cp0respawndisplay:
				display(sourcerespawns, prefixrespawns + cp0respawndisplay, None)
			else:
				display(sourcerespawns, None, True)
			displayed_respawns = cp0respawndisplay
		return
	
	current_respawns = prefixrespawns + str(current_respawns)
	
	if not finish_reached and (displayed_respawns != current_respawns or displayed_sourcerespawns != sourcerespawns):
		displayed_respawns = current_respawns
		displayed_sourcerespawns = sourcerespawns
		display(sourcerespawns, current_respawns, None)

def fps_updater(current_fps):
	global displayed_fps, displayed_sourcefps
	
	current_fps = prefixfps + str(current_fps)
	
	if displayed_fps != current_fps or displayed_sourcefps != sourcefps:
		displayed_fps = current_fps
		displayed_sourcefps = sourcefps
		display(sourcefps, current_fps, None)

def attempts_updater(current_checkpoint, carPos, current_respawns, current_checkpoint_time, current_mstime, total_time):
	global displayed_attempts, displayed_sourceattempts, settingscopy
	if current_checkpoint > 2:
		return
	
	triggers = all_triggers[current_checkpoint]

	for i, trigger in enumerate(triggers):
		if trigger.is_inside(carPos) and triggered[i] != current_respawns:
			triggered[i] = current_respawns
			attempts[current_checkpoint][i] += 1
			set_array_setting("attempts", attempts)
			set_array_setting("triggered", triggered)
		elif triggered[i] != current_respawns:
			triggered[i] = None
	
	current_attempts = ""
	for i in range(len(attempts[current_checkpoint])):
		attempt = attempts[current_checkpoint][i]
		per_hour = 0
		
		if attempt > 0:
			if current_checkpoint > 0:
				per_hour = attempt / ((current_mstime - current_checkpoint_time) / 3600000)
			else:
				per_hour = attempt / (total_time / 3600000)
		
		current_attempts += f"{attempts_message[current_checkpoint][i]} {str(attempt)} [{per_hour:.2f}/h]"
		if i != len(attempts[current_checkpoint]) - 1:
			current_attempts += "\n"

	if displayed_attempts != current_attempts or displayed_sourceattempts != sourceattempts:
		displayed_attempts = current_attempts
		displayed_sourceattempts = sourceattempts
		display(sourceattempts, current_attempts, None)

def total_time_updater(total_time):
	global displayed_total_time, displayed_sourcetotal_time

	total_time = prefixtotal_time + format_time(total_time, formattotal_time)

	if displayed_total_time != total_time or displayed_sourcetotal_time != sourcetotal_time:
		displayed_total_time = total_time
		displayed_sourcetotal_time = sourcetotal_time
		display(sourcetotal_time, total_time, None)

def cp_respawns_updater(current_respawns, current_checkpoint, current_max_checkpoint):
	global displayed_cprespawns, displayed_sourcecprespawns, finish_reached, cp_respawns, cp0cprespawndisplay, settingscopy, last_respawns
	
	if finish_reached:
		return

	while length := len(cp_respawns) != current_max_checkpoint + 1:
		if length < current_max_checkpoint:
			cp_respawns.append(0)
		elif length > current_max_checkpoint:
			cp_respawns.pop()
	
	if cp_respawns == []:
		return

	remove_respawns = sum(cp_respawns[:current_checkpoint])

	cp_respawns[current_checkpoint] = current_respawns - remove_respawns

	if last_respawns != current_respawns:
		set_array_setting("cprespawns", cp_respawns)
		last_respawns = current_respawns

	if current_checkpoint == 0:
		if cp0cprespawndisplay != displayed_cprespawns:
			if cp0cprespawndisplay:
				display(sourcecprespawns, prefixcprespawns + cp0cprespawndisplay, None)
			else:
				display(sourcecprespawns, None, True)
			displayed_cprespawns = cp0cprespawndisplay
		return

	current_cp_respawns = prefixcprespawns + str(cp_respawns[current_checkpoint])

	if displayed_cprespawns != current_cp_respawns or displayed_sourcecprespawns != sourcecprespawns:
		displayed_cprespawns = current_cp_respawns
		displayed_sourcecprespawns = sourcecprespawns
		display(sourcecprespawns, current_cp_respawns, None)

def get_total_respawns(current_respawns, current_mstime):
	global last_total_respawns, total_respawns

	if last_total_respawns != current_respawns and current_mstime != -1:
		if current_respawns != 0 and read_address_value(final_addresses[5] - 0x4, False) not in (0, 1):
			print(last_total_respawns, current_respawns)
			total_respawns += 1
		obs.obs_data_set_int(settingscopy, "total_respawns", total_respawns)
		last_total_respawns = current_respawns
		obs.obs_data_set_int(settingscopy, "last_total_respawns", last_total_respawns)

	return total_respawns

def get_total_time(current_mstime):
	global total_time_save1, total_time1, total_time_save2, total_time2, last_total_time2, settingscopy
	if current_mstime > 0:
		total_time1 = (total_time_save1 + current_mstime)
	elif total_time_save1 != total_time1:
		total_time_save1 = total_time1
		obs.obs_data_set_int(settingscopy, "sessiontime1", total_time_save1)

	if current_mstime != -1:
		current_mstime += 2600
	else:
		current_mstime = 0

	last_total_time2 = (total_time_save2 + current_mstime)
	if total_time2 > last_total_time2:
		total_time_save2 = total_time2
		obs.obs_data_set_int(settingscopy, "sessiontime2", total_time_save2)
	total_time2 = (total_time_save2 + current_mstime)

	if typetotal_time:
		return total_time2
	else:
		return total_time1 

def updater():
	global respawn_type, disabled_displays, alt, enabledcp, enabledcptime, updater_timer_on, update_rate, current_update_rate, finish_reached

	if update_rate != current_update_rate:
		obs.timer_remove(updater)
		obs.timer_add(updater, update_rate)
		current_update_rate = update_rate
	
	ingame_check = read_address_value(final_setup_addresses[alt], False)
	
	if ingame_check not in (512, 16384, 32768):
		setup()
		return
	
	current_mstime = read_address_value(final_addresses[0], False)
	current_respawns = read_address_value(final_addresses[5], False)

	total_time = get_total_time(current_mstime)
	total_respawns = get_total_respawns(current_respawns, current_mstime)

	if not respawn_type:
		current_respawns = total_respawns

	if enabledcp or enabledcptime or enabledrespawns or enabledattempts or enabledcprespawns:
		current_checkpoint = read_address_value(final_addresses[1], False)
	if enabledcp or enabledcptime or enabledcprespawns:
		current_max_checkpoint = read_address_value(final_addresses[2], False) - 1
	if enabledcptime or enabledattempts:
		current_checkpoint_time = read_address_value(final_addresses[3] + max(current_checkpoint - 1, 0) * 0x8, False)
	if enabledcp or enabledcptime or enabledrespawns or enabledcprespawns:
		finish_reached = read_address_value(final_addresses[4], False)
	if enabledfps:
		current_fps = int(read_address_value(final_addresses[6], True))
	if enabledattempts:
		carPosX = read_address_value(final_addresses[7], True)
		carPosY = read_address_value(final_addresses[7] + 0x4, True)
		carPosZ = read_address_value(final_addresses[7] + 0x8, True)
		carPos = (carPosX, carPosY, carPosZ)
		
	if disabled_displays:
		disabled_displays = None
		display(sourcecp, None, None)
		if current_checkpoint > 0 or cp0timedisplay:
			display(sourcecptime, None, None)
		if cp0respawndisplay or (current_checkpoint > 0 and not respawn_type):
			display(sourcerespawns, None, None)
		display(sourceattempts, None, None)
		display(sourcetotal_time, None, None)
		if current_checkpoint > 0 or cp0cprespawndisplay:
			display(sourcecprespawns, None, None)
	
	if enabledcp:
		checkpoint_updater(current_checkpoint, current_max_checkpoint)
	if enabledcptime:
		checkpoint_time_updater(current_mstime, current_checkpoint_time, current_checkpoint)
	if enabledrespawns:
		respawn_updater(current_respawns, current_checkpoint)
	if enabledfps:
		fps_updater(current_fps)
	if enabledattempts:
		attempts_updater(current_checkpoint, carPos, current_respawns, current_checkpoint_time, current_mstime, total_time)
	if enabledtotal_time:
		total_time_updater(total_time)
	if enabledcprespawns:
		cp_respawns_updater(current_respawns, current_checkpoint, current_max_checkpoint)
	
	
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
		if enabledfps:
			display(sourcefps, None, disabled_displays)
		if enabledattempts:
			display(sourceattempts, None, disabled_displays)
		if enabledtotal_time:
			display(sourcetotal_time, None, disabled_displays)
		if enabledcprespawns:
			display(sourcecprespawns, None, disabled_displays)
	elif disabled_displays:
		disabled_displays = None
		display(sourcecp, None, None)
		display(sourcecptime, None, None)
		display(sourcerespawns, None, None)
		display(sourceattempts, None, None)
		display(sourcetotal_time, None, None)
		display(sourcecprespawns, None, None)
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
	
	global settings_name_path
	settings_name_path = script_path() + settings_name # type: ignore
	
	global settingscopy
	settingscopy = settings

	get_session()

	setup()
	
	global autoload
	settings_autoload = obs.obs_data_create_from_json_file(settings_name_path)
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
	obs.obs_data_set_int(settings, "formatcptime", 0)
	obs.obs_data_set_int(settings, "formattotal_time", 0)
	obs.obs_data_set_int(settings, "setting_update_rate", 10)
	obs.obs_data_set_int(settings, "setting_setup_rate", 500)
	obs.obs_data_set_bool(settings, "setup_manualpid", False)
	obs.obs_data_set_bool(settings, "enabledcp", False)
	obs.obs_data_set_bool(settings, "enabledcptime", False)
	obs.obs_data_set_bool(settings, "enabledrespawns", False)
	obs.obs_data_set_bool(settings, "enabledfps", False)
	obs.obs_data_set_bool(settings, "enabledattempts", False)
	obs.obs_data_set_bool(settings, "enabledtotal_time", False)
	obs.obs_data_set_bool(settings, "enabledcprespawns", False)
	obs.obs_data_set_bool(settings, "setting_autosave", False)
	obs.obs_data_set_bool(settings, "setting_autoload", False)
	obs.obs_data_set_bool(settings, "setting_display_toggle", True)
	obs.obs_data_set_bool(settings, "convert_timer", True)
	obs.obs_data_set_bool(settings, "respawn_type", False)
	obs.obs_data_set_bool(settings, "typetotal_time", True)
	obs.obs_data_set_string(settings, "prefixtotal_time", "Session: ")
	obs.obs_data_set_string(settings, "prefixfps", "FPS: ")
	obs.obs_data_set_string(settings, "prefixrespawns", "Respawns: ")
	obs.obs_data_set_string(settings, "prefixcprespawns", "CP Respawns: ")
	obs.obs_data_set_string(settings, "cp0cprespawns", "")
	obs.obs_data_set_string(settings, "cp0respawndisplay", "")
	obs.obs_data_set_string(settings, "cp0timedisplay", "")
	obs.obs_data_set_string(settings, "options", "Status")
	obs.obs_data_set_string(settings, "prefixcp", "CP: ")
	obs.obs_data_set_string(settings, "seperatorcp", "/")
	obs.obs_data_set_string(settings, "prefixcptime", "CP Time: ")

def set_array_setting(name, array):
	global settingscopy
	obs_array = obs.obs_data_array_create()

	for i in array:
		if i == None:
			i = 0
		if isinstance(i, list):
			obs_inner_array = obs.obs_data_array_create()
			for index in i:
				temp_data = obs.obs_data_create()
				obs.obs_data_set_int(temp_data, "value", index)
				obs.obs_data_array_push_back(obs_inner_array, temp_data)
				obs.obs_data_release(temp_data)
			
			temp_data = obs.obs_data_create()
			obs.obs_data_set_array(temp_data, "value", obs_inner_array)
			obs.obs_data_array_push_back(obs_array, temp_data)
			obs.obs_data_release(temp_data)
			obs.obs_data_array_release(obs_inner_array)
		else:
			temp_data = obs.obs_data_create()
			obs.obs_data_set_int(temp_data, "value", i)
			obs.obs_data_array_push_back(obs_array, temp_data)
			obs.obs_data_release(temp_data)

	obs.obs_data_set_array(settingscopy, name, obs_array)
	obs.obs_data_array_release(obs_array)

def get_array_setting(name, inner):
	global settingscopy
	obs_array = obs.obs_data_get_array(settingscopy, name)
	array = []
	
	for i in range(obs.obs_data_array_count(obs_array)):
		if inner:
			inner_data = obs.obs_data_array_item(obs_array, i)
			obs_inner_array = obs.obs_data_get_array(inner_data, "value")
			temp_array = []

			for index in range(obs.obs_data_array_count(obs_inner_array)):
				item_data = obs.obs_data_array_item(obs_inner_array, index)
				value = obs.obs_data_get_int(item_data, "value")
				temp_array.append(value)
				obs.obs_data_release(item_data)

			obs.obs_data_release(inner_data)
			obs.obs_data_array_release(obs_inner_array)
			array.append(temp_array)
		else:
			item_data = obs.obs_data_array_item(obs_array, i)
			value = obs.obs_data_get_int(item_data, "value")
			array.append(value)
			obs.obs_data_release(item_data)

	obs.obs_data_array_release(obs_array)
	return array

def button_save_settings(props, prop, *settings):
	global prevent_first_load, settingscopy
	if prevent_first_load:
		filtered_settings = obs.obs_data_create()
		
		exclude = ["examplecprespawns", "exampletotal_time","examplesourcetotal_time","statustotal_time","statuscprespawns","examplesourcecprespawns","statusattempts","examplesourceattempts", "exampleattempts", "setup_altclient", "options", "setup_currentpid", "setup_tmloader", "statussetup", "examplesourcecp", "examplerespawns", "examplesourcerespawns", "examplecp", "examplefps", "examplesourcefps", "examplesourcecptime", "examplecptime", "setup_status", "statuscp", "statusrespawns", "statuscptime", "statusfps"]

		obs.obs_data_apply(filtered_settings, settingscopy)
		for name in exclude:
			obs.obs_data_erase(filtered_settings, name)
		saved = obs.obs_data_save_json(filtered_settings, settings_name_path)
		obs.obs_data_release(filtered_settings)
		if saved:
			print("Saved Successfully")
		else:
			print(f"Failed to save to {settings_name_path}\nTry making a file with the same name and save again.")
	return True

def button_load_settings(props, prop, *settings):
	global prevent_first_load, settingscopy
	if prevent_first_load:
		settingsload = obs.obs_data_create_from_json_file(settings_name_path)
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

def get_session():
	global cp_respawns, triggered, attempts, total_time_save1, total_time_save2, total_respawns, last_total_respawns
	cp_respawns = get_array_setting("cprespawns", False)
	cp_respawns = [] if cp_respawns is None else cp_respawns

	triggered = get_array_setting("triggered", False)
	triggered = [None, None] if len(triggered) == 0 else triggered

	attempts = get_array_setting("attempts", True)
	attempts = [[0, 0], [0, 0], [0, 0]] if len(attempts) == 0 else attempts

	total_time_save1 = obs.obs_data_get_int(settingscopy, "sessiontime1")
	total_time_save1 = 0 if total_time_save1 is None else total_time_save1

	total_time_save2 = obs.obs_data_get_int(settingscopy, "sessiontime2")
	total_time_save2 = 0 if total_time_save2 is None else total_time_save2

	total_respawns = obs.obs_data_get_int(settingscopy, "total_respawns")
	total_respawns = 0 if total_respawns is None else total_respawns

	last_total_respawns = obs.obs_data_get_int(settingscopy, "last_total_respawns")
	last_total_respawns = 0 if last_total_respawns is None else last_total_respawns

def button_reset_session(props, prop, *settings):
	global setuptimer, prevent_first_load, attempts, cp_respawns, total_time_save1, total_time_save2, triggered, total_time1, total_time2, total_respawns, last_total_respawns
	
	if prevent_first_load:
		attempts = [
			[0, 0],
			[0, 0],
			[0, 0]
		]
		triggered = [None, None]
		cp_respawns = []
		total_respawns = 0
		last_total_respawns = 0
		total_time_save1 = 0
		total_time1 = 0
		total_time_save2 = 0
		total_time2 = 0
		obs.obs_data_set_int(settingscopy, "total_respawns", 0)
		obs.obs_data_set_int(settingscopy, "last_total_respawns", 0)
		obs.obs_data_set_int(settingscopy, "sessiontime1", 0)
		obs.obs_data_set_int(settingscopy, "sessiontime2", 0)
		set_array_setting("attempts", attempts)
		set_array_setting("triggered", triggered)
		set_array_setting("cprespawns", cp_respawns)

	options_update(props, None, settingscopy)
	return True

def options_update(props, prop, *settings):
	global cp0cprespawndisplay, enabledcprespawns, sourcecprespawns, prefixcprespawns, prefixtotal_time, typetotal_time, respawn_type, enabledtotal_time, sourcetotal_time, formattotal_time, enabledattempts, sourceattempts, convert_timer, cp0respawndisplay, tmloader, enabledfps, sourcefps, prefixfps, setup_rate, enabledrespawns, sourcerespawns, prefixrespawns, display_toggle, formatcptime, autosave, pre_prevent_first_load, prevent_first_load, sourcecp, prefixcp, seperatorcp, enabledcp, setupinfo, pid, manualpid, alt, setuptimer, enabledcptime, sourcecptime, cp0timedisplay, prefixcptime, update_rate
	
	property_list = []
	
	property_list.append(p_statusrefresh := obs.obs_properties_get(props, "statusrefresh")) # Wish there was a better way of doing this :'(
	property_list.append(p_statussetup := obs.obs_properties_get(props, "statussetup"))
	property_list.append(p_statuscp := obs.obs_properties_get(props, "statuscp"))
	property_list.append(p_statuscptime := obs.obs_properties_get(props, "statuscptime"))
	property_list.append(p_statusrespawns := obs.obs_properties_get(props, "statusrespawns"))
	property_list.append(p_statusfps := obs.obs_properties_get(props, "statusfps"))
	property_list.append(p_statusattempts := obs.obs_properties_get(props, "statusattempts"))
	property_list.append(p_statustotal_time := obs.obs_properties_get(props, "statustotal_time"))
	property_list.append(p_statuscprespawns := obs.obs_properties_get(props, "statuscprespawns"))
	property_list.append(p_onlinewarning := obs.obs_properties_get(props, "onlinewarning"))
	
	property_list.append(p_enabledcp := obs.obs_properties_get(props, "enabledcp"))
	property_list.append(p_sourcecp := obs.obs_properties_get(props, "sourcecp"))
	property_list.append(p_prefixcp := obs.obs_properties_get(props, "prefixcp"))
	property_list.append(p_seperatorcp := obs.obs_properties_get(props, "seperatorcp"))
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
	property_list.append(p_respawn_type := obs.obs_properties_get(props, "respawn_type"))
	property_list.append(p_cp0respawndisplay := obs.obs_properties_get(props, "cp0respawndisplay"))
	property_list.append(p_examplesourcerespawns := obs.obs_properties_get(props, "examplesourcerespawns"))
	property_list.append(p_examplerespawns := obs.obs_properties_get(props, "examplerespawns"))  
	
	property_list.append(p_enabledfps := obs.obs_properties_get(props, "enabledfps"))
	property_list.append(p_sourcefps := obs.obs_properties_get(props, "sourcefps"))
	property_list.append(p_prefixfps := obs.obs_properties_get(props, "prefixfps"))
	property_list.append(p_examplesourcefps := obs.obs_properties_get(props, "examplesourcefps"))
	property_list.append(p_examplefps := obs.obs_properties_get(props, "examplefps"))

	property_list.append(p_enabledattempts := obs.obs_properties_get(props, "enabledattempts"))
	property_list.append(p_sourceattempts := obs.obs_properties_get(props, "sourceattempts"))
	property_list.append(p_examplesourceattempts := obs.obs_properties_get(props, "examplesourceattempts"))

	property_list.append(p_enabledtotal_time := obs.obs_properties_get(props, "enabledtotal_time"))
	property_list.append(p_sourcetotal_time := obs.obs_properties_get(props, "sourcetotal_time"))
	property_list.append(p_prefixtotal_time := obs.obs_properties_get(props, "prefixtotal_time"))
	property_list.append(p_typetotal_time := obs.obs_properties_get(props, "typetotal_time"))
	property_list.append(p_formattotal_time := obs.obs_properties_get(props, "formattotal_time"))
	property_list.append(p_exampletotal_time := obs.obs_properties_get(props, "exampletotal_time"))
	property_list.append(p_examplesourcetotal_time := obs.obs_properties_get(props, "examplesourcetotal_time"))
	property_list.append(p_warningtotal1_time := obs.obs_properties_get(props, "warningtotal1_time"))
	property_list.append(p_warningtotal2_time := obs.obs_properties_get(props, "warningtotal2_time"))
	property_list.append(p_warningtotal3_time := obs.obs_properties_get(props, "warningtotal3_time"))

	property_list.append(p_enabledcprespawns := obs.obs_properties_get(props, "enabledcprespawns"))
	property_list.append(p_sourcecprespawns := obs.obs_properties_get(props, "sourcecprespawns"))
	property_list.append(p_prefixcprespawns := obs.obs_properties_get(props, "prefixcprespawns"))
	property_list.append(p_cp0cprespawndisplay := obs.obs_properties_get(props, "cp0cprespawndisplay"))
	property_list.append(p_examplesourcecprespawns := obs.obs_properties_get(props, "examplesourcecprespawns"))
	property_list.append(p_examplecprespawns := obs.obs_properties_get(props, "examplecprespawns"))
	
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
	property_list.append(p_convert_timer := obs.obs_properties_get(props, "convert_timer"))

	property_list.append(p_reload := obs.obs_properties_get(props, "reload"))
	property_list.append(p_warning := obs.obs_properties_get(props, "warning"))
	property_list.append(p_reset_session := obs.obs_properties_get(props, "reset_session"))
	
	text_sources_list = []
	sources = obs.obs_enum_sources()
	if sources is not None:
		for source in sources:
			source_id = obs.obs_source_get_unversioned_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source":
				name = obs.obs_source_get_name(source)
				text_sources_list.append(name)
		obs.source_list_release(sources)
	
	if text_sources_list:
		source_list = [p_sourcecp, p_sourcecptime, p_sourcerespawns, p_sourcefps, p_sourceattempts, p_sourcetotal_time, p_sourcecprespawns]
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
	respawn_type = obs.obs_data_get_bool(settingscopy, "respawn_type")
	cp0respawndisplay = obs.obs_data_get_string(settingscopy, "cp0respawndisplay")
	
	if not sourcerespawns:
		sourcerespawns = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcerespawns", sourcerespawns)
	obs.obs_data_set_string(settingscopy, "examplerespawns", prefixrespawns + "35")
	#-Respawn Counter End-#
	
	#-FPS-#
	enabledfps = obs.obs_data_get_bool(settingscopy, "enabledfps")
	sourcefps = obs.obs_data_get_string(settingscopy, "sourcefps")
	prefixfps = obs.obs_data_get_string(settingscopy, "prefixfps")
	
	if not sourcefps:
		sourcefps = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcefps", sourcefps)
	obs.obs_data_set_string(settingscopy, "examplefps", prefixfps + "157")
	#-FPS End-#

	#-Attempts-#
	enabledattempts = obs.obs_data_get_bool(settingscopy, "enabledattempts")
	sourceattempts = obs.obs_data_get_string(settingscopy, "sourceattempts")
	
	if not sourceattempts:
		sourceattempts = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourceattempts", sourceattempts)
	#-Attempts End-#

	#-Session Time-#
	enabledtotal_time = obs.obs_data_get_bool(settingscopy, "enabledtotal_time")
	sourcetotal_time = obs.obs_data_get_string(settingscopy, "sourcetotal_time")
	prefixtotal_time = obs.obs_data_get_string(settingscopy, "prefixtotal_time")
	formattotal_time = obs.obs_data_get_int(settingscopy, "formattotal_time")
	typetotal_time = obs.obs_data_get_bool(settingscopy, "typetotal_time")
	
	if not sourcetotal_time:
		sourcetotal_time = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcetotal_time", sourcetotal_time)
	obs.obs_data_set_string(settingscopy, "exampletotal_time", prefixtotal_time + format_time(5025678, formattotal_time))
	#-Session Time End-#
	
	#-CP Respawns-#
	enabledcprespawns = obs.obs_data_get_bool(settingscopy, "enabledcprespawns")
	sourcecprespawns = obs.obs_data_get_string(settingscopy, "sourcecprespawns")
	prefixcprespawns = obs.obs_data_get_string(settingscopy, "prefixcprespawns")
	cp0cprespawndisplay = obs.obs_data_get_string(settingscopy, "cp0cprespawndisplay")
	
	if not sourcecprespawns:
		sourcecprespawns = "No Source"
	obs.obs_data_set_string(settingscopy, "examplesourcecprespawns", sourcecprespawns)
	obs.obs_data_set_string(settingscopy, "examplecprespawns", prefixcprespawns + "35")
	#-CP Respawns End-#

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
	convert_timer = obs.obs_data_get_bool(settingscopy, "convert_timer")
	#-Settings End-#
	
	#-Status-#
	status_disabled = "<font color=#ff8800><b>Disabled</b></font>"
	status_enabled = "<font color=#55ff55><b>Enabled</b></font>"
	status_enabled_nosource = "<font color=#ff5555><b>Enabled, NO SOURCE.</b></font>"
	
	obs.obs_data_set_string(settingscopy, "statussetup", setupinfo)

	status_source = [
		(sourcecp, "statuscp", enabledcp),
		(sourcecptime, "statuscptime", enabledcptime),
		(sourcerespawns, "statusrespawns", enabledrespawns),
		(sourcefps, "statusfps", enabledfps),
		(sourceattempts, "statusattempts", enabledattempts),
		(sourcetotal_time, "statustotal_time", enabledtotal_time),
		(sourcecprespawns, "statuscprespawns", enabledcprespawns)
	]
	
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
		obs.obs_property_set_visible(p_statusfps, True)
		obs.obs_property_set_visible(p_statusattempts, True)
		obs.obs_property_set_visible(p_statustotal_time, True)
		obs.obs_property_set_visible(p_statuscprespawns, True)
		obs.obs_property_set_visible(p_onlinewarning, True)
		
	elif s_option == "Checkpoint Counter":
		obs.obs_property_set_visible(p_enabledcp, True)
		obs.obs_property_set_visible(p_sourcecp, True)
		obs.obs_property_set_visible(p_prefixcp, True)
		obs.obs_property_set_visible(p_seperatorcp, True)
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
		obs.obs_property_set_visible(p_respawn_type, True)
		if respawn_type:
			obs.obs_property_set_visible(p_cp0respawndisplay, True)
		else:
			obs.obs_property_set_visible(p_warning, True)
			obs.obs_property_set_visible(p_reset_session, True)
		obs.obs_property_set_visible(p_examplesourcerespawns, True)
		obs.obs_property_set_visible(p_examplerespawns, True)
		
	elif s_option == "FPS":
		obs.obs_property_set_visible(p_enabledfps, True)
		obs.obs_property_set_visible(p_sourcefps, True)
		obs.obs_property_set_visible(p_prefixfps, True)
		obs.obs_property_set_visible(p_examplesourcefps, True)
		obs.obs_property_set_visible(p_examplefps, True)

	elif s_option == "Attempts":
		obs.obs_property_set_visible(p_enabledattempts, True)
		obs.obs_property_set_visible(p_sourceattempts, True)
		obs.obs_property_set_visible(p_examplesourceattempts, True)
		obs.obs_property_set_visible(p_warning, True)
		obs.obs_property_set_visible(p_reset_session, True)

	elif s_option == "Session Time":
		obs.obs_property_set_visible(p_enabledtotal_time, True)
		obs.obs_property_set_visible(p_sourcetotal_time, True)
		obs.obs_property_set_visible(p_prefixtotal_time, True)
		obs.obs_property_set_visible(p_typetotal_time, True)
		obs.obs_property_set_visible(p_formattotal_time, True)
		obs.obs_property_set_visible(p_exampletotal_time, True)
		obs.obs_property_set_visible(p_examplesourcetotal_time, True)
		obs.obs_property_set_visible(p_warningtotal1_time, True)
		obs.obs_property_set_visible(p_warningtotal2_time, True)
		obs.obs_property_set_visible(p_warningtotal3_time, True)
		obs.obs_property_set_visible(p_warning, True)
		obs.obs_property_set_visible(p_reset_session, True)

	elif s_option == "CP Respawns":
		obs.obs_property_set_visible(p_enabledcprespawns, True)
		obs.obs_property_set_visible(p_sourcecprespawns, True)
		obs.obs_property_set_visible(p_prefixcprespawns, True)
		obs.obs_property_set_visible(p_cp0cprespawndisplay, True)
		obs.obs_property_set_visible(p_examplesourcecprespawns, True)
		obs.obs_property_set_visible(p_examplecprespawns, True)
		obs.obs_property_set_visible(p_warning, True)
		obs.obs_property_set_visible(p_reset_session, True)
		
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
		obs.obs_property_set_visible(p_convert_timer, True)
		obs.obs_property_set_visible(p_reset_session, True)
	
	if prop == 10 and pre_prevent_first_load: #Scuffed way of preventing setup() from being called multiple times at script start.
		prevent_first_load = True
	
	if not prevent_first_load:
		obs.obs_property_set_visible(p_reload, True)
	
	return True

def script_properties():
	props = obs.obs_properties_create()
	obs.obs_properties_add_text(props, "reload", "<font color=#ff0000><b>RELOAD SCRIPT</b></font>", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_list(props, "options", "Options", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_list_add_string(p, "Status", "Status")
	obs.obs_property_list_add_string(p, "Checkpoint Counter", "Checkpoint Counter")
	obs.obs_property_list_add_string(p, "Checkpoint Timer", "Checkpoint Timer")
	obs.obs_property_list_add_string(p, "Respawn Counter", "Respawn Counter")
	obs.obs_property_list_add_string(p, "FPS", "FPS")
	obs.obs_property_list_add_string(p, "Attempts", "Attempts")
	obs.obs_property_list_add_string(p, "Session Time", "Session Time")
	obs.obs_property_list_add_string(p, "CP Respawns", "CP Respawns")
	obs.obs_property_list_add_string(p, "Setup", "Setup")
	obs.obs_property_list_add_string(p, "Settings", "Settings")
	obs.obs_property_set_modified_callback(p, options_update)
	
	#-Status-#
	p = obs.obs_properties_add_button(props, "statusrefresh", "Refresh Status", button)
	obs.obs_property_set_modified_callback(p, options_update)
	obs.obs_properties_add_text(props, "statussetup", "Setup:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statuscp", "Checkpoint Counter:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statuscptime", "Checkpoint Timer:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statusrespawns", "Respawn Counter:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statusfps", "FPS:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statusattempts", "Attempts:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statustotal_time", "Session Time:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "statuscprespawns", "CP Respawns:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "onlinewarning", "<font color=#ffff00><b>THIS SCRIPT WAS NOT TESTED FOR ONLINE, NOR MADE FOR ONLINE.</b></font>", obs.OBS_TEXT_INFO)
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
	
	obs.obs_properties_add_text(props, "examplesourcecp", "Source:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "examplecp", "Example:", obs.OBS_TEXT_INFO)
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
	obs.obs_property_list_add_int(p, "1:23:45.67", 3)
	obs.obs_property_list_add_int(p, "1:23:45", 2)
	obs.obs_property_list_add_int(p, "83:45.67", 1)
	obs.obs_property_list_add_int(p, "83:45", 0)
	obs.obs_property_set_modified_callback(p, options_update)
	
	obs.obs_properties_add_text(props, "examplesourcecptime", "Source:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "examplecptime", "Example:", obs.OBS_TEXT_INFO)
	#-Checkpoint Timer End-#
	
	#-Respawn Counter-#
	p = obs.obs_properties_add_bool(props, "enabledrespawns", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcerespawns", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixrespawns", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_bool(props, "respawn_type", "Only start counting after reaching cp1")
	obs.obs_property_set_long_description(p, "Disabled: Counts the total respawns from loading into the map. (One respawn will be added upon map load on some maps, but not on carton)\nEnabled: Only starts counting respawns after reaching checkpoint 1.")
	obs.obs_property_set_modified_callback(p, options_update)

	p = obs.obs_properties_add_text(props, "cp0respawndisplay", "CP 0", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_long_description(p, "What to display on Checkpoint 0.\nEmpty: Invisible")
	obs.obs_property_set_modified_callback(p, options_update)
	
	obs.obs_properties_add_text(props, "examplesourcerespawns", "Source:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "examplerespawns", "Example:", obs.OBS_TEXT_INFO)
	#-Respawn Counter End-#
	
	#-FPS-#
	p = obs.obs_properties_add_bool(props, "enabledfps", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcefps", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixfps", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)
	
	obs.obs_properties_add_text(props, "examplesourcefps", "Source:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "examplefps", "Example:", obs.OBS_TEXT_INFO)
	#-FPS End-#

	#-Attempts-#
	p = obs.obs_properties_add_bool(props, "enabledattempts", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourceattempts", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	obs.obs_properties_add_text(props, "examplesourceattempts", "Source:", obs.OBS_TEXT_INFO)
	#-Attempts End-#

	#-Session Time-#
	p = obs.obs_properties_add_bool(props, "enabledtotal_time", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcetotal_time", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)

	p = obs.obs_properties_add_text(props, "prefixtotal_time", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)

	p = obs.obs_properties_add_list(props, "formattotal_time", "Timer Format", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
	obs.obs_property_list_add_int(p, "1:23:45.67", 3)
	obs.obs_property_list_add_int(p, "1:23:45", 2)
	obs.obs_property_list_add_int(p, "83:45.67", 1)
	obs.obs_property_list_add_int(p, "83:45", 0)
	obs.obs_property_set_modified_callback(p, options_update)

	p = obs.obs_properties_add_bool(props, "typetotal_time", "Add the start countdown timer.")
	obs.obs_property_set_long_description(p, "The attempts counter will use the timer set by this checkbox regardless of whether Session Time is enabled or not.")
	obs.obs_property_set_modified_callback(p, options_update)
	
	obs.obs_properties_add_text(props, "examplesourcetotal_time", "Source:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "exampletotal_time", "Example:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "warningtotal1_time", "", obs.OBS_TEXT_INFO)
	obs.obs_property_set_long_description(p, "<font color=#ffff00><b>This timer's accuracy will depend on:</b></font>")
	p = obs.obs_properties_add_text(props, "warningtotal2_time", "", obs.OBS_TEXT_INFO)
	obs.obs_property_set_long_description(p, "<font color=#ffff00><b>1. The fps set in OBS.</b></font>")
	p = obs.obs_properties_add_text(props, "warningtotal3_time", "", obs.OBS_TEXT_INFO)
	obs.obs_property_set_long_description(p, "<font color=#ffff00><b>2. The script update rate.</b></font>")
	#-Session Time End-#

	#-CP Respawns-#
	p = obs.obs_properties_add_bool(props, "enabledcprespawns", "Enabled")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_list(props, "sourcecprespawns", "Source", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_text(props, "prefixcprespawns", "Prefix", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_modified_callback(p, options_update)

	p = obs.obs_properties_add_text(props, "cp0cprespawndisplay", "CP 0", obs.OBS_TEXT_DEFAULT)
	obs.obs_property_set_long_description(p, "What to display on Checkpoint 0.\nEmpty: Invisible")
	obs.obs_property_set_modified_callback(p, options_update)
	
	obs.obs_properties_add_text(props, "examplesourcecprespawns", "Source:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "examplecprespawns", "Example:", obs.OBS_TEXT_INFO)
	#-CP Respawns End-#
	
	#-Setup-#
	p = obs.obs_properties_add_button(props, "setup_refresh", "Refresh Setup", button)
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_button(props, "setup_start", "Start Setup", button) #Not shown while setup is running.
	obs.obs_property_set_modified_callback(p, button_start_setup)
	p = obs.obs_properties_add_bool(props, "setup_manualpid", "Manual PID")
	obs.obs_property_set_modified_callback(p, options_update)
	obs.obs_property_set_long_description(p, "Useful for when a PID is not found or while multiple games are open.\nTask manager > right click any column > toggle PID on.")
	obs.obs_properties_add_int(props, "setup_setpid", "PID to set:", 0, 10000000, 4)
	p = obs.obs_properties_add_button(props, "setup_setpidbutton", "Set PID", button)
	obs.obs_property_set_modified_callback(p, button_set_pid)
	obs.obs_properties_add_text(props, "setup_currentpid", "Current PID:", obs.OBS_TEXT_INFO)
	obs.obs_properties_add_text(props, "setup_status", "Status:", obs.OBS_TEXT_INFO)
	p = obs.obs_properties_add_text(props, "setup_altclient", "Alt Client:", obs.OBS_TEXT_INFO)
	obs.obs_property_set_long_description(p, "Usually a TmForever.exe from Steam.")
	obs.obs_properties_add_text(props, "setup_tmloader", "TMLoader:", obs.OBS_TEXT_INFO)
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
	
	p = obs.obs_properties_add_button(props, "setting_save_settings", f"Save to \"{settings_name}\"", button)
	obs.obs_property_set_modified_callback(p, button_save_settings)
	p = obs.obs_properties_add_button(props, "setting_load_settings", f"Load from \"{settings_name}\"", button)
	obs.obs_property_set_modified_callback(p, button_load_settings)
	p = obs.obs_properties_add_bool(props, "setting_autosave", "Autosave on exit")
	obs.obs_property_set_long_description(p, f"Saves to \"{settings_name_path}\"\nIMPORTANT: The file must already exist to autosave unless you have write permissions for the scripts folder.")
	obs.obs_property_set_modified_callback(p, options_update)
	p = obs.obs_properties_add_bool(props, "setting_autoload", "Autoload on script load")
	obs.obs_property_set_long_description(p, f"Loads from \"{settings_name_path}\"")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_bool(props, "setting_display_toggle", "Toggle display while not playing")
	obs.obs_property_set_long_description(p, "Makes every text source invisible while spectating, loading, in menu, etc.\nException: Server Timer and FPS counter will show while spectating.")
	obs.obs_property_set_modified_callback(p, options_update)
	
	p = obs.obs_properties_add_bool(props, "convert_timer", "Convert timer")
	obs.obs_property_set_long_description(p, "Automatically converts a short timer format when it goes above 60 minutes. \n64:35.77 > 01:04:35.77\n64:35 > 01:04:35")
	obs.obs_property_set_modified_callback(p, options_update)
	#-Settings End-#

	p = obs.obs_properties_add_text(props, "warning", "<font color=#ff0000><b>Warning</b></font>", obs.OBS_TEXT_INFO)
	obs.obs_property_set_long_description(p, "<font color=#ff7777><b>The data for this option is stored in the settings file, and not in TM memory. If you play without this script, it may not track your data. Make sure to pause the game, then save the settings before exiting OBS.</b></font>")
	
	p = obs.obs_properties_add_button(props, "reset_session", "Reset Session", button)
	obs.obs_property_set_modified_callback(p, button_reset_session)
	obs.obs_property_set_long_description(p, "<font color=#ff7777><b>Press this button when you want to reset the session and delete all the data. | Will delete data for the following: Attempts, Session Time, Cp Respawns, Total Respawns.</b></font>")

	global settingscopy, pre_prevent_first_load
	options_update(props, 10, settingscopy)
	pre_prevent_first_load = True
	
	return props

def button():
	return

def script_description():
	return f"<font><b>{version} / {date} / Edit of TMFDisplay 2.3</b></font>"