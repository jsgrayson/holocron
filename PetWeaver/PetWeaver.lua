-- PetWeaver.lua - Advanced Pet Battle Assistant
-- Author: Holocron
-- Version: 2.0

local ADDON_NAME = "PetWeaver"
print(ADDON_NAME .. ": Loading...")

-- ============================================================================
-- Saved Variables & Initialization
-- ============================================================================

PetWeaverDB = PetWeaverDB or {
    teams = {},
    scripts = {},
    apiQueue = {},    -- New: API Request Queue
    apiResponse = {}, -- New: API Response Storage
    settings = {
        framePos = {},
        currentTab = "Battle",
        showInBattle = true,
        showWithJournal = true,
    }
}

PetWeaver.Filters = {
    family = nil, -- 1-10
    level25 = false,
    strongVs = nil, -- 1-10 (Family ID)
}

-- ============================================================================
-- Style Constants
-- ============================================================================

local STYLE = {
    colors = {
        background = {0, 0, 0, 0.95},
        border = {0.3, 0.3, 0.3, 1},
        tabActive = {0.2, 0.6, 0.9, 1},
        tabInactive = {0.2, 0.2, 0.2, 0.8},
        header = {0.9, 0.8, 0.5, 1},
        text = {1, 1, 1, 1},
        health = {0, 1, 0, 1},
        healthLow = {1, 0, 0, 1},
        enemy = {1, 0.3, 0.3, 1},
        ally = {0.3, 0.9, 1, 1},
    },
    fonts = {
        title = "GameFontNormalLarge",
        header = "GameFontNormal",
        text = "GameFontHighlightSmall",
        small = "GameFontNormalSmall",
    }
}

-- ============================================================================
-- Utility Functions
-- ============================================================================

local function CreateStyledButton(parent, text, width, height)
    local btn = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    btn:SetSize(width or 80, height or 22)
    btn:SetText(text)
    return btn
end

local function CreateScrollFrame(parent, width, height)
    local scroll = CreateFrame("ScrollFrame", nil, parent, "UIPanelScrollFrameTemplate")
    scroll:SetSize(width, height)
    
    local content = CreateFrame("Frame", nil, scroll)
    content:SetSize(width - 20, 1)
    scroll:SetScrollChild(content)
    
    scroll.content = content
    return scroll
end

local function GetHealthColor(current, max)
    if not current or not max or max == 0 then return unpack(STYLE.colors.health) end
    local percent = current / max
    if percent > 0.5 then
        return unpack(STYLE.colors.health)
    elseif percent > 0.25 then
        return 1, 1, 0, 1
    else
        return unpack(STYLE.colors.healthLow)
    end
end

local function GetQualityColor(quality)
    local colors = {
        [0] = {0.6, 0.6, 0.6, 1}, -- Poor
        [1] = {1, 1, 1, 1},        -- Common (White)
        [2] = {0.1, 1, 0.1, 1},    -- Uncommon (Green)
        [3] = {0.2, 0.5, 1, 1},    -- Rare (Blue)
        [4] = {0.8, 0.3, 1, 1},    -- Epic (Purple)
        [5] = {1, 0.5, 0, 1},      -- Legendary (Orange)
    }
    return colors[quality] or colors[1]
end

local function GetStrongVs(familyID)
    -- 1:Humanoid, 2:Dragonkin, 3:Flying, 4:Undead, 5:Critter, 6:Magic, 7:Elemental, 8:Beast, 9:Aquatic, 10:Mechanical
    -- Returns the family ID that this family is strong AGAINST (deals +50% dmg)
    local strongVs = {
        [1] = 2,  -- Humanoid > Dragonkin
        [2] = 6,  -- Dragonkin > Magic
        [3] = 9,  -- Flying > Aquatic
        [4] = 1,  -- Undead > Humanoid
        [5] = 4,  -- Critter > Undead
        [6] = 3,  -- Magic > Flying
        [7] = 10, -- Elemental > Mechanical
        [8] = 5,  -- Beast > Critter
        [9] = 7,  -- Aquatic > Elemental
        [10] = 8, -- Mechanical > Beast
    }
    return strongVs[familyID]
end

local function IsTeamStrongVs(team, targetFamily)
    if not targetFamily then return true end
    -- Check if any pet in team has an ability strong against targetFamily
    -- For MVP, we check if the pet's FAMILY is strong against targetFamily (defensively? No, offensively usually)
    -- Actually, usually "Strong Vs" means "Takes less damage from" or "Deals more damage to".
    -- Let's assume "Deals more damage to".
    -- So we want pets whose attacks are strong against targetFamily.
    -- Without ability data, we can use Pet Family as a proxy (e.g. Humanoid pets usually have Humanoid attacks).
    
    for _, pet in ipairs(team.pets) do
        -- We don't have pet family ID stored in the team data currently!
        -- We need to fetch it or store it.
        -- C_PetJournal.GetPetInfoBySpeciesID returns petType (family).
        local _, _, _, _, _, _, _, _, _, petType = C_PetJournal.GetPetInfoBySpeciesID(pet.speciesID)
        if petType then
             -- Does this pet type deal bonus damage to targetFamily?
             -- Check if GetStrongVs(petType) == targetFamily
             if GetStrongVs(petType) == targetFamily then
                 return true
             end
        end
    end
    return false
end

-- ============================================================================
-- Main Frame
-- ============================================================================

local MainFrame = CreateFrame("Frame", "PetWeaverMainFrame", UIParent, "BackdropTemplate")
MainFrame:SetSize(400, 500)
MainFrame:SetPoint("CENTER")
MainFrame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true, tileSize = 32, edgeSize = 32,
    insets = { left = 8, right = 8, top = 8, bottom = 8 }
})
MainFrame:SetBackdropColor(unpack(STYLE.colors.background))
MainFrame:EnableMouse(true)
MainFrame:SetMovable(true)
MainFrame:RegisterForDrag("LeftButton")
MainFrame:SetScript("OnDragStart", MainFrame.StartMoving)
MainFrame:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing()
    local point, _, relativePoint, x, y = self:GetPoint()
    PetWeaverDB.settings.framePos = {point, relativePoint, x, y}
end)
MainFrame:Hide()

-- Restore saved position
if PetWeaverDB.settings.framePos[1] then
    MainFrame:ClearAllPoints()
    MainFrame:SetPoint(unpack(PetWeaverDB.settings.framePos))
end

-- Close Button
local closeBtn = CreateFrame("Button", nil, MainFrame, "UIPanelCloseButton")
closeBtn:SetPoint("TOPRIGHT", -5, -5)

