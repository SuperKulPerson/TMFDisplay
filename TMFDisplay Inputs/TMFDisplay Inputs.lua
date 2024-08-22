--[[

-Known Crashes-
Reloading the script while having the properties of a source open can crash OBS. Most likely an OBS issue.

]]--

local ffi = require("ffi")
local obs = obslua

local version = "v1.0"
local version_date = "22.08.2024"

local input = {}
input.id = "tmfdisplay_input"
input.type = obs.OBS_SOURCE_TYPE_INPUT
input.output_flags = obs.OBS_SOURCE_VIDEO
input.icon_type = obs.OBS_ICON_TYPE_GAME_CAPTURE


function image_source_load(image, file)
	obs.obs_enter_graphics()
	obs.gs_image_file_free(image)
	obs.obs_leave_graphics()

	obs.gs_image_file_init(image, file)

	obs.obs_enter_graphics()
	obs.gs_image_file_init_texture(image)
	obs.obs_leave_graphics()

	if not image.loaded then
		print("failed to load texture " .. file);
	end
end


input.get_name = function()
	return "TMFDisplay Input"
end


input.get_size = function(data)
	if not data.kbInputs.texture or not data.padInputs.texture then
		return nil
	end
	
	obs.obs_enter_graphics()
	data.kbSize = obs.gs_texture_get_width(data.kbInputs.texture) / 4
	if data.kbSize ~= obs.gs_texture_get_height(data.kbInputs.texture) / 2 then
		print("kbInputs.png not 2x1")
	end
	-- print("kbSize: " .. tostring(data.kbSize))
	
	data.padSize = obs.gs_texture_get_width(data.padInputs.texture) / 4
	if data.padSize ~= obs.gs_texture_get_height(data.padInputs.texture) / 4 then
		print("padInputs.png not 1x1")
	end
	obs.obs_leave_graphics()
	-- print("padSize: " .. tostring(data.padSize))
	
	data.scale = data.kbSize / data.padSize
end


input.create = function(settings, source)
	data = {}
	
	data.pad = obs.obs_data_get_bool(settings, "pad")
	data.imageShow = obs.obs_data_get_bool(settings, "imageShow")
	data.imageGapX = obs.obs_data_get_int(settings, "imageGapX")
	data.imageGapY = obs.obs_data_get_int(settings, "imageGapY")
	
	data.kbInputs = obs.gs_image_file()
	data.padInputs = obs.gs_image_file()
	
	image_source_load(data.kbInputs, obs.obs_data_get_string(settings, "kbImage"))
	image_source_load(data.padInputs, obs.obs_data_get_string(settings, "padImage"))
	
	input.get_size(data)
	
	return data
end


input.normalizePad = function(data, number)
	if number then
		return math.ceil((number*(data.padSize*2))/65536) -- Ceiling to fix a gap between the textures
	end
end


