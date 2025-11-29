-- HolocronViewer.lua

local addonName, addon = ...
local HolocronDB = HolocronDB or {} -- Loaded from Holocron_Index.lua

local function OnTooltipSetItem(tooltip)
    local _, link = tooltip:GetItem()
    if not link then return end

    local itemID = GetItemInfoInstant(link)
    if not itemID then return end

    local data = HolocronDB[itemID]
    if data then
        tooltip:AddLine(" ")
        tooltip:AddLine("|cFF00FF00Holocron Inventory:|r " .. data.total)
        for loc, count in pairs(data.locations) do
            tooltip:AddLine("  " .. loc .. ": " .. count, 1, 1, 1)
        end
    end
end

TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, OnTooltipSetItem)

-- Mailbox Automation
local HolocronJobs = HolocronJobs or {}

local function ProcessNextJob()
    -- 1. Identify current character
    local playerName = UnitName("player")
    local realmName = GetRealmName()
    local charKey = playerName .. "-" .. realmName

    -- 2. Find jobs for this character
    local jobs = HolocronJobs[charKey]
    if not jobs or #jobs == 0 then
        print("|cFF00FF00Holocron:|r No pending jobs.")
        return
    end

    -- 3. Process first job
    local job = jobs[1]
    
    -- 4. Auto-fill Mail
    -- Note: We cannot click 'Send', only fill.
    SendMailNameEditBox:SetText(job.target)
    SendMailSubjectEditBox:SetText("Holocron Logistics: " .. job.itemID)
    
    -- 5. Find item in bags and pickup
    for bag = 0, 4 do
        for slot = 1, C_Container.GetContainerNumSlots(bag) do
            local itemID = C_Container.GetContainerItemID(bag, slot)
            if itemID == job.itemID then
                C_Container.PickupContainerItem(bag, slot)
                ClickSendMailItemButton()
                print("|cFF00FF00Holocron:|r Attached " .. job.count .. "x " .. job.itemID)
                return -- Only do one item per click for safety
            end
        end
    end
    print("|cFFFF0000Holocron:|r Item not found in bags!")
end

-- Create Button on MailFrame (Modern Style)
local btn = CreateFrame("Button", "HolocronProcessButton", MailFrame, "BackdropTemplate")
btn:SetSize(120, 25)
btn:SetPoint("TOPRIGHT", -50, -30)

btn:SetBackdrop({
    bgFile = "Interface\\Buttons\\WHITE8x8",
    edgeFile = "Interface\\Buttons\\WHITE8x8",
    tile = false, tileSize = 0, edgeSize = 1,
    insets = { left = 0, right = 0, top = 0, bottom = 0 }
})
btn:SetBackdropColor(0.2, 0.6, 1, 0.8) -- Blue
btn:SetBackdropBorderColor(0, 0, 0, 1)

btn.text = btn:CreateFontString(nil, "OVERLAY", "GameFontNormal")
btn.text:SetPoint("CENTER")
btn.text:SetText("Process Holocron")
btn.text:SetTextColor(1, 1, 1)

btn:SetScript("OnEnter", function(self) self:SetBackdropColor(0.3, 0.7, 1, 0.9) end)
btn:SetScript("OnLeave", function(self) self:SetBackdropColor(0.2, 0.6, 1, 0.8) end)
btn:SetScript("OnClick", ProcessNextJob)

