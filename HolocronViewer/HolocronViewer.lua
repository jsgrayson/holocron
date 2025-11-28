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

-- Create Button on MailFrame
local btn = CreateFrame("Button", "HolocronProcessButton", MailFrame, "UIPanelButtonTemplate")
btn:SetSize(120, 25)
btn:SetPoint("TOPRIGHT", -50, -30)
btn:SetText("Process Holocron")
btn:SetScript("OnClick", ProcessNextJob)