input.video_render = function(data)
	if not data.kbInputs.texture or not data.padInputs.texture then
		return nil
	end
	
	-- print("1")
	local offsetUpDown = 1
	local offsetTexture = 65536
	if data.imageShow then
		offsetTexture = 0
	end
	
	obs.obs_source_draw(data.padInputs.texture, offsetTexture, (data.kbSize*2)+data.imageGapX, 0, 0, false)

	obs.gs_viewport_push()
	
	if data.pad then
		offsetUpDown = 2
		if not steer then
			steer = 0
		end
		
		-- LeftPad
		if steer > 0 then
			
			steer = input.normalizePad(data, steer)
			
			-- On
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f((data.padSize*2)-steer, data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, (data.padSize*2)-steer, 0, steer, data.padSize*2)
			obs.gs_matrix_pop()
			
			-- Off
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f(0, data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, 0, data.padSize*2, (data.padSize*2)-steer, data.padSize*2)
			obs.gs_matrix_pop()
			
			-- RightPadOff
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f((data.padSize*3)+(data.imageGapX/data.scale*2), data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, data.padSize*2, data.padSize*2, data.padSize*2, data.padSize*2)
			obs.gs_matrix_pop()
			
		-- RightPad
		elseif steer < 0 then
			steer = steer*-1
			
			steer = input.normalizePad(data, steer)
			
			-- On
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f((data.padSize*3)+(data.imageGapX/data.scale*2), data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, data.padSize*2, 0, steer, data.padSize*2)
			obs.gs_matrix_pop()
			
			-- Off
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f((data.padSize*3)+(data.imageGapX/data.scale*2)+steer, data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, (data.padSize*2)+steer, data.padSize*2, (data.padSize*2)-steer, data.padSize*2)
			obs.gs_matrix_pop()
			
			-- LeftPadOff
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f(0, data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, 0, data.padSize*2, data.padSize*2, data.padSize*2)
			obs.gs_matrix_pop()
		else
			-- LeftPadOff
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f(0, data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, 0, data.padSize*2, data.padSize*2, data.padSize*2)
			obs.gs_matrix_pop()
			
			-- RightPadOff
			obs.gs_matrix_push()
			obs.gs_matrix_scale3f(data.scale, data.scale, 0)
			obs.gs_matrix_translate3f((data.padSize*3)+(data.imageGapX/data.scale*2), data.imageGapY/data.scale/2, 0)
			obs.gs_draw_sprite_subregion(data.padInputs.texture, 0, data.padSize*2, data.padSize*2, data.padSize*2, data.padSize*2)
			obs.gs_matrix_pop()
		end
	end
	
	obs.obs_source_draw(data.kbInputs.texture, offsetTexture, data.kbSize*2*-1, 0, 0, false)
	
	if not data.pad then
		-- Left
		obs.gs_matrix_push()
		obs.gs_matrix_translate3f(0, data.kbSize+data.imageGapY, 0)
		if left then
			obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, 0, 0, data.kbSize, data.kbSize)
		else
			obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, 0, data.kbSize, data.kbSize, data.kbSize)
		end
		obs.gs_matrix_pop()
		
		
		-- Right
		obs.gs_matrix_push()
		obs.gs_matrix_translate3f(data.kbSize*2+(data.imageGapX*2), data.kbSize+data.imageGapY, 0)
		if right then
			obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, data.kbSize, 0, data.kbSize, data.kbSize)
		else
			obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, data.kbSize, data.kbSize, data.kbSize, data.kbSize)
		end
		obs.gs_matrix_pop()
	end
	
	-- Down
	obs.gs_matrix_push()
	obs.gs_matrix_translate3f(data.kbSize*offsetUpDown+data.imageGapX, data.kbSize+data.imageGapY, 0)
	if down then
		obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, data.kbSize*2, 0, data.kbSize, data.kbSize)
	else
		obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, data.kbSize*2, data.kbSize, data.kbSize, data.kbSize)
	end
	obs.gs_matrix_pop()
	
	-- Up
	obs.gs_matrix_push()
	obs.gs_matrix_translate3f(data.kbSize*offsetUpDown+data.imageGapX, 0, 0)
	if up then
		obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, data.kbSize*3, 0, data.kbSize, data.kbSize)
	else
		obs.gs_draw_sprite_subregion(data.kbInputs.texture, 0, data.kbSize*3, data.kbSize, data.kbSize, data.kbSize)
	end
	obs.gs_matrix_pop()
	obs.gs_viewport_pop()
end


input.destroy = function(data)
	obs.obs_enter_graphics();
	obs.gs_image_file_free(data.padInputs);
	obs.gs_image_file_free(data.kbInputs);
	obs.obs_leave_graphics();
end


input.get_width = function(data)
	if data.kbSize then
		if data.pad then
			return (data.kbSize*5)+(data.imageGapX*2)
		else
			return (data.kbSize*3)+(data.imageGapX*2)
		end
	else
		return 256
	end
end


input.get_height = function(data)
	if data.kbSize then
		return (data.kbSize*2)+data.imageGapY
	else
		return 256
	end
