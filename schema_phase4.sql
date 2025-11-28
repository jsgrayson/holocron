-- Phase 4 Schema Updates

-- LOGISTICS SCHEMA
CREATE TABLE IF NOT EXISTS holocron.logistics_jobs (
    job_id SERIAL PRIMARY KEY,
    source_char_guid VARCHAR(255) REFERENCES holocron.characters(character_guid),
    target_char_guid VARCHAR(255) REFERENCES holocron.characters(character_guid), -- Can be NULL if target is 'Auction House' (though usually an alt)
    item_id INT,
    count INT,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, COMPLETED, CANCELLED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookup by source character (who needs to send the mail)
CREATE INDEX idx_jobs_source ON holocron.logistics_jobs(source_char_guid);