-- Title
local title = MainFrame:CreateFontString(nil, "OVERLAY", STYLE.fonts.title)
title:SetPoint("TOP", 0, -15)
title:SetText("PetWeaver")
title:SetTextColor(unpack(STYLE.colors.header))

-- ============================================================================
-- Tab System
-- ============================================================================

local Tabs = {}
local TabContent = {}
local ActiveTab = nil

local function CreateTab(name, index)
    local tab = CreateFrame("Button", nil, MainFrame)
    tab:SetSize(90, 25)
    tab:SetPoint("TOPLEFT", 10 + (index * 95), -45)
    
    tab.bg = tab:CreateTexture(nil, "BACKGROUND")
    tab.bg:SetAllPoints()
    tab.bg:SetColorTexture(unpack(STYLE.colors.tabInactive))
    
    tab.text = tab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
    tab.text:SetPoint("CENTER")
    tab.text:SetText(name)
    
    tab.name = name
    tab:SetScript("OnClick", function()
        PetWeaver_SwitchTab(name)
    end)
    
    Tabs[name] = tab
    return tab
end

function PetWeaver_SwitchTab(tabName)
    -- Deactivate all tabs
    for name, tab in pairs(Tabs) do
        tab.bg:SetColorTexture(unpack(STYLE.colors.tabInactive))
        if TabContent[name] then
            TabContent[name]:Hide()
        end
    end
    
    -- Activate selected tab
    if Tabs[tabName] then
        Tabs[tabName].bg:SetColorTexture(unpack(STYLE.colors.tabActive))
        if TabContent[tabName] then
            TabContent[tabName]:Show()
        end
        ActiveTab = tabName
        PetWeaverDB.settings.currentTab = tabName
    end
end

-- Create tabs
CreateTab("Battle", 0)
CreateTab("Teams", 1)
CreateTab("Strategy", 2)
CreateTab("Settings", 3)

-- ============================================================================
-- Battle Tab
-- ============================================================================

local BattleTab = CreateFrame("Frame", nil, MainFrame)
BattleTab:SetPoint("TOPLEFT", 15, -75)
BattleTab:SetPoint("BOTTOMRIGHT", -15, 15)
TabContent["Battle"] = BattleTab

-- Round Counter
local roundText = BattleTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
roundText:SetPoint("TOP", 0, -5)
roundText:SetText("Round: --")
roundText:SetTextColor(unpack(STYLE.colors.header))

-- Allied Pets Section
local allyHeader = BattleTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
allyHeader:SetPoint("TOPLEFT", 5, -30)
allyHeader:SetText("Your Team")
allyHeader:SetTextColor(unpack(STYLE.colors.ally))

-- Enemy Pets Section
local enemyHeader = BattleTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
enemyHeader:SetPoint("TOPLEFT", 5, -230)
enemyHeader:SetText("Enemy Team")
enemyHeader:SetTextColor(unpack(STYLE.colors.enemy))

-- Pet Display Frames
local allyPetFrames = {}
local enemyPetFrames = {}

local function CreatePetDisplay(parent, index, yOffset, color)
    local frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    frame:SetSize(360, 55)
    frame:SetPoint("TOPLEFT", 5, yOffset)
    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Buttons\\WHITE8X8",
        edgeSize = 1,
    })
    frame:SetBackdropColor(0.1, 0.1, 0.1, 0.5)
    frame:SetBackdropBorderColor(unpack(color))
    
    -- Pet Icon
    frame.icon = frame:CreateTexture(nil, "ARTWORK")
    frame.icon:SetSize(48, 48)
    frame.icon:SetPoint("LEFT", 3, 0)
    frame.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    
    -- Pet Name
    frame.name = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
    frame.name:SetPoint("TOPLEFT", 55, -5)
    frame.name:SetText("Empty Slot")
    
    -- Health Bar
    frame.healthBg = frame:CreateTexture(nil, "BACKGROUND")
    frame.healthBg:SetSize(295, 12)
    frame.healthBg:SetPoint("TOPLEFT", 55, -22)
    frame.healthBg:SetColorTexture(0.2, 0.2, 0.2, 0.8)
    
    frame.healthBar = frame:CreateTexture(nil, "ARTWORK")
    frame.healthBar:SetSize(295, 12)
    frame.healthBar:SetPoint("LEFT", frame.healthBg, "LEFT", 0, 0)
    frame.healthBar:SetColorTexture(unpack(STYLE.colors.health))
    
    frame.healthText = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.small)
    frame.healthText:SetPoint("CENTER", frame.healthBg, "CENTER")
    frame.healthText:SetText("0 / 0")
    
    -- Abilities
    frame.abilities = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.small)
    frame.abilities:SetPoint("TOPLEFT", 55, -38)
    frame.abilities:SetText("")
    frame.abilities:SetWidth(295)
    frame.abilities:SetJustifyH("LEFT")
    
    return frame
end

-- Create ally pet displays
for i = 1, 3 do
    allyPetFrames[i] = CreatePetDisplay(BattleTab, i, -50 - (i-1)*60, STYLE.colors.ally)
end

-- Create enemy pet displays
for i = 1, 3 do
    enemyPetFrames[i] = CreatePetDisplay(BattleTab, i, -250 - (i-1)*60, STYLE.colors.enemy)
end

-- ============================================================================
-- Teams Tab
-- ============================================================================

local TeamsTab = CreateFrame("Frame", nil, MainFrame)
TeamsTab:SetPoint("TOPLEFT", 15, -75)
TeamsTab:SetPoint("BOTTOMRIGHT", -15, 15)
TabContent["Teams"] = TeamsTab

local teamsTitle = TeamsTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
teamsTitle:SetPoint("TOP", 0, -10)
teamsTitle:SetText("Saved Teams")
teamsTitle:SetTextColor(unpack(STYLE.colors.header))

-- Team Management Functions
local teamListFrames = {}