end


input.update = function(data, settings)
	data.pad = obs.obs_data_get_bool(settings, "pad")
	data.imageGapX = obs.obs_data_get_int(settings, "imageGapX")
	data.imageGapY = obs.obs_data_get_int(settings, "imageGapY")
	data.imageShow = obs.obs_data_get_bool(settings, "imageShow")
	
	image_source_load(data.kbInputs, obs.obs_data_get_string(settings, "kbImage"))
	image_source_load(data.padInputs, obs.obs_data_get_string(settings, "padImage"))
	
	input.get_size(data)
end


input.get_properties = function(data)
	local props = obs.obs_properties_create()
	
	obs.obs_properties_add_path(props, "kbImage", "Kb inputs image (2x1)", obs.OBS_PATH_FILE , nil, script_path() .. "input-style")
	obs.obs_properties_add_path(props, "padImage", "Pad inputs image (1x1)", obs.OBS_PATH_FILE, nil, script_path() .. "input-style")
	
	obs.obs_properties_add_bool(props, "pad", "Pad")
	obs.obs_properties_add_int(props, "imageGapX", "Image Gap X:", 0, 4096, 4)
	obs.obs_properties_add_int(props, "imageGapY", "Image Gap Y:", 0, 4096, 4)
	p = obs.obs_properties_add_bool(props, "imageShow", "Show image file")
	obs.obs_property_set_long_description(p, "Turn off any filtering on the source if you don't see the images.")
	obs.obs_properties_add_text(props, "info", "If you see color leaking onto transparent edges after resizing the source, try one of these solutions:\n- Increase or decrease the size of your Kb inputs image to avoid having to resize it in OBS. (Recommended)\n- Right click the source > Scale Filtering > Point or Area. This may change the colors of the transparent texture.", obs.OBS_TEXT_INFO)
	
	return props
end


obs.obs_register_source(input)


ffi.cdef[[
	typedef unsigned long DWORD;
	typedef void* HANDLE;
	typedef HANDLE *PHANDLE;
	typedef void* HMODULE;
	typedef int BOOL;
	typedef unsigned short WORD;
	typedef const char* LPCSTR;
	typedef DWORD* LPDWORD;

	typedef struct {
		DWORD dwSize;
		DWORD cntUsage;
		DWORD th32ProcessID;
		uintptr_t th32DefaultHeapID;
		DWORD th32ModuleID;
		DWORD cntThreads;
		DWORD th32ParentProcessID;
		long pcPriClassBase;
		DWORD dwFlags;
		char szExeFile[260];
	} PROCESSENTRY32;

	HANDLE CreateToolhelp32Snapshot(DWORD dwFlags, DWORD th32ProcessID);
	int Process32First(HANDLE hSnapshot, PROCESSENTRY32 *lppe);
	int Process32Next(HANDLE hSnapshot, PROCESSENTRY32 *lppe);
	void CloseHandle(HANDLE hObject);

	HANDLE OpenProcess(DWORD dwDesiredAccess, BOOL bInheritHandle, DWORD dwProcessId);
	BOOL EnumProcessModulesEx(HANDLE hProcess, HMODULE *lphModule, DWORD cb, LPDWORD lpcbNeeded, DWORD dwFilterFlag);
	DWORD GetModuleBaseNameA(HANDLE hProcess, HMODULE hModule, LPCSTR lpBaseName, DWORD nSize);
	BOOL ReadProcessMemory(HANDLE hProcess, uintptr_t lpBaseAddress, void *lpBuffer, size_t nSize, size_t *lpNumberOfBytesRead);
]]


