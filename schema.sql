-- Create Schemas
CREATE SCHEMA IF NOT EXISTS holocron;
CREATE SCHEMA IF NOT EXISTS goblin;
CREATE SCHEMA IF NOT EXISTS skillweaver;
CREATE SCHEMA IF NOT EXISTS petweaver;

-- Holocron Core Tables

-- Characters: Stores info about the player's characters
CREATE TABLE IF NOT EXISTS holocron.characters (
    character_guid VARCHAR(255) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    realm VARCHAR(100) NOT NULL,
    class VARCHAR(50),
    level INT,
    race VARCHAR(50),
    faction VARCHAR(20),
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Storage Locations: Bags, Banks, Guild Banks, etc.
CREATE TABLE IF NOT EXISTS holocron.storage_locations (
    location_id SERIAL PRIMARY KEY,
    character_guid VARCHAR(255) REFERENCES holocron.characters(character_guid),
    container_type VARCHAR(50) NOT NULL, -- 'Bag', 'Bank', 'ReagentBank', 'GuildBank', 'Mail'
    container_index INT, -- Bag ID or Tab ID
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Items: The master inventory table
CREATE TABLE IF NOT EXISTS holocron.items (
    item_guid VARCHAR(255) PRIMARY KEY, -- Unique instance ID if available, else generated
    item_id INT NOT NULL,
    name VARCHAR(255),
    count INT DEFAULT 1,
    location_id INT REFERENCES holocron.storage_locations(location_id),
    slot INT,
    quality INT,
    ilvl INT,
    class_id INT,
    subclass_id INT,
    texture VARCHAR(255),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster searching
CREATE INDEX idx_items_name ON holocron.items(name);
CREATE INDEX idx_items_item_id ON holocron.items(item_id);

-- SkillWeaver Tables

-- Profiles: Stores rotation profiles (e.g., Midnight, Balanced)
CREATE TABLE IF NOT EXISTS skillweaver.profiles (
    profile_id SERIAL PRIMARY KEY,
    class_id INT NOT NULL, -- WoW Class ID
    spec_id INT NOT NULL, -- WoW Spec ID
    profile_name VARCHAR(50) NOT NULL, -- 'Midnight', 'Balanced', 'HighPerformance'
    profile_type VARCHAR(20) NOT NULL, -- 'Priority', 'Sequence'
    content TEXT, -- JSON or Lua string of the profile
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(spec_id, profile_name)
);

-- Index for faster lookups
-- Index for faster lookups
CREATE INDEX idx_profiles_spec ON skillweaver.profiles(spec_id);

-- Gear: Equipped items
CREATE TABLE IF NOT EXISTS holocron.gear (
    character_guid VARCHAR(255) REFERENCES holocron.characters(character_guid),
    slot_id INT NOT NULL, -- 1=Head, 2=Neck, etc.
    item_id INT NOT NULL,
    item_level INT,
    item_link TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (character_guid, slot_id)
);

-- Professions: Skill levels
CREATE TABLE IF NOT EXISTS goblin.professions (
    character_guid VARCHAR(255) REFERENCES holocron.characters(character_guid),
    profession_id INT NOT NULL,
    profession_name VARCHAR(100),
    skill_level INT,
    max_skill INT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (character_guid, profession_id)
);

-- Recipes: Known recipes
CREATE TABLE IF NOT EXISTS goblin.recipes (
    character_guid VARCHAR(255) REFERENCES holocron.characters(character_guid),
    recipe_id INT NOT NULL,
    profession_id INT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (character_guid, recipe_id)
);