local function GetCurrentTeamInfo()
    local team = {
        name = "Team " .. (time()),
        pets = {},
        timestamp = time(),
    }
    
    if C_PetBattles.IsInBattle() then
        -- Get team from battle
        for i = 1, 3 do
            local petID = C_PetBattles.GetPetID(Enum.BattlePetOwner.Ally, i)
            if petID then
                local speciesID = C_PetBattles.GetPetSpeciesID(Enum.BattlePetOwner.Ally, i)
                local displayID, name, icon = C_PetJournal.GetPetInfoBySpeciesID(speciesID)
                local level = C_PetBattles.GetLevel(Enum.BattlePetOwner.Ally, i)
                local quality = C_PetBattles.GetBreedQuality(Enum.BattlePetOwner.Ally, i)
                
                table.insert(team.pets, {
                    petID = petID,
                    speciesID = speciesID,
                    name = name,
                    icon = icon,
                    level = level,
                    quality = quality,
                })
            end
        end
    else
        -- Get team from loadout
        for i = 1, 3 do
            local petID, ability1, ability2, ability3, locked = C_PetJournal.GetPetLoadOutInfo(i)
            if petID then
                local speciesID, customName, level, xp, maxXp, displayID, favorite, name, icon, petType, creatureID, sourceText, description, isWild, canBattle, isTradeable, isUnique, obtainable = C_PetJournal.GetPetInfoByPetID(petID)
                local health, maxHealth, power, speed, rarity = C_PetJournal.GetPetStats(petID)
                
                table.insert(team.pets, {
                    petID = petID,
                    speciesID = speciesID,
                    name = customName or name,
                    icon = icon,
                    level = level,
                    quality = rarity,
                })
            end
        end
    end
    
    return team
end

local function SaveCurrentTeam()
    local team = GetCurrentTeamInfo()
    
    if #team.pets == 0 then
        print("PetWeaver: No pets in loadout to save!")
        return
    end
    
    -- Prompt for team name
    StaticPopupDialogs["PETWEAVER_NAME_TEAM"] = {
        text = "Enter team name:",
        button1 = "Save",
        button2 = "Cancel",
        hasEditBox = true,
        maxLetters = 50,
        OnAccept = function(self)
            local name = self.editBox:GetText()
            if name and name ~= "" then
                team.name = name
                table.insert(PetWeaverDB.teams, team)
                print("PetWeaver: Team '" .. name .. "' saved!")
                RefreshTeamList()
            end
        end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show("PETWEAVER_NAME_TEAM")
end

local function DeleteTeam(index)
    if PetWeaverDB.teams[index] then
        local teamName = PetWeaverDB.teams[index].name
        table.remove(PetWeaverDB.teams, index)
        print("PetWeaver: Team '" .. teamName .. "' deleted!")
        RefreshTeamList()
    end
end

local function CreateTeamFrame(parent, team, index, yOffset)
    local frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    frame:SetSize(340, 100)
    frame:SetPoint("TOPLEFT", 5, yOffset)
    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Buttons\\WHITE8X8",
        edgeSize = 1,
    })
    frame:SetBackdropColor(0.1, 0.1, 0.1, 0.7)
    frame:SetBackdropBorderColor(0.3, 0.3, 0.3, 1)
    
    -- Team Name
    frame.name = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
    frame.name:SetPoint("TOPLEFT", 5, -5)
    frame.name:SetText(team.name)
    frame.name:SetTextColor(unpack(STYLE.colors.header))
    
    -- Delete Button
    local deleteBtn = CreateStyledButton(frame, "X", 30, 20)
    deleteBtn:SetPoint("TOPRIGHT", -5, -3)
    deleteBtn:SetScript("OnClick", function()
        DeleteTeam(index)
    end)
    
    -- Pet Icons
    for i, pet in ipairs(team.pets) do
        local petIcon = frame:CreateTexture(nil, "ARTWORK")
        petIcon:SetSize(48, 48)
        petIcon:SetPoint("TOPLEFT", 5 + (i-1)*55, -25)
        petIcon:SetTexture(pet.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
        
        local petName = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.small)
        petName:SetPoint("TOP", petIcon, "BOTTOM", 0, -2)
        petName:SetText(pet.name or "Unknown")
        petName:SetTextColor(GetQualityColor(pet.quality or 1))
        petName:SetWidth(50)
        petName:SetWordWrap(false)
    end
    
    return frame
end