function get_pids(process_name)
	local pids = {}
	local snapshot = ffi.C.CreateToolhelp32Snapshot(0x2, 0)
	if snapshot == ffi.cast("HANDLE", -1) then
		return pids
	end
	
	ffi.gc(snapshot, ffi.C.CloseHandle)

	local entry = ffi.new("PROCESSENTRY32")
	entry.dwSize = ffi.sizeof("PROCESSENTRY32")

	if ffi.C.Process32First(snapshot, entry) ~= 0 then
		repeat
			local exe_file = ffi.string(entry.szExeFile)
			if exe_file == process_name then
				table.insert(pids, entry.th32ProcessID)
			end
		until ffi.C.Process32Next(snapshot, entry) == 0
	end

	return pids
end


function get_base_address(pid)
	local hProcess = ffi.C.OpenProcess(0x400 + 0x10, false, pid)
	if hProcess == nil then
		return nil
	end

	ffi.gc(hProcess, ffi.C.CloseHandle)

	local hMod = ffi.new("HMODULE[1024]")
	local cbNeeded = ffi.new("DWORD[1]")
	local psapi = ffi.load("psapi")
	
	if psapi.EnumProcessModulesEx(hProcess, hMod, ffi.sizeof(hMod), cbNeeded, 0x3) == 0 then
		return nil
	end

	local modBaseAddr = tonumber(ffi.cast("uintptr_t", hMod[0]))
	return modBaseAddr
end


function read_address_value(address)
	local buffer = ffi.new("uint8_t[4]")
	local bytesRead = ffi.new("size_t[1]")
	
	ffi.C.ReadProcessMemory(process_handle, ffi.cast("uintptr_t", address), buffer, 4, bytesRead)

	return ffi.cast("uint32_t*", buffer)[0]
end


function get_final_addresses(base_address, offset_address, offsets)
	offset_address = offset_address + base_address
	
	if not offsets then
		return offset_address
	end
	
	for _, offset in ipairs(offsets) do
		local address_value = read_address_value(offset_address)
		offset_address = address_value + offset
	end
	return offset_address
end


local alt_checker_addresses = {0x968C44, 0x96A2A4}
local alt_checker_offsets = {
	{0x12C, 0x300, 0x0, 0x124}, -- state (global)
	{0x12C, 0x300, 0x0, 0x124}  -- alt state (global)
}

local lvl0_addresses = {0x968C44, 0x968C44}
local lvl0_offsets = {
	{0x12C, 0x300, 0x0, 0x38C, 0x8}, -- inputs
	{0x12C, 0x300, 0x0, 0x33C} -- finish
}

local process_name = "TmForever.exe"


function update()
	-- print("update")
	state = read_address_value(alt_checker_calc_addresses[alt])
	if state == 0 or pid ~= pids[selected_pid] then
		
		if update_timer then
			update_timer = false
			obs.timer_remove(update)
		end
		
		if lvl0() == true then
			if not lvl0_timer then
				obs.timer_add(lvl0, 500)
				lvl0_timer = true
			end
		end
		return nil
	end
	finish = read_address_value(lvl0_calc_addresses[2]) ~= 0
	-- print(tostring(finish) .. " " .. tostring(state))
	
	if (state == 8 or state == 512 or state == 1024 or state == 16384 or state == 32768) and not finish then
		left = (read_address_value(lvl0_calc_addresses[1]) % 2) ~= 0
		right = (read_address_value(lvl0_calc_addresses[1] + 0xC) % 2) ~= 0
		steer = read_address_value(lvl0_calc_addresses[1] + 0x18)
		down = (read_address_value(lvl0_calc_addresses[1] + 0x24) % 2) ~= 0
		up = (read_address_value(lvl0_calc_addresses[1] + 0x30) % 2) ~= 0
		
		if 0x2000001 <= steer and steer <= 0x2010000 then
			steer = steer - 0x2000000
		elseif 0x2FF0000 <= steer and steer <= 0x2FFFFFF then
			steer = steer - 0x3000000
		else
			steer = 0
		end
	else
		left = false
		right = false
		steer = 0
		down = false
		up = false
	end
	-- print(tostring(lvl0_calc_addresses[1]))
	-- 65536
	-- print(string.format("0x%X", steer) .. " " .. tostring(steer))
	if not update_timer then
		update_timer = true
		obs.timer_add(update, 1)
	end
end


function lvl0() -- get pid > get base_address > open proc_handle > calc alt_checker_addresses > check if alt > calc lvl0_addresses > update() | return to lvl0 if pid changes or game closes
	pids = get_pids(process_name)
	
	if selected_pid then
		if selected_pid > #pids or #pids == 1 then
			selected_pid = 1
		end
	else
		selected_pid = 1
	end
	
	pid = pids[selected_pid]
	
	if process_handle and process_handle_pid ~= pid then
		ffi.C.CloseHandle(process_handle)
		process_handle = nil
		process_handle_pid = pid
		-- print("closed")
	end
	
	if not pid then
		return true
	end
	
	base_address = get_base_address(pid)
	
	alt_checker_calc_addresses = {}
	lvl0_calc_addresses = {}
	
	if pid and not process_handle then
		process_handle = ffi.C.OpenProcess(0x10, false, pid)
		process_handle_pid = pid
		-- print("opened")
	end
	
	-- for i, address in ipairs(lvl0_calc_addresses) do
		-- print(string.format("Address: 0x%X", address))
		
		-- local offset = lvl0_offsets[i]
		-- if offset then
			-- print("Offsets: " .. table.concat(offset, ", "))
		-- else
			-- print("No offsets for this address.")
		-- end
	-- end
	
	if process_handle and base_address then
		
		if base_address == 0x400000 then
			tmloader = false
		else
			tmloader = true
		end
		
		for i, address in ipairs(alt_checker_addresses) do
			table.insert(alt_checker_calc_addresses, get_final_addresses(base_address, address, alt_checker_offsets[i]))
		end
		
		-- print(tostring(read_address_value(lvl0_calc_addresses[1])))
		-- print(tostring(lvl0_calc_addresses[1]))
		
		if read_address_value(alt_checker_calc_addresses[1]) ~= 0 then
			alt = 1
		elseif read_address_value(alt_checker_calc_addresses[2]) ~= 0 then
			alt = 2
			base_address = base_address + 0x1660
		else -- Too early lvl0_addresses calc
			return true
		end
		
		for i, address in ipairs(lvl0_addresses) do
			table.insert(lvl0_calc_addresses, get_final_addresses(base_address, address, lvl0_offsets[i]))
		end
		
		if lvl0_timer then
			lvl0_timer = false
			obs.timer_remove(lvl0)
		end
		
		print(process_name .. " | Alt: " .. tostring(alt ~= 1) .. " | TMLoader: " .. tostring(tmloader) .. " | PID: " .. tostring(pid))
		
		update()
	else
		return true
	end
end


function script_load(settings)
	if lvl0() == true then
		if not lvl0_timer then
			obs.timer_add(lvl0, 500)
			lvl0_timer = true
		end
	end
end


function script_unload()
	if process_handle then
		ffi.C.CloseHandle(process_handle)
		process_handle = nil
	end
end


function refresh_pids(props, prop, settings)
	local p_pids = obs.obs_properties_get(props, "pids")
	
	if pids then
		pids = get_pids(process_name)
		obs.obs_property_list_clear(p_pids)
		for i, pid in ipairs(pids) do
			obs.obs_property_list_add_int(p_pids, pid, i)
		end
	end
	
	return true
end


function script_update(settings)
	selected_pid = obs.obs_data_get_int(settings, "pids")
end


function script_properties()
	local props = obs.obs_properties_create()
	p = obs.obs_properties_add_button(props, "refresh", "Refresh PID List", button)
	obs.obs_property_set_modified_callback(p, refresh_pids)
	obs.obs_properties_add_list(props, "pids", "PID List", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
	return props
end


function script_description()
	return (tostring(version) .. " | " .. tostring(version_date) .. " " .. "\nAdd a new \"TMFDisplay Input\" source, select the correct image files, and open your game.")
end


function button()
	return nil
end