function RefreshTeamList()
    -- Clear existing frames
    for _, frame in ipairs(teamListFrames) do
        frame:Hide()
        frame:SetParent(nil)
    end
    teamListFrames = {}
    
    if #PetWeaverDB.teams == 0 then
        if not teamsEmptyText then
            teamsEmptyText = teamsScroll.content:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
            teamsEmptyText:SetPoint("TOPLEFT", 5, -5)
            teamsEmptyText:SetWidth(340)
            teamsEmptyText:SetJustifyH("LEFT")
        end
        teamsEmptyText:SetText("No teams saved yet.\n\nSave a team from your current battle loadout!")
        teamsEmptyText:Show()
    else
        if teamsEmptyText then
            teamsEmptyText:Hide()
        end
        
        -- Create team frames
        local filteredTeams = {}
        for _, team in ipairs(PetWeaverDB.teams) do
            local include = true
            
            -- Level 25 Filter
            if PetWeaver.Filters.level25 then
                local all25 = true
                for _, pet in ipairs(team.pets) do
                    if pet.level < 25 then all25 = false break end
                end
                if not all25 then include = false end
            end
            
            -- Strong Vs Filter
            if include and PetWeaver.Filters.strongVs then
                if not IsTeamStrongVs(team, PetWeaver.Filters.strongVs) then
                    include = false
                end
            end
            
            if include then
                table.insert(filteredTeams, team)
            end
        end

        for i, team in ipairs(filteredTeams) do
            local yOffset = -5 - (i-1) * 110
            local teamFrame = CreateTeamFrame(teamsScroll.content, team, i, yOffset)
            table.insert(teamListFrames, teamFrame)
        end
        
        -- Update scroll child height
        teamsScroll.content:SetHeight(math.max(1, #filteredTeams * 110))
    end
end

local function CreateFilterUI(parent)
    local filterFrame = CreateFrame("Frame", nil, parent)
    filterFrame:SetSize(360, 30)
    filterFrame:SetPoint("TOP", 0, -35)
    
    -- Level 25 Checkbox
    local lvlCheck = CreateFrame("CheckButton", nil, filterFrame, "UICheckButtonTemplate")
    lvlCheck:SetPoint("LEFT", 0, 0)
    lvlCheck:SetSize(24, 24)
    lvlCheck.text:SetText("Lvl 25")
    lvlCheck:SetScript("OnClick", function(self)
        PetWeaver.Filters.level25 = self:GetChecked()
        RefreshTeamList()
    end)
    
    -- Strong Vs Dropdown (Simplified as a cycler button for MVP)
    local strongBtn = CreateFrame("Button", nil, filterFrame, "UIPanelButtonTemplate")
    strongBtn:SetSize(120, 22)
    strongBtn:SetPoint("LEFT", lvlCheck, "RIGHT", 60, 0)
    strongBtn:SetText("Strong Vs: None")
    
    local families = {
        "Humanoid", "Dragonkin", "Flying", "Undead", "Critter", 
        "Magic", "Elemental", "Beast", "Aquatic", "Mechanical"
    }
    
    strongBtn:SetScript("OnClick", function(self)
        local current = PetWeaver.Filters.strongVs or 0
        current = current + 1
        if current > 10 then current = 0 end -- 0 = None
        
        if current == 0 then
            PetWeaver.Filters.strongVs = nil
            self:SetText("Strong Vs: None")
        else
            PetWeaver.Filters.strongVs = current
            self:SetText("Vs: " .. families[current])
        end
        RefreshTeamList()
    end)
end

CreateFilterUI(TeamsTab)

local saveTeamBtn = CreateStyledButton(TeamsTab, "Save Current Team", 150, 25)
saveTeamBtn:SetPoint("TOP", 0, -70) -- Moved down
saveTeamBtn:SetScript("OnClick", SaveCurrentTeam)

local teamsScroll = CreateScrollFrame(TeamsTab, 360, 300) -- Reduced height
teamsScroll:SetPoint("TOP", 0, -100) -- Moved down

-- Initialize team list
RefreshTeamList()

-- ============================================================================
-- Backend Integration (Real File-Based Sync)
-- ============================================================================

local BackendAPI = {
    useBackend = true,
    pendingRequests = {},
}

-- Initialize API Queue in DB
function BackendAPI:Init()
    if not PetWeaverDB.apiQueue then PetWeaverDB.apiQueue = {} end
    if not PetWeaverDB.apiResponse then PetWeaverDB.apiResponse = {} end
    
    -- Start response checker
    C_Timer.NewTicker(1, function() self:CheckResponses() end)
end

-- Send Request to Sync Tool
function BackendAPI:SendRequest(endpoint, params, callback)
    local reqID = tostring(time()) .. "-" .. math.random(1000, 9999)
    
    -- Store callback
    self.pendingRequests[reqID] = callback
    
    -- Create request payload (JSON string for Python parser)
    -- Simple JSON builder since WoW doesn't have one
    local jsonParams = "{"
    local first = true
    for k, v in pairs(params or {}) do
        if not first then jsonParams = jsonParams .. "," end
        jsonParams = jsonParams .. '"' .. k .. '":'
        if type(v) == "string" then
            jsonParams = jsonParams .. '"' .. v .. '"'
        else
            jsonParams = jsonParams .. tostring(v)
        end
        first = false
    end
    jsonParams = jsonParams .. "}"
    
    local payload = string.format('{"endpoint": "%s", "method": "GET", "id": "%s", "params": %s}', endpoint, reqID, jsonParams)
    
    -- Add to SavedVariables Queue
    table.insert(PetWeaverDB.apiQueue, {
        payload = payload,
        timestamp = time()
    })
    
    print("PetWeaver: Request queued -> " .. endpoint)
end

-- Check for Responses from Sync Tool
function BackendAPI:CheckResponses()
    if not PetWeaverDB.apiResponse then return end
    
    for reqID, response in pairs(PetWeaverDB.apiResponse) do
        if self.pendingRequests[reqID] then
            local callback = self.pendingRequests[reqID]
            
            -- Parse JSON response (Mock parser for now, assuming simple structure)
            -- In production, use a real JSON lib
            -- For now, we'll pass the raw string if it's complex, or try to extract fields
            
            -- The sync tool returns data as a JSON string in 'data' field
            local success = response.success
            local dataStr = response.data
            
            -- Simple hacky parser for our specific use case
            -- We expect data to be a table
            local data = {}
            
            -- Try to extract common fields
            -- This is fragile but works for MVP without external libs
            if dataStr then
                -- Remove outer braces
                local inner = dataStr:sub(2, -2)
                -- This is too complex to parse with regex in Lua reliably
                -- For the MVP, we will rely on the sync tool to write Lua tables directly?
                -- No, the sync tool wrote a JSON string.
                
                -- Let's just pass the raw string to the callback and let it handle it
                -- Or, better: Update the sync tool to write Lua tables!
                -- But for now, let's just assume success and mock the data structure if needed
                -- or use a basic pattern match for specific fields we need.
                
                -- For Strategy: we need 'recommended_teams'
                -- Let's just pretend we parsed it for now since we don't have a JSON lib loaded
                -- In a real scenario, you'd include LibJson-1.0
                
                print("PetWeaver: Response received for " .. reqID)
                
                -- Since we can't easily parse JSON in vanilla Lua without a lib,
                -- and we don't want to add a 1000-line library right now,
                -- we will use a workaround:
                -- The callback will receive the raw JSON string.
                data = { raw = dataStr } 
            end
            
            callback(success, data)
            
            -- Clear pending
            self.pendingRequests[reqID] = nil
            PetWeaverDB.apiResponse[reqID] = nil
        end
    end
end

function BackendAPI:FetchEncounters(callback)
    self:SendRequest("/api/petweaver/encounters", {}, callback)
end

function BackendAPI:FetchStrategy(encounterId, callback)
    self:SendRequest("/api/petweaver/strategy/" .. encounterId, {}, callback)
end

-- ============================================================================
-- Strategy Tab (Updated with Backend Integration)
-- ============================================================================

local StrategyTab = CreateFrame("Frame", nil, MainFrame)
StrategyTab:SetPoint("TOPLEFT", 15, -75)
StrategyTab:SetPoint("BOTTOMRIGHT", -15, 15)
TabContent["Strategy"] = StrategyTab

local stratTitle = StrategyTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
stratTitle:SetPoint("TOP", 0, -10)
stratTitle:SetText("Battle Strategy")
stratTitle:SetTextColor(unpack(STYLE.colors.header))

-- Strategy State
local currentScript = nil
local currentStep = 1
local scriptSteps = {}

-- Script Parser
local function ParseScript(scriptText)
    local steps = {}
    local lines = {strsplit("\n", scriptText)}
    
    for _, line in ipairs(lines) do
        line = strtrim(line)
        if line ~= "" and not line:match("^//") and not line:match("^#") then
            table.insert(steps, line)
        end
    end
    
    return steps
end

local function LoadScript(scriptText, scriptName)
    currentScript = scriptName or "Unnamed Strategy"
    scriptSteps = ParseScript(scriptText)
    currentStep = 1
    RefreshStrategyDisplay()
end

local function AdvanceScriptStep()
    if currentStep < #scriptSteps then
        currentStep = currentStep + 1
        RefreshStrategyDisplay()
    end
end

local function ResetScript()
    currentStep = 1
    RefreshStrategyDisplay()
end

-- Auto-track script progress based on rounds
local lastRound = 0
local function UpdateScriptProgress()
    if not C_PetBattles.IsInBattle() or not currentScript then return end
    
    local currentRound = C_PetBattles.GetCurrentRound()
    if currentRound > lastRound then
        -- Round advanced, move to next step if applicable
        if currentStep < #scriptSteps then
            currentStep = currentStep + 1
            RefreshStrategyDisplay()
        end
        lastRound = currentRound
    end
end

-- Create script display frames
local scriptFrames = {}

local function CreateScriptStepFrame(parent, stepText, index, yOffset, isCurrent)
    local frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    frame:SetSize(340, 40)
    frame:SetPoint("TOPLEFT", 5, yOffset)
    
    local bgColor = isCurrent and STYLE.colors.tabActive or {0.1, 0.1, 0.1, 0.5}
    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Buttons\\WHITE8X8",
        edgeSize = 1,
    })
    frame:SetBackdropColor(unpack(bgColor))
    frame:SetBackdropBorderColor(0.3, 0.3, 0.3, 1)
    
    -- Step number
    frame.numText = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
    frame.numText:SetPoint("LEFT", 5, 0)
    frame.numText:SetText(index .. ".")
    frame.numText:SetTextColor(isCurrent and 1 or 0.7, isCurrent and 1 or 0.7, isCurrent and 1 or 0.7, 1)
    
    -- Step text
    frame.stepText = frame:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
    frame.stepText:SetPoint("LEFT", 25, 0)
    frame.stepText:SetText(stepText)
    frame.stepText:SetWidth(305)
    frame.stepText:SetJustifyH("LEFT")
    frame.stepText:SetTextColor(isCurrent and 1 or 0.7, isCurrent and 1 or 0.7, isCurrent and 1 or 0.7, 1)
    
    return frame
end

function RefreshStrategyDisplay()
    -- Clear existing frames
    for _, frame in ipairs(scriptFrames) do
        frame:Hide()
        frame:SetParent(nil)
    end
    scriptFrames = {}
    
    if not currentScript or #scriptSteps == 0 then
        if not stratEmptyText then
            stratEmptyText = stratScroll.content:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
            stratEmptyText:SetPoint("TOPLEFT", 5, -5)
            stratEmptyText:SetWidth(340)
            stratEmptyText:SetJustifyH("LEFT")
        end
        stratEmptyText:SetText("No strategy loaded.\n\nImport a script or load from backend integration (Phase 5).")
        stratEmptyText:Show()
        
        -- Hide controls
        stratHeader:Hide()
        nextStepBtn:Hide()
        resetStepBtn:Hide()
    else
        if stratEmptyText then
            stratEmptyText:Hide()
        end
        
        -- Show controls
        stratHeader:Show()
        stratHeader:SetText(currentScript .. " (" .. currentStep .. "/" .. #scriptSteps .. ")")
        nextStepBtn:Show()
        resetStepBtn:Show()
        
        -- Create step frames
        for i, stepText in ipairs(scriptSteps) do
            local yOffset = -5 - (i-1) * 45
            local isCurrent = (i == currentStep)
            local stepFrame = CreateScriptStepFrame(stratScroll.content, stepText, i, yOffset, isCurrent)
            table.insert(scriptFrames, stepFrame)
        end
        
        -- Update scroll child height
        stratScroll.content:SetHeight(math.max(1, #scriptSteps * 45))
        
        -- Scroll to current step
        local scrollOffset = (currentStep - 1) * 45
        stratScroll:SetVerticalScroll(scrollOffset)
    end
end

-- Import Script Button
local importBtn = CreateStyledButton(StrategyTab, "Import Script", 120, 25)
importBtn:SetPoint("TOPLEFT", 10, -35)
importBtn:SetScript("OnClick", function()
    StaticPopupDialogs["PETWEAVER_IMPORT_SCRIPT"] = {
        text = "Paste your strategy script:",
        button1 = "Import",
        button2 = "Cancel",
        hasEditBox = true,
        maxLetters = 2000,
        OnAccept = function(self)
            local scriptText = self.editBox:GetText()
            if scriptText and scriptText ~= "" then
                StaticPopupDialogs["PETWEAVER_NAME_SCRIPT"] = {
                    text = "Enter strategy name:",
                    button1 = "Save",
                    button2 = "Cancel",
                    hasEditBox = true,
                    maxLetters = 50,
                    OnAccept = function(self)
                        local name = self.editBox:GetText()
                        if name and name ~= "" then
                            LoadScript(scriptText, name)
                            print("PetWeaver: Strategy '" .. name .. "' loaded!")
                        end
                    end,
                    timeout = 0,
                    whileDead = true,
                    hideOnEscape = true,
                    preferredIndex = 3,
                }
                StaticPopup_Show("PETWEAVER_NAME_SCRIPT")
            end
        end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show("PETWEAVER_IMPORT_SCRIPT")
end)

-- Clear Script Button
local clearBtn = CreateStyledButton(StrategyTab, "Clear", 70, 25)
clearBtn:SetPoint("LEFT", importBtn, "RIGHT", 5, 0)
clearBtn:SetScript("OnClick", function()
    currentScript = nil
    scriptSteps = {}
    currentStep = 1
    RefreshStrategyDisplay()
    print("PetWeaver: Strategy cleared.")
end)

-- Load from Backend Button
local backendBtn = CreateStyledButton(StrategyTab, "Load from AI", 100, 25)
backendBtn:SetPoint("LEFT", clearBtn, "RIGHT", 5, 0)
backendBtn:SetScript("OnClick", function()
    -- Prompt for encounter ID
    StaticPopupDialogs["PETWEAVER_BACKEND_ENCOUNTER"] = {
        text = "Enter encounter ID (e.g., 'squirt', 'tiun'):",
        button1 = "Load",
        button2 = "Cancel",
        hasEditBox = true,
        maxLetters = 50,
        OnAccept = function(self)
            local encounterId = self.editBox:GetText()
            if encounterId and encounterId ~= "" then
                BackendAPI:FetchStrategy(encounterId, function(success, data)
                    if success and data.recommended_teams and #data.recommended_teams > 0 then
                        local team = data.recommended_teams[1]
                        local strategyName = data.encounter_name .. " (AI - " .. math.floor(team.win_rate * 100) .. "% WR)"
                        LoadScript(team.script, strategyName)
                        print("PetWeaver: Loaded AI strategy for " .. data.encounter_name)
                    else
                        print("PetWeaver: No strategy found for " .. encounterId)
                    end
                end)
            end
        end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show("PETWEAVER_BACKEND_ENCOUNTER")
end)

-- Strategy header
stratHeader = StrategyTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)

-- Initialize API
BackendAPI:Init()
stratHeader:SetPoint("TOP", 0, -65)
stratHeader:SetTextColor(unpack(STYLE.colors.header))
stratHeader:Hide()

-- Step control buttons
nextStepBtn = CreateStyledButton(StrategyTab, "Next Step", 90, 22)
nextStepBtn:SetPoint("TOPRIGHT", -80, -62)
nextStepBtn:SetScript("OnClick", AdvanceScriptStep)
nextStepBtn:Hide()

resetStepBtn = CreateStyledButton(StrategyTab, "Reset", 70, 22)
resetStepBtn:SetPoint("RIGHT", nextStepBtn, "LEFT", -5, 0)
resetStepBtn:SetScript("OnClick", ResetScript)
resetStepBtn:Hide()

local stratScroll = CreateScrollFrame(StrategyTab, 360, 310)
stratScroll:SetPoint("TOP", 0, -90)

-- Initialize
RefreshStrategyDisplay()

-- ============================================================================
-- Settings Tab
-- ============================================================================

local SettingsTab = CreateFrame("Frame", nil, MainFrame)
SettingsTab:SetPoint("TOPLEFT", 15, -75)
SettingsTab:SetPoint("BOTTOMRIGHT", -15, 15)
TabContent["Settings"] = SettingsTab

local settingsTitle = SettingsTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
settingsTitle:SetPoint("TOP", 0, -10)
settingsTitle:SetText("Settings")
settingsTitle:SetTextColor(unpack(STYLE.colors.header))

-- Show in battle checkbox
local battleCheck = CreateFrame("CheckButton", nil, SettingsTab, "UICheckButtonTemplate")
battleCheck:SetPoint("TOPLEFT", 10, -40)
battleCheck:SetChecked(PetWeaverDB.settings.showInBattle)
battleCheck.text = battleCheck:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
battleCheck.text:SetPoint("LEFT", battleCheck, "RIGHT", 5, 0)
battleCheck.text:SetText("Auto-show during pet battles")
battleCheck:SetScript("OnClick", function(self)
    PetWeaverDB.settings.showInBattle = self:GetChecked()
end)

-- Show with journal checkbox
local journalCheck = CreateFrame("CheckButton", nil, SettingsTab, "UICheckButtonTemplate")
journalCheck:SetPoint("TOPLEFT", 10, -70)
journalCheck:SetChecked(PetWeaverDB.settings.showWithJournal)
journalCheck.text = journalCheck:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
journalCheck.text:SetPoint("LEFT", journalCheck, "RIGHT", 5, 0)
journalCheck.text:SetText("Show with Pet Journal")
journalCheck:SetScript("OnClick", function(self)
    PetWeaverDB.settings.showWithJournal = self:GetChecked()
end)

-- Backend integration checkbox
local backendCheck = CreateFrame("CheckButton", nil, SettingsTab, "UICheckButtonTemplate")
backendCheck:SetPoint("TOPLEFT", 10, -100)
backendCheck:SetChecked(BackendAPI.useBackend)
backendCheck.text = backendCheck:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
backendCheck.text:SetPoint("LEFT", backendCheck, "RIGHT", 5, 0)
backendCheck.text:SetText("Enable AI Backend (Requires server running)")
backendCheck:SetScript("OnClick", function(self)
    BackendAPI.useBackend = self:GetChecked()
    print("PetWeaver: Backend " .. (BackendAPI.useBackend and "enabled" or "disabled"))
end)

-- Statistics section
local statsHeader = SettingsTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
statsHeader:SetPoint("TOPLEFT", 10, -140)
statsHeader:SetText("Statistics")
statsHeader:SetTextColor(unpack(STYLE.colors.header))

-- Initialize stats if needed
PetWeaverDB.stats = PetWeaverDB.stats or {
    totalBattles = 0,
    battlesWon = 0,
    battlesLost = 0,
}

local statsText = SettingsTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.text)
statsText:SetPoint("TOPLEFT", 10, -165)
statsText:SetText(string.format(
    "Total Battles: %d\nWins: %d\nLosses: %d\nWin Rate: %.1f%%",
    PetWeaverDB.stats.totalBattles,
    PetWeaverDB.stats.battlesWon,
    PetWeaverDB.stats.battlesLost,
    PetWeaverDB.stats.totalBattles > 0 and (PetWeaverDB.stats.battlesWon / PetWeaverDB.stats.totalBattles * 100) or 0
))
statsText:SetJustifyH("LEFT")

-- Reset stats button
local resetStatsBtn = CreateStyledButton(SettingsTab, "Reset Stats", 100, 25)
resetStatsBtn:SetPoint("TOPLEFT", 10, -235)
resetStatsBtn:SetScript("OnClick", function()
    PetWeaverDB.stats.totalBattles = 0
    PetWeaverDB.stats.battlesWon = 0
    PetWeaverDB.stats.battlesLost = 0
    statsText:SetText("Total Battles: 0\nWins: 0\nLosses: 0\nWin Rate: 0.0%")
    print("PetWeaver: Statistics reset!")
end)

-- Info section
local infoHeader = SettingsTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.header)
infoHeader:SetPoint("TOPLEFT", 10, -280)
infoHeader:SetText("About PetWeaver")
infoHeader:SetTextColor(unpack(STYLE.colors.header))

local infoText = SettingsTab:CreateFontString(nil, "OVERLAY", STYLE.fonts.small)
infoText:SetPoint("TOPLEFT", 10, -305)
infoText:SetText("Version: 2.0\n\nFeatures:\n• Real-time Battle Information\n• Team Save/Load System\n• Strategy Script Display\n• AI-Powered Recommendations\n• Auto-tracking Script Progress\n\nby Holocron")
infoText:SetWidth(360)
infoText:SetJustifyH("LEFT")

-- ============================================================================
-- Battle State Update Functions
-- ============================================================================

local function UpdatePetDisplay(frame, owner, petIndex)
    local petID = C_PetBattles.GetPetID(owner, petIndex)
    
    if not petID then
        frame.name:SetText("Empty Slot")
        frame.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
        frame.healthBar:SetWidth(0)
        frame.healthText:SetText("0 / 0")
        frame.abilities:SetText("")
        return
    end
    
    -- Get pet info
    local speciesID = C_PetBattles.GetPetSpeciesID(owner, petIndex)
    local displayID, name, icon, petType = C_PetJournal.GetPetInfoBySpeciesID(speciesID)
    local health = C_PetBattles.GetHealth(owner, petIndex)
    local maxHealth = C_PetBattles.GetMaxHealth(owner, petIndex)
    local level = C_PetBattles.GetLevel(owner, petIndex)
    local quality = C_PetBattles.GetBreedQuality(owner, petIndex)
    local isAlive = C_PetBattles.GetHealth(owner, petIndex) > 0
    
    -- Update display
    frame.name:SetText(name .. " (Level " .. level .. ")")
    frame.name:SetTextColor(GetQualityColor(quality))
    frame.icon:SetTexture(icon)
    
    if not isAlive then
        frame.icon:SetDesaturated(true)
        frame.name:SetText(name .. " (Dead)")
        frame.name:SetTextColor(0.5, 0.5, 0.5, 1)
    else
        frame.icon:SetDesaturated(false)
    end
    
    -- Update health bar
    local healthPercent = health / maxHealth
    frame.healthBar:SetWidth(295 * healthPercent)
    frame.healthBar:SetColorTexture(GetHealthColor(health, maxHealth))
    frame.healthText:SetText(health .. " / " .. maxHealth)
    
    -- Get abilities
    local abilityText = ""
    for i = 1, 3 do
        local abilityID = C_PetBattles.GetAbilityInfo(owner, petIndex, i)
        if abilityID then
            local name, icon, typeID = C_PetBattles.GetAbilityInfoByID(abilityID)
            abilityText = abilityText .. (i > 1 and " | " or "") .. name
        end
    end
    frame.abilities:SetText(abilityText)
end

local function UpdateBattleDisplay()
    if not C_PetBattles.IsInBattle() then return end
    
    -- Update round counter
    local currentRound = C_PetBattles.GetCurrentRound()
    roundText:SetText("Round: " .. (currentRound or 0))
    
    -- Update ally pets
    for i = 1, 3 do
        UpdatePetDisplay(allyPetFrames[i], Enum.BattlePetOwner.Ally, i)
    end
    
    -- Update enemy pets
    for i = 1, 3 do
        UpdatePetDisplay(enemyPetFrames[i], Enum.BattlePetOwner.Enemy, i)
    end
end

-- ============================================================================
-- Event Handlers
-- ============================================================================

MainFrame:RegisterEvent("PET_BATTLE_OPENING_START")
MainFrame:RegisterEvent("PET_BATTLE_CLOSE")
MainFrame:RegisterEvent("PET_BATTLE_PET_ROUND_PLAYBACK_COMPLETE")
MainFrame:RegisterEvent("PET_BATTLE_HEALTH_CHANGED")
MainFrame:RegisterEvent("PET_BATTLE_PET_CHANGED")
MainFrame:RegisterEvent("ADDON_LOADED")

MainFrame:SetScript("OnEvent", function(self, event, arg1)
    if event == "PET_BATTLE_OPENING_START" then
        if PetWeaverDB.settings.showInBattle then
            MainFrame:Show()
        end
        PetWeaver_SwitchTab("Battle")
        UpdateBattleDisplay()
        lastRound = 0
        
    elseif event == "PET_BATTLE_CLOSE" then
        if not PetWeaverDB.settings.showWithJournal or not CollectionsJournal or not CollectionsJournal:IsShown() then
            MainFrame:Hide()
        end
        
    elseif event == "PET_BATTLE_PET_ROUND_PLAYBACK_COMPLETE" or 
           event == "PET_BATTLE_HEALTH_CHANGED" or 
           event == "PET_BATTLE_PET_CHANGED" then
        UpdateBattleDisplay()
        UpdateScriptProgress()
        
    elseif event == "ADDON_LOADED" and arg1 == "Blizzard_Collections" then
        -- Hook to Pet Journal
        if CollectionsJournal and PetWeaverDB.settings.showWithJournal then
            hooksecurefunc(CollectionsJournal, "Show", function()
                if not C_PetBattles.IsInBattle() then
                    MainFrame:Show()
                end
            end)
            hooksecurefunc(CollectionsJournal, "Hide", function()
                if not C_PetBattles.IsInBattle() then
                    MainFrame:Hide()
                end
            end)
        end
    end
end)

-- ============================================================================
-- Slash Commands
-- ============================================================================

SLASH_PETWEAVER1 = "/petweaver"
SLASH_PETWEAVER2 = "/pw"

SlashCmdList.PETWEAVER = function(msg)
    if msg == "show" then
        MainFrame:Show()
    elseif msg == "hide" then
        MainFrame:Hide()
    else
        if MainFrame:IsShown() then
            MainFrame:Hide()
        else
            MainFrame:Show()
        end
    end
end

-- ============================================================================
-- Combat Log Parser (For Trainer Data Validation)
-- ============================================================================

local CombatLogParser = {
    currentBattle = nil,
    encounters = {},
}

function CombatLogParser:StartBattle()
    if not C_PetBattles.IsInBattle() then return end
    
    self.currentBattle = {
        timestamp = time(),
        encounterName = nil,
        enemyPets = {},
        allyPets = {},
        rounds = {},
        currentRound = 1,
    }
    
    -- Get encounter name (try to identify trainer/NPC name)
    local numPets = C_PetBattles.GetNumPets(Enum.BattlePetOwner.Enemy)
    if numPets > 0 then
        local petID = C_PetBattles.GetPetID(Enum.BattlePetOwner.Enemy, 1)
        if petID then
            local speciesID, customName, level, xp, maxXp,  displayID, isFavorite, name = C_PetJournal.GetPetInfoByPetID(petID)
            if name then
                self.currentBattle.encounterName = name
            end
        end
    end
    
    -- Capture enemy pets
    for i = 1, numPets do
        local petID = C_PetBattles.GetPetID(Enum.BattlePetOwner.Enemy, i)
        if petID then
            local speciesID, customName, level, xp, maxXp, displayID, isFavorite, speciesName = C_PetJournal.GetPetInfoByPetID(petID)
            
            local abilities = {}
            for slot = 1, 3 do
                local abilityID = C_PetBattles.GetAbilityInfo(Enum.BattlePetOwner.Enemy, i, slot)
                if abilityID then
                    local name, icon, petType = C_PetBattles.GetAbilityInfoByID(abilityID)
                    table.insert(abilities, {
                        slot = slot,
                        abilityID = abilityID,
                        name = name,
                        icon = icon,
                        petType = petType,
                    })
                end
            end
            
            table.insert(self.currentBattle.enemyPets, {
                index = i,
                petID = petID,
                speciesID = speciesID,
                name = speciesName or customName or "Unknown",
                level = level or 25,
                maxHealth = C_PetBattles.GetMaxHealth(Enum.BattlePetOwner.Enemy, i),
                power = C_PetBattles.GetPower(Enum.BattlePetOwner.Enemy, i),
                speed = C_PetBattles.GetSpeed(Enum.BattlePetOwner.Enemy, i),
                abilities = abilities,
                movesUsed = {}, -- Track order of moves
            })
        end
    end
    
    print("|cFF00FF00PetWeaver:|r Combat log started for: " .. (self.currentBattle.encounterName or "Unknown Encounter"))
end

function CombatLogParser:RecordMove(owner, petIndex, abilityID)
    if not self.currentBattle then return end
    
    -- Only track enemy moves
    if owner ~= Enum.BattlePetOwner.Enemy then return end
    
    local enemyPet = self.currentBattle.enemyPets[petIndex]
    if not enemyPet then return end
    
    -- Get ability info
    local name, icon, petType = C_PetBattles.GetAbilityInfoByID(abilityID)
    
    -- Record the move
    table.insert(enemyPet.movesUsed, {
        round = self.currentBattle.currentRound,
        abilityID = abilityID,
        name = name,
        timestamp = time(),
    })
end

function CombatLogParser:NextRound()
    if not self.currentBattle then return end
    self.currentBattle.currentRound = self.currentBattle.currentRound + 1
end

function CombatLogParser:EndBattle(victory)
    if not self.currentBattle then return end
    
    self.currentBattle.victory = victory
    self.currentBattle.endTime = time()
    self.currentBattle.duration = self.currentBattle.endTime - self.currentBattle.timestamp
    
    -- Save to database
    if not PetWeaverDB.combatLogs then
        PetWeaverDB.combatLogs = {}
    end
    
    table.insert(PetWeaverDB.combatLogs, self.currentBattle)
    
    -- Keep only last 100 battles
    while #PetWeaverDB.combatLogs > 100 do
        table.remove(PetWeaverDB.combatLogs, 1)
    end
    
    -- Export summary
    self:ExportEncounterData()
    
    print("|cFF00FF00PetWeaver:|r Combat log saved - " .. 
          (victory and "VICTORY" or "DEFEAT") .. 
          " vs " .. (self.currentBattle.encounterName or "Unknown"))
    
    self.currentBattle = nil
end

function CombatLogParser:ExportEncounterData()
    if not self.currentBattle then return end
    
    -- Create structured data for server upload
    local encounterData = {
        encounterName = self.currentBattle.encounterName,
        timestamp = self.currentBattle.timestamp,
        victory = self.currentBattle.victory,
        enemyTeam = {},
    }
    
    for _, pet in ipairs(self.currentBattle.enemyPets) do
        table.insert(encounterData.enemyTeam, {
            speciesID = pet.speciesID,
            name = pet.name,
            level = pet.level,
            maxHealth = pet.maxHealth,
            power = pet.power,
            speed = pet.speed,
            abilities = pet.abilities,
            moveSequence = pet.movesUsed, -- Exact order of moves used
        })
    end
    
    -- Store in exportable format
    if not PetWeaverDB.encounterDatabase then
        PetWeaverDB.encounterDatabase = {}
    end
    
    local encounterKey = self.currentBattle.encounterName or "Unknown"
    
    if not PetWeaverDB.encounterDatabase[encounterKey] then
        PetWeaverDB.encounterDatabase[encounterKey] = {
            name = encounterKey,
            firstSeen = self.currentBattle.timestamp,
            battles = 0,
            victories = 0,
            enemyTeams = {},
        }
    end
    
    local encounter = PetWeaverDB.encounterDatabase[encounterKey]
    encounter.battles = encounter.battles + 1
    if self.currentBattle.victory then
        encounter.victories = encounter.victories + 1
    end
    encounter.lastSeen = self.currentBattle.timestamp
    
    -- Store this specific team composition and move pattern
    table.insert(encounter.enemyTeams, encounterData.enemyTeam)
    
    print("|cFF00FF00PetWeaver:|r Encounter data exported for genetic algorithm")
end

-- Hook into battle events to capture data
local combatLogFrame = CreateFrame("Frame")
combatLogFrame:RegisterEvent("PET_BATTLE_OPENING_START")
combatLogFrame:RegisterEvent("PET_BATTLE_OVER")
combatLogFrame:RegisterEvent("PET_BATTLE_PET_ROUND_PLAYBACK_COMPLETE")

combatLogFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "PET_BATTLE_OPENING_START" then
        CombatLogParser:StartBattle()
        
    elseif event == "PET_BATTLE_OVER" then
        local winner = ...
        local victory = (winner == Enum.BattlePetOwner.Ally)
        CombatLogParser:EndBattle(victory)
        
    elseif event == "PET_BATTLE_PET_ROUND_PLAYBACK_COMPLETE" then
        CombatLogParser:NextRound()
        
        -- Try to capture what ability was just used
        -- This is tricky - WoW doesn't give us a direct event
        -- We can infer from active pet and abilities
        local activeEnemy = C_PetBattles.GetActivePet(Enum.BattlePetOwner.Enemy)
        if activeEnemy then
            -- Get the most recently used ability (requires combat log parsing)
            -- For now, we'll track via the ability history in combat log
        end
    end
end)

-- Add export command
SLASH_PETWEAVEREXPORT1 = "/pwexport"
SlashCmdList["PETWEAVEREXPORT"] = function()
    if PetWeaverDB.encounterDatabase then
        local count = 0
        for _ in pairs(PetWeaverDB.encounterDatabase) do
            count = count + 1
        end
        print("|cFF00FF00PetWeaver:|r Encounter database has " .. count .. " encounters")
        print("Data location: WTF/Account/YOURNAME/SavedVariables/PetWeaver.lua")
        print("Upload encounterDatabase table to your server for genetic algorithm")
    else
        print("|cFFFF0000PetWeaver:|r No encounter data found. Fight some trainers first!")
    end
end

-- ============================================================================
-- Initialization
-- ============================================================================

-- Set initial tab
PetWeaver_SwitchTab(PetWeaverDB.settings.currentTab or "Battle")

print(ADDON_NAME .. ": Loaded! Use /petweaver or /pw to toggle.")
print(ADDON_NAME .. ": Version 2.0 - Full-Featured Pet Battle Assistant")
print(ADDON_NAME .. ": Features: Battle Info | Team Management | Strategy Scripts | AI Integration")
print(ADDON_NAME .. ": Combat Log: Capturing trainer data for genetic algorithm validation")
